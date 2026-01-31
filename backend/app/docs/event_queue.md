# Processing Layer: EventWorkerPool & CursorStore

This layer handles the idempotent processing of ingested events, data transformation, and persistent state management. It acts as the bridge between the raw `WSBridge` ingest and the `Broadcaster` output.

## Components

### 1. CursorStore (JSON-based Persistence Layer)
`CursorStore` manages the local persistence of event sequence numbers (`seq`) mapped to specific `jobId` keys.
*   **Reliability**: Utilizes a local JSON file to maintain state across application restarts.
*   **Recovery**: On initialization, it reloads historical cursors to provide the `WSBridge` with an accurate `resumeFromSeq` starting point.
*   **Implementation**: Simple file-based I/O with directory auto-creation via `pathlib`.

### Persistence: Redis-Backed CursorStore (Future Upgrade)
The application utilizes **Redis** for cursor persistence to ensure high-throughput and atomic state updates.
*   **Storage Pattern**: Uses a [Redis Hash (HSET)](https://redis.io) to store `job_id` to `sequence_number` mappings.
*   **Performance**: Updates are O(1) and occur in-memory, eliminating the I/O bottleneck found in file-based storage.
*   **Concurrency**: Multiple worker processes can safely read/write to the same Redis instance without risk of state corruption or race conditions.

### 2. EventWorkerPool (Execution Layer)
A managed pool of asynchronous workers that consume from an `asyncio.Queue`.
*   **Scalable Concurrency**: Configurable `num_workers` allows horizontal scaling of event processing within a single process.
*   **Deduplication Logic**: Implements a strict "Greater-Than-Cursor" check. Events with a sequence number less than or equal to the stored cursor are discarded to prevent duplicate data entry.
*   **Transformation Pipeline**: 
    *   Filters for `item.analyzed` event types.
    *   Normalizes payloads into `FeedbackRecord` objects (using `uuid` for unique identification and `timezone.utc` for consistent timestamps).
    *   Integrates with a persistence function (`append_feedback`) and triggers the `Broadcaster` for real-time UI updates.

## Workflow Detail

1.  **Dequeue**: A worker pulls a raw event dict from the queue.
2.  **Validate**: The worker queries `CursorStore` to see if this `seq` has already been processed for the given `jobId`.
3.  **Process**: If the type is `item.analyzed`, the worker transforms the payload and commits it to the primary database.
4.  **Finalize**: The `CursorStore` is updated on disk, and the event is forwarded to the `Broadcaster` for all connected WebSocket clients.

## Configuration

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `num_workers` | `int` | `2` | Number of parallel worker tasks to spawn. |
| `queue_size` | `int` | `256` | Maximum depth of the inbound event buffer before backpressure kicks in. |
| `path` | `str` | N/A | File system path for the JSON cursor storage. |