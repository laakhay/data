"""Coinbase WebSocket-only provider (shim for backward compatibility).

This module is a shim that wraps the connector-based WS provider.
The actual implementation has been moved to connectors/coinbase/ws/provider.py.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from laakhay.data.connectors.coinbase.ws.provider import CoinbaseWSConnector

from ....core import MarketType, Timeframe
from ....models.streaming_bar import StreamingBar
from ....runtime.ws import WSProvider

if TYPE_CHECKING:
    from ....models import OrderBook, Trade


class CoinbaseWSProvider(WSProvider):
    """Streaming-only provider for Coinbase Spot (shim)."""

    def __init__(self, *, market_type: MarketType = MarketType.SPOT) -> None:
        self.market_type = market_type
        self._connector = CoinbaseWSConnector(market_type=market_type)

    async def stream_ohlcv(  # type: ignore[override,misc]
        self,
        symbol: str,
        interval: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        async for obj in self._connector.stream_ohlcv(
            symbol,
            interval,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_same_candle=dedupe_same_candle,
        ):
            yield obj

    async def stream_ohlcv_multi(  # type: ignore[override,misc]
        self,
        symbols: list[str],
        interval: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        async for obj in self._connector.stream_ohlcv_multi(
            symbols,
            interval,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_same_candle=dedupe_same_candle,
        ):
            yield obj

    async def stream_trades(self, symbol: str) -> AsyncIterator[Trade]:
        async for obj in self._connector.stream_trades(symbol):
            yield obj

    async def stream_trades_multi(self, symbols: list[str]) -> AsyncIterator[Trade]:
        async for obj in self._connector.stream_trades_multi(symbols):
            yield obj

    async def stream_order_book(
        self, symbol: str, update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        async for obj in self._connector.stream_order_book(symbol, update_speed=update_speed):
            yield obj

    async def stream_order_book_multi(
        self, symbols: list[str], update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        async for obj in self._connector.stream_order_book_multi(
            symbols, update_speed=update_speed
        ):
            yield obj

    async def stream(
        self,
        endpoint_id: str,
        symbols: list[str],
        params: dict[str, Any],
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_key: Any | None = None,
    ) -> AsyncIterator[Any]:
        """Stream data from a Coinbase WebSocket endpoint (for backward compatibility).

        Args:
            endpoint_id: Endpoint identifier
            symbols: List of trading symbols
            params: Request parameters
            only_closed: Only yield closed candles (for OHLCV)
            throttle_ms: Optional throttle in milliseconds
            dedupe_key: Optional deduplication key function

        Yields:
            Parsed messages from the endpoint adapter
        """
        async for obj in self._connector.stream(
            endpoint_id,
            symbols,
            params,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_key=dedupe_key,
        ):
            yield obj

    async def stream_liquidations(self) -> AsyncIterator[Any]:
        """Stream liquidations - NOT SUPPORTED by Coinbase."""
        raise NotImplementedError(
            "Coinbase Advanced Trade API does not support liquidations "
            "(Futures feature, not available on Spot markets)"
        )

    async def stream_open_interest(
        self, symbols: list[str], period: str = "5m"
    ) -> AsyncIterator[Any]:
        """Stream open interest - NOT SUPPORTED by Coinbase."""
        raise NotImplementedError(
            "Coinbase Advanced Trade API does not support open interest "
            "(Futures feature, not available on Spot markets)"
        )

    async def stream_funding_rate(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[Any]:
        """Stream funding rate - NOT SUPPORTED by Coinbase."""
        raise NotImplementedError(
            "Coinbase Advanced Trade API does not support funding rates "
            "(Futures feature, not available on Spot markets)"
        )

    async def close(self) -> None:
        await self._connector.close()
