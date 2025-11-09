"""Event system for real-time data streaming."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .bar import Bar


class DataEventType(Enum):
    """Types of data events."""

    CANDLE_UPDATE = "candle_update"
    CANDLE_CLOSED = "candle_closed"
    CONNECTION_STATUS = "connection_status"


class ConnectionStatus(Enum):
    """Connection status types."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    STALE = "stale"


@dataclass(frozen=True)
class ConnectionEvent:
    """Connection status event."""

    status: ConnectionStatus
    connection_id: str
    timestamp: datetime
    symbols_count: int = 0
    error: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


@dataclass(frozen=True)
class DataEvent:
    """Structured event for data streaming."""

    event_type: DataEventType
    timestamp: datetime
    symbol: str
    bar: Bar | None = None
    connection_id: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

    @classmethod
    def bar_update(
        cls,
        bar: Bar,
        symbol: str,
        connection_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DataEvent:
        """Create a bar update event."""
        event_type = DataEventType.CANDLE_CLOSED if bar.is_closed else DataEventType.CANDLE_UPDATE
        return cls(
            event_type=event_type,
            timestamp=datetime.now(),
            symbol=symbol,
            bar=bar,
            connection_id=connection_id,
            metadata=metadata or {},
        )

    @classmethod
    def connection_status(
        cls,
        connection_event: ConnectionEvent,
    ) -> DataEvent:
        """Create a connection status event."""
        return cls(
            event_type=DataEventType.CONNECTION_STATUS,
            timestamp=connection_event.timestamp,
            symbol="",  # No specific symbol for connection events
            connection_id=connection_event.connection_id,
            metadata={
                "status": connection_event.status.value,
                "symbols_count": connection_event.symbols_count,
                "error": connection_event.error,
                **(connection_event.metadata or {}),
            },
        )
