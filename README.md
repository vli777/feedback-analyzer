# Feedback Analyzer

An intelligent feedback analysis platform that uses Large Language Models to automatically analyze, categorize, and extract insights from user feedback. A mocked WebSocket event source generates randomized submissions that stream into the dashboard in realtime, while manual input remains decoupled to keep the UI responsive under load. Redis-backed cursor tracking ensures the streaming pipeline can resume safely and deduplicate events by job sequence.

<img width="1315" height="969" alt="image" src="https://github.com/user-attachments/assets/0bbf34b4-a48b-4366-8672-78b668b402bc" />


## Features

- **Automated Sentiment Analysis**: Automatically classifies feedback as positive, neutral, or negative using LLM-powered analysis
- **Topic Extraction**: Identifies and extracts key topics and themes from feedback text
- **Action Detection**: Flags feedback that requires follow-up or immediate attention
- **Smart Summaries**: Generates concise, natural language summaries using Pydantic-based structured outputs
- **Bulk Upload**: Process multiple feedback entries efficiently in a single batch operation
- **Analytics Dashboard**: Visualize sentiment distribution, topic trends, and submission patterns over time
- **Historical Records**: Browse and search through all analyzed feedback with detailed breakdowns

## Tech Stack

**Backend:**
- FastAPI (Python web framework)
- LangChain with NVIDIA AI Endpoints
- Pydantic for structured data validation and LLM outputs
- WebSocket bridge + event worker pool
- Redis (cursor store for WS dedup/resume)

**Frontend:**
- React + TypeScript
- Vite (build tool)
- Recharts for data visualization

## Architecture Overview

The system follows a straightforward client-server architecture with a realtime event stream:

1. **User submits feedback** via the web interface (single or bulk upload)
2. **Backend API** receives the feedback and routes it to the LLM analysis pipeline
3. **LLM processes the text** using Pydantic-based structured outputs to ensure type-safe responses
4. **Analysis results** are validated, stored, and returned to the client
5. **WebSocket bridge** streams mocked realtime events into the UI
6. **Redis cursor store** persists per-job sequence offsets for dedup/resume
7. **Dashboard displays** realtime metrics and visualizations based on analyzed feedback

### LLM Integration

The application uses a single-call LLM pipeline powered by NVIDIA AI Endpoints with LangChain:

- **Structured Outputs**: Pydantic models define the exact schema for sentiment, topics, action flags, and summaries
- **Type Safety**: LangChain's `with_structured_output()` method ensures responses conform to expected types
- **Batch Processing**: Efficient bulk analysis for processing multiple feedback entries simultaneously
- **Built-in Safety**: The model includes content safety features appropriate for handling user-generated content

### Data Storage

The current implementation uses a JSON file-based storage system (`feedback.json`) for simplicity:

- **Fast prototyping**: No database setup required
- **Easy debugging**: Data is human-readable and easily inspectable
- **Sufficient for demos**: In-memory operations are fast for moderate datasets

**Production Considerations:**
- For production use, migrate to a relational database (PostgreSQL/SQLite) for better concurrency, indexing, and scalability
- Add database indices on frequently queried fields (timestamp, sentiment, topics)
- Implement proper data retention and backup policies

## Getting Started

### Prerequisites
- Python 3.9+
- Node.js 16+
- NVIDIA API Key (for LLM integration)
- Redis (for WS cursor persistence)

### Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Set your NVIDIA API key
export NVIDIA_API_KEY=your_api_key_here

# Start Redis (required for WS cursor store)
docker run -p 6379:6379 redis

# Run the FastAPI server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. API documentation is accessible at `http://localhost:8000/docs`.

### WebSocket Event Stub (for live updates)

The live dashboard stream uses a local stub WebSocket source. Run it in a separate terminal:

```bash
cd backend
python stub_event_source.py --host 127.0.0.1 --port 8765
```

The backend will connect to it automatically on startup. If you change the port, set `STUB_WS_URL` accordingly.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The web interface will be available at `http://localhost:5173`.

## API Endpoints

- `POST /feedback` - Submit single feedback entry for analysis
- `POST /feedback/bulk` - Submit multiple feedback entries for batch analysis
- `GET /feedback/history` - Retrieve all analyzed feedback records
- `GET /feedback/metrics` - Get analytics and metrics data

## Future Enhancements

Potential improvements for production deployment:

### Enhanced Filtering
- Date range filtering for historical data
- Topic-based search and filtering
- Sentiment filtering on dashboard
- Advanced search with text queries

### Security & Compliance
- Authentication and authorization (OAuth2/JWT)
- Role-based access control (RBAC)
- Data encryption at rest and in transit
- Audit logging for compliance
- PII/PHI handling and anonymization

### Scalability & Performance
- Database migration (PostgreSQL/MongoDB)
- Caching layer (Redis) for frequently accessed data
- Rate limiting and request throttling
- Background job processing for bulk operations
- Horizontal scaling with load balancing

### Monitoring & Observability
- Centralized logging (structured logs)
- Application performance monitoring
- LLM usage metrics and cost tracking
- Error tracking and alerting
- Health checks and readiness probes

## Design Philosophy

This application balances simplicity with functionality:

- **Single LLM call**: Reduces latency and complexity while maintaining accuracy
- **Structured outputs**: Pydantic models ensure type safety and consistent data validation
- **Batch processing**: Efficient handling of multiple feedback entries
- **Simple storage**: JSON-based persistence allows rapid iteration without database overhead
- **Clean architecture**: Clear separation between API, analysis pipeline, and data models
