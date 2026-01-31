"""Tests for the WebSocket streaming pipeline components."""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ws_broadcaster import Broadcaster
from app.event_queue import CursorStore, EventWorkerPool


# ── Broadcaster tests ─────────────────────────────────────────────────

class TestBroadcaster:
    @pytest.fixture
    def broadcaster(self):
        return Broadcaster()

    @pytest.mark.asyncio
    async def test_connect_and_count(self, broadcaster):
        ws = AsyncMock()
        await broadcaster.connect(ws)
        assert broadcaster.client_count == 1
        ws.accept.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, broadcaster):
        ws = AsyncMock()
        await broadcaster.connect(ws)
        await broadcaster.disconnect(ws)
        assert broadcaster.client_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self, broadcaster):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await broadcaster.connect(ws1)
        await broadcaster.connect(ws2)

        event = {"type": "test", "data": "hello"}
        await broadcaster.broadcast(event)

        expected_msg = json.dumps(event)
        ws1.send_text.assert_awaited_once_with(expected_msg)
        ws2.send_text.assert_awaited_once_with(expected_msg)

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_clients(self, broadcaster):
        ws_alive = AsyncMock()
        ws_dead = AsyncMock()
        ws_dead.send_text.side_effect = RuntimeError("connection closed")

        await broadcaster.connect(ws_alive)
        await broadcaster.connect(ws_dead)
        assert broadcaster.client_count == 2

        await broadcaster.broadcast({"type": "test"})
        assert broadcaster.client_count == 1

    @pytest.mark.asyncio
    async def test_broadcast_empty_clients(self, broadcaster):
        # Should not raise
        await broadcaster.broadcast({"type": "test"})


# ── CursorStore tests ─────────────────────────────────────────────────

class TestCursorStore:
    @pytest.fixture
    def cursor_file(self, tmp_path):
        return str(tmp_path / "cursors.json")

    def test_get_default_zero(self, cursor_file):
        store = CursorStore(cursor_file)
        assert store.get("job1") == 0

    def test_update_and_get(self, cursor_file):
        store = CursorStore(cursor_file)
        store.update("job1", 5)
        assert store.get("job1") == 5

    def test_persistence(self, cursor_file):
        store1 = CursorStore(cursor_file)
        store1.update("job1", 10)
        store1.update("job2", 20)

        # New instance reads from file
        store2 = CursorStore(cursor_file)
        assert store2.get("job1") == 10
        assert store2.get("job2") == 20

    def test_all_cursors(self, cursor_file):
        store = CursorStore(cursor_file)
        store.update("a", 1)
        store.update("b", 2)
        assert store.all_cursors() == {"a": 1, "b": 2}

    def test_corrupt_file_fallback(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json", encoding="utf-8")
        store = CursorStore(str(path))
        assert store.get("anything") == 0


# ── EventWorkerPool tests ────────────────────────────────────────────

class TestEventWorkerPool:
    @pytest.fixture
    def cursor_store(self, tmp_path):
        return CursorStore(str(tmp_path / "cursors.json"))

    @pytest.fixture
    def broadcaster(self):
        b = Broadcaster()
        b.broadcast = AsyncMock()
        return b

    def _make_event(self, job_id, seq, event_type="item.analyzed", payload=None):
        return {
            "jobId": job_id,
            "seq": seq,
            "type": event_type,
            "ts": datetime.now(timezone.utc).isoformat(),
            "payload": payload or {
                "index": 0,
                "text": "Test feedback",
                "sentiment": "positive",
                "keyTopics": ["test"],
                "actionRequired": False,
                "summary": "Test summary for this feedback item.",
            },
        }

    @pytest.mark.asyncio
    async def test_process_and_broadcast(self, broadcaster, cursor_store, mock_storage):
        pool = EventWorkerPool(broadcaster, cursor_store, num_workers=1, queue_size=16)
        await pool.start()

        event = self._make_event("job1", 1)
        await pool.queue.put(event)

        # Wait for worker to process
        await asyncio.sleep(0.1)

        broadcaster.broadcast.assert_awaited()
        assert cursor_store.get("job1") == 1

        await pool.stop()

    @pytest.mark.asyncio
    async def test_dedup_skips_old_seq(self, broadcaster, cursor_store, mock_storage):
        # Pre-set cursor so seq=1 is already processed
        cursor_store.update("job1", 5)

        pool = EventWorkerPool(broadcaster, cursor_store, num_workers=1, queue_size=16)
        await pool.start()

        # Send event with seq <= cursor (should be skipped)
        event = self._make_event("job1", 3)
        await pool.queue.put(event)
        await asyncio.sleep(0.1)

        broadcaster.broadcast.assert_not_awaited()

        await pool.stop()

    @pytest.mark.asyncio
    async def test_job_started_broadcast_no_persist(self, broadcaster, cursor_store, mock_storage):
        pool = EventWorkerPool(broadcaster, cursor_store, num_workers=1, queue_size=16)
        await pool.start()

        event = self._make_event("job1", 1, "job.started", {"totalItems": 5})
        await pool.queue.put(event)
        await asyncio.sleep(0.1)

        broadcaster.broadcast.assert_awaited_once()
        # Cursor still updated
        assert cursor_store.get("job1") == 1

        # Storage should not have been called for job.started
        storage_data = json.loads(mock_storage.read_text())
        assert len(storage_data) == 0

        await pool.stop()

    @pytest.mark.asyncio
    async def test_item_analyzed_persists_record(self, broadcaster, cursor_store, mock_storage):
        pool = EventWorkerPool(broadcaster, cursor_store, num_workers=1, queue_size=16)
        await pool.start()

        event = self._make_event("job1", 1, "item.analyzed", {
            "index": 0,
            "text": "Great service!",
            "sentiment": "positive",
            "keyTopics": ["service"],
            "actionRequired": False,
            "summary": "User praises the quality of service received.",
        })
        await pool.queue.put(event)
        await asyncio.sleep(0.1)

        storage_data = json.loads(mock_storage.read_text())
        assert len(storage_data) == 1
        assert storage_data[0]["text"] == "Great service!"
        assert storage_data[0]["sentiment"] == "positive"

        await pool.stop()

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self, broadcaster, cursor_store):
        pool = EventWorkerPool(broadcaster, cursor_store, num_workers=2, queue_size=8)
        await pool.start()
        assert len(pool._workers) == 2
        await pool.stop()
        assert len(pool._workers) == 0


