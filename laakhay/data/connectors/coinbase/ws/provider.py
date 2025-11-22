"""Coinbase WebSocket connector for direct use by researchers.

This connector provides direct access to Coinbase WebSocket streams without
going through the DataRouter or capability validation. It's designed for
research use cases where developers want full control.

Architecture:
    This connector uses the endpoint registry to look up specs and adapters,
    then uses StreamRunner to execute streams. It implements WSProvider
    interface for compatibility with the router system.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from laakhay.data.core import MarketType, Timeframe
from laakhay.data.models.streaming_bar import StreamingBar
from laakhay.data.runtime.ws import StreamRunner, WSProvider

from .endpoints import get_endpoint_adapter, get_endpoint_spec

if TYPE_CHECKING:
    from laakhay.data.models import OrderBook, Trade


class CoinbaseWSConnector(WSProvider):
    """Coinbase WebSocket connector for direct research use.

    This connector can be used directly without going through DataRouter.
    It provides full access to Coinbase WebSocket streams with automatic
    endpoint spec and adapter resolution.
    """

    def __init__(self, *, market_type: MarketType = MarketType.SPOT) -> None:
        """Initialize Coinbase WebSocket connector.

        Args:
            market_type: Market type (only SPOT supported for Coinbase)
        """
        # Coinbase Advanced Trade API only supports Spot markets
        if market_type != MarketType.SPOT:
            raise ValueError(
                "Coinbase Advanced Trade API only supports Spot markets. "
                f"Got market_type={market_type}"
            )

        self.market_type = MarketType.SPOT  # Force to SPOT

    async def _stream(
        self,
        spec: Any,
        adapter: Any,
        symbols: list[str],
        params: dict[str, Any],
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_key: Any | None = None,
    ) -> AsyncIterator[Any]:
        """Internal stream method using StreamRunner."""
        runner = StreamRunner()
        async for obj in runner.run(
            spec=spec,
            adapter=adapter,
            symbols=symbols,
            params=params,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_key=dedupe_key,
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
        """Stream data from a Coinbase WebSocket endpoint.

        Args:
            endpoint_id: Endpoint identifier (e.g., "ohlcv", "trades")
            symbols: List of trading symbols
            params: Request parameters
            only_closed: Only yield closed candles (for OHLCV)
            throttle_ms: Optional throttle in milliseconds
            dedupe_key: Optional deduplication key function

        Yields:
            Parsed messages from the endpoint adapter

        Raises:
            ValueError: If endpoint_id is not found in registry
        """
        spec = get_endpoint_spec(endpoint_id, self.market_type)
        adapter_cls = get_endpoint_adapter(endpoint_id)
        if spec is None or adapter_cls is None:
            raise ValueError(f"Unknown endpoint: {endpoint_id}")

        adapter = adapter_cls()
        async for obj in self._stream(
            spec,
            adapter,
            symbols,
            params,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_key=dedupe_key,
        ):
            yield obj

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
        """
        async for obj in self.stream(
            "ohlcv",
            [symbol],
            {"interval": timeframe},
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_key=None if not dedupe_same_candle else self._ohlcv_key,
        ):
            yield obj

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
        """
        async for obj in self.stream(
            "ohlcv",
            symbols,
            {"interval": timeframe},
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_key=None if not dedupe_same_candle else self._ohlcv_key,
        ):
            yield obj

    def _ohlcv_key(self, obj: Any) -> tuple[str, int, str]:
        """Deduplication key for OHLCV bars."""
        return (obj.symbol, int(obj.timestamp.timestamp() * 1000), str(obj.close))

    async def stream_trades(self, symbol: str) -> AsyncIterator[Trade]:
        """Yield streaming trade updates for a single symbol.

        Args:
            symbol: Trading symbol

        Yields:
            Trade objects
        """
        async for obj in self.stream("trades", [symbol], {}):
            yield obj

    async def stream_trades_multi(self, symbols: list[str]) -> AsyncIterator[Trade]:
        """Yield streaming trade updates for multiple symbols.

        Args:
            symbols: List of trading symbols

        Yields:
            Trade objects
        """
        async for obj in self.stream("trades", symbols, {}):
            yield obj

    async def stream_order_book(
        self, symbol: str, update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        """Yield streaming order book updates for a single symbol.

        Args:
            symbol: Trading symbol
            update_speed: Update speed (not used for Coinbase)

        Yields:
            OrderBook objects
        """
        async for obj in self.stream("order_book", [symbol], {}):
            yield obj

    async def stream_order_book_multi(
        self, symbols: list[str], update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        """Yield streaming order book updates for multiple symbols.

        Args:
            symbols: List of trading symbols
            update_speed: Update speed (not used for Coinbase)

        Yields:
            OrderBook objects
        """
        async for obj in self.stream("order_book", symbols, {}):
            yield obj

    async def stream_funding_rate(self, symbols: list[str]) -> AsyncIterator[Any]:
        """Stream funding rate updates (not supported for Coinbase).

        Args:
            symbols: List of trading symbols

        Raises:
            NotImplementedError: Coinbase Advanced Trade API does not support funding rates
        """
        raise NotImplementedError("Coinbase Advanced Trade API does not support funding rates")

    async def stream_open_interest(self, symbols: list[str]) -> AsyncIterator[Any]:
        """Stream open interest updates (not supported for Coinbase).

        Args:
            symbols: List of trading symbols

        Raises:
            NotImplementedError: Coinbase Advanced Trade API does not support open interest
        """
        raise NotImplementedError("Coinbase Advanced Trade API does not support open interest")

    async def stream_liquidations(self) -> AsyncIterator[Any]:
        """Stream liquidation updates (not supported for Coinbase).

        Raises:
            NotImplementedError: Coinbase Advanced Trade API does not support liquidations
        """
        raise NotImplementedError("Coinbase Advanced Trade API does not support liquidations")

    async def close(self) -> None:
        """Close underlying resources."""
        return None
