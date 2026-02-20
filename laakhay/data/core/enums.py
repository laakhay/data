"""Core enumerations for standardized types across all providers.

Re-exports core types from laakhay-core and defines data-specific enums.
"""

from enum import Enum

from laakhay.core import (
    InstrumentType,
    MarketType,
    MarketVariant,
)
from laakhay.core import (
    Timeframe as CoreTimeframe,
)
from laakhay.core.models import InstrumentSpec


class Timeframe(CoreTimeframe):
    """Data-specific timeframe with legacy compatibility."""

    @property
    def value(self) -> str:
        """Compatibility property for legacy code expecting .value."""
        return str(self)

    @classmethod
    def from_str(cls, value: str) -> "Timeframe":
        """Compatibility method for legacy code."""
        return cls(value)

    # Standard constants
    M1: "Timeframe"
    M3: "Timeframe"
    M5: "Timeframe"
    M15: "Timeframe"
    M30: "Timeframe"
    H1: "Timeframe"
    H2: "Timeframe"
    H4: "Timeframe"
    H6: "Timeframe"
    H8: "Timeframe"
    H12: "Timeframe"
    D1: "Timeframe"
    D3: "Timeframe"
    W1: "Timeframe"
    MO1: "Timeframe"

    # Iterable support for discovery
    @classmethod
    def all(cls):
        return [
            cls.M1,
            cls.M3,
            cls.M5,
            cls.M15,
            cls.M30,
            cls.H1,
            cls.H2,
            cls.H4,
            cls.H6,
            cls.H8,
            cls.H12,
            cls.D1,
            cls.D3,
            cls.W1,
            cls.MO1,
        ]


# Initialize constants
Timeframe.M1 = Timeframe("1m")
Timeframe.M3 = Timeframe("3m")
Timeframe.M5 = Timeframe("5m")
Timeframe.M15 = Timeframe("15m")
Timeframe.M30 = Timeframe("30m")
Timeframe.H1 = Timeframe("1h")
Timeframe.H2 = Timeframe("2h")
Timeframe.H4 = Timeframe("4h")
Timeframe.H6 = Timeframe("6h")
Timeframe.H8 = Timeframe("8h")
Timeframe.H12 = Timeframe("12h")
Timeframe.D1 = Timeframe("1d")
Timeframe.D3 = Timeframe("3d")
Timeframe.W1 = Timeframe("1w")
Timeframe.MO1 = Timeframe("1M")


# Data-specific features and transports
class DataFeature(str, Enum):
    """Data features available from exchanges."""

    OHLCV = "ohlcv"
    HEALTH = "health"
    ORDER_BOOK = "order_book"
    TRADES = "trades"
    HISTORICAL_TRADES = "historical_trades"
    LIQUIDATIONS = "liquidations"
    OPEN_INTEREST = "open_interest"
    FUNDING_RATE = "funding_rates"
    MARK_PRICE = "mark_price"
    SYMBOL_METADATA = "symbol_metadata"

    def __str__(self) -> str:
        return self.value


class TransportKind(str, Enum):
    """Transport mechanisms for data access."""

    REST = "rest"
    WS = "ws"

    def __str__(self) -> str:
        return self.value


__all__ = [
    "Timeframe",
    "DataFeature",
    "TransportKind",
    "InstrumentType",
    "MarketType",
    "MarketVariant",
    "InstrumentSpec",
]
