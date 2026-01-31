"""
Standalone stub WebSocket event source for development/testing.

Produces realistic demo feedback analysis events on a configurable interval.
Clients can send { "resumeFromSeq": N } on connect to skip already-seen events.

Usage:
    python stub_event_source.py [--host HOST] [--port PORT] [--interval SECONDS]
"""

import argparse
import asyncio
import json
import random
import uuid
from datetime import datetime, timezone

import websockets

DEMO_FEEDBACKS = [
    {
        "text": "The onboarding process was smooth and intuitive.",
        "sentiment": "positive",
        "keyTopics": ["onboarding", "user experience"],
        "actionRequired": False,
        "summary": "User found the onboarding process smooth and intuitive.",
    },
    {
        "text": "App crashes every time I try to upload a photo.",
        "sentiment": "negative",
        "keyTopics": ["crash", "photo upload", "bug"],
        "actionRequired": True,
        "summary": "App crashes consistently during photo upload attempts.",
    },
    {
        "text": "Customer support resolved my issue within minutes.",
        "sentiment": "positive",
        "keyTopics": ["customer support", "resolution time"],
        "actionRequired": False,
        "summary": "Customer support provided a quick and effective resolution.",
    },
    {
        "text": "The pricing page is confusing and hard to navigate.",
        "sentiment": "negative",
        "keyTopics": ["pricing", "navigation", "usability"],
        "actionRequired": True,
        "summary": "Pricing page layout is confusing and needs redesign.",
    },
    {
        "text": "I like the new dashboard layout, it's much cleaner.",
        "sentiment": "positive",
        "keyTopics": ["dashboard", "design", "improvement"],
        "actionRequired": False,
        "summary": "User appreciates the cleaner new dashboard layout.",
    },
    {
        "text": "Search results are not relevant to my queries.",
        "sentiment": "negative",
        "keyTopics": ["search", "relevance", "accuracy"],
        "actionRequired": True,
        "summary": "Search functionality returns irrelevant results for user queries.",
    },
    {
        "text": "The mobile app works fine but nothing special.",
        "sentiment": "neutral",
        "keyTopics": ["mobile app", "functionality"],
        "actionRequired": False,
        "summary": "Mobile app functions adequately without standout features.",
    },
    {
        "text": "Password reset emails take too long to arrive.",
        "sentiment": "negative",
        "keyTopics": ["password reset", "email delay", "authentication"],
        "actionRequired": True,
        "summary": "Password reset emails have excessive delivery delays.",
    },
    {
        "text": "Great integration with third-party tools we already use.",
        "sentiment": "positive",
        "keyTopics": ["integration", "third-party", "compatibility"],
        "actionRequired": False,
        "summary": "User praises seamless integration with existing third-party tools.",
    },
    {
        "text": "The notification settings are adequate for my needs.",
        "sentiment": "neutral",
        "keyTopics": ["notifications", "settings"],
        "actionRequired": False,
        "summary": "Notification settings meet basic user requirements.",
    },
]


class StubEventSource:
    def __init__(self, interval: float = 2.0):
        self.interval = interval
        self.clients: set = set()
        self._seq = 0
        self._running = False

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _make_event(self, event_type: str, payload: dict, job_id: str) -> dict:
        return {
            "jobId": job_id,
            "seq": self._next_seq(),
            "type": event_type,
            "ts": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }

    async def _broadcast(self, event: dict, resume_seq: int = 0):
        if event["seq"] <= resume_seq:
            return
        message = json.dumps(event)
        dead = set()
        for ws in self.clients:
            try:
                await ws.send(message)
            except websockets.exceptions.ConnectionClosed:
                dead.add(ws)
        self.clients -= dead

    async def _produce_job(self):
        job_id = str(uuid.uuid4())
        items = random.sample(DEMO_FEEDBACKS, k=random.randint(3, len(DEMO_FEEDBACKS)))

        # job.started
        started_event = self._make_event(
            "job.started", {"totalItems": len(items)}, job_id
        )
        await self._broadcast(started_event)

        # item.analyzed events
        for idx, item in enumerate(items):
            await asyncio.sleep(self.interval)
            if not self.clients:
                return
            event = self._make_event(
                "item.analyzed",
                {
                    "index": idx,
                    "text": item["text"],
                    "sentiment": item["sentiment"],
                    "keyTopics": item["keyTopics"],
                    "actionRequired": item["actionRequired"],
                    "summary": item["summary"],
                },
                job_id,
            )
            await self._broadcast(event)

        # job.completed
        completed_event = self._make_event(
            "job.completed",
            {
                "totalItems": len(items),
                "processedItems": len(items),
                "failedItems": 0,
            },
            job_id,
        )
        await self._broadcast(completed_event)

    async def _producer_loop(self):
        self._running = True
        while self._running:
            if self.clients:
                await self._produce_job()
                # Pause between jobs
                await asyncio.sleep(self.interval * 2)
            else:
                await asyncio.sleep(0.5)

    async def handler(self, websocket):
        # Read optional resumeFromSeq from client
        resume_seq = 0
        try:
            msg = await asyncio.wait_for(websocket.recv(), timeout=1.0)
            data = json.loads(msg)
            resume_seq = data.get("resumeFromSeq", 0)
        except (asyncio.TimeoutError, json.JSONDecodeError, Exception):
            pass

        self.clients.add(websocket)
        print(f"[stub] Client connected (resumeFromSeq={resume_seq}), total={len(self.clients)}")

        try:
            # Keep connection alive by reading (handles pings and detects disconnect)
            async for _ in websocket:
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            print(f"[stub] Client disconnected, total={len(self.clients)}")

    def stop(self):
        self._running = False


async def main(host: str, port: int, interval: float):
    source = StubEventSource(interval=interval)

    # Start producer in background
    producer_task = asyncio.create_task(source._producer_loop())

    print(f"[stub] WebSocket event source running on ws://{host}:{port}")
    print(f"[stub] Producing events every {interval}s when clients are connected")

    async with websockets.serve(source.handler, host, port):
        try:
            await asyncio.Future()  # Run forever
        except asyncio.CancelledError:
            pass
        finally:
            source.stop()
            producer_task.cancel()
            try:
                await producer_task
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stub WebSocket event source")
    parser.add_argument("--host", default="localhost", help="Bind host (default: localhost)")
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between events (default: 2.0)")
    args = parser.parse_args()

    asyncio.run(main(args.host, args.port, args.interval))
