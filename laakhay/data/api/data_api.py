"""Ergonomic DataAPI facade for unified data access.

The DataAPI provides a high-level interface that wraps the DataRouter,
offering convenient fetch_* and stream_* methods while maintaining
backward compatibility with direct provider usage.

Architecture:
    This module implements the Facade pattern (GoF) to provide a simplified
    interface to the complex routing system. DataAPI handles:
    - Default parameter resolution (exchange, market_type, instrument_type)
    - Request construction (DataRequest from method parameters)
    - Delegation to DataRouter for actual routing
    - Resource lifecycle management

Design Decisions:
    - Facade pattern chosen over direct router access for better UX
    - Default parameters reduce boilerplate in common use cases
    - Router injection allows testing with mock routers
    - Context manager pattern ensures proper resource cleanup

See Also:
    - DataRouter: The underlying routing system
    - DataRequest: Request model used for routing
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ..core.enums import (
    DataFeature,
    InstrumentType,
    MarketType,
    MarketVariant,
    Timeframe,
    TransportKind,
)
from ..runtime.router import DataRouter
from .request_builder import APIRequestBuilder

if TYPE_CHECKING:
    from ..models import (
        OHLCV,
        FundingRate,
        Liquidation,
        MarkPrice,
        OpenInterest,
        OrderBook,
        Symbol,
        Trade,
    )

logger = logging.getLogger(__name__)


class DataAPI:
    """High-level facade for unified data access across exchanges.

    The DataAPI provides a single entry point for fetching and streaming
    market data, automatically handling URM resolution, capability validation,
    and provider routing.

    Example:
        >>> async with DataAPI() as api:
        ...     # Fetch OHLCV data
        ...     ohlcv = await api.fetch_ohlcv(
        ...         symbol="BTCUSDT",
        ...         timeframe=Timeframe.H1,
        ...         exchange="binance",
        ...         market_type=MarketType.SPOT,
        ...         limit=100,
        ...     )
        ...
        ...     # Stream trades
        ...     async for trade in api.stream_trades(
        ...         symbol="BTCUSDT",
        ...         exchange="binance",
        ...         market_type=MarketType.SPOT,
        ...     ):
        ...         print(trade)
    """

    def __init__(
        self,
        *,
        default_exchange: str | None = None,
        default_market_type: MarketType | None = None,
        default_market_variant: MarketVariant | None = None,
        default_instrument_type: InstrumentType = InstrumentType.SPOT,
        router: DataRouter | None = None,
    ) -> None:
        """Initialize the DataAPI.

        Args:
            default_exchange: Default exchange to use if not specified in method calls
            default_market_type: Default market type to use if not specified
            default_market_variant: Default market variant to use if not specified
            default_instrument_type: Default instrument type (default: SPOT)
            router: Optional DataRouter instance (creates new one if not provided)

        Note:
            Router injection allows dependency injection for testing. If not provided,
            a new DataRouter is created, which uses the global ProviderRegistry singleton.
        """
        self._default_exchange = default_exchange
        self._default_market_type = default_market_type
        self._default_market_variant = default_market_variant
        self._default_instrument_type = default_instrument_type
        # Architecture: Router injection for testability (dependency injection pattern)
        self._owns_router = router is None
        self._router = router or DataRouter()
        self._closed = False

    def _resolve_exchange(self, exchange: str | None) -> str:
        """Resolve exchange parameter.

        Resolution order:
            1. Explicit parameter (method argument)
            2. Default from __init__
            3. Raise error if neither provided

        This pattern allows method-level overrides while supporting defaults.
        """
        if exchange is not None:
            return exchange
        if self._default_exchange is not None:
            return self._default_exchange
        raise ValueError("exchange must be provided (no default set)")

    def _resolve_market_type(self, market_type: MarketType | None) -> MarketType:
        """Resolve market type parameter."""
        if market_type is not None:
            return market_type
        if self._default_market_type is not None:
            return self._default_market_type
        raise ValueError("market_type must be provided (no default set)")

    def _resolve_market_variant(self, market_variant: MarketVariant | None) -> MarketVariant | None:
        """Resolve market variant parameter.

        Returns None if not provided and no default set (will be derived from market_type).
        """
        if market_variant is not None:
            return market_variant
        return self._default_market_variant

    def _resolve_instrument_type(self, instrument_type: InstrumentType | None) -> InstrumentType:
        """Resolve instrument type parameter."""
        if instrument_type is not None:
            return instrument_type
        return self._default_instrument_type

    def _create_request_builder(
        self,
        feature: DataFeature,
        transport: TransportKind,
        *,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType | None = None,
    ) -> APIRequestBuilder:
        """Create an APIRequestBuilder with resolved defaults.

        Architecture:
            Helper method encapsulates the pattern of resolving defaults and
            creating a request builder. This reduces boilerplate in methods
            while maintaining the same functionality.

        Args:
            feature: Data feature to request
            transport: Transport kind (REST or WS)
            exchange: Exchange name (uses default if not provided)
            market_type: Market type (uses default if not provided)
            market_variant: Market variant (uses default if not provided, None if no default)
            instrument_type: Instrument type (uses default if not provided)

        Returns:
            APIRequestBuilder configured with defaults and resolved parameters

        Design Decision:
            Returns builder instead of DataRequest to allow method chaining
            in calling methods for feature-specific parameters. The _from_dataapi
            flag ensures DataAPI-style error messages are always used.
        """
        resolved_market_variant = self._resolve_market_variant(market_variant)
        builder = (
            APIRequestBuilder.with_defaults(
                default_exchange=self._default_exchange,
                default_market_type=self._default_market_type,
                default_market_variant=self._default_market_variant,
                default_instrument_type=self._default_instrument_type,
                _from_dataapi=True,  # Always use DataAPI-style error messages
            )
            .feature(feature)
            .transport(transport)
            .exchange(exchange)
            .market_type(market_type)
            .instrument_type(instrument_type)
        )
        if resolved_market_variant is not None:
            builder = builder.market_variant(resolved_market_variant)
        return builder

    # --- REST / Historical Methods -------------------------------------------

    async def fetch_health(
        self,
        *,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType | None = None,
    ) -> dict[str, Any]:
        """Fetch exchange health information."""
        request = self._create_request_builder(
            DataFeature.HEALTH,
            TransportKind.REST,
            exchange=exchange,
            market_type=market_type,
            market_variant=market_variant,
            instrument_type=instrument_type,
        ).build()
        logger.debug(
            "Fetching health",
            extra={
                "exchange": request.exchange,
                "market_type": request.market_type.value,
            },
        )
        return await self._router.route(request)

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe | str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
        max_chunks: int | None = None,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType | None = None,
    ) -> OHLCV:
        """Fetch OHLCV bar history.

        Args:
            symbol: Symbol identifier (alias, URM ID, or exchange-native)
            timeframe: Timeframe for bars
            start_time: Optional start time for historical data
            end_time: Optional end time for historical data
            limit: Maximum number of bars to fetch
            max_chunks: Maximum number of pagination chunks
            exchange: Exchange name (uses default if set)
            market_type: Market type (uses default if set)
            market_variant: Market variant (uses default if set, derived from market_type otherwise)
            instrument_type: Instrument type (default: SPOT)

        Returns:
            OHLCV data series

        Raises:
            CapabilityError: If OHLCV REST is not supported
            SymbolResolutionError: If symbol cannot be resolved
        """
        # Architecture: Build DataRequest using builder pattern
        # This reduces boilerplate while maintaining same functionality
        request = (
            self._create_request_builder(
                DataFeature.OHLCV,
                TransportKind.REST,
                exchange=exchange,
                market_type=market_type,
                market_variant=market_variant,
                instrument_type=instrument_type,
            )
            .symbol(symbol)
            .timeframe(timeframe)
            .start_time(start_time)
            .end_time(end_time)
            .limit(limit)
            .max_chunks(max_chunks)
            .build()
        )
        logger.debug(
            "Fetching OHLCV",
            extra={
                "exchange": request.exchange,
                "symbol": symbol,
                "timeframe": str(timeframe),
            },
        )
        # Architecture: Delegate to DataRouter for actual routing
        # Router handles: capability validation, URM resolution, provider lookup
        return await self._router.route(request)

    async def fetch_order_book(
        self,
        symbol: str,
        *,
        depth: int = 100,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType | None = None,
    ) -> OrderBook:
        """Fetch order book snapshot.

        Args:
            symbol: Symbol identifier
            depth: Order book depth (default: 100)
            exchange: Exchange name (uses default if set)
            market_type: Market type (uses default if set)
            market_variant: Market variant (uses default if set, derived from market_type otherwise)
            instrument_type: Instrument type (default: SPOT)

        Returns:
            OrderBook with computed metrics

        Raises:
            CapabilityError: If order book REST is not supported
            SymbolResolutionError: If symbol cannot be resolved
        """
        request = (
            self._create_request_builder(
                DataFeature.ORDER_BOOK,
                TransportKind.REST,
                exchange=exchange,
                market_type=market_type,
                market_variant=market_variant,
                instrument_type=instrument_type,
            )
            .symbol(symbol)
            .depth(depth)
            .build()
        )
        logger.debug(
            "Fetching order book",
            extra={"exchange": request.exchange, "symbol": symbol, "depth": depth},
        )
        return await self._router.route(request)

    async def fetch_recent_trades(
        self,
        symbol: str,
        *,
        limit: int = 500,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType | None = None,
    ) -> list[Trade]:
        """Fetch recent trades.

        Args:
            symbol: Symbol identifier
            limit: Maximum number of trades (default: 500)
            exchange: Exchange name (uses default if set)
            market_type: Market type (uses default if set)
            market_variant: Market variant (uses default if set, derived from market_type otherwise)
            instrument_type: Instrument type (default: SPOT)

        Returns:
            List of recent trades

        Raises:
            CapabilityError: If trades REST is not supported
            SymbolResolutionError: If symbol cannot be resolved
        """
        request = (
            self._create_request_builder(
                DataFeature.TRADES,
                TransportKind.REST,
                exchange=exchange,
                market_type=market_type,
                market_variant=market_variant,
                instrument_type=instrument_type,
            )
            .symbol(symbol)
            .limit(limit)
            .build()
        )
        logger.debug(
            "Fetching recent trades",
            extra={"exchange": request.exchange, "symbol": symbol, "limit": limit},
        )
        return await self._router.route(request)

    async def fetch_historical_trades(
        self,
        symbol: str,
        *,
        limit: int | None = None,
        from_id: int | None = None,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType | None = None,
    ) -> list[Trade]:
        """Fetch historical trades with exchange pagination support."""
        request = (
            self._create_request_builder(
                DataFeature.HISTORICAL_TRADES,
                TransportKind.REST,
                exchange=exchange,
                market_type=market_type,
                market_variant=market_variant,
                instrument_type=instrument_type,
            )
            .symbol(symbol)
            .limit(limit)
            .from_id(from_id)
            .build()
        )
        logger.debug(
            "Fetching historical trades",
            extra={
                "exchange": request.exchange,
                "symbol": symbol,
                "limit": limit,
                "from_id": from_id,
            },
        )
        return await self._router.route(request)

    async def fetch_symbols(
        self,
        *,
        quote_asset: str | None = None,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        market_variant: MarketVariant | None = None,
        use_cache: bool = True,
    ) -> list[Symbol]:
        """Fetch symbol metadata.

        Args:
            quote_asset: Optional quote asset filter
            exchange: Exchange name (uses default if set)
            market_type: Market type (uses default if set)
            market_variant: Market variant (uses default if set, derived from market_type otherwise)
            use_cache: Whether to use cached symbol data

        Returns:
            List of symbol metadata

        Raises:
            CapabilityError: If symbol metadata REST is not supported
        """
        request = (
            self._create_request_builder(
                DataFeature.SYMBOL_METADATA,
                TransportKind.REST,
                exchange=exchange,
                market_type=market_type,
                market_variant=market_variant,
                instrument_type=InstrumentType.SPOT,  # Symbol metadata doesn't use instrument_type
            )
            .extra_param("quote_asset", quote_asset)
            .extra_param("use_cache", use_cache)
            .build()
        )
        logger.debug(
            "Fetching symbols",
            extra={"exchange": request.exchange, "quote_asset": quote_asset},
        )
        return await self._router.route(request)

    async def fetch_open_interest(
        self,
        symbol: str,
        *,
        historical: bool = False,
        period: str = "5m",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 30,
        exchange: str | None = None,
        market_type: MarketType = MarketType.FUTURES,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType = InstrumentType.PERPETUAL,
    ) -> list[OpenInterest]:
        """Fetch open interest data.

        Args:
            symbol: Symbol identifier
            historical: Whether to fetch historical data
            period: Period for open interest (default: "5m")
            start_time: Optional start time for historical data
            end_time: Optional end time for historical data
            limit: Maximum number of records
            exchange: Exchange name (uses default if set)
            market_type: Market type (default: FUTURES)
            market_variant: Market variant (uses default if set, derived from market_type otherwise)
            instrument_type: Instrument type (default: PERPETUAL)

        Returns:
            List of open interest records

        Raises:
            CapabilityError: If open interest REST is not supported
            SymbolResolutionError: If symbol cannot be resolved
        """
        request = (
            self._create_request_builder(
                DataFeature.OPEN_INTEREST,
                TransportKind.REST,
                exchange=exchange,
                market_type=market_type,
                market_variant=market_variant,
                instrument_type=instrument_type,
            )
            .symbol(symbol)
            .historical(historical)
            .period(period)
            .start_time(start_time)
            .end_time(end_time)
            .limit(limit)
            .build()
        )
        logger.debug(
            "Fetching open interest",
            extra={
                "exchange": request.exchange,
                "symbol": symbol,
                "historical": historical,
            },
        )
        return await self._router.route(request)

    async def fetch_funding_rates(
        self,
        symbol: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        exchange: str | None = None,
        market_type: MarketType = MarketType.FUTURES,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType = InstrumentType.PERPETUAL,
    ) -> list[FundingRate]:
        """Fetch funding rate data.

        Args:
            symbol: Symbol identifier
            start_time: Optional start time for historical data
            end_time: Optional end time for historical data
            limit: Maximum number of records
            exchange: Exchange name (uses default if set)
            market_type: Market type (default: FUTURES)
            market_variant: Market variant (uses default if set, derived from market_type otherwise)
            instrument_type: Instrument type (default: PERPETUAL)

        Returns:
            List of funding rate records

        Raises:
            CapabilityError: If funding rate REST is not supported
            SymbolResolutionError: If symbol cannot be resolved
        """
        request = (
            self._create_request_builder(
                DataFeature.FUNDING_RATE,
                TransportKind.REST,
                exchange=exchange,
                market_type=market_type,
                market_variant=market_variant,
                instrument_type=instrument_type,
            )
            .symbol(symbol)
            .start_time(start_time)
            .end_time(end_time)
            .limit(limit)
            .build()
        )
        logger.debug(
            "Fetching funding rates",
            extra={"exchange": request.exchange, "symbol": symbol},
        )
        return await self._router.route(request)

    # --- WebSocket / Streaming Methods ---------------------------------------

    async def stream_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType | None = None,
    ) -> AsyncIterator[Any]:  # StreamingBar
        """Stream real-time OHLCV updates.

        Args:
            symbol: Symbol identifier
            timeframe: Timeframe for bars
            only_closed: Only emit closed candles
            throttle_ms: Throttle updates (milliseconds)
            dedupe_same_candle: Deduplicate same candle updates
            exchange: Exchange name (uses default if set)
            market_type: Market type (uses default if set)
            market_variant: Market variant (uses default if set, derived from market_type otherwise)
            instrument_type: Instrument type (default: SPOT)

        Yields:
            StreamingBar updates

        Raises:
            CapabilityError: If OHLCV WS is not supported
            SymbolResolutionError: If symbol cannot be resolved
        """
        request = (
            self._create_request_builder(
                DataFeature.OHLCV,
                TransportKind.WS,
                exchange=exchange,
                market_type=market_type,
                market_variant=market_variant,
                instrument_type=instrument_type,
            )
            .symbol(symbol)
            .timeframe(timeframe)
            .only_closed(only_closed)
            .throttle_ms(throttle_ms)
            .dedupe_same_candle(dedupe_same_candle)
            .build()
        )
        logger.debug(
            "Streaming OHLCV",
            extra={
                "exchange": request.exchange,
                "symbol": symbol,
                "timeframe": str(timeframe),
            },
        )
        async for item in self._router.route_stream(request):
            yield item

    async def stream_trades(
        self,
        symbol: str,
        *,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType | None = None,
    ) -> AsyncIterator[Trade]:
        """Stream real-time trades.

        Args:
            symbol: Symbol identifier
            exchange: Exchange name (uses default if set)
            market_type: Market type (uses default if set)
            market_variant: Market variant (uses default if set, derived from market_type otherwise)
            instrument_type: Instrument type (default: SPOT)

        Yields:
            Trade updates

        Raises:
            CapabilityError: If trades WS is not supported
            SymbolResolutionError: If symbol cannot be resolved
        """
        request = (
            self._create_request_builder(
                DataFeature.TRADES,
                TransportKind.WS,
                exchange=exchange,
                market_type=market_type,
                market_variant=market_variant,
                instrument_type=instrument_type,
            )
            .symbol(symbol)
            .build()
        )
        logger.debug(
            "Streaming trades",
            extra={"exchange": request.exchange, "symbol": symbol},
        )
        async for item in self._router.route_stream(request):
            yield item

    async def stream_ohlcv_multi(
        self,
        symbols: list[str],
        timeframe: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType | None = None,
    ) -> AsyncIterator[Any]:  # StreamingBar
        """Stream real-time OHLCV updates for multiple symbols.

        Args:
            symbols: List of symbol identifiers
            timeframe: Timeframe for bars
            only_closed: Only emit closed candles
            throttle_ms: Throttle updates (milliseconds)
            dedupe_same_candle: Deduplicate same candle updates
            exchange: Exchange name (uses default if set)
            market_type: Market type (uses default if set)
            market_variant: Market variant (uses default if set, derived from market_type otherwise)
            instrument_type: Instrument type (default: SPOT)

        Yields:
            StreamingBar updates (may be from different symbols)

        Raises:
            CapabilityError: If OHLCV WS is not supported
            SymbolResolutionError: If symbols cannot be resolved
            ProviderError: If provider doesn't support multi-symbol streaming
        """
        exchange_name = self._resolve_exchange(exchange)
        market_type_resolved = self._resolve_market_type(market_type)
        instrument_type_resolved = self._resolve_instrument_type(instrument_type)

        # Architecture: Multi-symbol streaming bypasses router for performance
        # Router's route_stream() handles single symbols, but multi-symbol requires
        # direct provider access to leverage provider-optimized subscriptions
        registry = self._router._provider_registry
        if not registry.is_registered(exchange_name):
            # Lazy registration: ensure provider is available
            from ..registration import register_all

            register_all(registry)

        # Get provider directly for multi-symbol streaming
        # Performance: Direct provider access avoids router overhead for multi-symbol
        provider = await registry.get_provider(
            exchange_name,
            market_type_resolved,
        )

        # Architecture: Validate capability using first symbol as representative
        # All symbols should have the same capability for multi-symbol streams
        if symbols:
            request = (
                self._create_request_builder(
                    DataFeature.OHLCV,
                    TransportKind.WS,
                    exchange=exchange_name,
                    market_type=market_type_resolved,
                    market_variant=market_variant,
                    instrument_type=instrument_type_resolved,
                )
                .symbol(symbols[0])
                .timeframe(timeframe)
                .build()
            )
            self._router._capability_service.validate_request(request)

        logger.debug(
            "Streaming OHLCV multi",
            extra={
                "exchange": exchange_name,
                "symbols": symbols,
                "timeframe": str(timeframe),
            },
        )

        async for item in provider.stream_ohlcv_multi(
            symbols=symbols,
            timeframe=timeframe,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_same_candle=dedupe_same_candle,
            instrument_type=instrument_type_resolved,
        ):
            yield item

    async def stream_trades_multi(
        self,
        symbols: list[str],
        *,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType | None = None,
    ) -> AsyncIterator[Trade]:
        """Stream real-time trades for multiple symbols.

        Args:
            symbols: List of symbol identifiers
            exchange: Exchange name (uses default if set)
            market_type: Market type (uses default if set)
            market_variant: Market variant (uses default if set, derived from market_type otherwise)
            instrument_type: Instrument type (default: SPOT)

        Yields:
            Trade updates (may be from different symbols)

        Raises:
            CapabilityError: If trades WS is not supported
            SymbolResolutionError: If symbols cannot be resolved
            ProviderError: If provider doesn't support multi-symbol streaming
        """
        exchange_name = self._resolve_exchange(exchange)
        market_type_resolved = self._resolve_market_type(market_type)
        instrument_type_resolved = self._resolve_instrument_type(instrument_type)

        # Ensure provider is registered before accessing
        registry = self._router._provider_registry
        if not registry.is_registered(exchange_name):
            from ..registration import register_all

            register_all(registry)

        # Get provider directly for multi-symbol streaming
        provider = await registry.get_provider(
            exchange_name,
            market_type_resolved,
        )

        # Validate capability for first symbol (all should have same capability)
        if symbols:
            request = (
                self._create_request_builder(
                    DataFeature.TRADES,
                    TransportKind.WS,
                    exchange=exchange_name,
                    market_type=market_type_resolved,
                    market_variant=market_variant,
                    instrument_type=instrument_type_resolved,
                )
                .symbol(symbols[0])
                .build()
            )
            self._router._capability_service.validate_request(request)

        logger.debug(
            "Streaming trades multi",
            extra={"exchange": exchange_name, "symbols": symbols},
        )

        async for trade in provider.stream_trades_multi(symbols=symbols):
            yield trade

    async def stream_order_book(
        self,
        symbol: str,
        *,
        depth: int | None = None,
        update_speed: str = "100ms",
        exchange: str | None = None,
        market_type: MarketType | None = None,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType | None = None,
    ) -> AsyncIterator[OrderBook]:
        """Stream order book updates.

        Args:
            symbol: Symbol identifier
            depth: Order book depth
            update_speed: Update speed (default: "100ms")
            exchange: Exchange name (uses default if set)
            market_type: Market type (uses default if set)
            instrument_type: Instrument type (default: SPOT)

        Yields:
            OrderBook updates

        Raises:
            CapabilityError: If order book WS is not supported
            SymbolResolutionError: If symbol cannot be resolved
        """
        request = (
            self._create_request_builder(
                DataFeature.ORDER_BOOK,
                TransportKind.WS,
                exchange=exchange,
                market_type=market_type,
                market_variant=market_variant,
                instrument_type=instrument_type,
            )
            .symbol(symbol)
            .depth(depth)
            .update_speed(update_speed)
            .build()
        )
        logger.debug(
            "Streaming order book",
            extra={"exchange": request.exchange, "symbol": symbol},
        )
        async for item in self._router.route_stream(request):
            yield item

    async def stream_order_book_multi(
        self,
        symbols: list[str],
        *,
        depth: int | None = None,
        update_speed: str = "100ms",
        exchange: str | None = None,
        market_type: MarketType | None = None,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType | None = None,
    ) -> AsyncIterator[OrderBook]:
        """Stream order book updates for multiple symbols.

        Args:
            symbols: List of symbol identifiers
            depth: Order book depth
            update_speed: Update speed (default: "100ms")
            exchange: Exchange name (uses default if set)
            market_type: Market type (uses default if set)
            market_variant: Market variant (uses default if set, derived from market_type otherwise)
            instrument_type: Instrument type (default: SPOT)

        Yields:
            OrderBook updates (may be from different symbols)

        Raises:
            CapabilityError: If order book WS is not supported
            SymbolResolutionError: If symbols cannot be resolved
            ProviderError: If provider doesn't support multi-symbol streaming
        """
        exchange_name = self._resolve_exchange(exchange)
        market_type_resolved = self._resolve_market_type(market_type)
        instrument_type_resolved = self._resolve_instrument_type(instrument_type)

        # Ensure provider is registered before accessing
        registry = self._router._provider_registry
        if not registry.is_registered(exchange_name):
            from ..registration import register_all

            register_all(registry)

        # Get provider directly for multi-symbol streaming
        provider = await registry.get_provider(
            exchange_name,
            market_type_resolved,
        )

        # Validate capability for first symbol (all should have same capability)
        if symbols:
            request = (
                self._create_request_builder(
                    DataFeature.ORDER_BOOK,
                    TransportKind.WS,
                    exchange=exchange_name,
                    market_type=market_type_resolved,
                    market_variant=market_variant,
                    instrument_type=instrument_type_resolved,
                )
                .symbol(symbols[0])
                .update_speed(update_speed)
                .build()
            )
            self._router._capability_service.validate_request(request)

        logger.debug(
            "Streaming order book multi",
            extra={
                "exchange": exchange_name,
                "symbols": symbols,
            },
        )

        async for item in provider.stream_order_book_multi(
            symbols=symbols,
            update_speed=update_speed,
        ):
            yield item

    async def stream_liquidations(
        self,
        *,
        exchange: str | None = None,
        market_type: MarketType = MarketType.FUTURES,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType = InstrumentType.PERPETUAL,
    ) -> AsyncIterator[Liquidation]:
        """Stream liquidations.

        Args:
            exchange: Exchange name (uses default if set)
            market_type: Market type (default: FUTURES)
            market_variant: Market variant (uses default if set, derived from market_type otherwise)
            instrument_type: Instrument type (default: PERPETUAL)

        Yields:
            Liquidation events

        Raises:
            CapabilityError: If liquidations WS is not supported
        """
        request = self._create_request_builder(
            DataFeature.LIQUIDATIONS,
            TransportKind.WS,
            exchange=exchange,
            market_type=market_type,
            market_variant=market_variant,
            instrument_type=instrument_type,
        ).build()
        logger.debug("Streaming liquidations", extra={"exchange": request.exchange})
        async for item in self._router.route_stream(request):
            yield item

    async def stream_open_interest(
        self,
        symbols: list[str],
        *,
        period: str = "5m",
        exchange: str | None = None,
        market_type: MarketType = MarketType.FUTURES,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType = InstrumentType.PERPETUAL,
    ) -> AsyncIterator[OpenInterest]:
        """Stream open interest updates.

        Args:
            symbols: List of symbol identifiers
            period: Period for open interest (default: "5m")
            exchange: Exchange name (uses default if set)
            market_type: Market type (default: FUTURES)
            market_variant: Market variant (uses default if set, derived from market_type otherwise)
            instrument_type: Instrument type (default: PERPETUAL)

        Yields:
            OpenInterest updates

        Raises:
            CapabilityError: If open interest WS is not supported
            SymbolResolutionError: If symbols cannot be resolved
        """
        request = (
            self._create_request_builder(
                DataFeature.OPEN_INTEREST,
                TransportKind.WS,
                exchange=exchange,
                market_type=market_type,
                market_variant=market_variant,
                instrument_type=instrument_type,
            )
            .symbols(symbols)
            .period(period)
            .build()
        )
        logger.debug(
            "Streaming open interest",
            extra={"exchange": request.exchange, "symbols": symbols},
        )
        async for item in self._router.route_stream(request):
            yield item

    async def stream_funding_rates(
        self,
        symbols: list[str],
        *,
        update_speed: str = "1s",
        exchange: str | None = None,
        market_type: MarketType = MarketType.FUTURES,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType = InstrumentType.PERPETUAL,
    ) -> AsyncIterator[FundingRate]:
        """Stream funding rate updates.

        Args:
            symbols: List of symbol identifiers
            update_speed: Update speed (default: "1s")
            exchange: Exchange name (uses default if set)
            market_type: Market type (default: FUTURES)
            market_variant: Market variant (uses default if set, derived from market_type otherwise)
            instrument_type: Instrument type (default: PERPETUAL)

        Yields:
            FundingRate updates

        Raises:
            CapabilityError: If funding rate WS is not supported
            SymbolResolutionError: If symbols cannot be resolved
        """
        request = (
            self._create_request_builder(
                DataFeature.FUNDING_RATE,
                TransportKind.WS,
                exchange=exchange,
                market_type=market_type,
                market_variant=market_variant,
                instrument_type=instrument_type,
            )
            .symbols(symbols)
            .update_speed(update_speed)
            .build()
        )
        logger.debug(
            "Streaming funding rates",
            extra={"exchange": request.exchange, "symbols": symbols},
        )
        async for item in self._router.route_stream(request):
            yield item

    async def stream_mark_price(
        self,
        symbols: list[str],
        *,
        update_speed: str = "1s",
        exchange: str | None = None,
        market_type: MarketType = MarketType.FUTURES,
        market_variant: MarketVariant | None = None,
        instrument_type: InstrumentType = InstrumentType.PERPETUAL,
    ) -> AsyncIterator[MarkPrice]:
        """Stream mark price updates.

        Args:
            symbols: List of symbol identifiers
            update_speed: Update speed (default: "1s")
            exchange: Exchange name (uses default if set)
            market_type: Market type (default: FUTURES)
            market_variant: Market variant (uses default if set, derived from market_type otherwise)
            instrument_type: Instrument type (default: PERPETUAL)

        Yields:
            MarkPrice updates

        Raises:
            CapabilityError: If mark price WS is not supported
            SymbolResolutionError: If symbols cannot be resolved
        """
        request = (
            self._create_request_builder(
                DataFeature.MARK_PRICE,
                TransportKind.WS,
                exchange=exchange,
                market_type=market_type,
                market_variant=market_variant,
                instrument_type=instrument_type,
            )
            .symbols(symbols)
            .update_speed(update_speed)
            .build()
        )
        logger.debug(
            "Streaming mark price",
            extra={"exchange": request.exchange, "symbols": symbols},
        )
        async for item in self._router.route_stream(request):
            yield item

    # --- Lifecycle -----------------------------------------------------------

    async def close(self) -> None:
        """Close the API and clean up resources."""
        if self._closed:
            return
        self._closed = True
        logger.debug("Closing DataAPI")
        if self._owns_router:
            await self._router.close()

    async def __aenter__(self) -> DataAPI:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
