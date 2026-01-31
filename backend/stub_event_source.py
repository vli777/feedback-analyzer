"""
Standalone stub WebSocket event source for development/testing.

Loads seed feedback records from data/stub_seed.json and produces
dynamically varied events over WebSocket. Each job picks a random subset
of seed entries and applies light mutations (shuffled topics, varied
userIds, jittered timestamps) so no two jobs are identical.

Clients can send { "resumeFromSeq": N } on connect to skip already-seen events.

Usage:
    python stub_event_source.py [--host HOST] [--port PORT] [--interval SECONDS]
                                [--seed-file PATH]
"""

import argparse
import asyncio
import json
import random
import string
import uuid
from datetime import datetime, timezone
from pathlib import Path

import websockets

DEFAULT_SEED_FILE = Path(__file__).parent / "data" / "stub_seed.json"

# Fragments used to synthesize new feedback text when --generate is used
_TEXT_PREFIXES = [
    "I recently visited the clinic and",
    "During my last appointment,",
    "After seeing the doctor,",
    "At my follow-up visit,",
    "When I checked in today,",
]
_TEXT_BODIES = [
    "the staff was very professional.",
    "I had to wait longer than expected.",
    "the doctor explained everything clearly.",
    "the nurse was kind and efficient.",
    "I felt rushed during the consultation.",
    "the front desk was unresponsive to my questions.",
    "my concerns were addressed thoroughly.",
    "the facility was clean and well-maintained.",
    "I was not satisfied with the billing process.",
    "the referral process was handled smoothly.",
]
_SENTIMENTS = ["positive", "neutral", "negative"]
_TOPIC_POOL = [
    "wait times", "doctor care", "billing", "referral", "prescription",
    "follow-up", "diagnosis", "blood pressure", "test results", "clinic visit",
    "nurse", "injection", "x-ray", "appointment", "fatigue", "infection",
    "antibiotics", "pediatrician", "dermatologist", "smoking", "health",
]
_USER_POOL = [
    "Alex", "Maria", "Chris", "David", "Emily", "Frank", "Grace",
    "Henry", "Isabel", "Jack", "Karen", "Leo", "Mia", "Noah",
    "Olivia", "Peter", "Quinn", "Rachel", "Steve", "Tina",
]


def _load_seed(path: Path) -> list[dict]:
    """Load seed entries from a JSON file. Returns [] on failure."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception as e:
        print(f"[stub] Warning: could not load seed file {path}: {e}")
    return []


def _generate_entry() -> dict:
    """Synthesize a brand-new feedback entry from fragments."""
    sentiment = random.choice(_SENTIMENTS)
    action = sentiment == "negative" and random.random() < 0.6
    text = f"{random.choice(_TEXT_PREFIXES)} {random.choice(_TEXT_BODIES)}"
    topics = random.sample(_TOPIC_POOL, k=random.randint(1, 3))
    return {
        "text": text,
        "userId": random.choice(_USER_POOL),
        "sentiment": sentiment,
        "keyTopics": topics,
        "actionRequired": action,
        "summary": text,  # use the full sentence as summary
    }


def _mutate_entry(entry: dict) -> dict:
    """Return a lightly varied copy of a seed entry."""
    out = dict(entry)
    # Sometimes swap userId
    if random.random() < 0.3:
        out["userId"] = random.choice(_USER_POOL)
    # Sometimes shuffle / trim topics
    topics = list(out.get("keyTopics", []))
    if topics and random.random() < 0.4:
        random.shuffle(topics)
        topics = topics[: max(1, len(topics) - 1)]
        out["keyTopics"] = topics
    return out


class StubEventSource:
    def __init__(self, seed: list[dict], interval: float = 2.0, generate_ratio: float = 0.3):
        self._seed = seed
        self.interval = interval
        self._generate_ratio = generate_ratio  # fraction of items that are fully generated
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

    def _pick_items(self) -> list[dict]:
        """Build the item list for one job: mix of seed mutations + generated."""
        count = random.randint(3, min(10, max(3, len(self._seed))))
        items: list[dict] = []
        for _ in range(count):
            if self._seed and random.random() > self._generate_ratio:
                items.append(_mutate_entry(random.choice(self._seed)))
            else:
                items.append(_generate_entry())
        return items

    async def _broadcast(self, event: dict):
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
        items = self._pick_items()

        await self._broadcast(
            self._make_event("job.started", {"totalItems": len(items)}, job_id)
        )

        for idx, item in enumerate(items):
            await asyncio.sleep(self.interval)
            if not self.clients:
                return
            await self._broadcast(
                self._make_event(
                    "item.analyzed",
                    {
                        "index": idx,
                        "text": item["text"],
                        "sentiment": item["sentiment"],
                        "keyTopics": item.get("keyTopics", []),
                        "actionRequired": item.get("actionRequired", False),
                        "summary": item.get("summary", ""),
                    },
                    job_id,
                )
            )

        await self._broadcast(
            self._make_event(
                "job.completed",
                {"totalItems": len(items), "processedItems": len(items), "failedItems": 0},
                job_id,
            )
        )

    async def _producer_loop(self):
        self._running = True
        while self._running:
            if self.clients:
                await self._produce_job()
                await asyncio.sleep(self.interval * 2)
            else:
                await asyncio.sleep(0.5)

    async def handler(self, websocket):
        resume_seq = 0
        try:
            msg = await asyncio.wait_for(websocket.recv(), timeout=1.0)
            data = json.loads(msg)
            resume_seq = data.get("resumeFromSeq", 0)
        except Exception:
            pass

        self.clients.add(websocket)
        print(f"[stub] Client connected (resumeFromSeq={resume_seq}), total={len(self.clients)}")

        try:
            async for _ in websocket:
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            print(f"[stub] Client disconnected, total={len(self.clients)}")

    def stop(self):
        self._running = False


async def main(host: str, port: int, interval: float, seed_file: Path, generate_ratio: float):
    seed = _load_seed(seed_file)
    print(f"[stub] Loaded {len(seed)} seed entries from {seed_file}")

    source = StubEventSource(seed=seed, interval=interval, generate_ratio=generate_ratio)
    producer_task = asyncio.create_task(source._producer_loop())

    print(f"[stub] WebSocket event source running on ws://{host}:{port}")
    print(f"[stub] Event interval: {interval}s | Generate ratio: {generate_ratio:.0%}")

    async with websockets.serve(source.handler, host, port):
        try:
            await asyncio.Future()
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
    parser.add_argument("--seed-file", type=Path, default=DEFAULT_SEED_FILE,
                        help="Path to seed JSON file (default: data/stub_seed.json)")
    parser.add_argument("--generate-ratio", type=float, default=0.3,
                        help="Fraction of items that are fully generated vs seed-based (default: 0.3)")
    args = parser.parse_args()

    asyncio.run(main(args.host, args.port, args.interval, args.seed_file, args.generate_ratio))
