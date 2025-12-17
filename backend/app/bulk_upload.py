import csv
import io
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import HTTPException, UploadFile


def parse_bulk_file(upload: UploadFile, content: bytes) -> List[Dict[str, Any]]:
    """Parse the raw uploaded file into a list of dict items."""
    if not content:
        raise HTTPException(400, "Uploaded file is empty.")

    filename = (upload.filename or "").lower()

    if filename.endswith(".json"):
        return _parse_json(content)
    if filename.endswith(".csv"):
        return _parse_csv(content)

    # Fallback: try JSON then CSV
    try:
        return _parse_json(content)
    except Exception:
        pass

    try:
        return _parse_csv(content)
    except Exception:
        raise HTTPException(400, "Unsupported file format. Use .json or .csv.")


def make_record_id(item: Dict[str, Any]) -> str:
    return str(item.get("id") or uuid.uuid4())


def parse_created_at(value: Any) -> datetime:
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return datetime.utcnow()


def _parse_json(content: bytes) -> List[Dict[str, Any]]:
    parsed = json.loads(content.decode("utf-8"))
    if isinstance(parsed, dict):
        if "items" in parsed and isinstance(parsed["items"], list):
            return parsed["items"]
        return [parsed]
    if not isinstance(parsed, list):
        raise HTTPException(400, "JSON payload must be an array or an object with 'items'.")
    return parsed


def _parse_csv(content: bytes) -> List[Dict[str, Any]]:
    text_stream = io.StringIO(content.decode("utf-8"))
    reader = csv.DictReader(text_stream)
    return [row for row in reader]
