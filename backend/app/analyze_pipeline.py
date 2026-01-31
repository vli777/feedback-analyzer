import asyncio

from .llm_client import base_client
from .models import Sentiment, FeedbackAnalysis, BatchFeedbackAnalysis


def ANALYSIS_PROMPT(feedback: str) -> str:
    return f"""You are analyzing user feedback.

Analyze the sentiment, identify key topics, determine if action is required, and provide a summary.

IMPORTANT: The summary must be a complete, natural language sentence or phrase (about at least 5-7 words), not just 1-3 words.

Feedback:
\"\"\"{feedback}\"\"\"""".strip()


def BATCH_ANALYSIS_PROMPT(feedbacks: list[str]) -> str:
    feedback_items = "\n".join(
        [f'{i+1}. "{text}"' for i, text in enumerate(feedbacks)]
    )
    return f"""You are analyzing user feedback.

Analyze these {len(feedbacks)} feedback entries in the EXACT same order:

{feedback_items}

For each feedback, analyze the sentiment, identify key topics, determine if action is required, and provide a summary.

IMPORTANT: Each summary must be a complete, natural language sentence or phrase (about at least 5-7 words), not just 1-3 words.""".strip()


def normalize_topics(raw):
    """Normalize topic strings to lowercase and filter empty values"""
    if not isinstance(raw, list):
        return []
    return [str(t).strip().lower() for t in raw if str(t).strip()]


async def analyze_feedback(text: str) -> dict:
    try:
        # Create structured output client with Pydantic model
        structured_client = base_client.with_structured_output(FeedbackAnalysis)

        # Invoke with structured output - returns FeedbackAnalysis instance
        result: FeedbackAnalysis = await asyncio.to_thread(
            structured_client.invoke, ANALYSIS_PROMPT(text)
        )

        return {
            "sentiment": result.sentiment,
            "keyTopics": normalize_topics(result.key_topics),
            "actionRequired": result.action_required,
            "summary": result.summary or "No summary provided.",
        }
    except Exception as e:
        # Fallback in case of API error
        return {
            "sentiment": Sentiment.neutral,
            "keyTopics": ["error"],
            "actionRequired": True,
            "summary": f"Error analyzing feedback: {str(e)}",
        }


async def analyze_feedback_batch(texts: list[str]) -> list[dict]:
    """
    Analyze multiple feedback texts in a single LLM call.

    Args:
        texts: List of feedback text strings to analyze

    Returns:
        List of analysis dicts, one per input text in the same order
    """
    if not texts:
        return []

    # If only one text, use the single-item function
    if len(texts) == 1:
        return [await analyze_feedback(texts[0])]

    # Create structured output client with Pydantic model for batch analysis
    structured_client = base_client.with_structured_output(BatchFeedbackAnalysis)

    # Invoke with structured output - returns BatchFeedbackAnalysis instance
    result: BatchFeedbackAnalysis = await asyncio.to_thread(
        structured_client.invoke, BATCH_ANALYSIS_PROMPT(texts)
    )

    # Validate response structure
    if len(result.analyses) != len(texts):
        raise ValueError(f"Expected {len(texts)} results, got {len(result.analyses)}")

    # Normalize each result and convert to dict format
    results = []
    for analysis in result.analyses:
        results.append({
            "sentiment": analysis.sentiment,
            "keyTopics": normalize_topics(analysis.key_topics),
            "actionRequired": analysis.action_required,
            "summary": analysis.summary or "No summary provided.",
        })

    return results
