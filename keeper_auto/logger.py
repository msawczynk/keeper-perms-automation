"""Structured JSON logger."""
import json, datetime, gzip, sys

def log(event: dict, compress: bool = True) -> bytes:
    event.setdefault("ts", datetime.datetime.utcnow().isoformat())
    data = json.dumps(event, separators=(",", ":")).encode()
    return gzip.compress(data) if compress else data
