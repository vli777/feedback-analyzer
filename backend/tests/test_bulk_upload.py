import io
import json
import pytest
from app.bulk_upload import parse_bulk_file, make_record_id, parse_created_at
from datetime import datetime
from fastapi import UploadFile


class TestParseBulkFile:
    """Test file parsing utilities."""

    def test_parse_json_array(self):
        content = json.dumps([
            {"text": "Item 1", "userId": "user1"},
            {"text": "Item 2", "userId": "user2"}
        ]).encode("utf-8")

        upload = UploadFile(filename="test.json", file=io.BytesIO(content))
        items = parse_bulk_file(upload, content)

        assert len(items) == 2
        assert items[0]["text"] == "Item 1"
        assert items[1]["userId"] == "user2"

    def test_parse_json_object_with_items(self):
        content = json.dumps({
            "items": [
                {"text": "Item 1"},
                {"text": "Item 2"}
            ]
        }).encode("utf-8")

        upload = UploadFile(filename="test.json", file=io.BytesIO(content))
        items = parse_bulk_file(upload, content)

        assert len(items) == 2

    def test_parse_csv(self):
        content = b"text,userId\nItem 1,user1\nItem 2,user2"

        upload = UploadFile(filename="test.csv", file=io.BytesIO(content))
        items = parse_bulk_file(upload, content)

        assert len(items) == 2
        assert items[0]["text"] == "Item 1"
        assert items[1]["userId"] == "user2"

    def test_empty_file_raises_error(self):
        upload = UploadFile(filename="test.json", file=io.BytesIO(b""))

        with pytest.raises(Exception):
            parse_bulk_file(upload, b"")


class TestMakeRecordId:
    """Test record ID generation."""

    def test_uses_existing_id(self):
        item = {"id": "custom-id-123"}
        record_id = make_record_id(item)
        assert record_id == "custom-id-123"

    def test_generates_uuid_when_no_id(self):
        item = {"text": "No ID"}
        record_id = make_record_id(item)
        assert len(record_id) > 0
        # Should be a valid UUID format
        assert "-" in record_id


class TestParseCreatedAt:
    """Test timestamp parsing."""

    def test_parse_iso_format(self):
        iso_string = "2025-11-24T10:30:00Z"
        result = parse_created_at(iso_string)
        assert isinstance(result, datetime)

    def test_invalid_format_returns_current_time(self):
        result = parse_created_at("invalid-date")
        assert isinstance(result, datetime)
        # Should be close to now
        assert (datetime.utcnow() - result).total_seconds() < 5


