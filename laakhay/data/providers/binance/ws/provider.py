"""Binance WebSocket-only provider (shim for backward compatibility).

This module is a shim that wraps the connector-based WS provider.
The actual implementation has been moved to connectors/binance/ws/provider.py.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from ....core import MarketType, Timeframe
from ....models.streaming_bar import StreamingBar
from ....runtime.ws import WSProvider
from ...connectors.binance.ws.provider import BinanceWSConnector

if TYPE_CHECKING:
    from ....models import FundingRate, Liquidation, MarkPrice, OpenInterest, OrderBook, Trade


class BinanceWSProvider(WSProvider):
    """Streaming-only provider for Binance Spot or Futures (shim)."""

    def __init__(self, *, market_type: MarketType = MarketType.SPOT) -> None:
        """Initialize WS provider shim.

        Args:
            market_type: Market type (spot or futures)
        """
        self.market_type = market_type
        self._connector = BinanceWSConnector(market_type=market_type)

    async def stream_ohlcv(  # type: ignore[override,misc]
        self,
        symbol: str,
        interval: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        """Stream OHLCV bars (delegates to connector)."""
        async for bar in self._connector.stream_ohlcv(
            symbol=symbol,
            interval=interval,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_same_candle=dedupe_same_candle,
        ):
            yield bar

    async def stream_ohlcv_multi(  # type: ignore[override,misc]
        self,
        symbols: list[str],
        interval: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        """Stream OHLCV bars for multiple symbols (delegates to connector)."""
        async for bar in self._connector.stream_ohlcv_multi(
            symbols=symbols,
            interval=interval,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_same_candle=dedupe_same_candle,
        ):
            yield bar

    async def stream_trades(self, symbol: str) -> AsyncIterator[Trade]:
        """Stream trades (delegates to connector)."""
        async for trade in self._connector.stream_trades(symbol=symbol):
            yield trade

    async def stream_trades_multi(self, symbols: list[str]) -> AsyncIterator[Trade]:
        """Stream trades for multiple symbols (delegates to connector)."""
        async for trade in self._connector.stream_trades_multi(symbols=symbols):
            yield trade

    async def stream_open_interest(
        self, symbols: list[str], period: str = "5m"
    ) -> AsyncIterator[OpenInterest]:
        """Stream open interest (delegates to connector)."""
        async for oi in self._connector.stream_open_interest(symbols=symbols, period=period):
            yield oi

    async def stream_funding_rate(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[FundingRate]:
        """Stream funding rate (delegates to connector)."""
        async for fr in self._connector.stream_funding_rate(
            symbols=symbols, update_speed=update_speed
        ):
            yield fr

    async def stream_mark_price(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[MarkPrice]:
        """Stream mark price (delegates to connector)."""
        async for mp in self._connector.stream_mark_price(
            symbols=symbols, update_speed=update_speed
        ):
            yield mp

    async def stream_order_book(
        self, symbol: str, update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        """Stream order book (delegates to connector)."""
        async for ob in self._connector.stream_order_book(symbol=symbol, update_speed=update_speed):
            yield ob

    async def stream_order_book_multi(
        self, symbols: list[str], update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        """Stream order book for multiple symbols (delegates to connector)."""
        async for ob in self._connector.stream_order_book_multi(
            symbols=symbols, update_speed=update_speed
        ):
            yield ob

    async def stream_liquidations(self) -> AsyncIterator[Liquidation]:
        """Stream liquidations (delegates to connector)."""
        async for liq in self._connector.stream_liquidations():
            yield liq

    async def close(self) -> None:
        """Close underlying resources."""
        await self._connector.close()
