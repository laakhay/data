"""Core enumerations for standardized types across all providers."""

from enum import Enum
from typing import Optional

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
