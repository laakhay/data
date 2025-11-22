"""OKX WebSocket connector for direct use by researchers.

This connector provides direct access to OKX WebSocket streams without
going through the DataRouter or capability validation. It's designed for
research use cases where developers want full control.

Note: This is a minimal implementation. Full WS support can be added later
following the Binance pattern with endpoint specs and adapters.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from laakhay.data.core import MarketType, Timeframe
from laakhay.data.models.streaming_bar import StreamingBar
from laakhay.data.runtime.ws import WSProvider

if TYPE_CHECKING:
    from laakhay.data.models import (
        FundingRate,
        Liquidation,
        MarkPrice,
        OpenInterest,
        OrderBook,
        Trade,
    )


class OKXWSConnector(WSProvider):
    """OKX WebSocket connector for direct research use.

    This connector can be used directly without going through DataRouter.
    It provides full access to OKX WebSocket streams.

    Note: This is a minimal stub implementation. Full WS support with
    endpoint specs and adapters should be added following the Binance pattern.
    """

    def __init__(self, *, market_type: MarketType = MarketType.SPOT) -> None:
        """Initialize OKX WebSocket connector.

        Args:
            market_type: Market type (spot or futures)
        """
        self.market_type = market_type
        # TODO: Initialize WebSocket transport and endpoint registry

    async def stream_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        """Yield streaming OHLCV (bar) updates for a single symbol.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe for bars
            only_closed: Only yield closed candles
            throttle_ms: Optional throttle in milliseconds
            dedupe_same_candle: Deduplicate same candle updates

        Yields:
            StreamingBar objects

        Raises:
            NotImplementedError: WS support not yet implemented
        """
        raise NotImplementedError("OKX WebSocket streaming not yet implemented")

    async def stream_ohlcv_multi(
        self,
        symbols: list[str],
        timeframe: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        """Yield streaming OHLCV (bar) updates for multiple symbols.

        Args:
            symbols: List of trading symbols
            timeframe: Timeframe for bars
            only_closed: Only yield closed candles
            throttle_ms: Optional throttle in milliseconds
            dedupe_same_candle: Deduplicate same candle updates

        Yields:
            StreamingBar objects

        Raises:
            NotImplementedError: WS support not yet implemented
        """
        raise NotImplementedError("OKX WebSocket streaming not yet implemented")

    async def stream_trades(self, symbol: str) -> AsyncIterator[Trade]:
        """Stream trades for a symbol.

        Args:
            symbol: Trading symbol

        Yields:
            Trade objects

        Raises:
            NotImplementedError: WS support not yet implemented
        """
        raise NotImplementedError("OKX WebSocket streaming not yet implemented")

    async def stream_trades_multi(self, symbols: list[str]) -> AsyncIterator[Trade]:
        """Stream trades for multiple symbols.

        Args:
            symbols: List of trading symbols

        Yields:
            Trade objects

        Raises:
            NotImplementedError: WS support not yet implemented
        """
        raise NotImplementedError("OKX WebSocket streaming not yet implemented")

    async def stream_open_interest(
        self, symbols: list[str], period: str = "5m"
    ) -> AsyncIterator[OpenInterest]:
        """Stream open interest updates.

        Args:
            symbols: List of trading symbols
            period: Period for updates (default "5m")

        Yields:
            OpenInterest objects

        Raises:
            NotImplementedError: WS support not yet implemented
        """
        raise NotImplementedError("OKX WebSocket streaming not yet implemented")

    async def stream_funding_rate(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[FundingRate]:
        """Stream funding rate updates.

        Args:
            symbols: List of trading symbols
            update_speed: Update speed (default "1s")

        Yields:
            FundingRate objects

        Raises:
            NotImplementedError: WS support not yet implemented
        """
        raise NotImplementedError("OKX WebSocket streaming not yet implemented")

    async def stream_mark_price(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[MarkPrice]:
        """Stream mark price updates.

        Args:
            symbols: List of trading symbols
            update_speed: Update speed (default "1s")

        Yields:
            MarkPrice objects

        Raises:
            NotImplementedError: WS support not yet implemented
        """
        raise NotImplementedError("OKX WebSocket streaming not yet implemented")

    async def stream_order_book(
        self, symbol: str, update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        """Stream order book updates.

        Args:
            symbol: Trading symbol
            update_speed: Update speed (default "100ms")

        Yields:
            OrderBook objects

        Raises:
            NotImplementedError: WS support not yet implemented
        """
        raise NotImplementedError("OKX WebSocket streaming not yet implemented")

    async def stream_liquidations(self) -> AsyncIterator[Liquidation]:
        """Stream liquidation events.

        Yields:
            Liquidation objects

        Raises:
            NotImplementedError: WS support not yet implemented
        """
        raise NotImplementedError("OKX WebSocket streaming not yet implemented")

    async def close(self) -> None:
        """Close underlying WebSocket resources."""
        # TODO: Close WebSocket connections
        pass
