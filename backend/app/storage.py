import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from fastapi import HTTPException
from .models import FeedbackRecord

FILE_PATH = Path("data/feedback.json")
_storage_lock = threading.Lock()


def _ensure():
    if not FILE_PATH.parent.exists():
        FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not FILE_PATH.exists():
        FILE_PATH.write_text("[]", encoding="utf-8")


def _normalize_created_at(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalize_record(record: FeedbackRecord) -> FeedbackRecord:
    return record.copy(update={"createdAt": _normalize_created_at(record.createdAt)})


def read_all_feedback() -> List[FeedbackRecord]:
    _ensure()
    try:
        with _storage_lock:
            raw = FILE_PATH.read_text()
            arr = json.loads(raw or "[]")
        return [FeedbackRecord(**item) for item in arr]
    except Exception as e:
        raise HTTPException(500, f"Error reading DB: {e}")


def append_feedback(record: FeedbackRecord):
    _ensure()
    try:
        record = _normalize_record(record)
        with _storage_lock:
            raw = FILE_PATH.read_text() or "[]"
            arr = json.loads(raw)
            arr.append(json.loads(record.json()))
            FILE_PATH.write_text(json.dumps(arr, indent=2))
    except Exception as e:
        raise HTTPException(500, f"Error writing DB: {e}")


def append_feedback_many(records: List[FeedbackRecord]):
    """Append multiple records in a single read-modify-write cycle."""
    if not records:
        return
    _ensure()
    try:
        records = [_normalize_record(record) for record in records]
        with _storage_lock:
            raw = FILE_PATH.read_text() or "[]"
            arr = json.loads(raw)
            for record in records:
                arr.append(json.loads(record.json()))
            FILE_PATH.write_text(json.dumps(arr, indent=2))
    except Exception as e:
        raise HTTPException(500, f"Error writing DB: {e}")