# ── WSBridge tests ────────────────────────────────────────────────────

class TestWSBridge:
    @pytest.mark.asyncio
    async def test_bridge_start_stop(self):
        from app.ws_bridge import WSBridge
        queue = asyncio.Queue(maxsize=16)

        with patch("app.ws_bridge.websockets.connect", side_effect=ConnectionRefusedError):
            bridge = WSBridge(queue, url="ws://localhost:19999")
            await bridge.start()
            # Let it attempt a connection
            await asyncio.sleep(0.2)
            await bridge.stop()

    @pytest.mark.asyncio
    async def test_bridge_enqueues_events(self):
        from app.ws_bridge import WSBridge

        queue = asyncio.Queue(maxsize=16)
        test_event = json.dumps({
            "jobId": "j1",
            "seq": 1,
            "type": "item.analyzed",
            "ts": "2025-01-01T00:00:00Z",
            "payload": {},
        })

        # Mock websocket as async context manager that yields one message
        call_count = 0

        class MockWSContext:
            async def __aenter__(self_ws):
                nonlocal call_count
                call_count += 1
                if call_count > 1:
                    raise ConnectionRefusedError("no more")
                return self_ws

            async def __aexit__(self_ws, *args):
                return False

            async def send(self_ws, msg):
                pass

            def __aiter__(self_ws):
                return self_ws

            async def __anext__(self_ws):
                nonlocal call_count
                if call_count == 1 and not hasattr(self_ws, '_sent'):
                    self_ws._sent = True
                    return test_event
                raise StopAsyncIteration

        with patch("app.ws_bridge.websockets.connect", return_value=MockWSContext()):
            bridge = WSBridge(queue, url="ws://localhost:19999")
            await bridge.start()
            await asyncio.sleep(0.3)
            await bridge.stop()

        assert not queue.empty()
        event = queue.get_nowait()
        assert event["jobId"] == "j1"
        assert event["seq"] == 1
