import io
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_llm_client(monkeypatch):
    """Mock the LLM client to avoid actual API calls during tests."""
    from app.models import FeedbackAnalysis, BatchFeedbackAnalysis, Sentiment

    def _make_single():
        return FeedbackAnalysis(
            sentiment=Sentiment.positive,
            key_topics=["test", "feedback"],
            action_required=False,
            summary="Test feedback analysis summary result",
        )

    class _StructuredSingle:
        def invoke(self, prompt):
            return _make_single()

    class _StructuredBatch:
        def invoke(self, prompt):
            # Count numbered items in the prompt (e.g. '1. "...' , '2. "...')
            import re
            num_items = len(re.findall(r'^\d+\.\s+"', prompt, re.MULTILINE))
            num_items = max(num_items, 1)
            return BatchFeedbackAnalysis(
                analyses=[
                    FeedbackAnalysis(
                        sentiment=Sentiment.positive,
                        key_topics=["test", "batch"],
                        action_required=False,
                        summary=f"Test feedback {i+1} analysis result",
                    )
                    for i in range(num_items)
                ]
            )

    mock_client = Mock()

    def _with_structured_output(model_cls):
        if model_cls is BatchFeedbackAnalysis:
            return _StructuredBatch()
        return _StructuredSingle()

    mock_client.with_structured_output = _with_structured_output

    monkeypatch.setattr("app.analyze_pipeline.base_client", mock_client)
    return mock_client


@pytest.fixture
def mock_storage(monkeypatch, tmp_path):
    """Mock storage to use temporary file instead of real data file."""
    from pathlib import Path
    storage_file = tmp_path / "feedback.json"
    storage_file.write_text("[]")

    monkeypatch.setattr("app.storage.FILE_PATH", Path(storage_file))
    return storage_file


@pytest.fixture
def test_client(mock_llm_client, mock_storage):
    """Create a test client for the FastAPI app."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def sample_csv_file():
    """Create a sample CSV file for testing."""
    csv_content = """text,userId
"Great product, love it!",user123
"Needs improvement in speed",user456
"Customer service was excellent",user789"""

    return io.BytesIO(csv_content.encode("utf-8"))


@pytest.fixture
def sample_json_file():
    """Create a sample JSON file for testing."""
    json_content = [
        {"text": "Great product, love it!", "userId": "user123"},
        {"text": "Needs improvement in speed", "userId": "user456"},
        {"text": "Customer service was excellent", "userId": "user789"}
    ]

    return io.BytesIO(json.dumps(json_content).encode("utf-8"))


@pytest.fixture
def large_csv_file():
    """Create a large CSV file for batch testing (25 items)."""
    lines = ["text,userId"]
    for i in range(25):
        lines.append(f'"Test feedback item {i+1}",user{i+1}')

    csv_content = "\n".join(lines)
    return io.BytesIO(csv_content.encode("utf-8"))


@pytest.fixture
def sample_feedback_texts():
    """Sample feedback texts for testing batch analysis."""
    return [
        "The service was amazing!",
        "Product arrived damaged.",
        "Average experience, nothing special.",
        "Exceeded my expectations!",
        "Terrible customer support."
    ]
