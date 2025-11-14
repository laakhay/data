"""Unified Hyperliquid provider that wraps REST and WebSocket implementations.

Hyperliquid supports both Spot and Perpetual Futures markets.
API documentation: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

from ...core import (
    BaseProvider,
    DataFeature,
    InstrumentType,
    MarketType,
    Timeframe,
    TransportKind,
    register_feature_handler,
)
from ...core.capabilities import CapabilityStatus, supports
from ...models import (
    OHLCV,
    FundingRate,
    Liquidation,
    MarkPrice,
    OpenInterest,
    OrderBook,
    StreamingBar,
    Symbol,
    Trade,
)
from .rest.provider import HyperliquidRESTProvider
from .ws.provider import HyperliquidWSProvider


class HyperliquidProvider(BaseProvider):
    """High-level Hyperliquid provider exposing REST and streaming helpers."""

    def __init__(
        self,
        *,
        market_type: MarketType = MarketType.FUTURES,
        api_key: str | None = None,
        api_secret: str | None = None,
        rest_provider: HyperliquidRESTProvider | None = None,
        ws_provider: HyperliquidWSProvider | None = None,
    ) -> None:
        super().__init__(name="hyperliquid")
        self.market_type = market_type
        self._rest = rest_provider or HyperliquidRESTProvider(
            market_type=market_type, api_key=api_key, api_secret=api_secret
        )
        self._ws = ws_provider or HyperliquidWSProvider(market_type=market_type)
        self._owns_rest = rest_provider is None
        self._owns_ws = ws_provider is None
        self._closed = False

    def get_timeframes(self) -> list[str]:
        from .constants import INTERVAL_MAP

        return list(INTERVAL_MAP.keys())

    # --- REST delegations -------------------------------------------------
    @register_feature_handler(DataFeature.OHLCV, TransportKind.REST)
    async def get_candles(
        self,
        symbol: str,
        timeframe: str | Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> OHLCV:
        return await self._rest.get_candles(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    @register_feature_handler(DataFeature.SYMBOL_METADATA, TransportKind.REST)
    async def get_symbols(  # type: ignore[override]
        self, quote_asset: str | None = None, use_cache: bool = True
    ) -> list[Symbol]:
        return await self._rest.get_symbols(quote_asset=quote_asset, use_cache=use_cache)

    @register_feature_handler(DataFeature.ORDER_BOOK, TransportKind.REST)
    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        return await self._rest.get_order_book(symbol=symbol, limit=limit)

    async def get_exchange_info(self) -> dict:
        return await self._rest.get_exchange_info()

    @register_feature_handler(DataFeature.TRADES, TransportKind.REST)
    async def get_recent_trades(self, symbol: str, limit: int = 500) -> list[Trade]:
        return await self._rest.get_recent_trades(symbol=symbol, limit=limit)

    @register_feature_handler(DataFeature.FUNDING_RATE, TransportKind.REST)
    async def get_funding_rate(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[FundingRate]:
        return await self._rest.get_funding_rate(
            symbol=symbol, start_time=start_time, end_time=end_time, limit=limit
        )

    @register_feature_handler(DataFeature.OPEN_INTEREST, TransportKind.REST)
    async def get_open_interest(
        self,
        symbol: str,
        historical: bool = False,
        period: str = "5m",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 30,
    ) -> list[OpenInterest]:
        return await self._rest.get_open_interest(
            symbol=symbol,
            historical=historical,
            period=period,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    # --- Streaming delegations -------------------------------------------
    @register_feature_handler(DataFeature.OHLCV, TransportKind.WS)
    async def stream_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        async for bar in self._ws.stream_ohlcv(
            symbol,
            timeframe,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_same_candle=dedupe_same_candle,
        ):
            yield bar

    async def stream_ohlcv_multi(
        self,
        symbols: list[str],
        timeframe: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        async for bar in self._ws.stream_ohlcv_multi(
            symbols,
            timeframe,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_same_candle=dedupe_same_candle,
        ):
            yield bar

    @register_feature_handler(DataFeature.TRADES, TransportKind.WS)
    async def stream_trades(self, symbol: str) -> AsyncIterator[Trade]:
        async for trade in self._ws.stream_trades(symbol):
            yield trade

    async def stream_trades_multi(self, symbols: list[str]) -> AsyncIterator[Trade]:
        async for trade in self._ws.stream_trades_multi(symbols):
            yield trade

    @register_feature_handler(DataFeature.OPEN_INTEREST, TransportKind.WS)
    async def stream_open_interest(
        self, symbols: list[str], period: str = "5m"
    ) -> AsyncIterator[OpenInterest]:
        async for oi in self._ws.stream_open_interest(symbols, period=period):
            yield oi

    @register_feature_handler(DataFeature.FUNDING_RATE, TransportKind.WS)
    async def stream_funding_rate(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[FundingRate]:
        async for rate in self._ws.stream_funding_rate(symbols, update_speed=update_speed):
            yield rate

    @register_feature_handler(DataFeature.MARK_PRICE, TransportKind.WS)
    async def stream_mark_price(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[MarkPrice]:
        async for mark in self._ws.stream_mark_price(symbols, update_speed=update_speed):
            yield mark

    @register_feature_handler(DataFeature.ORDER_BOOK, TransportKind.WS)
    async def stream_order_book(
        self, symbol: str, update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        async for ob in self._ws.stream_order_book(symbol, update_speed=update_speed):
            yield ob

    @register_feature_handler(DataFeature.LIQUIDATIONS, TransportKind.WS)
    async def stream_liquidations(self) -> AsyncIterator[Liquidation]:
        async for liq in self._ws.stream_liquidations():
            yield liq

    # --- Capability discovery ----------------------------------------------
    async def describe_capabilities(
        self,
        feature: DataFeature,
        transport: TransportKind,
        *,
        market_type: MarketType,
        instrument_type: InstrumentType,
    ) -> CapabilityStatus:
        """Describe capabilities for Hyperliquid.

        Returns static capability status from the registry.
        Runtime discovery can be added later to probe actual API availability.
        """
        return supports(
            feature=feature,
            transport=transport,
            exchange="hyperliquid",
            market_type=market_type,
            instrument_type=instrument_type,
        )

    # --- Lifecycle --------------------------------------------------------
    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._owns_rest:
            await self._rest.close()
        if self._owns_ws:
            await self._ws.close()
