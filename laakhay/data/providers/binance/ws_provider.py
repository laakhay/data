"""Binance WebSocket-only provider.

Implements the WSProvider interface using shared transport/runner with
Binance-specific endpoint specs and adapters.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, Callable, Type

from ...core import MarketType, Timeframe
from ...io import StreamRunner, WSProvider, MessageAdapter
from ...models.streaming_bar import StreamingBar
from .ws.adapters import (
    FundingRateAdapter,
    MarkPriceAdapter,
    OhlcvAdapter,
    OpenInterestAdapter,
    OrderBookAdapter,
    TradesAdapter,
    LiquidationsAdapter,
)
from .ws.endpoints import (
    mark_price_spec,
    ohlcv_spec,
    open_interest_spec,
    order_book_spec,
    trades_spec,
    liquidations_spec,
)

if TYPE_CHECKING:
    from ...models import FundingRate, MarkPrice, OpenInterest, OrderBook, Trade, Liquidation


class BinanceWSProvider(WSProvider):
    """Streaming-only provider for Binance Spot or Futures."""

    def __init__(self, *, market_type: MarketType = MarketType.SPOT) -> None:
        self.market_type = market_type
        # Endpoint registry: key -> (spec_builder, adapter_class)
        self._ENDPOINTS: dict[str, tuple[Callable[[MarketType], Any], Type[MessageAdapter]]] = {
            "ohlcv": (ohlcv_spec, OhlcvAdapter),
            "trades": (trades_spec, TradesAdapter),
            "open_interest": (open_interest_spec, OpenInterestAdapter),
            "funding_rate": (mark_price_spec, FundingRateAdapter),
            "mark_price": (mark_price_spec, MarkPriceAdapter),
            "order_book": (order_book_spec, OrderBookAdapter),
            "liquidations": (liquidations_spec, LiquidationsAdapter),
        }

    async def stream_ohlcv(  # type: ignore[override]
        self,
        symbol: str,
        interval: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        # Delegate to registry-backed stream(); dedupe handled in stream()
        async for obj in self.stream(
            "ohlcv",
            [symbol],
            {"interval": interval},
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_key=None,
        ):
            yield obj

    async def stream_ohlcv_multi(  # type: ignore[override]
        self,
        symbols: list[str],
        interval: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        # Delegate to registry-backed stream(); dedupe handled in stream()
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

    # --- Funding Rate (predicted via markPrice stream) ---
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
        async for obj in self.stream("liquidations", ["!forceOrder@arr"], {}):
            yield obj
