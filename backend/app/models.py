from enum import Enum
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class Sentiment(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class FeedbackRecord(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "text": "The doctor was very helpful and attentive during my visit.",
                "userId": "user123",
                "sentiment": "positive",
                "keyTopics": ["doctor", "attentive", "helpful"],
                "actionRequired": False,
                "summary": "Patient praises doctor's attentiveness",
                "createdAt": "2025-11-24T10:30:00Z"
            }
        }
    )

    id: str
    text: str
    userId: Optional[str] = None
    sentiment: Sentiment
    keyTopics: List[str] = Field(default_factory=list)
    actionRequired: bool
    summary: str
    createdAt: datetime


class FeedbackCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "The doctor was very helpful and attentive during my visit.",
                "userId": "user123"
            }
        }
    )

    text: str
    userId: Optional[str] = None


class FeedbackCreateResponse(BaseModel):
    record: FeedbackRecord


class HistoryItem(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "userId": "user123",
                "summary": "Patient praises doctor's attentiveness",
                "createdAt": "2025-11-24T10:30:00Z",
                "sentiment": "positive"
            }
        }
    )

    id: str
    userId: Optional[str]
    summary: str
    createdAt: datetime
    sentiment: Sentiment


class HourCount(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "hour": 14,
                "count": 5
            }
        }
    )

    hour: int
    count: int


class TopicCount(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "topic": "doctor",
                "count": 12
            }
        }
    )

    topic: str
    count: int


class Metrics(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sentimentDistribution": {
                    "positive": 10,
                    "neutral": 5,
                    "negative": 2
                },
                "submissionsByHour": [
                    {"hour": 9, "count": 3},
                    {"hour": 14, "count": 5}
                ],
                "topTopics": [
                    {"topic": "doctor", "count": 12},
                    {"topic": "wait time", "count": 8}
                ]
            }
        }
    )

    sentimentDistribution: dict[str, int]
    submissionsByHour: list[HourCount]
    topTopics: list[TopicCount]
