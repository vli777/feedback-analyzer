from enum import Enum
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class Sentiment(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


# Pydantic models for LLM structured outputs
class FeedbackAnalysis(BaseModel):
    """Structured output model for single feedback analysis"""
    sentiment: Sentiment
    key_topics: List[str] = Field(description="Key topics or themes identified in the feedback")
    action_required: bool = Field(description="Whether this feedback requires follow-up action")
    summary: str = Field(description="A complete sentence or natural language phrase (about at least 5-7 words) summarizing the feedback")


class BatchFeedbackAnalysis(BaseModel):
    """Structured output model for batch feedback analysis"""
    analyses: List[FeedbackAnalysis] = Field(description="List of feedback analyses in the same order as input")


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
                "analyzedAt"
                "analyze_status"
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


class TimeBucketCount(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bucket": "14:05",
                "count": 5,
                "positive": 2,
                "neutral": 2,
                "negative": 1,
            }
        }
    )

    bucket: str
    count: int
    positive: int
    neutral: int
    negative: int


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
                ],
                "topicTrends": [
                    {"date": "2025-11-24", "doctor": 5, "wait time": 3},
                    {"date": "2025-11-25", "doctor": 7, "wait time": 5}
                ]
            }
        }
    )

    sentimentDistribution: dict[str, int]
    submissionsByTime: list[TimeBucketCount]
    topTopics: list[TopicCount]
    topicTrends: list[dict]
