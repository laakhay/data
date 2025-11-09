"""Hyperliquid WebSocket-only provider.

Implements the WSProvider interface using Hyperliquid-specific transport with subscription support.
Hyperliquid supports both Spot and Perpetual Futures markets.
API documentation: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Any

from ....core import MarketType, Timeframe
from ....io import MessageAdapter, WSProvider
from ....models.streaming_bar import StreamingBar
from .adapters import (
    FundingRateAdapter,
    LiquidationsAdapter,
    MarkPriceAdapter,
    OhlcvAdapter,
    OpenInterestAdapter,
    OrderBookAdapter,
    TradesAdapter,
)
from .endpoints import (
    funding_rate_spec,
    liquidations_spec,
    mark_price_spec,
    ohlcv_spec,
    open_interest_spec,
    order_book_spec,
    trades_spec,
)
from .transport import HyperliquidWebSocketTransport

if TYPE_CHECKING:
    from ....models import FundingRate, Liquidation, MarkPrice, OpenInterest, OrderBook, Trade
else:
    from ....models import FundingRate, Liquidation, MarkPrice, OpenInterest, OrderBook, Trade


class HyperliquidWSProvider(WSProvider):
    """Streaming-only provider for Hyperliquid Spot or Futures."""

    def __init__(self, *, market_type: MarketType = MarketType.FUTURES) -> None:
        self.market_type = market_type
        from ..constants import WS_PUBLIC_URLS

        self._ws_url = WS_PUBLIC_URLS.get(market_type)
        if not self._ws_url:
            raise ValueError(f"WebSocket not supported for market type: {market_type}")

        # Endpoint registry: key -> (spec_builder, adapter_class)
        self._ENDPOINTS: dict[str, tuple[Callable[[MarketType], Any], type[MessageAdapter]]] = {
            "ohlcv": (ohlcv_spec, OhlcvAdapter),
            "trades": (trades_spec, TradesAdapter),
            "open_interest": (open_interest_spec, OpenInterestAdapter),
            "funding_rate": (funding_rate_spec, FundingRateAdapter),
            "mark_price": (mark_price_spec, MarkPriceAdapter),
            "order_book": (order_book_spec, OrderBookAdapter),
            "liquidations": (liquidations_spec, LiquidationsAdapter),
        }

    async def stream_ohlcv(  # type: ignore[override,misc]
        self,
        symbol: str,
        interval: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        async for obj in self.stream(
            "ohlcv",
            [symbol],
            {"interval": interval},
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_key=None,
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
        async for obj in self.stream(
            "ohlcv",
            symbols,
            {"interval": interval},
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_key=None,
        ):
            yield obj

    async def stream(
        self,
        endpoint: str,
        symbols: list[str],
        params: dict[str, Any],
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_key: Any | None = None,
    ) -> AsyncIterator[Any]:
        if endpoint not in self._ENDPOINTS:
            raise ValueError(f"Unknown endpoint: {endpoint}")
        spec_fn, adapter_cls = self._ENDPOINTS[endpoint]
        spec = spec_fn(self.market_type)
        adapter = adapter_cls()

        # Apply endpoint-specific defaults
        if endpoint == "ohlcv" and not only_closed and dedupe_key is None:

            def _ohlcv_key(obj) -> tuple[str, int, str]:
                return (obj.symbol, int(obj.timestamp.timestamp() * 1000), str(obj.close))

            dedupe_key = _ohlcv_key

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

    # --- Trades ---
    async def stream_trades(self, symbol: str) -> AsyncIterator[Trade]:
        async for obj in self.stream("trades", [symbol], {}):
            yield obj

    async def stream_trades_multi(self, symbols: list[str]) -> AsyncIterator[Trade]:
        async for obj in self.stream("trades", symbols, {}):
            yield obj

    # --- Open Interest ---
    async def stream_open_interest(
        self, symbols: list[str], period: str = "5m"
    ) -> AsyncIterator[OpenInterest]:
        async for obj in self.stream("open_interest", symbols, {"period": period}):
            yield obj

    # --- Funding Rate ---
    async def stream_funding_rate(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[FundingRate]:
        async for obj in self.stream("funding_rate", symbols, {"update_speed": update_speed}):
            yield obj

    # --- Mark Price ---
    async def stream_mark_price(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[MarkPrice]:
        async for obj in self.stream("mark_price", symbols, {"update_speed": update_speed}):
            yield obj

    # --- Order Book ---
    async def stream_order_book(
        self, symbol: str, update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        async for obj in self.stream("order_book", [symbol], {"update_speed": update_speed}):
            yield obj

    # --- Liquidations ---
    async def stream_liquidations(self) -> AsyncIterator[Liquidation]:
        # Note: Hyperliquid doesn't have public liquidation subscription
        # Liquidations are only available via userEvents (requires user address)
        # This is a limitation - public liquidations are not directly available
        # For now, return empty stream - would need user addresses to monitor
        # In a real implementation, you'd need to:
        # 1. Get list of user addresses with positions
        # 2. Subscribe to userEvents for each address
        # 3. Filter for liquidation events
        if False:  # Placeholder - not implemented yet
            yield

    async def close(self) -> None:
        # No persistent sockets to close beyond task cancellation handled by callers
        return None

    async def _stream(
        self,
        spec: Any,
        adapter: MessageAdapter,
        symbols: list[str],
        params: dict[str, Any],
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_key: Any | None = None,
    ) -> AsyncIterator[Any]:
        """Custom stream implementation for Hyperliquid that handles subscriptions."""

        # Build topic names for all symbols
        topics = [spec.build_stream_name(s, params) for s in symbols]

        # Chunk topics if needed (Hyperliquid supports up to spec.max_streams_per_connection)
        cap = max(1, spec.max_streams_per_connection)
        topic_chunks = [topics[i : i + cap] for i in range(0, len(topics), cap)]

        # Single chunk fast path
        if len(topic_chunks) == 1:
            last_emit: dict[str, float] = {}
            last_close: dict[tuple[str, int], str] = {}

            if self._ws_url is None:
                raise RuntimeError("WebSocket URL not configured")
            transport = HyperliquidWebSocketTransport(url=self._ws_url)
            async for payload in transport.stream(topic_chunks[0]):
                if not adapter.is_relevant(payload):
                    continue

                for obj in adapter.parse(payload):
                    if only_closed and getattr(obj, "is_closed", False) is False:
                        continue
                    if throttle_ms:
                        now = time.time()
                        sym = getattr(obj, "symbol", "")
                        last = last_emit.get(sym)
                        if last is not None and (now - last) < (throttle_ms / 1000.0):
                            continue
                        last_emit[sym] = now
                    if dedupe_key and not only_closed:
                        sym, ts, close_str = dedupe_key(obj)
                        key = (sym, ts)
                        if last_close.get(key) == close_str:
                            continue
                        last_close[key] = close_str
                    yield obj

        # Multi-chunk: merge streams
        else:
            tasks = []
            for chunk in topic_chunks:
                tasks.append(
                    self._stream_chunk(
                        spec, adapter, chunk, params, only_closed, throttle_ms, dedupe_key
                    )
                )

            # Merge streams
            async for obj in self._merge_streams(tasks):
                yield obj

    async def _stream_chunk(
        self,
        spec: Any,
        adapter: MessageAdapter,
        topics: list[str],
        params: dict[str, Any],
        only_closed: bool,
        throttle_ms: int | None,
        dedupe_key: Any | None,
    ) -> AsyncIterator[Any]:
        """Stream a single chunk of topics."""
        last_emit: dict[str, float] = {}
        last_close: dict[tuple[str, int], str] = {}

        if self._ws_url is None:
            raise RuntimeError("WebSocket URL not configured")
        transport = HyperliquidWebSocketTransport(url=self._ws_url)
        async for payload in transport.stream(topics):
            if not adapter.is_relevant(payload):
                continue

            for obj in adapter.parse(payload):
                if only_closed and getattr(obj, "is_closed", False) is False:
                    continue
                if throttle_ms:
                    now = time.time()
                    sym = getattr(obj, "symbol", "")
                    last = last_emit.get(sym)
                    if last is not None and (now - last) < (throttle_ms / 1000.0):
                        continue
                    last_emit[sym] = now
                if dedupe_key and not only_closed:
                    sym, ts, close_str = dedupe_key(obj)
                    key = (sym, ts)
                    if last_close.get(key) == close_str:
                        continue
                    last_close[key] = close_str
                yield obj

    async def _merge_streams(self, tasks: list[AsyncIterator[Any]]) -> AsyncIterator[Any]:
        """Merge multiple async iterators."""
        # Simple round-robin merge
        # More sophisticated merging can be added if needed
        iterators = [task.__aiter__() for task in tasks]
        active = set(range(len(iterators)))

        while active:
            for i in list(active):
                try:
                    obj = await iterators[i].__anext__()
                    yield obj
                except StopAsyncIteration:
                    active.remove(i)
                except Exception as e:
                    # Log error and remove iterator
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.error(f"Error in stream {i}: {e}")
                    active.remove(i)
