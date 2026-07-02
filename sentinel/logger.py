"""Structured JSON logging with run and correlation context."""
from __future__ import annotations

import contextvars
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

from .config import settings

_run_id = contextvars.ContextVar("run_id", default="-")
_correlation_id = contextvars.ContextVar("correlation_id", default="-")
_STANDARD = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


def set_run_id(value: str | None = None) -> str:
    """Set and return the current pipeline run identifier."""
    identifier = value or uuid.uuid4().hex[:12]
    _run_id.set(identifier)
    return identifier


def set_correlation_id(value: str | None = None) -> str:
    """Set and return the current case or driver correlation identifier."""
    identifier = value or uuid.uuid4().hex[:12]
    _correlation_id.set(identifier)
    return identifier


class JsonFormatter(logging.Formatter):
    """Serialize log records into one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "run_id": _run_id.get(),
            "correlation_id": _correlation_id.get(),
        }
        payload.update(
            {key: value for key, value in record.__dict__.items() if key not in _STANDARD}
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str | None = None) -> None:
    """Configure root logging once for CLI and module entry points."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel((level or settings.log_level).upper())
