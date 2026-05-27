"""Event emitter/listener for internal process tracking.

Provides an in-process pub/sub bus used to trace:
 - document uploads
 - tax-engine calculation steps
 - data-purge operations

Structured log lines are emitted for every event so that the
audit trail exists even before a persistent event store is added later.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

import structlog

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

class EventType(str, Enum):
    # Document lifecycle
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PARSE_STARTED = "document.parse.started"
    DOCUMENT_PARSE_COMPLETED = "document.parse.completed"
    DOCUMENT_PARSE_FAILED = "document.parse.failed"

    # Tax engine
    TAX_CALCULATION_STARTED = "tax.calculation.started"
    TAX_CALCULATION_STEP = "tax.calculation.step"
    TAX_CALCULATION_COMPLETED = "tax.calculation.completed"
    TAX_CALCULATION_ERROR = "tax.calculation.error"

    # Data management
    DATA_PURGE_STARTED = "data.purge.started"
    DATA_PURGE_COMPLETED = "data.purge.completed"

    # User / session
    USER_CREATED = "user.created"
    SESSION_STARTED = "session.started"


@dataclass
class Event:
    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Listener type alias
# ---------------------------------------------------------------------------

Listener = Callable[[Event], Any]


class EventBus:
    """Simple in-process event bus with synchronous and async listeners."""

    def __init__(self) -> None:
        self._listeners: dict[EventType, list[Listener]] = {}

    def on(self, event_type: EventType, listener: Listener):
        """Register a listener for a specific event type."""
        self._listeners.setdefault(event_type, []).append(listener)
        return lambda: self.off(event_type, listener)

    def off(self, event_type: EventType, listener: Listener):
        """Remove a listener."""
        listeners = self._listeners.get(event_type, [])
        if listener in listeners:
            listeners.remove(listener)

    async def emit(self, event: Event) -> None:
        """Emit an event to all registered listeners and log it."""
        # Always log the event for audit trail
        logger.info(
            "event.emitted",
            event_type=event.type.value,
            event_id=event.event_id,
            payload=event.payload,
        )

        for listener in self._listeners.get(event.type, []):
            result = listener(event)
            if asyncio.iscoroutinefunction(listener):
                await result
            elif asyncio.iscoroutine(result):
                await result


# Module-level singleton used by routers / services
bus = EventBus()
