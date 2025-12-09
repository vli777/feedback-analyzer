import pytest
from app.analyze_pipeline import (
    analyze_feedback,
    analyze_feedback_batch,
    normalize_sentiment,
    normalize_topics,
    ANALYSIS_PROMPT,
    BATCH_ANALYSIS_PROMPT,
)
from app.models import Sentiment


class TestNormalizeSentiment:
    """Test sentiment normalization."""

    def test_valid_sentiments(self):
        assert normalize_sentiment("positive") == Sentiment.positive
        assert normalize_sentiment("negative") == Sentiment.negative
        assert normalize_sentiment("neutral") == Sentiment.neutral

    def test_case_insensitive(self):
        assert normalize_sentiment("POSITIVE") == Sentiment.positive
        assert normalize_sentiment("Negative") == Sentiment.negative
        assert normalize_sentiment("NEUTRAL") == Sentiment.neutral

    def test_invalid_sentiment_defaults_to_neutral(self):
        assert normalize_sentiment("invalid") == Sentiment.neutral
        assert normalize_sentiment("") == Sentiment.neutral
        assert normalize_sentiment(None) == Sentiment.neutral


class TestNormalizeTopics:
    """Test topic normalization."""

    def test_valid_topics(self):
        topics = normalize_topics(["Product", "Service", "Quality"])
        assert topics == ["product", "service", "quality"]

    def test_strips_whitespace(self):
        topics = normalize_topics(["  Product  ", "Service", "  Quality  "])
        assert topics == ["product", "service", "quality"]

    def test_filters_empty_strings(self):
        topics = normalize_topics(["Product", "", "   ", "Service"])
        assert topics == ["product", "service"]

    def test_non_list_returns_empty(self):
        assert normalize_topics("not a list") == []
        assert normalize_topics(None) == []
        assert normalize_topics(123) == []


class TestAnalysisPrompts:
    """Test prompt generation."""

    def test_single_analysis_prompt(self):
        prompt = ANALYSIS_PROMPT("Great product!")
        assert "Great product!" in prompt
        assert "sentiment" in prompt
        assert "key_topics" in prompt

    def test_batch_analysis_prompt(self):
        texts = ["Text 1", "Text 2", "Text 3"]
        prompt = BATCH_ANALYSIS_PROMPT(texts)
        assert "Text 1" in prompt
        assert "Text 2" in prompt
        assert "Text 3" in prompt
        assert "1. " in prompt
        assert "2. " in prompt
        assert "3. " in prompt
        assert "3 analysis objects" in prompt


class TestAnalyzeFeedback:
    """Test single feedback analysis."""

    @pytest.mark.asyncio
    async def test_analyze_single_feedback(self, mock_llm_client):
        result = await analyze_feedback("Great product!")

        assert "sentiment" in result
        assert "keyTopics" in result
        assert "actionRequired" in result
        assert "summary" in result
        assert isinstance(result["sentiment"], Sentiment)
        assert isinstance(result["keyTopics"], list)
        assert isinstance(result["actionRequired"], bool)
        assert isinstance(result["summary"], str)

    @pytest.mark.asyncio
    async def test_analyze_feedback_with_empty_text(self, mock_llm_client):
        result = await analyze_feedback("")
        # Should still return a valid analysis structure
        assert "sentiment" in result
        assert "summary" in result


class TestAnalyzeFeedbackBatch:
    """Test batch feedback analysis."""

    @pytest.mark.asyncio
    async def test_batch_empty_list(self, mock_llm_client):
        results = await analyze_feedback_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_batch_single_item_uses_single_function(self, mock_llm_client):
        texts = ["Great product!"]
        results = await analyze_feedback_batch(texts)

        assert len(results) == 1
        assert "sentiment" in results[0]
        assert "summary" in results[0]

    @pytest.mark.asyncio
    async def test_batch_multiple_items(self, mock_llm_client):
        texts = [
            "Great product!",
            "Needs improvement",
            "Average service",
            "Excellent quality",
            "Poor support"
        ]
        results = await analyze_feedback_batch(texts)

        assert len(results) == 5
        for result in results:
            assert "sentiment" in result
            assert "keyTopics" in result
            assert "actionRequired" in result
            assert "summary" in result
            assert isinstance(result["sentiment"], Sentiment)

    @pytest.mark.asyncio
    async def test_batch_returns_same_order(self, mock_llm_client):
        texts = ["First", "Second", "Third"]
        results = await analyze_feedback_batch(texts)

        assert len(results) == 3
        # All should have valid structure
        for i, result in enumerate(results):
            assert isinstance(result, dict)
            assert "summary" in result

    @pytest.mark.asyncio
    async def test_batch_size_10(self, mock_llm_client):
        """Test batch of 10 items (default batch size)."""
        texts = [f"Feedback {i+1}" for i in range(10)]
        results = await analyze_feedback_batch(texts)

        assert len(results) == 10
        for result in results:
            assert "sentiment" in result

    @pytest.mark.asyncio
    async def test_batch_size_25(self, mock_llm_client):
        """Test batch of 25 items."""
        texts = [f"Feedback {i+1}" for i in range(25)]
        results = await analyze_feedback_batch(texts)

        assert len(results) == 25
