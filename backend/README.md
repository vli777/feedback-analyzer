# Feedback Analyzer - Backend

FastAPI backend for analyzing feedback using AI/LLM.

## Setup

1. Create a virtual environment:
```bash
python -m venv .venv
```

2. Activate the virtual environment:
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file from the example:
```bash
cp .env.example .env
```

5. Add your NVIDIA API key to the `.env` file:
```
NVIDIA_API_KEY=your_actual_api_key
```

## Running the Server

```bash
cd backend
uvicorn app.main:app --reload
```

## Note: For demo purposes, Websocket and Redis services need to be running
```bash
# websocket 
python stub_event_source.py 

# redis (for cursor store)
docker run -p 6379:6379 redis
```

The API will be available at `http://localhost:8000`

## Architecture

- **models.py** - Pydantic models for request/response validation
- **storage.py** - Simple JSON file-based storage (data/feedback.json)
- **llm_client.py** - OpenAI client configured for NVIDIA API
- **analyze_pipeline.py** - LLM analysis logic with error handling
- **metrics.py** - Analytics computation for dashboard
- **main.py** - FastAPI app with all endpoints

## LLM Integration Features

The analyze_pipeline includes:
- **Error handling**: Catches API errors and returns fallback responses
- **JSON validation**: Handles cases where LLM returns invalid JSON
- **Normalization**: Ensures sentiment and topics are in expected format