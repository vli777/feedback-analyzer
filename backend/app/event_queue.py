"""
Inbound event queue with deduplication via cursor tracking and worker pool.

Events from the WS bridge are enqueued, deduplicated by sequence number,
processed (persisted + broadcast), and cursors are stored for resume.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .models import FeedbackRecord, Sentiment
from .storage import append_feedback
from .ws_broadcaster import Broadcaster

logger = logging.getLogger(__name__)


class CursorStore:
    """Persists last-processed sequence number per job to a JSON file."""

    def __init__(self, path: str):
        self._path = Path(path)
        self._cursors: dict[str, int] = {}
        self._load()

    def _load(self):
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._cursors = {str(k): int(v) for k, v in data.items()}
        except Exception as e:
            logger.warning("Failed to load cursor file: %s", e)
            self._cursors = {}

    def _save(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._cursors, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.warning("Failed to save cursor file: %s", e)

    def get(self, job_id: str) -> int:
        return self._cursors.get(job_id, 0)

    def update(self, job_id: str, seq: int):
        self._cursors[job_id] = seq
        self._save()

    def all_cursors(self) -> dict[str, int]:
        return dict(self._cursors)


class EventWorkerPool:
    """
    Owns an asyncio.Queue and spawns N worker tasks that dequeue events,
    deduplicate via CursorStore, persist item.analyzed events, and broadcast.
    """

    def __init__(
        self,
        broadcaster: Broadcaster,
        cursor_store: CursorStore,
        num_workers: int = 2,
        queue_size: int = 256,
    ):
        self.broadcaster = broadcaster
        self.cursor_store = cursor_store
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self._num_workers = num_workers
        self._workers: list[asyncio.Task] = []

    async def start(self):
        for i in range(self._num_workers):
            task = asyncio.create_task(self._worker(i))
            self._workers.append(task)
        logger.info("EventWorkerPool started with %d workers", self._num_workers)

    async def stop(self):
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("EventWorkerPool stopped")

    async def _worker(self, worker_id: int):
        while True:
            try:
                event = await self.queue.get()
                await self._process_event(event, worker_id)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Worker %d error: %s", worker_id, e)

    async def _process_event(self, event: dict, worker_id: int):
        job_id = event.get("jobId", "")
        seq = event.get("seq", 0)
        event_type = event.get("type", "")

        # Dedup check
        cursor = self.cursor_store.get(job_id)
        if seq <= cursor:
            logger.debug("Worker %d: skipping duplicate seq=%d for job=%s", worker_id, seq, job_id)
            return

        if event_type == "item.analyzed":
            payload = event.get("payload", {})
            try:
                sentiment_val = payload.get("sentiment", "neutral")
                try:
                    sentiment = Sentiment(sentiment_val)
                except ValueError:
                    sentiment = Sentiment.neutral

                record = FeedbackRecord(
                    id=str(uuid.uuid4()),
                    text=payload.get("text", ""),
                    userId=None,
                    sentiment=sentiment,
                    keyTopics=payload.get("keyTopics", []),
                    actionRequired=payload.get("actionRequired", False),
                    summary=payload.get("summary", "No summary provided."),
                    createdAt=datetime.now(timezone.utc),
                )
                append_feedback(record)
                logger.debug("Worker %d: persisted record %s (seq=%d)", worker_id, record.id, seq)
            except Exception as e:
                logger.error("Worker %d: failed to persist item seq=%d: %s", worker_id, seq, e)

        # Update cursor and broadcast for all event types
        self.cursor_store.update(job_id, seq)
        await self.broadcaster.broadcast(event)
