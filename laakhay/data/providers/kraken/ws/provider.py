"""Kraken WebSocket-only provider.

Implements the WSProvider interface using Kraken-specific transport with subscription support.
"""

from __future__ import annotations

import asyncio
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
from .transport import KrakenWebSocketTransport

if TYPE_CHECKING:
    from ....models import FundingRate, Liquidation, MarkPrice, OpenInterest, OrderBook, Trade


class KrakenWSProvider(WSProvider):
    """Streaming-only provider for Kraken Spot or Futures."""

    def __init__(self, *, market_type: MarketType = MarketType.SPOT) -> None:
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
        """Custom stream implementation for Kraken that handles subscriptions."""

        # Build channel names for all symbols
        channels = [spec.build_stream_name(s, params) for s in symbols]

        # Chunk channels if needed (Kraken supports up to spec.max_streams_per_connection)
        cap = max(1, spec.max_streams_per_connection)
        channel_chunks = [channels[i : i + cap] for i in range(0, len(channels), cap)]

        # Single chunk fast path
        if len(channel_chunks) == 1:
            last_emit: dict[str, float] = {}
            last_close: dict[tuple[str, int], str] = {}

            if self._ws_url is None:
                raise RuntimeError("WebSocket URL not configured")
            transport = KrakenWebSocketTransport(url=self._ws_url)
            async for payload in transport.stream(channel_chunks[0]):
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
            return

        # Multi-chunk fan-in
        queue: asyncio.Queue = asyncio.Queue()

        async def pump(channels_chunk: list[str]):
            if self._ws_url is None:
                raise RuntimeError("WebSocket URL not configured")
            transport = KrakenWebSocketTransport(url=self._ws_url)
            async for payload in transport.stream(channels_chunk):
                if adapter.is_relevant(payload):
                    await queue.put(payload)

        tasks = [asyncio.create_task(pump(chunk)) for chunk in channel_chunks]
        last_emit: dict[str, float] = {}  # type: ignore[no-redef]
        last_close: dict[tuple[str, int], str] = {}  # type: ignore[no-redef]

        try:
            while True:
                payload = await queue.get()
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
        finally:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

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

    # --- Liquidations (Futures) ---
    async def stream_liquidations(self) -> AsyncIterator[Liquidation]:
        # Kraken liquidations require subscribing to specific symbols
        # Subscribe to major symbols for liquidations
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "ADAUSDT"]
        async for obj in self.stream("liquidations", symbols, {}):
            yield obj
