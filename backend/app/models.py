from enum import Enum
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Sentiment(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class FeedbackRecord(BaseModel):
    id: str
    text: str
    userId: Optional[str] = None
    sentiment: Sentiment
    keyTopics: List[str] = Field(default_factory=list)
    actionRequired: bool
    summary: str
    createdAt: datetime


class FeedbackCreateRequest(BaseModel):
    text: str
    userId: Optional[str] = None


class FeedbackCreateResponse(BaseModel):
    record: FeedbackRecord


class HistoryItem(BaseModel):
    id: str
    userId: Optional[str]
    summary: str
    createdAt: datetime
    sentiment: Sentiment
