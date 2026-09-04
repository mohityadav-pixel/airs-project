"""Structured JSON logging. Never logs credentials."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

from app.core.config import settings

_REDACT_KEYS = {"token", "api_key", "apikey", "password", "secret", "authorization"}


def redact(payload: dict) -> dict:
    out = {}
    for k, v in payload.items():
        out[k] = "***redacted***" if k.lower() in _REDACT_KEYS else v
    return out


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            base["exception"] = self.formatException(record.exc_info)
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            base.update(redact(extra))
        return json.dumps(base, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.airs_log_level.upper())
    for noisy in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, level: int, message: str, **fields) -> None:
    logger.log(level, message, extra={"extra_fields": fields})
