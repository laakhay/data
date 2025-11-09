"""Unified Hyperliquid provider that wraps REST and WebSocket implementations.

Hyperliquid supports both Spot and Perpetual Futures markets.
API documentation: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

from ...core import BaseProvider, MarketType, Timeframe
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

    async def get_symbols(  # type: ignore[override]
        self, quote_asset: str | None = None, use_cache: bool = True
    ) -> list[Symbol]:
        return await self._rest.get_symbols(quote_asset=quote_asset, use_cache=use_cache)

    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        return await self._rest.get_order_book(symbol=symbol, limit=limit)

    async def get_exchange_info(self) -> dict:
        return await self._rest.get_exchange_info()

    async def get_recent_trades(self, symbol: str, limit: int = 500) -> list[Trade]:
        return await self._rest.get_recent_trades(symbol=symbol, limit=limit)

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

    async def stream_trades(self, symbol: str) -> AsyncIterator[Trade]:
        async for trade in self._ws.stream_trades(symbol):
            yield trade

    async def stream_trades_multi(self, symbols: list[str]) -> AsyncIterator[Trade]:
        async for trade in self._ws.stream_trades_multi(symbols):
            yield trade

    async def stream_open_interest(
        self, symbols: list[str], period: str = "5m"
    ) -> AsyncIterator[OpenInterest]:
        async for oi in self._ws.stream_open_interest(symbols, period=period):
            yield oi

    async def stream_funding_rate(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[FundingRate]:
        async for rate in self._ws.stream_funding_rate(symbols, update_speed=update_speed):
            yield rate

    async def stream_mark_price(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[MarkPrice]:
        async for mark in self._ws.stream_mark_price(symbols, update_speed=update_speed):
            yield mark

    async def stream_order_book(
        self, symbol: str, update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        async for ob in self._ws.stream_order_book(symbol, update_speed=update_speed):
            yield ob

    async def stream_liquidations(self) -> AsyncIterator[Liquidation]:
        async for liq in self._ws.stream_liquidations():
            yield liq

    # --- Lifecycle --------------------------------------------------------
    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._owns_rest:
            await self._rest.close()
        if self._owns_ws:
            await self._ws.close()
