from datetime import datetime, timedelta, timezone
from collections import defaultdict
from .models import FeedbackRecord, Sentiment


def compute_metrics(records: list[FeedbackRecord]):
    now = datetime.now(timezone.utc)
    sentimentDistribution = {
        "positive": 0,
        "neutral": 0,
        "negative": 0,
    }

    topicCounts = {}

    window_minutes = 60
    bucket_minutes = 5
    bucket_count = window_minutes // bucket_minutes

    def _as_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _floor_bucket(dt: datetime) -> datetime:
        dt = dt.replace(second=0, microsecond=0)
        minute_offset = dt.minute % bucket_minutes
        return dt - timedelta(minutes=minute_offset)

    window_end = _floor_bucket(now)
    window_start = window_end - timedelta(minutes=(bucket_count - 1) * bucket_minutes)

    buckets = [
        {
            "bucket": (window_start + timedelta(minutes=i * bucket_minutes)).strftime("%H:%M"),
            "count": 0,
            "positive": 0,
            "neutral": 0,
            "negative": 0,
        }
        for i in range(bucket_count)
    ]

    for r in records:
        sentimentDistribution[r.sentiment.value] += 1
        created_at = _as_utc(r.createdAt)
        if window_start <= created_at <= window_end + timedelta(minutes=bucket_minutes):
            idx = int((created_at - window_start).total_seconds() // (bucket_minutes * 60))
            if 0 <= idx < bucket_count:
                buckets[idx]["count"] += 1
                buckets[idx][r.sentiment.value] += 1

        for t in r.keyTopics:
            topicCounts[t] = topicCounts.get(t, 0) + 1

    submissionsByTime = buckets

    topTopics = sorted(
        [{"topic": t, "count": c} for t, c in topicCounts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    # Compute topic trends over time
    topicTrends = compute_topic_trends(records, top_k=5)

    return {
        "sentimentDistribution": sentimentDistribution,
        "submissionsByTime": submissionsByTime,
        "topTopics": topTopics,
        "topicTrends": topicTrends,
    }


def compute_topic_trends(records: list[FeedbackRecord], top_k: int = 5):
    """Compute time-series data for top K topics."""
    if not records:
        return []

    # First, find the top K topics overall
    topicCounts = {}
    for r in records:
        for t in r.keyTopics:
            topicCounts[t] = topicCounts.get(t, 0) + 1

    topTopics = sorted(topicCounts.items(), key=lambda x: x[1], reverse=True)[:top_k]
    topTopicNames = [t[0] for t in topTopics]

    if not topTopicNames:
        return []

    # Group records by date
    dateTopicCounts = defaultdict(lambda: defaultdict(int))

    for r in records:
        date_key = r.createdAt.date().isoformat()
        for t in r.keyTopics:
            if t in topTopicNames:
                dateTopicCounts[date_key][t] += 1

    # Get date range
    dates = sorted(dateTopicCounts.keys())
    if not dates:
        return []

    # Build time series data
    result = []
    for date_key in dates:
        data_point = {"date": date_key}
        for topic in topTopicNames:
            data_point[topic] = dateTopicCounts[date_key].get(topic, 0)
        result.append(data_point)

    return result
