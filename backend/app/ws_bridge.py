"""
WebSocket bridge: connects to the upstream stub event source,
receives events, and enqueues them for processing.
"""

import asyncio
import json
import logging

import websockets

from .config import (
    STUB_WS_URL,
    WS_RECONNECT_BASE_DELAY,
    WS_RECONNECT_MAX_DELAY,
)

logger = logging.getLogger(__name__)


class WSBridge:
    """
    Connects to the upstream stub WS server, receives events,
    and pushes them into the inbound asyncio.Queue.

    Reconnects with exponential backoff on disconnection.
    Sends { resumeFromSeq } on each connect so the stub can skip old events.
    """

    def __init__(
        self,
        inbound_queue: asyncio.Queue,
        initial_cursors: dict[str, int] | None = None,
        url: str = STUB_WS_URL,
    ):
        self.queue = inbound_queue
        self.url = url
        self._last_seq_by_job: dict[str, int] = dict(initial_cursors or {})
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._connect_loop())
        logger.info("WSBridge started, connecting to %s", self.url)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("WSBridge stopped")

    def _max_seq(self) -> int:
        if not self._last_seq_by_job:
            return 0
        return max(self._last_seq_by_job.values())

    async def _connect_loop(self):
        delay = WS_RECONNECT_BASE_DELAY
        while self._running:
            try:
                async with websockets.connect(self.url) as ws:
                    # Send resume cursor
                    resume_msg = json.dumps({"resumeFromSeq": self._max_seq()})
                    await ws.send(resume_msg)
                    logger.info("Connected to stub WS at %s (resumeFromSeq=%d)", self.url, self._max_seq())

                    # Reset backoff on successful connect
                    delay = WS_RECONNECT_BASE_DELAY

                    await self._receive_loop(ws)
            except asyncio.CancelledError:
                break
            except Exception as e:
                if not self._running:
                    break
                logger.warning("WSBridge connection error: %s. Reconnecting in %.1fs", e, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, WS_RECONNECT_MAX_DELAY)

    async def _receive_loop(self, ws):
        async for raw in ws:
            if not self._running:
                break
            try:
                event = json.loads(raw)
                job_id = event.get("jobId", "")
                seq = event.get("seq", 0)

                # Track latest seq per job for resume
                self._last_seq_by_job[job_id] = max(
                    self._last_seq_by_job.get(job_id, 0), seq
                )

                # Enqueue without blocking — drop on full
                try:
                    self.queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning("Inbound queue full, dropping event seq=%d", seq)
            except json.JSONDecodeError:
                logger.warning("WSBridge received non-JSON message, ignoring")
