"""Request builder for fluent DataRequest construction.

This module provides a fluent API for constructing DataRequest instances,
designed for use with DataAPI and as a standalone builder.

Architecture:
    The request builder implements the Builder pattern to provide a fluent,
    chainable API for constructing complex DataRequest objects. This module:
    - Re-exports the core DataRequestBuilder from core.request
    - Provides DataAPI-aware factory methods that handle default resolution
    - Enables programmatic request construction for advanced use cases

Design Decisions:
    - Fluent API: Method chaining improves readability for complex requests
    - Immutable result: build() returns frozen DataRequest, preventing modification
    - Default resolution: Factory methods accept DataAPI defaults for convenience
    - Re-export pattern: Core builder remains in core, API layer enhances it

Use Cases:
    - Programmatic request construction with many parameters
    - Building requests in loops or conditionally
    - Advanced users who want more control than DataAPI method parameters
    - Testing and mock data generation

See Also:
    - DataRequest: The immutable request model
    - DataAPI: High-level facade that uses builders internally
    - DataRouter: Routes DataRequest instances to providers
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.enums import (
    DataFeature,
    InstrumentType,
    MarketType,
    MarketVariant,
    Timeframe,
    TransportKind,
)
from ..core.request import DataRequest, DataRequestBuilder

if TYPE_CHECKING:
    pass

__all__ = [
    "DataRequest",
    "DataRequestBuilder",
    "APIRequestBuilder",
    "api_request",
]


class APIRequestBuilder(DataRequestBuilder):
    """Enhanced request builder with DataAPI-aware defaults.

    This builder extends the core DataRequestBuilder with factory methods
    that work seamlessly with DataAPI's default resolution pattern.

    Architecture:
        Extends DataRequestBuilder to add DataAPI-specific convenience methods.
        Factory methods accept optional parameters that resolve to DataAPI defaults
        if not provided, matching the behavior of DataAPI method parameters.

    Example:
        >>> # With DataAPI defaults
        >>> builder = APIRequestBuilder.with_defaults(
        ...     default_exchange="binance",
        ...     default_market_type=MarketType.SPOT,
        ... )
        >>> request = (builder
        ...     .feature(DataFeature.OHLCV)
        ...     .transport(TransportKind.REST)
        ...     .symbol("BTC/USDT")
        ...     .timeframe(Timeframe.H1)
        ...     .limit(100)
        ...     .build())

        >>> # Standalone usage (no defaults)
        >>> builder = APIRequestBuilder()
        >>> request = (builder
        ...     .feature(DataFeature.OHLCV)
        ...     .transport(TransportKind.REST)
        ...     .exchange("binance")
        ...     .market_type(MarketType.SPOT)
        ...     .symbol("BTC/USDT")
        ...     .timeframe(Timeframe.H1)
        ...     .limit(100)
        ...     .build())
    """

    def __init__(
        self,
        *,
        default_exchange: str | None = None,
        default_market_type: MarketType | None = None,
        default_market_variant: MarketVariant | None = None,
        default_instrument_type: InstrumentType = InstrumentType.SPOT,
        _from_dataapi: bool = False,
    ) -> None:
        """Initialize builder with optional DataAPI-style defaults.

        Args:
            default_exchange: Default exchange to use if exchange() not called
            default_market_type: Default market type if market_type() not called
            default_market_variant: Default market variant if market_variant() not called
            default_instrument_type: Default instrument type (default: SPOT)
            _from_dataapi: Internal flag indicating builder is from DataAPI context

        Architecture:
            Defaults are stored and applied during build() if not explicitly set.
            This matches DataAPI's default resolution pattern for consistency.
            The _from_dataapi flag ensures DataAPI-style error messages even when
            defaults are None.
        """
        super().__init__()
        self._default_exchange = default_exchange
        self._default_market_type = default_market_type
        self._default_market_variant = default_market_variant
        self._default_instrument_type = default_instrument_type
        self._from_dataapi = _from_dataapi

    @classmethod
    def with_defaults(
        cls,
        *,
        default_exchange: str | None = None,
        default_market_type: MarketType | None = None,
        default_market_variant: MarketVariant | None = None,
        default_instrument_type: InstrumentType = InstrumentType.SPOT,
        _from_dataapi: bool = False,
    ) -> APIRequestBuilder:
        """Create builder with DataAPI-style defaults.

        Args:
            default_exchange: Default exchange name
            default_market_type: Default market type
            default_market_variant: Default market variant
            default_instrument_type: Default instrument type
            _from_dataapi: Internal flag for DataAPI context (auto-set by DataAPI)

        Returns:
            APIRequestBuilder instance configured with defaults

        Architecture:
            Factory method pattern provides named constructor with defaults.
            Useful when creating multiple requests with same defaults.

        Example:
            >>> builder = APIRequestBuilder.with_defaults(
            ...     default_exchange="binance",
            ...     default_market_type=MarketType.SPOT,
            ... )
        """
        return cls(
            default_exchange=default_exchange,
            default_market_type=default_market_type,
            default_market_variant=default_market_variant,
            default_instrument_type=default_instrument_type,
            _from_dataapi=_from_dataapi,
        )

    def exchange(
        self,
        exchange: str | None = None,
    ) -> APIRequestBuilder:
        """Set the exchange, using default if None provided.

        Args:
            exchange: Exchange name, or None to use default

        Architecture:
            Overrides base method to support None parameter for default resolution.
            This enables builder usage that matches DataAPI method parameter behavior.

        Returns:
            Self for method chaining
        """
        if exchange is not None:
            self._exchange = exchange
        elif self._default_exchange is not None:
            self._exchange = self._default_exchange
        return self

    def market_type(
        self,
        market_type: MarketType | None = None,
    ) -> APIRequestBuilder:
        """Set the market type, using default if None provided.

        Args:
            market_type: Market type, or None to use default

        Architecture:
            Overrides base method to support None parameter for default resolution.

        Returns:
            Self for method chaining
        """
        if market_type is not None:
            self._market_type = market_type
        elif self._default_market_type is not None:
            self._market_type = self._default_market_type
        return self

    def market_variant(
        self,
        market_variant: MarketVariant | None = None,
    ) -> APIRequestBuilder:
        """Set the market variant, using default if None provided.

        Args:
            market_variant: Market variant, or None to use default

        Architecture:
            Overrides base method to support None parameter for default resolution.

        Returns:
            Self for method chaining
        """
        if market_variant is not None:
            self._market_variant = market_variant
        elif self._default_market_variant is not None:
            self._market_variant = self._default_market_variant
        return self

    def instrument_type(
        self,
        instrument_type: InstrumentType | None = None,
    ) -> APIRequestBuilder:
        """Set the instrument type, using default if None provided.

        Args:
            instrument_type: Instrument type, or None to use default

        Architecture:
            Overrides base method to support None parameter for default resolution.

        Returns:
            Self for method chaining
        """
        if instrument_type is not None:
            self._instrument_type = instrument_type
        else:
            self._instrument_type = self._default_instrument_type
        return self

    def build(self) -> DataRequest:
        """Build the DataRequest, applying defaults if needed.

        Architecture:
            Overrides build() to apply defaults before validation.
            Raises ValueError with DataAPI-style messages if required fields
            still missing after defaults applied.

        Returns:
            Immutable DataRequest instance

        Raises:
            ValueError: If required fields (feature, transport, exchange, market_type)
                        are missing even after applying defaults. Messages match
                        DataAPI's _resolve_* methods for consistency.
        """
        # Apply defaults if not explicitly set
        if self._exchange is None and self._default_exchange is not None:
            self._exchange = self._default_exchange
        if self._market_type is None and self._default_market_type is not None:
            self._market_type = self._default_market_type
        if self._market_variant is None and self._default_market_variant is not None:
            self._market_variant = self._default_market_variant

        # Check required fields with appropriate error messages
        # Use DataAPI-style messages if:
        # 1. Builder is from DataAPI context (_from_dataapi=True), OR
        # 2. Specific field has a default that was set but still missing
        # Otherwise use base builder messages for standalone usage
        if self._feature is None:
            raise ValueError("feature is required")
        if self._transport is None:
            raise ValueError("transport is required")
        if self._exchange is None and (self._from_dataapi or self._default_exchange is not None):
            raise ValueError("exchange must be provided (no default set)")
        if self._market_type is None and (
            self._from_dataapi or self._default_market_type is not None
        ):
            raise ValueError("market_type must be provided (no default set)")

        return super().build()

    # --- Convenience factory methods for common patterns --------------------

    @classmethod
    def for_ohlcv(
        cls,
        symbol: str,
        timeframe: Timeframe | str,
        *,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        instrument_type: InstrumentType | None = None,
        transport: TransportKind = TransportKind.REST,
    ) -> APIRequestBuilder:
        """Create builder pre-configured for OHLCV request.

        Args:
            symbol: Symbol identifier
            timeframe: Timeframe for bars
            exchange: Exchange name (optional, can be set later)
            market_type: Market type (optional, can be set later)
            instrument_type: Instrument type (optional, defaults to SPOT)
            transport: Transport kind (default: REST)

        Returns:
            APIRequestBuilder pre-configured for OHLCV

        Architecture:
            Factory method provides convenient starting point for common requests.
            Reduces boilerplate for most common use case.

        Example:
            >>> builder = APIRequestBuilder.for_ohlcv(
            ...     "BTC/USDT",
            ...     Timeframe.H1,
            ...     exchange="binance",
            ... )
            >>> request = builder.limit(100).build()
        """
        builder = cls()
        if exchange is not None:
            builder.exchange(exchange)
        if market_type is not None:
            builder.market_type(market_type)
        if instrument_type is not None:
            builder.instrument_type(instrument_type)

        return (
            builder.feature(DataFeature.OHLCV)
            .transport(transport)
            .symbol(symbol)
            .timeframe(timeframe)
        )

    @classmethod
    def for_order_book(
        cls,
        symbol: str,
        *,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        instrument_type: InstrumentType | None = None,
        transport: TransportKind = TransportKind.REST,
    ) -> APIRequestBuilder:
        """Create builder pre-configured for order book request.

        Args:
            symbol: Symbol identifier
            exchange: Exchange name (optional)
            market_type: Market type (optional)
            instrument_type: Instrument type (optional)
            transport: Transport kind (default: REST)

        Returns:
            APIRequestBuilder pre-configured for order book

        Example:
            >>> builder = APIRequestBuilder.for_order_book(
            ...     "BTC/USDT",
            ...     exchange="binance",
            ... )
            >>> request = builder.depth(100).build()
        """
        builder = cls()
        if exchange is not None:
            builder.exchange(exchange)
        if market_type is not None:
            builder.market_type(market_type)
        if instrument_type is not None:
            builder.instrument_type(instrument_type)

        return builder.feature(DataFeature.ORDER_BOOK).transport(transport).symbol(symbol)

    @classmethod
    def for_trades(
        cls,
        symbol: str,
        *,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        instrument_type: InstrumentType | None = None,
        transport: TransportKind = TransportKind.REST,
    ) -> APIRequestBuilder:
        """Create builder pre-configured for trades request.

        Args:
            symbol: Symbol identifier
            exchange: Exchange name (optional)
            market_type: Market type (optional)
            instrument_type: Instrument type (optional)
            transport: Transport kind (default: REST)

        Returns:
            APIRequestBuilder pre-configured for trades

        Example:
            >>> builder = APIRequestBuilder.for_trades(
            ...     "BTC/USDT",
            ...     exchange="binance",
            ... )
            >>> request = builder.limit(100).build()
        """
        builder = cls()
        if exchange is not None:
            builder.exchange(exchange)
        if market_type is not None:
            builder.market_type(market_type)
        if instrument_type is not None:
            builder.instrument_type(instrument_type)

        return builder.feature(DataFeature.TRADES).transport(transport).symbol(symbol)

    @classmethod
    def for_stream(
        cls,
        feature: DataFeature,
        symbol: str | list[str],
        *,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        instrument_type: InstrumentType | None = None,
        timeframe: Timeframe | str | None = None,
    ) -> APIRequestBuilder:
        """Create builder pre-configured for WebSocket stream.

        Args:
            feature: Data feature to stream
            symbol: Single symbol or list of symbols
            exchange: Exchange name (optional)
            market_type: Market type (optional)
            instrument_type: Instrument type (optional)
            timeframe: Timeframe (required for OHLCV streams)

        Returns:
            APIRequestBuilder pre-configured for streaming

        Architecture:
            Factory method for WebSocket streaming requests. Automatically sets
            transport to WS and handles single vs multiple symbols.

        Example:
            >>> builder = APIRequestBuilder.for_stream(
            ...     DataFeature.OHLCV,
            ...     "BTC/USDT",
            ...     exchange="binance",
            ...     timeframe=Timeframe.M1,
            ... )
            >>> request = builder.only_closed(True).build()
        """
        builder = cls()
        if exchange is not None:
            builder.exchange(exchange)
        if market_type is not None:
            builder.market_type(market_type)
        if instrument_type is not None:
            builder.instrument_type(instrument_type)

        builder.feature(feature).transport(TransportKind.WS)
        if isinstance(symbol, list):
            builder.symbols(symbol)
        else:
            builder.symbol(symbol)

        if timeframe is not None:
            builder.timeframe(timeframe)

        return builder


def api_request(
    feature: DataFeature,
    transport: TransportKind,
    *,
    exchange: str | None = None,
    market_type: MarketType | None = None,
    market_variant: MarketVariant | None = None,
    instrument_type: InstrumentType = InstrumentType.SPOT,
    default_exchange: str | None = None,
    default_market_type: MarketType | None = None,
    default_market_variant: MarketVariant | None = None,
    default_instrument_type: InstrumentType = InstrumentType.SPOT,
    symbol: str | None = None,
    symbols: list[str] | None = None,
    **kwargs: dict[str, object],
) -> DataRequest:
    """Convenience function to create DataRequest with DataAPI-style defaults.

    This function combines the convenience of the request() factory from core
    with the default resolution pattern from DataAPI.

    Args:
        feature: Data feature to request
        transport: Transport kind (REST or WS)
        exchange: Exchange name (uses default_exchange if not provided)
        market_type: Market type (uses default_market_type if not provided)
        market_variant: Market variant (uses default_market_variant if not provided)
        instrument_type: Instrument type (uses default_instrument_type if not provided)
        default_exchange: Default exchange for resolution
        default_market_type: Default market type for resolution
        default_market_variant: Default market variant for resolution
        default_instrument_type: Default instrument type for resolution
        symbol: Single symbol (alias, URM ID, or exchange-native)
        symbols: Multiple symbols
        **kwargs: Additional parameters (timeframe, limit, depth, etc.)

    Returns:
        DataRequest instance

    Architecture:
        Factory function provides one-shot request creation with default resolution.
        Useful for inline request creation when builder pattern is overkill.

    Example:
        >>> req = api_request(
        ...     DataFeature.OHLCV,
        ...     TransportKind.REST,
        ...     symbol="BTC/USDT",
        ...     timeframe=Timeframe.H1,
        ...     limit=100,
        ...     default_exchange="binance",
        ...     default_market_type=MarketType.SPOT,
        ... )

    See Also:
        - request(): Core factory function without default resolution
        - APIRequestBuilder: Fluent builder API
    """
    # Resolve defaults (prefer explicit over defaults)
    resolved_exchange = exchange if exchange is not None else default_exchange
    resolved_market_type = market_type if market_type is not None else default_market_type
    resolved_market_variant = (
        market_variant if market_variant is not None else default_market_variant
    )
    resolved_instrument_type = (
        instrument_type if instrument_type != InstrumentType.SPOT else default_instrument_type
    )

    if resolved_exchange is None:
        raise ValueError("exchange must be provided (no default_exchange set)")
    if resolved_market_type is None:
        raise ValueError("market_type must be provided (no default_market_type set)")

    # Use builder pattern with defaults
    builder = APIRequestBuilder.with_defaults(
        default_exchange=default_exchange,
        default_market_type=default_market_type,
        default_market_variant=default_market_variant,
        default_instrument_type=default_instrument_type,
    )

    # Set core parameters
    builder = (
        builder.feature(feature)
        .transport(transport)
        .exchange(resolved_exchange)
        .market_type(resolved_market_type)
        .instrument_type(resolved_instrument_type)
    )

    # Set market_variant if resolved
    if resolved_market_variant is not None:
        builder = builder.market_variant(resolved_market_variant)

    # Set symbol(s)
    if symbol is not None:
        builder = builder.symbol(symbol)
    elif symbols is not None:
        builder = builder.symbols(symbols)

    # Apply kwargs (timeframe, limit, etc.)
    for key, value in kwargs.items():
        if hasattr(builder, key):
            method = getattr(builder, key)
            builder = method(value)
        else:
            builder = builder.extra_param(key, value)

    return builder.build()
