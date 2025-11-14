"""Data request models and builders.

This module defines the DataRequest model that encapsulates all parameters
needed to route a data request through the DataRouter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .enums import DataFeature, InstrumentType, MarketType, Timeframe, TransportKind


@dataclass(frozen=True)
class DataRequest:
    """Encapsulates all parameters for a data request.

    This model is used by DataRouter to coordinate URM resolution,
    capability validation, and provider method invocation.
    """

    # Core routing parameters
    feature: DataFeature
    transport: TransportKind
    exchange: str
    market_type: MarketType
    instrument_type: InstrumentType = InstrumentType.SPOT

    # Symbol identification (can be alias, URM ID, exchange-native, or InstrumentSpec)
    symbol: str | None = None
    symbols: list[str] | None = None

    # Feature-specific parameters
    timeframe: Timeframe | str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int | None = None
    depth: int | None = None
    period: str | None = None
    update_speed: str | None = None
    only_closed: bool = False
    throttle_ms: int | None = None
    dedupe_same_candle: bool = False
    historical: bool = False
    max_chunks: int | None = None

    # Additional parameters
    extra_params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate request parameters."""
        if (
            self.symbol is None
            and self.symbols is None
            and self.feature not in (DataFeature.LIQUIDATIONS,)
        ):
            raise ValueError("Either 'symbol' or 'symbols' must be provided")

        if self.symbol is not None and self.symbols is not None:
            raise ValueError("Cannot specify both 'symbol' and 'symbols'")

        # Validate timeframe for OHLCV
        if (
            self.feature == DataFeature.OHLCV
            and self.transport == TransportKind.REST
            and self.timeframe is None
        ):
            raise ValueError("timeframe is required for OHLCV REST requests")

        # Validate depth for order book
        if self.feature == DataFeature.ORDER_BOOK and self.depth is None:
            # Set default depth
            object.__setattr__(self, "depth", 100)


