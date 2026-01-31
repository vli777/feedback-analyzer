# WSBridge: Resilient Upstream WebSocket Consumer

`WSBridge` is an asynchronous bridge designed to ingest event streams from an upstream server into an internal `asyncio.Queue`. It is engineered for high availability, implementing persistent state tracking and fault-tolerant reconnection logic.

## Technical Architecture

### 1. Persistent Event Cursor (`resumeFromSeq`)
To ensure "at-least-once" delivery semantics without redundant data transfer, the bridge maintains a high-water mark of event sequence numbers (`seq`).
*   **Resumption**: Upon every successful handshake, the bridge transmits a `resumeFromSeq` payload derived from the maximum sequence number observed across all tracked jobs.
*   **State Tracking**: Internal state is updated in real-time as events are parsed, ensuring the bridge can recover from mid-stream failures.

### 2. Connection Management & Backoff
The bridge utilizes a managed event loop (`_connect_loop`) to handle the WebSocket lifecycle:
*   **Exponential Backoff**: Implements a truncated exponential backoff strategy for reconnections, mitigating "thundering herd" issues during upstream outages.
*   **Automatic Reset**: Backoff timers are reset to base values immediately upon successful connection establishment.

### 3. Ingest Pipeline & Backpressure
Data flow is decoupled via an `asyncio.Queue` to isolate networking overhead from business logic.
*   **Drop-on-Full Strategy**: The bridge uses `put_nowait` to prevent network ingestion from blocking on a saturated internal queue. This ensures the process remains responsive even under heavy load, favoring data freshness over unbounded buffering.
*   **Serialization Safety**: Implements guarded JSON decoding to prevent malformed upstream payloads from crashing the bridge task.

## Interface

| Method | Description |
| :--- | :--- |
| `start()` | Spawns the background `asyncio.Task` for the connection loop. |
| `stop()` | Signals the loop to terminate and gracefully awaits task cancellation. |
| `_max_seq()` | Calculates the global high-water mark for the resume cursor. |

## Usage

```python
queue = asyncio.Queue(maxsize=100)
bridge = WSBridge(inbound_queue=queue, url="wss://://api.stub.com")

await bridge.start()
# The bridge now populates 'queue' in the background.