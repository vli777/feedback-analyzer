# Tests

This directory contains pytest tests for the Feedback Analyzer backend.

## Setup

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

## Running Tests

### Run all tests:
```bash
pytest
```

### Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

### Run specific test file:
```bash
pytest tests/test_bulk_upload.py
```

### Run specific test:
```bash
pytest tests/test_bulk_upload.py::TestBulkUploadEndpoint::test_bulk_upload_csv_default_batch
```

### Run with verbose output:
```bash
pytest -v
```

### Run with output (print statements):
```bash
pytest -s
```

## Test Structure

- `conftest.py` - Shared fixtures and test configuration
  - `mock_llm_client` - Mocks the NVIDIA LLM API to avoid real API calls
  - `mock_storage` - Uses temporary files for storage during tests
  - `test_client` - FastAPI test client
  - Sample data fixtures for CSV/JSON files

- `test_analyze_pipeline.py` - Tests for the analysis pipeline
  - Single feedback analysis
  - Batch feedback analysis
  - Prompt generation
  - Normalization functions

- `test_bulk_upload.py` - Tests for bulk upload endpoint
  - File parsing (CSV, JSON)
  - Batching logic (10 items per batch by default)
  - Rate limiting
  - Error handling
  - Custom batch sizes
  - Integration tests

## Key Test Cases

### Batching Tests
- Default batch size (10 items)
- Custom batch sizes (1-50)
- Multiple batches (25 items = 3 batches)
- Single batch (< 10 items)

### Rate Limiting Tests
- Default 30 RPM (2 second delay)
- Custom RPM values
- Delay calculation correctness

### Error Handling Tests
- Missing text fields
- Empty files
- Invalid file formats
- Failed API calls

### Integration Tests
- End-to-end upload of 25 items
- Verification of storage
- History endpoint integration

## Mocking Strategy

Tests mock the NVIDIA LLM client to:
1. Avoid real API calls during testing
2. Ensure consistent test results
3. Test batch vs single analysis logic
4. Simulate error conditions

The mock client automatically detects batch requests (numbered list in prompt) and returns appropriate JSON responses.
