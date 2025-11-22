"""Core enumerations for standardized types across all providers.

Architecture:
    This module defines all standardized enums and types used throughout the
    library. These enums provide type safety and ensure consistent values
    across all providers and exchanges.

Design Decisions:
    - String enums: Allow easy serialization and exchange compatibility
    - Frozen dataclass: InstrumentSpec is immutable for safety
    - Standardized values: Normalize differences between exchanges

Key Types:
    - Timeframe: Standardized time intervals
    - MarketType: Spot vs Futures markets
    - DataFeature: Available data features
    - TransportKind: REST vs WebSocket
    - InstrumentType: Spot, Perpetual, Future, Option, etc.
    - InstrumentSpec: Canonical instrument description

See Also:
    - URM: Uses InstrumentSpec for symbol normalization
    - Capabilities: Uses enums for capability queries
    - DataRouter: Uses enums for routing decisions
"""

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
    """Standardized time intervals normalized across all exchanges.

    Architecture:
        String enum allows easy conversion to/from exchange-specific formats.
        Provides helper methods for time calculations (seconds, milliseconds).
        All exchanges support a subset of these timeframes.
    """

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
    """Top-level market category for exchange trading.

    Different exchanges may support different market types.
    This enum standardizes high-level market category identification across providers.
    MarketType represents broad categories; for more specific variants, use MarketVariant.
    """

    SPOT = "spot"
    FUTURES = "futures"
    OPTIONS = "options"
    EQUITY = "equity"  # for cash equities
    FX = "fx"  # forex markets

    def __str__(self) -> str:
        """String representation returns the value."""
        return self.value


class MarketVariant(str, Enum):
    """Specific market variant within a MarketType.

    MarketVariant provides fine-grained distinction between different market
    implementations. For example, FUTURES can be LINEAR_PERP (USDT-margined)
    or INVERSE_PERP (coin-margined).

    Architecture:
        Some variants align with MarketType (e.g., SPOT).
        Others are more specific (e.g., LINEAR_PERP, INVERSE_PERP under FUTURES).
    """

    SPOT = "spot"  # cash/spot trading (works for crypto, equities, FX)
    LINEAR_PERP = "linear_perp"  # stable-quote perpetual (USDT-margined)
    INVERSE_PERP = "inverse_perp"  # coin-quote perpetual (BTCUSD, ETHUSD...)
    LINEAR_DELIVERY = "linear_delivery"  # expiring stable-quote futures
    INVERSE_DELIVERY = "inverse_delivery"  # expiring coin futures
    OPTIONS = "options"  # any options (equity or crypto)
    EQUITY = "equity"  # cash equities (optional if you want to distinguish)

    def __str__(self) -> str:
        """String representation returns the value."""
        return self.value

    @classmethod
    def from_market_type(
        cls, market_type: MarketType, default: "MarketVariant | None" = None
    ) -> "MarketVariant":
        """Get default MarketVariant for a MarketType.

        Args:
            market_type: The market type to get a variant for
            default: Optional default variant if market_type is FUTURES.
                    If None, defaults to LINEAR_PERP.

        Returns:
            The appropriate MarketVariant for the given MarketType

        Examples:
            >>> MarketVariant.from_market_type(MarketType.SPOT)
            <MarketVariant.SPOT: 'spot'>
            >>> MarketVariant.from_market_type(MarketType.FUTURES)
            <MarketVariant.LINEAR_PERP: 'linear_perp'>
            >>> MarketVariant.from_market_type(MarketType.FUTURES, MarketVariant.INVERSE_PERP)
            <MarketVariant.INVERSE_PERP: 'inverse_perp'>
        """
        if market_type == MarketType.SPOT:
            return cls.SPOT
        if market_type == MarketType.FUTURES:
            return default if default is not None else cls.LINEAR_PERP
        if market_type == MarketType.OPTIONS:
            return cls.OPTIONS
        if market_type == MarketType.EQUITY:
            return cls.EQUITY
        if market_type == MarketType.FX:
            return cls.SPOT  # FX spot uses the same SPOT variant
        raise ValueError(f"Unsupported market type: {market_type}")

    def to_market_type(self) -> MarketType:
        """Get the MarketType that this variant belongs to.

        Returns:
            The corresponding MarketType

        Examples:
            >>> MarketVariant.LINEAR_PERP.to_market_type()
            <MarketType.FUTURES: 'futures'>
            >>> MarketVariant.SPOT.to_market_type()
            <MarketType.SPOT: 'spot'>
        """
        if self == MarketVariant.SPOT:
            return MarketType.SPOT
        if self in (
            MarketVariant.LINEAR_PERP,
            MarketVariant.INVERSE_PERP,
            MarketVariant.LINEAR_DELIVERY,
            MarketVariant.INVERSE_DELIVERY,
        ):
            return MarketType.FUTURES
        if self == MarketVariant.OPTIONS:
            return MarketType.OPTIONS
        if self == MarketVariant.EQUITY:
            return MarketType.EQUITY
        raise ValueError(f"Cannot determine MarketType for variant: {self}")


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

    Architecture:
        This is the canonical representation used by URM for symbol normalization.
        Frozen dataclass ensures immutability. All exchange-specific symbols
        are converted to/from InstrumentSpec via URM mappers.

    Design Decision:
        Frozen dataclass prevents accidental modification during routing.
        Metadata dict allows extensibility for exchange-specific attributes.
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
