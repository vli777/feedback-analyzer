import json
from .llm_client import client
from .models import Sentiment


def ANALYSIS_PROMPT(feedback: str) -> str:
    return f"""
You are analyzing user feedback.

Return ONLY valid JSON with exactly this structure:

{{
  "sentiment": "positive" | "neutral" | "negative",
  "key_topics": ["topic1", "topic2"],
  "action_required": boolean,
  "summary": "short summary"
}}

Feedback:
\"\"\"{feedback}\"\"\"
""".strip()


def normalize_sentiment(x) -> Sentiment:
    low = str(x or "").lower()
    if low in ("positive", "negative", "neutral"):
        return Sentiment(low)
    return Sentiment.neutral


def normalize_topics(raw):
    if not isinstance(raw, list):
        return []
    return [str(t).strip().lower() for t in raw if str(t).strip()]


async def analyze_feedback(text: str) -> dict:
    try:
        # Using NVIDIA responses API
        response = client.responses.create(
            model="openai/gpt-oss-20b",
            input=ANALYSIS_PROMPT(text),
            max_output_tokens=512,
            temperature=0.2,
            top_p=0.7,
            stream=True
        )

        # Collect output from streaming response
        output_text = ""
        for chunk in response:
            if chunk.type == "response.output_text.delta":
                output_text += chunk.delta

        output = output_text.strip()

        try:
            parsed = json.loads(output)
        except Exception:
            parsed = {
                "sentiment": "neutral",
                "key_topics": [],
                "action_required": False,
                "summary": "Model returned invalid JSON.",
            }

        return {
            "sentiment": normalize_sentiment(parsed.get("sentiment")),
            "keyTopics": normalize_topics(parsed.get("key_topics")),
            "actionRequired": bool(parsed.get("action_required")),
            "summary": parsed.get("summary") or "No summary provided.",
        }
    except Exception as e:
        # Fallback in case of API error
        return {
            "sentiment": Sentiment.neutral,
            "keyTopics": ["error"],
            "actionRequired": True,
            "summary": f"Error analyzing feedback: {str(e)}",
        }
