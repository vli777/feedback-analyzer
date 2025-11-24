# Patient Feedback Analysis – Engineering Decision Summary

<img width="1965" height="1120" alt="image" src="https://github.com/user-attachments/assets/9a6c9f0a-c59f-4d92-b7e0-0c0907afb852" />


## Core Feature Prioritization

The primary value proposition for this proof-of-concept is the LLM-driven feedback analysis workflow. Given limited time, I prioritized:

- Getting the reasoning/analysis LLM pipeline fully functional
- Ensuring the feedback → analysis → insight loop was stable
- Returning structured JSON reliably for downstream UI and metrics computations

This enabled us to validate the core experience early without investing in peripheral concerns prematurely (authentication, database setup, etc.).

---

## Model Selection & Safety Tradeoffs

### Initial Approach

The initial plan was to run:

- A dedicated analysis model
- A separate trust & safety checker
- A fallback QC step for JSON validation

This would mirror a production-grade multi-model pipeline but adds latency, complexity, and infrastructure overhead.

### Consolidation to a Single LLM Call

For the PoC, I collapsed the architecture into a single LLM call using NVIDIA’s OSS-aligned, OpenAI-compatible model (`openai/gpt-oss-20b`). This model includes built-in safety behavior, which removed the need for a fully separate moderation stage for this phase.

**Reasons for this choice:**

- Reduced latency and implementation complexity
- No extra finetuned trust/safety model to provision and operate
- Removed multi-call orchestration and JSON drift between calls
- Safety guarantees from the model are sufficient for an internal prototype / demo

The result is a predictable, single-step analysis pipeline that is easier to maintain and straightforward to extend later if we decide to reintroduce a separate safety layer.

---

## API & Client Integration Choices

### NVIDIA vs Direct OpenAI API

There were issues calling the OpenAI API directly from outside the NVIDIA environment (intermittent errors and inconsistent behavior). To de-risk the PoC, I switched back to the NVIDIA-hosted endpoint and used the OpenAI-compatible interface exposed there.

On top of that, I chose to use LangChain instead of the older chat completions API directly:

- Faster prototyping and iteration
- Cleaner prompt templating and model configuration
- Easier model swapping if we want to experiment with different OSS models later

This is a tradeoff toward developer velocity and familiarity over minimal dependencies, which is appropriate at this stage.

---

## Storage Layer Decision: JSON Fixture vs Database

### Chosen Option: JSON Fixture

For this proof-of-concept, I intentionally avoided setting up a relational database (PostgreSQL/SQLite) and instead used a simple JSON file as a data fixture acting as a lightweight “DB stub”. All feedback records are stored as an array in `feedback.json` and loaded into memory for analytics.

**Reasons for this choice:**

- Data size remains small; O(N) scans are acceptable
- No need to manage schema migrations or migrations tooling
- Sorting, grouping, and aggregating over a small dataset is trivial
- Fewer moving pieces makes debugging and iteration simpler

### Tradeoffs and Future Direction

For production or higher traffic:

- We would move to a relational database for concurrency, indexing, and relational modeling (e.g., user → feedback → visits).
- We would add indices on timestamp, topic, and user ID for efficient filtering.
- We would implement audit logging and structured retention controls at the DB level.
- Async fetch calls need loading states with common components for loading and error states.
- If history becomes extensive, we use lazy loading within infinite scroll, and define a static date range cutoff to display unless there's date range filter integration.

---

## Additional Features With More Time

With roughly one extra hour of engineering time, I would focus on filterable insights, since they significantly increase the value of the existing LLM pipeline:

### 1. Date Range Filtering

- Add query parameters or request body filters (e.g., `from`, `to`) on history and metrics endpoints.
- Filter records server-side by `createdAt` before computing metrics.
- Propagate those filters into charts and history lists on the frontend.

### 2. Topic Search

- Normalize topics (lowercase, trimming, basic stemming/aliasing).
- Add a topic filter that narrows:
  - History list
  - Top-topics panel
  - Metrics breakdowns
- Optionally introduce a simple synonym map to collapse near-duplicate topics (e.g., “wait time”, “long wait”, “delays” → “wait time”).

These improvements would help the system move from a static dashboard to a more interactive analysis tool without requiring major architectural changes.

---

## Security Considerations for a Production Deployment

For a production environment, I would prioritize:

### Authentication & Authorization

- Introduce an auth layer (e.g., OAuth2, OIDC, or JWT-based login).
- Implement role-based access control (RBAC):
  - Admin roles for configuration and data export
  - Analyst roles for viewing aggregated insights
  - Restricted roles for viewing only anonymized or scoped data
- Enforce route-level and data-level authorization:
  - Protect history and metrics routes behind authenticated sessions
  - Restrict raw feedback access to appropriate roles

### Data Handling & Privacy

- Clearly separate PII/PHI from derived insights.
- Apply appropriate encryption at rest and in transit.
- Consider on-prem or VPC-hosted models if regulatory requirements prohibit external LLM calls.

---

## Data Retention & Deletion Policies

The exact approach depends heavily on the regulatory context (e.g., HIPAA, GDPR, local healthcare regulations). I’d approach it in two layers:

### 1. Regulatory-Driven Retention

- If regulated, design retention windows and deletion workflows according to legal requirements.
- Implement scheduled jobs to purge data beyond retention windows.
- Provide traceable deletion logs and, where required, user-driven “right to be forgotten” flows.

### 2. Operational Retention (If Not Strictly Regulated)

Even in non-regulated contexts, uncontrolled data growth is a risk. I’d implement:

- Time-to-live (TTL) policies for old records.
- LRU-style pruning for caches or high-frequency stores.
- Clear configuration flags for retention durations per environment (dev, staging, prod).

---

## Future Hardening & Observability

If this PoC becomes the basis for a production system, next steps would include:

- Centralized logging and error tracking (e.g., structured logs, Sentry).
- Metrics for LLM latency, error rates, and call volumes.
- Health checks and readiness probes for the API.
- CI/CD pipeline with automated tests for:
  - LLM contract (JSON schema adherence)
  - Metrics aggregation
  - Permissions and access restrictions

---

## Summary

This PoC was intentionally optimized for:

- Delivering the **LLM-driven feedback analysis** as the core feature.
- Keeping the architecture simple enough to iterate quickly.
- Making conscious tradeoffs (single LLM call, JSON storage) that are safe for a prototype but have a clear upgrade path.

With additional time, I would focus first on **filterable insights**, then on **security, data retention, and persistence hardening** to evolve this into a production-ready system.
