import json
from pathlib import Path
from typing import List
from fastapi import HTTPException
from .models import FeedbackRecord

FILE_PATH = Path("data/feedback.json")


def _ensure():
    if not FILE_PATH.parent.exists():
        FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not FILE_PATH.exists():
        FILE_PATH.write_text("[]", encoding="utf-8")


def read_all_feedback() -> List[FeedbackRecord]:
    _ensure()
    try:
        raw = FILE_PATH.read_text()
        arr = json.loads(raw or "[]")
        return [FeedbackRecord(**item) for item in arr]
    except Exception as e:
        raise HTTPException(500, f"Error reading DB: {e}")


def append_feedback(record: FeedbackRecord):
    _ensure()
    try:
        raw = FILE_PATH.read_text() or "[]"
        arr = json.loads(raw)
        arr.append(json.loads(record.json()))
        FILE_PATH.write_text(json.dumps(arr, indent=2))
    except Exception as e:
        raise HTTPException(500, f"Error writing DB: {e}")
