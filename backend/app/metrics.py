from datetime import datetime, timedelta
from collections import defaultdict
from .models import FeedbackRecord, Sentiment


def compute_metrics(records: list[FeedbackRecord]):
    sentimentDistribution = {
        "positive": 0,
        "neutral": 0,
        "negative": 0,
    }

    hourBuckets = [0] * 24
    topicCounts = {}

    for r in records:
        sentimentDistribution[r.sentiment.value] += 1
        hourBuckets[r.createdAt.hour] += 1

        for t in r.keyTopics:
            topicCounts[t] = topicCounts.get(t, 0) + 1

    submissionsByHour = [
        {"hour": h, "count": c} for h, c in enumerate(hourBuckets)
    ]

    topTopics = sorted(
        [{"topic": t, "count": c} for t, c in topicCounts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    # Compute topic trends over time
    topicTrends = compute_topic_trends(records, top_k=5)

    return {
        "sentimentDistribution": sentimentDistribution,
        "submissionsByHour": submissionsByHour,
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