class TestBulkUploadEndpoint:
    """Test the bulk upload API endpoint with batching."""

    def test_bulk_upload_csv_default_batch(self, test_client, sample_csv_file):
        """Test bulk upload with default batch size (10)."""
        response = test_client.post(
            "/api/v1/feedback/bulk",
            files={"file": ("test.csv", sample_csv_file, "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 3
        assert len(data["success"]) == 3
        assert len(data["failed"]) == 0
        assert data["batchSize"] == 10
        assert data["batches"] == 1  # 3 items in 1 batch

    def test_bulk_upload_json(self, test_client, sample_json_file):
        """Test bulk upload with JSON file."""
        response = test_client.post(
            "/api/v1/feedback/bulk",
            files={"file": ("test.json", sample_json_file, "application/json")}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 3
        assert len(data["success"]) == 3
        assert data["batches"] == 1

    def test_bulk_upload_large_file_multiple_batches(self, test_client, large_csv_file):
        """Test bulk upload with 25 items creates 3 batches (10, 10, 5)."""
        response = test_client.post(
            "/api/v1/feedback/bulk",
            files={"file": ("large.csv", large_csv_file, "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 25
        assert len(data["success"]) == 25
        assert data["batchSize"] == 10
        assert data["batches"] == 3  # 25 items / 10 per batch = 3 batches

    def test_bulk_upload_custom_batch_size(self, test_client, large_csv_file):
        """Test bulk upload with custom batch size."""
        response = test_client.post(
            "/api/v1/feedback/bulk?batch_size=5",
            files={"file": ("large.csv", large_csv_file, "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 25
        assert data["batchSize"] == 5
        assert data["batches"] == 5  # 25 items / 5 per batch = 5 batches

    def test_bulk_upload_custom_rpm(self, test_client, sample_csv_file):
        """Test bulk upload with custom rate limit."""
        response = test_client.post(
            "/api/v1/feedback/bulk?rate_limit_rpm=20",
            files={"file": ("test.csv", sample_csv_file, "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["rateLimitRpm"] == 20
        assert data["delaySeconds"] == 3.0  # 60 / 20 = 3

    def test_bulk_upload_missing_text_fields(self, test_client):
        """Test bulk upload handles items with missing text."""
        csv_content = b"text,userId\n,user1\nValid text,user2\n,user3"

        response = test_client.post(
            "/api/v1/feedback/bulk",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 3
        assert len(data["success"]) == 1  # Only 1 valid item
        assert len(data["failed"]) == 2  # 2 items with missing text

        # Check failed items have error messages
        for failed in data["failed"]:
            assert "error" in failed
            assert "Missing text" in failed["error"]

    def test_bulk_upload_empty_file(self, test_client):
        """Test bulk upload with empty file."""
        empty_file = io.BytesIO(b"")

        response = test_client.post(
            "/api/v1/feedback/bulk",
            files={"file": ("empty.csv", empty_file, "text/csv")}
        )

        assert response.status_code == 400

    def test_bulk_upload_preserves_user_ids(self, test_client, sample_csv_file):
        """Test that user IDs are preserved from input."""
        response = test_client.post(
            "/api/v1/feedback/bulk",
            files={"file": ("test.csv", sample_csv_file, "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify records were created (check via history endpoint)
        history_response = test_client.get("/api/v1/history")
        history = history_response.json()

        # Should have our uploaded items
        assert len(history) >= 3

    def test_bulk_upload_batch_size_boundaries(self, test_client):
        """Test batch size parameter boundaries."""
        csv_content = b"text,userId\nTest 1,user1"

        # Minimum batch size (1)
        response = test_client.post(
            "/api/v1/feedback/bulk?batch_size=1",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        )
        assert response.status_code == 200
        assert response.json()["batchSize"] == 1

        # Maximum batch size (50)
        response = test_client.post(
            "/api/v1/feedback/bulk?batch_size=50",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        )
        assert response.status_code == 200
        assert response.json()["batchSize"] == 50

    def test_bulk_upload_mixed_user_id_fields(self, test_client):
        """Test that different userId field names are handled."""
        json_content = json.dumps([
            {"text": "Text 1", "userId": "user1"},
            {"text": "Text 2", "user_id": "user2"},
            {"text": "Text 3", "user": "user3"}
        ]).encode("utf-8")

        response = test_client.post(
            "/api/v1/feedback/bulk",
            files={"file": ("test.json", io.BytesIO(json_content), "application/json")}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["success"]) == 3


class TestBulkUploadIntegration:
    """Integration tests for bulk upload with batching."""

    def test_end_to_end_25_items(self, test_client, large_csv_file):
        """
        End-to-end test: Upload 25 items, verify batching and results.
        With batch_size=10, should create 3 batches.
        """
        response = test_client.post(
            "/api/v1/feedback/bulk",
            files={"file": ("large.csv", large_csv_file, "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify batching
        assert data["total"] == 25
        assert data["batches"] == 3
        assert data["batchSize"] == 10

        # Verify all succeeded
        assert len(data["success"]) == 25
        assert len(data["failed"]) == 0

        # Verify each success item has index and id
        for item in data["success"]:
            assert "index" in item
            assert "id" in item

        # Verify records are in storage (via history endpoint)
        history_response = test_client.get("/api/v1/history")
        history = history_response.json()
        assert len(history) >= 25

    def test_rate_limiting_calculation(self, test_client, sample_csv_file):
        """Test that rate limiting values are calculated correctly."""
        test_cases = [
            (30, 2.0),   # 30 RPM = 2 seconds delay
            (20, 3.0),   # 20 RPM = 3 seconds delay
            (60, 1.0),   # 60 RPM = 1 second delay
        ]

        for rpm, expected_delay in test_cases:
            response = test_client.post(
                f"/api/v1/feedback/bulk?rate_limit_rpm={rpm}",
                files={"file": ("test.csv", sample_csv_file, "text/csv")}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["rateLimitRpm"] == rpm
            assert data["delaySeconds"] == expected_delay
