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
from .storage import read_all_feedback, append_feedback
from .analyze_pipeline import analyze_feedback, analyze_feedback_batch
from .metrics import compute_metrics
from .bulk_upload import parse_bulk_file, parse_created_at, make_record_id
from .config import BULK_RATE_LIMIT_RPM, BULK_BATCH_SIZE

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
):
    """
    Bulk upload feedback for analysis.

    Processes items in batches with a configurable delay to respect rate limits.
    Each batch sends multiple items in a single LLM call for better throughput.
    """
    effective_rpm = rate_limit_rpm or BULK_RATE_LIMIT_RPM
    effective_batch_size = batch_size or BULK_BATCH_SIZE

    if effective_rpm and effective_rpm > 0:
        delay_seconds = max(60.0 / effective_rpm, 0.1)
    else:
        delay_seconds = 2.0

    content = await file.read()
    items = parse_bulk_file(file, content)
    results = {"total": len(items), "success": [], "failed": [], "batches": 0}

    # Process items in batches
    for batch_idx in range(0, len(items), effective_batch_size):
        batch = items[batch_idx:batch_idx + effective_batch_size]
        results["batches"] += 1

        # Prepare batch data
        batch_texts = []
        batch_metadata = []

        for idx, item in enumerate(batch):
            global_idx = batch_idx + idx
            text = str(item.get("text") or "").strip()

            if not text:
                results["failed"].append({"index": global_idx, "error": "Missing text"})
                batch_texts.append(None)
                batch_metadata.append(None)
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

        # Filter out None entries (items with missing text)
        valid_texts = [t for t in batch_texts if t is not None]
        valid_metadata = [m for m in batch_metadata if m is not None]

        if not valid_texts:
            continue

        # Batch analysis
        try:
            analyses = await analyze_feedback_batch(valid_texts)

            # Create records from batch results
            for metadata, analysis in zip(valid_metadata, analyses):
                try:
                    record = FeedbackRecord(
                        id=make_record_id(metadata["item"]),
                        text=valid_texts[valid_metadata.index(metadata)],
                        userId=metadata["userId"],
                        sentiment=analysis["sentiment"],
                        keyTopics=analysis["keyTopics"],
                        actionRequired=analysis["actionRequired"],
                        summary=analysis["summary"],
                        createdAt=metadata["createdAt"],
                    )
                    append_feedback(record)
                    results["success"].append({"index": metadata["index"], "id": record.id})
                except Exception as e:
                    results["failed"].append({"index": metadata["index"], "error": str(e)})

        except Exception as e:
            # If batch analysis fails, mark all items in batch as failed
            for metadata in valid_metadata:
                results["failed"].append({"index": metadata["index"], "error": f"Batch error: {str(e)}"})

        # Rate limiting delay between batches (not after the last batch)
        if delay_seconds and batch_idx + effective_batch_size < len(items):
            await asyncio.sleep(delay_seconds)

    results["rateLimitRpm"] = effective_rpm
    results["batchSize"] = effective_batch_size
    results["delaySeconds"] = delay_seconds
    return results