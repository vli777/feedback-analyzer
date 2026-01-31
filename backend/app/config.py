import os

def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except Exception:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default


# Target: 30 RPM by default (NVIDIA free tier is ~40 RPM)
BULK_RATE_LIMIT_RPM = _env_float("BULK_RATE_LIMIT_RPM", 30.0)

# Number of feedback items to batch together in a single LLM call
BULK_BATCH_SIZE = _env_int("BULK_BATCH_SIZE", 10)

# Maximum number of batches to process in parallel
BULK_MAX_CONCURRENCY = _env_int("BULK_MAX_CONCURRENCY", 4)

# Fallback delay between LLM calls for bulk analysis
if BULK_RATE_LIMIT_RPM > 0:
    BULK_DELAY_SECONDS = max(60.0 / BULK_RATE_LIMIT_RPM, 0.1)
else:
    # Keep a small delay even if misconfigured
    BULK_DELAY_SECONDS = 2.0

# ── WebSocket pipeline settings ──────────────────────────────────────
STUB_WS_URL = os.getenv("STUB_WS_URL", "ws://localhost:8765")
WS_RECONNECT_BASE_DELAY = _env_float("WS_RECONNECT_BASE_DELAY", 1.0)
WS_RECONNECT_MAX_DELAY = _env_float("WS_RECONNECT_MAX_DELAY", 30.0)
WS_INBOUND_QUEUE_SIZE = _env_int("WS_INBOUND_QUEUE_SIZE", 256)
WS_WORKER_COUNT = _env_int("WS_WORKER_COUNT", 2)
WS_CURSOR_FILE = os.getenv("WS_CURSOR_FILE", "data/ws_cursors.json")
