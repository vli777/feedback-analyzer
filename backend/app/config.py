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

# Fallback delay between LLM calls for bulk analysis
if BULK_RATE_LIMIT_RPM > 0:
    BULK_DELAY_SECONDS = max(60.0 / BULK_RATE_LIMIT_RPM, 0.1)
else:
    # Keep a small delay even if misconfigured
    BULK_DELAY_SECONDS = 2.0
