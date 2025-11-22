"""Bybit WebSocket connector for direct use by researchers.

This connector provides direct access to Bybit WebSocket streams without
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

from laakhay.data.core import MarketType, MarketVariant, Timeframe
from laakhay.data.models.streaming_bar import StreamingBar
from laakhay.data.runtime.ws import StreamRunner, WSProvider

from .endpoints import get_endpoint_adapter, get_endpoint_spec

if TYPE_CHECKING:
    from laakhay.data.models import (
        FundingRate,
        Liquidation,
        MarkPrice,
        OpenInterest,
        OrderBook,
        Trade,
    )


class BybitWSConnector(WSProvider):
    """Bybit WebSocket connector for direct research use.

    This connector can be used directly without going through DataRouter.
    It provides full access to Bybit WebSocket streams with automatic
    endpoint spec and adapter resolution.
    """

    def __init__(
        self,
        *,
        market_type: MarketType = MarketType.SPOT,
        market_variant: MarketVariant | None = None,
    ) -> None:
        """Initialize Bybit WebSocket connector.

        Args:
            market_type: Market type (spot or futures)
            market_variant: Optional market variant. If not provided, derived from
                          market_type with smart defaults:
                          - SPOT → SPOT
                          - FUTURES → LINEAR_PERP (can be overridden)
                          - OPTIONS → OPTIONS
        """
        self.market_type = market_type
        # Derive market_variant from market_type if not provided (backward compatibility)
        if market_variant is None:
            self.market_variant = MarketVariant.from_market_type(market_type)
        else:
            self.market_variant = market_variant

    async def stream_ohlcv(
        self,
        symbol: str,
        interval: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        """Yield streaming OHLCV (bar) updates for a single symbol.

        Args:
            symbol: Trading symbol
            interval: Timeframe for bars
            only_closed: Only yield closed candles
            throttle_ms: Optional throttle in milliseconds
            dedupe_same_candle: Deduplicate same candle updates

        Yields:
            StreamingBar objects
        """
        async for obj in self.stream(
            "ohlcv",
            [symbol],
            {"interval": interval},
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_key=None if not dedupe_same_candle else self._ohlcv_key,
        ):
            yield obj

    async def stream_ohlcv_multi(
        self,
        symbols: list[str],
        interval: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        """Yield streaming OHLCV (bar) updates for multiple symbols.

        Args:
            symbols: List of trading symbols
            interval: Timeframe for bars
            only_closed: Only yield closed candles
            throttle_ms: Optional throttle in milliseconds
            dedupe_same_candle: Deduplicate same candle updates

        Yields:
            StreamingBar objects
        """
        async for obj in self.stream(
            "ohlcv",
            symbols,
            {"interval": interval},
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_key=None if not dedupe_same_candle else self._ohlcv_key,
        ):
            yield obj

    async def stream_trades(self, symbol: str) -> AsyncIterator[Trade]:
        """Stream trades for a single symbol.

        Args:
            symbol: Trading symbol

        Yields:
            Trade objects
        """
        async for obj in self.stream("trades", [symbol], {}):
            yield obj

    async def stream_trades_multi(self, symbols: list[str]) -> AsyncIterator[Trade]:
        """Stream trades for multiple symbols.

        Args:
            symbols: List of trading symbols

        Yields:
            Trade objects
        """
        async for obj in self.stream("trades", symbols, {}):
            yield obj

    async def stream_open_interest(
        self, symbols: list[str], period: str = "5m"
    ) -> AsyncIterator[OpenInterest]:
        """Stream open interest updates (Futures-only).

        Args:
            symbols: List of trading symbols
            period: Update period (default "5m", not used by Bybit)

        Yields:
            OpenInterest objects
        """
        async for obj in self.stream("open_interest", symbols, {"period": period}):
            yield obj

    async def stream_funding_rate(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[FundingRate]:
        """Stream funding rate updates (Futures-only).

        Args:
            symbols: List of trading symbols
            update_speed: Update speed (default "1s", not used by Bybit)

        Yields:
            FundingRate objects
        """
        async for obj in self.stream("funding_rate", symbols, {"update_speed": update_speed}):
            yield obj

    async def stream_mark_price(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[MarkPrice]:
        """Stream mark price updates.

        Args:
            symbols: List of trading symbols
            update_speed: Update speed (default "1s", not used by Bybit)

        Yields:
            MarkPrice objects
        """
        async for obj in self.stream("mark_price", symbols, {"update_speed": update_speed}):
            yield obj

    async def stream_order_book(
        self, symbol: str, update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        """Stream order book updates for a single symbol.

        Args:
            symbol: Trading symbol
            update_speed: Update speed (default "100ms", not used by Bybit)

        Yields:
            OrderBook objects
        """
        async for obj in self.stream(
            "order_book", [symbol], {"update_speed": update_speed, "depth": "1"}
        ):
            yield obj

    async def stream_order_book_multi(
        self, symbols: list[str], update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        """Stream order book updates for multiple symbols.

        Args:
            symbols: List of trading symbols
            update_speed: Update speed (default "100ms", not used by Bybit)

        Yields:
            OrderBook objects
        """
        async for obj in self.stream(
            "order_book", symbols, {"update_speed": update_speed, "depth": "1"}
        ):
            yield obj

    async def stream_liquidations(self) -> AsyncIterator[Liquidation]:
        """Stream liquidation events (Futures-only, global stream).

        Yields:
            Liquidation objects
        """
        async for obj in self.stream("liquidations", ["!global"], {}):
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
        """Stream data from a Bybit WebSocket endpoint.

        Args:
            endpoint_id: Endpoint identifier (e.g., "ohlcv", "trades")
            symbols: List of symbols to stream
            params: Endpoint-specific parameters
            only_closed: Only yield closed candles (for OHLCV)
            throttle_ms: Optional throttle in milliseconds
            dedupe_key: Optional deduplication key function

        Yields:
            Parsed messages from the endpoint adapter

        Raises:
            ValueError: If endpoint_id is not found in registry
        """
        spec = get_endpoint_spec(endpoint_id, self.market_type)
        if spec is None:
            raise ValueError(f"Unknown WebSocket endpoint: {endpoint_id}")

        adapter_cls = get_endpoint_adapter(endpoint_id)
        if adapter_cls is None:
            raise ValueError(f"No adapter found for endpoint: {endpoint_id}")

        # Apply endpoint-specific defaults
        if endpoint_id == "ohlcv" and not only_closed and dedupe_key is None:
            dedupe_key = self._ohlcv_key

        adapter = adapter_cls()
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

    def _ohlcv_key(self, obj: Any) -> tuple[str, int, str]:
        """Generate deduplication key for OHLCV bars."""
        return (obj.symbol, int(obj.timestamp.timestamp() * 1000), str(obj.close))

    async def close(self) -> None:
        """Close any underlying streaming resources."""
        # No persistent sockets to close beyond task cancellation handled by callers
        return None
