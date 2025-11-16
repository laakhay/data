"""Ergonomic DataAPI facade for unified data access.

The DataAPI provides a high-level interface that wraps the DataRouter,
offering convenient fetch_* and stream_* methods while maintaining
backward compatibility with direct provider usage.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import datetime
from typing import TYPE_CHECKING, Any

from .enums import DataFeature, InstrumentType, MarketType, Timeframe, TransportKind
from .request import DataRequest
from .router import DataRouter

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
        default_instrument_type: InstrumentType = InstrumentType.SPOT,
        router: DataRouter | None = None,
    ) -> None:
        """Initialize the DataAPI.

        Args:
            default_exchange: Default exchange to use if not specified in method calls
            default_market_type: Default market type to use if not specified
            default_instrument_type: Default instrument type (default: SPOT)
            router: Optional DataRouter instance (creates new one if not provided)
        """
        self._default_exchange = default_exchange
        self._default_market_type = default_market_type
        self._default_instrument_type = default_instrument_type
        self._router = router or DataRouter()
        self._closed = False

    def _resolve_exchange(self, exchange: str | None) -> str:
        """Resolve exchange parameter."""
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

    def _resolve_instrument_type(self, instrument_type: InstrumentType | None) -> InstrumentType:
        """Resolve instrument type parameter."""
        if instrument_type is not None:
            return instrument_type
        return self._default_instrument_type

    # --- REST / Historical Methods -------------------------------------------

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
            instrument_type: Instrument type (default: SPOT)

        Returns:
            OHLCV data series

        Raises:
            CapabilityError: If OHLCV REST is not supported
            SymbolResolutionError: If symbol cannot be resolved
        """
        request = DataRequest(
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
            exchange=self._resolve_exchange(exchange),
            market_type=self._resolve_market_type(market_type),
            instrument_type=self._resolve_instrument_type(instrument_type),
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            max_chunks=max_chunks,
        )
        logger.debug(
            "Fetching OHLCV",
            extra={
                "exchange": request.exchange,
                "symbol": symbol,
                "timeframe": str(timeframe),
            },
        )
        return await self._router.route(request)

    async def fetch_order_book(
        self,
        symbol: str,
        *,
        depth: int = 100,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        instrument_type: InstrumentType | None = None,
    ) -> OrderBook:
        """Fetch order book snapshot.

        Args:
            symbol: Symbol identifier
            depth: Order book depth (default: 100)
            exchange: Exchange name (uses default if set)
            market_type: Market type (uses default if set)
            instrument_type: Instrument type (default: SPOT)

        Returns:
            OrderBook with computed metrics

        Raises:
            CapabilityError: If order book REST is not supported
            SymbolResolutionError: If symbol cannot be resolved
        """
        request = DataRequest(
            feature=DataFeature.ORDER_BOOK,
            transport=TransportKind.REST,
            exchange=self._resolve_exchange(exchange),
            market_type=self._resolve_market_type(market_type),
            instrument_type=self._resolve_instrument_type(instrument_type),
            symbol=symbol,
            depth=depth,
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
        instrument_type: InstrumentType | None = None,
    ) -> list[Trade]:
        """Fetch recent trades.

        Args:
            symbol: Symbol identifier
            limit: Maximum number of trades (default: 500)
            exchange: Exchange name (uses default if set)
            market_type: Market type (uses default if set)
            instrument_type: Instrument type (default: SPOT)

        Returns:
            List of recent trades

        Raises:
            CapabilityError: If trades REST is not supported
            SymbolResolutionError: If symbol cannot be resolved
        """
        request = DataRequest(
            feature=DataFeature.TRADES,
            transport=TransportKind.REST,
            exchange=self._resolve_exchange(exchange),
            market_type=self._resolve_market_type(market_type),
            instrument_type=self._resolve_instrument_type(instrument_type),
            symbol=symbol,
            limit=limit,
        )
        logger.debug(
            "Fetching recent trades",
            extra={"exchange": request.exchange, "symbol": symbol, "limit": limit},
        )
        return await self._router.route(request)

    async def fetch_symbols(
        self,
        *,
        quote_asset: str | None = None,
        exchange: str | None = None,
        market_type: MarketType | None = None,
        use_cache: bool = True,
    ) -> list[Symbol]:
        """Fetch symbol metadata.

        Args:
            quote_asset: Optional quote asset filter
            exchange: Exchange name (uses default if set)
            market_type: Market type (uses default if set)
            use_cache: Whether to use cached symbol data

        Returns:
            List of symbol metadata

        Raises:
            CapabilityError: If symbol metadata REST is not supported
        """
        request = DataRequest(
            feature=DataFeature.SYMBOL_METADATA,
            transport=TransportKind.REST,
            exchange=self._resolve_exchange(exchange),
            market_type=self._resolve_market_type(market_type),
            instrument_type=InstrumentType.SPOT,  # Symbol metadata doesn't use instrument_type
            extra_params={"quote_asset": quote_asset, "use_cache": use_cache},
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
            instrument_type: Instrument type (default: PERPETUAL)

        Returns:
            List of open interest records

        Raises:
            CapabilityError: If open interest REST is not supported
            SymbolResolutionError: If symbol cannot be resolved
        """
        request = DataRequest(
            feature=DataFeature.OPEN_INTEREST,
            transport=TransportKind.REST,
            exchange=self._resolve_exchange(exchange),
            market_type=market_type,
            instrument_type=instrument_type,
            symbol=symbol,
            historical=historical,
            period=period,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
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
            instrument_type: Instrument type (default: PERPETUAL)

        Returns:
            List of funding rate records

        Raises:
            CapabilityError: If funding rate REST is not supported
            SymbolResolutionError: If symbol cannot be resolved
        """
        request = DataRequest(
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.REST,
            exchange=self._resolve_exchange(exchange),
            market_type=market_type,
            instrument_type=instrument_type,
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
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
            instrument_type: Instrument type (default: SPOT)

        Yields:
            StreamingBar updates

        Raises:
            CapabilityError: If OHLCV WS is not supported
            SymbolResolutionError: If symbol cannot be resolved
        """
        request = DataRequest(
            feature=DataFeature.OHLCV,
            transport=TransportKind.WS,
            exchange=self._resolve_exchange(exchange),
            market_type=self._resolve_market_type(market_type),
            instrument_type=self._resolve_instrument_type(instrument_type),
            symbol=symbol,
            timeframe=timeframe,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_same_candle=dedupe_same_candle,
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
        instrument_type: InstrumentType | None = None,
    ) -> AsyncIterator[Trade]:
        """Stream real-time trades.

        Args:
            symbol: Symbol identifier
            exchange: Exchange name (uses default if set)
            market_type: Market type (uses default if set)
            instrument_type: Instrument type (default: SPOT)

        Yields:
            Trade updates

        Raises:
            CapabilityError: If trades WS is not supported
            SymbolResolutionError: If symbol cannot be resolved
        """
        request = DataRequest(
            feature=DataFeature.TRADES,
            transport=TransportKind.WS,
            exchange=self._resolve_exchange(exchange),
            market_type=self._resolve_market_type(market_type),
            instrument_type=self._resolve_instrument_type(instrument_type),
            symbol=symbol,
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

        # Ensure provider is registered before accessing
        registry = self._router._provider_registry
        if not registry.is_registered(exchange_name):
            from ..providers import register_all

            register_all(registry)

        # Get provider directly for multi-symbol streaming
        provider = await registry.get_provider(
            exchange_name,
            market_type_resolved,
        )

        # Validate capability for first symbol (all should have same capability)
        if symbols:
            request = DataRequest(
                feature=DataFeature.OHLCV,
                transport=TransportKind.WS,
                exchange=exchange_name,
                market_type=market_type_resolved,
                instrument_type=instrument_type_resolved,
                symbol=symbols[0],
                timeframe=timeframe,
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
        instrument_type: InstrumentType | None = None,
    ) -> AsyncIterator[Trade]:
        """Stream real-time trades for multiple symbols.

        Args:
            symbols: List of symbol identifiers
            exchange: Exchange name (uses default if set)
            market_type: Market type (uses default if set)
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
            from ..providers import register_all

            register_all(registry)

        # Get provider directly for multi-symbol streaming
        provider = await registry.get_provider(
            exchange_name,
            market_type_resolved,
        )

        # Validate capability for first symbol (all should have same capability)
        if symbols:
            request = DataRequest(
                feature=DataFeature.TRADES,
                transport=TransportKind.WS,
                exchange=exchange_name,
                market_type=market_type_resolved,
                instrument_type=instrument_type_resolved,
                symbol=symbols[0],
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
        request = DataRequest(
            feature=DataFeature.ORDER_BOOK,
            transport=TransportKind.WS,
            exchange=self._resolve_exchange(exchange),
            market_type=self._resolve_market_type(market_type),
            instrument_type=self._resolve_instrument_type(instrument_type),
            symbol=symbol,
            depth=depth,
            update_speed=update_speed,
        )
        logger.debug(
            "Streaming order book",
            extra={"exchange": request.exchange, "symbol": symbol},
        )
        async for item in self._router.route_stream(request):
            yield item

    async def stream_liquidations(
        self,
        *,
        exchange: str | None = None,
        market_type: MarketType = MarketType.FUTURES,
        instrument_type: InstrumentType = InstrumentType.PERPETUAL,
    ) -> AsyncIterator[Liquidation]:
        """Stream liquidations.

        Args:
            exchange: Exchange name (uses default if set)
            market_type: Market type (default: FUTURES)
            instrument_type: Instrument type (default: PERPETUAL)

        Yields:
            Liquidation events

        Raises:
            CapabilityError: If liquidations WS is not supported
        """
        request = DataRequest(
            feature=DataFeature.LIQUIDATIONS,
            transport=TransportKind.WS,
            exchange=self._resolve_exchange(exchange),
            market_type=market_type,
            instrument_type=instrument_type,
        )
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
        instrument_type: InstrumentType = InstrumentType.PERPETUAL,
    ) -> AsyncIterator[OpenInterest]:
        """Stream open interest updates.

        Args:
            symbols: List of symbol identifiers
            period: Period for open interest (default: "5m")
            exchange: Exchange name (uses default if set)
            market_type: Market type (default: FUTURES)
            instrument_type: Instrument type (default: PERPETUAL)

        Yields:
            OpenInterest updates

        Raises:
            CapabilityError: If open interest WS is not supported
            SymbolResolutionError: If symbols cannot be resolved
        """
        request = DataRequest(
            feature=DataFeature.OPEN_INTEREST,
            transport=TransportKind.WS,
            exchange=self._resolve_exchange(exchange),
            market_type=market_type,
            instrument_type=instrument_type,
            symbols=symbols,
            period=period,
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
        instrument_type: InstrumentType = InstrumentType.PERPETUAL,
    ) -> AsyncIterator[FundingRate]:
        """Stream funding rate updates.

        Args:
            symbols: List of symbol identifiers
            update_speed: Update speed (default: "1s")
            exchange: Exchange name (uses default if set)
            market_type: Market type (default: FUTURES)
            instrument_type: Instrument type (default: PERPETUAL)

        Yields:
            FundingRate updates

        Raises:
            CapabilityError: If funding rate WS is not supported
            SymbolResolutionError: If symbols cannot be resolved
        """
        request = DataRequest(
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.WS,
            exchange=self._resolve_exchange(exchange),
            market_type=market_type,
            instrument_type=instrument_type,
            symbols=symbols,
            update_speed=update_speed,
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
        instrument_type: InstrumentType = InstrumentType.PERPETUAL,
    ) -> AsyncIterator[MarkPrice]:
        """Stream mark price updates.

        Args:
            symbols: List of symbol identifiers
            update_speed: Update speed (default: "1s")
            exchange: Exchange name (uses default if set)
            market_type: Market type (default: FUTURES)
            instrument_type: Instrument type (default: PERPETUAL)

        Yields:
            MarkPrice updates

        Raises:
            CapabilityError: If mark price WS is not supported
            SymbolResolutionError: If symbols cannot be resolved
        """
        request = DataRequest(
            feature=DataFeature.MARK_PRICE,
            transport=TransportKind.WS,
            exchange=self._resolve_exchange(exchange),
            market_type=market_type,
            instrument_type=instrument_type,
            symbols=symbols,
            update_speed=update_speed,
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

    async def __aenter__(self) -> DataAPI:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
