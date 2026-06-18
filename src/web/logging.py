"""
Structured JSON logging configuration for the OpenF1 Data Platform API.

Provides:
  1. `configure_logging()` — sets up root logger with JSON formatter.
  2. `RequestIDFilter` — attaches request_id to every log record.
  3. Middleware helpers for FastAPI request logging.

Usage:
    from src.web.logging import configure_logging
    configure_logging(level="INFO")

    logger = logging.getLogger("openf1.api")
    logger.info("request completed", extra={"request_id": "...", "endpoint": "..."})
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects for structured logging.

    Output schema:
    {
        "timestamp": "2026-06-17T12:34:56.789Z",
        "level": "INFO",
        "logger": "openf1.api",
        "message": "...",
        "request_id": "abc-123",  (if available from extra)
        "endpoint": "/api/sessions",
        "method": "GET",
        "status_code": 200,
        "duration_ms": 42.5,
        ...any other `extra` fields
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include standard fields
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id  # type: ignore[attr-defined]
        if hasattr(record, "endpoint"):
            log_entry["endpoint"] = record.endpoint  # type: ignore[attr-defined]
        if hasattr(record, "method"):
            log_entry["method"] = record.method  # type: ignore[attr-defined]
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code  # type: ignore[attr-defined]
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms  # type: ignore[attr-defined]
        if hasattr(record, "client_ip"):
            log_entry["client_ip"] = record.client_ip  # type: ignore[attr-defined]
        if hasattr(record, "user_agent"):
            log_entry["user_agent"] = record.user_agent  # type: ignore[attr-defined]

        # Include exc_info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class RequestIDFilter(logging.Filter):
    """
    Attaches a `request_id` to log records if not already present.
    The actual request_id is set per-request by the middleware.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = None  # type: ignore[attr-defined]
        return True


def generate_request_id() -> str:
    """Generate a unique request ID (short UUID4)."""
    return str(uuid.uuid4())[:12]


def configure_logging(
    level: str = "INFO",
    json_format: bool = True,
) -> None:
    """
    Configure the root logger for structured JSON output.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_format: If True, use JSON formatter. If False, use standard
            text format (useful for local development).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicate log output
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    handler.setFormatter(formatter)
    handler.addFilter(RequestIDFilter())
    root_logger.addHandler(handler)

    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)


def get_request_logger(name: str = "openf1.api") -> logging.Logger:
    """
    Return a named logger for request-level logging.
    The request_id is injected via extra fields in the middleware.
    """
    return logging.getLogger(name)
