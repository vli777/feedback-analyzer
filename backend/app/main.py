import asyncio
import uuid
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

load_dotenv()

from .models import (
    FeedbackCreateRequest,
    FeedbackCreateResponse,
    FeedbackRecord,
    HistoryItem,
    Metrics,
)
from .storage import read_all_feedback, append_feedback, append_feedback_many
from .analyze_pipeline import analyze_feedback, analyze_feedback_batch
from .metrics import compute_metrics
from .bulk_upload import parse_bulk_file, parse_created_at, make_record_id
from .config import BULK_RATE_LIMIT_RPM, BULK_BATCH_SIZE, BULK_MAX_CONCURRENCY

app = FastAPI(
    title="Feedback Analyzer API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
def read_root():
    return RedirectResponse(url="/docs")

@app.post("/api/v1/feedback", response_model=FeedbackCreateResponse)
async def create_feedback(payload: FeedbackCreateRequest):
    """
    Submit feedback for AI analysis.

    Analyzes the submitted feedback text using an LLM to extract:
    - Sentiment (positive/neutral/negative)
    - Key topics mentioned
    - Whether action is required
    - A concise summary

    The analyzed feedback is stored and returned with a unique ID.
    """
    text = payload.text.strip()
    if not text:
        raise HTTPException(400, "Text required")

    analysis = await analyze_feedback(text)

    record = FeedbackRecord(
        id=str(uuid.uuid4()),
        text=text,
        userId=payload.userId,
        sentiment=analysis["sentiment"],
        keyTopics=analysis["keyTopics"],
        actionRequired=analysis["actionRequired"],
        summary=analysis["summary"],
        createdAt=datetime.utcnow(),        
    )

    append_feedback(record)
    return {"record": record}


@app.get("/api/v1/history", response_model=List[HistoryItem])
def history():
    """
    Get all feedback submissions.

    Returns a list of all submitted feedback entries sorted by creation date
    (newest first). Each entry includes the ID, summary, timestamp, and sentiment.
    """
    records = read_all_feedback()
    sorted_records = sorted(records, key=lambda r: r.createdAt, reverse=True)
    return [
        HistoryItem(
            id=r.id,
            userId=r.userId,
            summary=r.summary,
            createdAt=r.createdAt,
            sentiment=r.sentiment,
        )
        for r in sorted_records
    ]


@app.get("/api/v1/metrics", response_model=Metrics)
def metrics():
    """
    Get analytics metrics across all feedback.

    Returns aggregated metrics including:
    - **Sentiment Distribution**: Count of positive/neutral/negative feedback
    - **Submissions by Hour**: 24-hour breakdown of when feedback was submitted
    - **Top Topics**: Most frequently mentioned topics across all feedback
    """
    return compute_metrics(read_all_feedback())


@app.post("/api/v1/feedback/bulk")
async def bulk_upload(
    file: UploadFile = File(...),
    rate_limit_rpm: float | None = Query(None, ge=0, description="Overrides default RPM (default 30)"),
    batch_size: int | None = Query(None, ge=1, le=50, description="Items per batch (default 10)"),
    max_concurrency: int | None = Query(None, ge=1, le=10, description="Max parallel batches (default 4)"),
):
    """
    Bulk upload feedback for analysis.

    Processes items in batch-parallel: batches are dispatched concurrently via
    asyncio.gather, bounded by a semaphore (max_concurrency). Starts are
    staggered by delay_seconds to respect API rate limits.
    """
    effective_rpm = rate_limit_rpm or BULK_RATE_LIMIT_RPM
    effective_batch_size = batch_size or BULK_BATCH_SIZE
    effective_concurrency = max_concurrency or BULK_MAX_CONCURRENCY

    if effective_rpm and effective_rpm > 0:
        delay_seconds = max(60.0 / effective_rpm, 0.1)
    else:
        delay_seconds = 2.0

    content = await file.read()
    items = parse_bulk_file(file, content)

    # ── Phase 1: prepare all batches ──────────────────────────────────
    prepared_batches = []
    prep_failures = []

    for batch_idx in range(0, len(items), effective_batch_size):
        batch = items[batch_idx:batch_idx + effective_batch_size]

        batch_texts = []
        batch_metadata = []

        for idx, item in enumerate(batch):
            global_idx = batch_idx + idx
            text = str(item.get("text") or "").strip()

            if not text:
                prep_failures.append({"index": global_idx, "error": "Missing text"})
                continue

            user_id = item.get("userId") or item.get("user_id") or item.get("user")
            created_at_raw = item.get("createdAt") or item.get("created_at")
            created_at = parse_created_at(created_at_raw) if created_at_raw else datetime.utcnow()

            batch_texts.append(text)
            batch_metadata.append({
                "index": global_idx,
                "item": item,
                "userId": str(user_id) if user_id is not None else None,
                "createdAt": created_at,
            })

        if batch_texts:
            prepared_batches.append({"texts": batch_texts, "metadata": batch_metadata})

    # ── Phase 2: process batches in parallel ──────────────────────────
    semaphore = asyncio.Semaphore(effective_concurrency)

    async def _process_batch(batch_info, batch_number):
        # Stagger starts to respect rate limits
        if delay_seconds and batch_number > 0:
            await asyncio.sleep(delay_seconds * batch_number)

        async with semaphore:
            try:
                analyses = await analyze_feedback_batch(batch_info["texts"])
                return {
                    "ok": True,
                    "texts": batch_info["texts"],
                    "metadata": batch_info["metadata"],
                    "analyses": analyses,
                }
            except Exception as e:
                return {
                    "ok": False,
                    "metadata": batch_info["metadata"],
                    "error": str(e),
                }

    batch_results = await asyncio.gather(
        *[_process_batch(b, i) for i, b in enumerate(prepared_batches)]
    )

    # ── Phase 3: collect results & persist ────────────────────────────
    results = {
        "total": len(items),
        "success": [],
        "failed": list(prep_failures),
        "batches": len(prepared_batches),
    }
    all_records = []

    for br in batch_results:
        if br["ok"]:
            for meta, analysis in zip(br["metadata"], br["analyses"]):
                try:
                    text_idx = br["metadata"].index(meta)
                    record = FeedbackRecord(
                        id=make_record_id(meta["item"]),
                        text=br["texts"][text_idx],
                        userId=meta["userId"],
                        sentiment=analysis["sentiment"],
                        keyTopics=analysis["keyTopics"],
                        actionRequired=analysis["actionRequired"],
                        summary=analysis["summary"],
                        createdAt=meta["createdAt"],
                    )
                    all_records.append(record)
                    results["success"].append({"index": meta["index"], "id": record.id})
                except Exception as e:
                    results["failed"].append({"index": meta["index"], "error": str(e)})
        else:
            for meta in br["metadata"]:
                results["failed"].append({"index": meta["index"], "error": f"Batch error: {br['error']}"})

    if all_records:
        append_feedback_many(all_records)

    results["rateLimitRpm"] = effective_rpm
    results["batchSize"] = effective_batch_size
    results["maxConcurrency"] = effective_concurrency
    results["delaySeconds"] = delay_seconds
    return results