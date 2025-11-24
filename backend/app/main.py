import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .models import (
    FeedbackCreateRequest,
    FeedbackCreateResponse,
    FeedbackRecord,
    HistoryItem,
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


@app.get("/api/v1/history")
def history():
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


@app.get("/api/v1/metrics")
def metrics():
    return compute_metrics(read_all_feedback())