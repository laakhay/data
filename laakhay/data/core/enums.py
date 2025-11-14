"""Core enumerations for standardized types across all providers."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

# Conversion mapping
_SECONDS_MAP = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
    "3d": 259200,
    "1w": 604800,
    "1M": 2592000,  # 30 days approximation
}


class Timeframe(str, Enum):
    """Standardized time intervals normalized across all exchanges."""

    # Minutes
    M1 = "1m"
    M3 = "3m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"

    # Hours
    H1 = "1h"
    H2 = "2h"
    H4 = "4h"
    H6 = "6h"
    H8 = "8h"
    H12 = "12h"

    # Days/Weeks/Months
    D1 = "1d"
    D3 = "3d"
    W1 = "1w"
    MO1 = "1M"

    @property
    def seconds(self) -> int:
        """Number of seconds in this interval."""
        return _SECONDS_MAP[self.value]

    @property
    def milliseconds(self) -> int:
        """Number of milliseconds in this interval."""
        return self.seconds * 1000

    @classmethod
    def from_seconds(cls, seconds: int) -> Optional["Timeframe"]:
        """Get interval from seconds value. Returns None if no match."""
        for interval in cls:
            if interval.seconds == seconds:
                return interval
        return None

    @classmethod
    def from_str(cls, tf: str) -> Optional["Timeframe"]:
        """Get interval from string value. Returns None if no match."""
        try:
            return cls(tf)
        except ValueError:
            return None


class MarketType(str, Enum):
    """Market type for exchange trading.

    Different exchanges may support different market types.
    This enum standardizes market type identification across providers.
    """

    SPOT = "spot"
    FUTURES = "futures"

    def __str__(self) -> str:
        """String representation returns the value."""
        return self.value


class DataFeature(str, Enum):
    """Data features available from exchanges."""

    OHLCV = "ohlcv"
    ORDER_BOOK = "order_book"
    TRADES = "trades"
    LIQUIDATIONS = "liquidations"
    OPEN_INTEREST = "open_interest"
    FUNDING_RATE = "funding_rates"
    MARK_PRICE = "mark_price"
    SYMBOL_METADATA = "symbol_metadata"

    def __str__(self) -> str:
        """String representation returns the value."""
        return self.value


class TransportKind(str, Enum):
    """Transport mechanisms for data access."""

    REST = "rest"
    WS = "ws"

    def __str__(self) -> str:
        """String representation returns the value."""
        return self.value


class InstrumentType(str, Enum):
    """Instrument types for trading."""

    SPOT = "spot"
    PERPETUAL = "perpetual"
    FUTURE = "future"
    OPTION = "option"
    MOVE = "move"
    BASKET = "basket"

    def __str__(self) -> str:
        """String representation returns the value."""
        return self.value


@dataclass(frozen=True)
class InstrumentSpec:
    """Canonical description of an instrument.

    Encodes base, quote, instrument type, and optional metadata
    (expiry, strike, contract size, etc.).
    """

    base: str
    quote: str
    instrument_type: InstrumentType
    expiry: datetime | None = None
    strike: float | None = None
    contract_size: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """String representation."""
        parts = [f"{self.base}/{self.quote}"]
        if self.instrument_type != InstrumentType.SPOT:
            parts.append(self.instrument_type.value)
        if self.expiry:
            parts.append(self.expiry.strftime("%Y%m%d"))
        if self.strike:
            parts.append(f"C{int(self.strike)}" if self.strike else "")
        return ":".join(filter(None, parts))
