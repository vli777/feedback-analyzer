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

    return {
        "sentimentDistribution": sentimentDistribution,
        "submissionsByHour": submissionsByHour,
        "topTopics": topTopics,
    }
