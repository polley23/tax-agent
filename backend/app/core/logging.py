"""Structured JSON logging with request correlation IDs and tax-engine step traces."""

import logging
import sys
import uuid
from typing import Any

import structlog

from app.config import get_settings


# ---------------------------------------------------------------------------
# Context keys used across log lines to correlate related events
# ---------------------------------------------------------------------------
REQUEST_ID_KEY = "request_id"
TAX_STEP_KEY = "tax_step"
TAX_ENGINE_KEY = "tax_engine"


class _Renderer:
    """Choose between JSON and console renderer based on config."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def __call__(self, _: Any, __: Any, event_dict: dict[str, Any]) -> str:
        if self.settings.log_json:
            import json
            return json.dumps(event_dict, default=str)
        return structlog.dev.ConsoleRenderer().render(_, __, event_dict)


def _add_request_id(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN401
    """Ensure every log line carries a request_id (created lazily)."""
    if REQUEST_ID_KEY not in event_dict:
        event_dict[REQUEST_ID_KEY] = str(uuid.uuid4())
    return event_dict


def setup_logging() -> None:
    """Initialise structlog for the entire process."""
    settings = get_settings()

    # Share state between the standard logging bridge and structlog
    shared = structlog.stdlib.LoggerFactory()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_request_id,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            _Renderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=shared,
        cache_logger_on_first_use=True,
    )

    # Also configure the stdlib root logger so non-structlog libs route through
    # our handlers (uvicorn, sqlalchemy, etc.)
    level = getattr(logging, settings.log_level.upper(), logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.root.addHandler(handler)
    logging.root.setLevel(level)
