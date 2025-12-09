import io
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_llm_client(monkeypatch):
    """Mock the LLM client to avoid actual API calls during tests."""
    mock_client = Mock()

    def mock_stream(messages):
        """Mock streaming response with valid JSON."""
        content = messages[0]["content"]

        # Check if it's a batch request (contains numbered list)
        if "1. " in content and "2. " in content:
            # Count number of items in batch
            num_items = content.count('"""') // 2
            # Return array of analyses
            response = [
                {
                    "sentiment": "positive",
                    "key_topics": ["test", "batch"],
                    "action_required": False,
                    "summary": f"Test feedback {i+1} analysis"
                }
                for i in range(num_items)
            ]
            response_json = json.dumps(response)
        else:
            # Single item analysis
            response_json = json.dumps({
                "sentiment": "positive",
                "key_topics": ["test", "feedback"],
                "action_required": False,
                "summary": "Test feedback analysis"
            })

        # Return mock chunks that simulate streaming
        chunk = Mock()
        chunk.content = response_json
        return [chunk]

    mock_client.stream = mock_stream

    # Patch the client in the analyze_pipeline module
    monkeypatch.setattr("app.analyze_pipeline.client", mock_client)
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
