# Broadcaster: Asynchronous WebSocket Event Distribution

A thread-safe, asynchronous manager designed to handle WebSocket client lifecycles and fan-out event broadcasting. This class is optimized for high-concurrency environments (e.g., FastAPI, Starlette) where maintaining a consistent state of active connections is critical.

## Core Features

### 1. Connection Lifecycle Management
The `Broadcaster` maintains a registry of active `WebSocket` objects using a `set` to ensure uniqueness.
*   **`connect(ws)`**: Transitions a connection to the 'open' state and performs an atomic insertion into the registry.
*   **`disconnect(ws)`**: Removes the client using `discard` to avoid `KeyError` exceptions during race conditions or redundant disconnect calls.

### 2. Concurrency & State Integrity
To prevent `RuntimeError: Set changed size during iteration`, the class utilizes `asyncio.Lock`. 
*   **Snapshot Pattern**: The `broadcast` method creates a shallow copy of the client set within the lock context. This allows the broadcast loop to run without blocking the registration of new clients.
*   **Atomic Updates**: Additions and removals are wrapped in asynchronous context managers to ensure internal state consistency across the event loop.

### 3. Fault-Tolerant Broadcasting
The `broadcast` method implements a "Fire-and-Reap" strategy:
*   **JSON Serialization**: Dict-based events are serialized once per broadcast call to minimize overhead.
*   **Automatic Pruning**: Individual send failures (network drops, protocol errors) are caught silently. Failed clients are aggregated into a `dead` set and removed in a single atomic operation post-broadcast, preventing stale connections from bloating memory.

## Usage Example

```python
broadcaster = Broadcaster()

# In your WebSocket endpoint:
async def websocket_endpoint(websocket: WebSocket):
    await broadcaster.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming logic
    except WebSocketDisconnect:
        await broadcaster.disconnect(websocket)

# To push updates from elsewhere in your app:
await broadcaster.broadcast({"event": "update", "data": "payload"})