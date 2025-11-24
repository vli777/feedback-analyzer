import uuid
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException
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
from .analyze_pipeline import analyze_feedback
from .metrics import compute_metrics

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