class DataRequestBuilder:
    """Builder for creating DataRequest instances with a fluent API."""

    def __init__(self) -> None:
        """Initialize builder with defaults."""
        self._feature: DataFeature | None = None
        self._transport: TransportKind | None = None
        self._exchange: str | None = None
        self._market_type: MarketType | None = None
        self._instrument_type: InstrumentType = InstrumentType.SPOT
        self._symbol: str | None = None
        self._symbols: list[str] | None = None
        self._timeframe: Timeframe | str | None = None
        self._start_time: datetime | None = None
        self._end_time: datetime | None = None
        self._limit: int | None = None
        self._depth: int | None = None
        self._period: str | None = None
        self._update_speed: str | None = None
        self._only_closed: bool = False
        self._throttle_ms: int | None = None
        self._dedupe_same_candle: bool = False
        self._historical: bool = False
        self._max_chunks: int | None = None
        self._extra_params: dict[str, Any] = {}

    def feature(self, feature: DataFeature) -> DataRequestBuilder:
        """Set the data feature."""
        self._feature = feature
        return self

    def transport(self, transport: TransportKind) -> DataRequestBuilder:
        """Set the transport kind."""
        self._transport = transport
        return self

    def exchange(self, exchange: str) -> DataRequestBuilder:
        """Set the exchange."""
        self._exchange = exchange
        return self

    def market_type(self, market_type: MarketType) -> DataRequestBuilder:
        """Set the market type."""
        self._market_type = market_type
        return self

    def instrument_type(self, instrument_type: InstrumentType) -> DataRequestBuilder:
        """Set the instrument type."""
        self._instrument_type = instrument_type
        return self

    def symbol(self, symbol: str) -> DataRequestBuilder:
        """Set a single symbol."""
        self._symbol = symbol
        self._symbols = None
        return self

    def symbols(self, symbols: list[str]) -> DataRequestBuilder:
        """Set multiple symbols."""
        self._symbols = symbols
        self._symbol = None
        return self

    def timeframe(self, timeframe: Timeframe | str) -> DataRequestBuilder:
        """Set the timeframe."""
        self._timeframe = timeframe
        return self

    def start_time(self, start_time: datetime) -> DataRequestBuilder:
        """Set the start time."""
        self._start_time = start_time
        return self

    def end_time(self, end_time: datetime) -> DataRequestBuilder:
        """Set the end time."""
        self._end_time = end_time
        return self

    def limit(self, limit: int) -> DataRequestBuilder:
        """Set the limit."""
        self._limit = limit
        return self

    def depth(self, depth: int) -> DataRequestBuilder:
        """Set the order book depth."""
        self._depth = depth
        return self

    def period(self, period: str) -> DataRequestBuilder:
        """Set the period (for open interest, funding rates)."""
        self._period = period
        return self

    def update_speed(self, update_speed: str) -> DataRequestBuilder:
        """Set the update speed (for WebSocket streams)."""
        self._update_speed = update_speed
        return self

    def only_closed(self, only_closed: bool = True) -> DataRequestBuilder:
        """Set only_closed flag for OHLCV streams."""
        self._only_closed = only_closed
        return self

    def throttle_ms(self, throttle_ms: int) -> DataRequestBuilder:
        """Set throttle milliseconds for streams."""
        self._throttle_ms = throttle_ms
        return self

    def dedupe_same_candle(self, dedupe: bool = True) -> DataRequestBuilder:
        """Set dedupe_same_candle flag for OHLCV streams."""
        self._dedupe_same_candle = dedupe
        return self

    def historical(self, historical: bool = True) -> DataRequestBuilder:
        """Set historical flag for open interest."""
        self._historical = historical
        return self

    def max_chunks(self, max_chunks: int) -> DataRequestBuilder:
        """Set max_chunks for paginated requests."""
        self._max_chunks = max_chunks
        return self

    def extra_param(self, key: str, value: Any) -> DataRequestBuilder:
        """Add an extra parameter."""
        self._extra_params[key] = value
        return self

    def build(self) -> DataRequest:
        """Build the DataRequest."""
        if self._feature is None:
            raise ValueError("feature is required")
        if self._transport is None:
            raise ValueError("transport is required")
        if self._exchange is None:
            raise ValueError("exchange is required")
        if self._market_type is None:
            raise ValueError("market_type is required")

        return DataRequest(
            feature=self._feature,
            transport=self._transport,
            exchange=self._exchange,
            market_type=self._market_type,
            instrument_type=self._instrument_type,
            symbol=self._symbol,
            symbols=self._symbols,
            timeframe=self._timeframe,
            start_time=self._start_time,
            end_time=self._end_time,
            limit=self._limit,
            depth=self._depth,
            period=self._period,
            update_speed=self._update_speed,
            only_closed=self._only_closed,
            throttle_ms=self._throttle_ms,
            dedupe_same_candle=self._dedupe_same_candle,
            historical=self._historical,
            max_chunks=self._max_chunks,
            extra_params=self._extra_params,
        )


# Convenience factory functions
def request(
    feature: DataFeature,
    transport: TransportKind,
    *,
    exchange: str,
    market_type: MarketType,
    instrument_type: InstrumentType = InstrumentType.SPOT,
    symbol: str | None = None,
    symbols: list[str] | None = None,
    **kwargs: Any,
) -> DataRequest:
    """Create a DataRequest with a simple function call.

    Args:
        feature: Data feature to request
        transport: Transport kind (REST or WS)
        exchange: Exchange name
        market_type: Market type (spot or futures)
        instrument_type: Instrument type (default: SPOT)
        symbol: Single symbol (alias, URM ID, or exchange-native)
        symbols: Multiple symbols
        **kwargs: Additional parameters (timeframe, limit, depth, etc.)

    Returns:
        DataRequest instance

    Example:
        >>> req = request(
        ...     DataFeature.OHLCV,
        ...     TransportKind.REST,
        ...     exchange="binance",
        ...     market_type=MarketType.SPOT,
        ...     symbol="BTCUSDT",
        ...     timeframe=Timeframe.H1,
        ...     limit=100,
        ... )
    """
    builder = (
        DataRequestBuilder()
        .feature(feature)
        .transport(transport)
        .exchange(exchange)
        .market_type(market_type)
        .instrument_type(instrument_type)
    )

    if symbol is not None:
        builder.symbol(symbol)
    elif symbols is not None:
        builder.symbols(symbols)

    # Map kwargs to builder methods
    for key, value in kwargs.items():
        if hasattr(builder, key):
            getattr(builder, key)(value)
        else:
            builder.extra_param(key, value)

    return builder.build()
