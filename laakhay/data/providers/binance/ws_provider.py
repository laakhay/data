"""Binance WebSocket-only provider.

Implements the WSProvider interface using shared transport/runner with
Binance-specific endpoint specs and adapters.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from ...core import MarketType, Timeframe
from ...io import StreamRunner, WSProvider
from ...models.streaming_bar import StreamingBar
from .adapters import (
    CandlesAdapter,
    FundingRateAdapter,
    MarkPriceAdapter,
    OpenInterestAdapter,
    OrderBookAdapter,
    TradesAdapter,
)
from .endpoints import (
    candles_spec,
    mark_price_spec,
    open_interest_spec,
    order_book_spec,
    trades_spec,
)

if TYPE_CHECKING:
    from ...models import FundingRate, MarkPrice, OpenInterest, OrderBook, Trade


class BinanceWSProvider(WSProvider):
    """Streaming-only provider for Binance Spot or Futures."""

    def __init__(self, *, market_type: MarketType = MarketType.SPOT) -> None:
        self.market_type = market_type

    async def stream_candles(  # type: ignore[override]
        self,
        symbol: str,
        interval: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        # Use generic runner + adapter + endpoint spec
        runner = StreamRunner()
        spec = candles_spec(self.market_type)
        adapter = CandlesAdapter()
        params = {"interval": interval}

        dedupe_key = None
        if not only_closed and dedupe_same_candle:

            def _key(obj: StreamingBar) -> tuple[str, int, str]:
                return (
                    obj.symbol,
                    int(obj.timestamp.timestamp() * 1000),
                    str(obj.close),
                )

            dedupe_key = _key

        async for obj in runner.run(
            spec=spec,
            adapter=adapter,
            symbols=[symbol],
            params=params,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_key=dedupe_key,
        ):
            yield obj

    async def stream_candles_multi(  # type: ignore[override]
        self,
        symbols: list[str],
        interval: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        runner = StreamRunner()
        spec = candles_spec(self.market_type)
        adapter = CandlesAdapter()
        params = {"interval": interval}

        dedupe_key = None
        if not only_closed and dedupe_same_candle:

            def _key(obj: StreamingBar) -> tuple[str, int, str]:
                return (
                    obj.symbol,
                    int(obj.timestamp.timestamp() * 1000),
                    str(obj.close),
                )

            dedupe_key = _key

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

    async def close(self) -> None:
        # No persistent sockets to close beyond task cancellation handled by callers
        return None

    # --- Trades ---
    async def stream_trades(self, symbol: str) -> AsyncIterator[Trade]:
        runner = StreamRunner()
        spec = trades_spec(self.market_type)
        adapter = TradesAdapter()
        async for obj in runner.run(spec=spec, adapter=adapter, symbols=[symbol], params={}):
            yield obj

    async def stream_trades_multi(self, symbols: list[str]) -> AsyncIterator[Trade]:
        runner = StreamRunner()
        spec = trades_spec(self.market_type)
        adapter = TradesAdapter()
        async for obj in runner.run(spec=spec, adapter=adapter, symbols=symbols, params={}):
            yield obj

    # --- Open Interest ---
    async def stream_open_interest(
        self, symbols: list[str], period: str = "5m"
    ) -> AsyncIterator[OpenInterest]:
        runner = StreamRunner()
        spec = open_interest_spec(self.market_type)
        adapter = OpenInterestAdapter()
        params = {"period": period}
        async for obj in runner.run(spec=spec, adapter=adapter, symbols=symbols, params=params):
            yield obj

    # --- Funding Rate (predicted via markPrice stream) ---
    async def stream_funding_rate(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[FundingRate]:
        runner = StreamRunner()
        spec = mark_price_spec(self.market_type)
        adapter = FundingRateAdapter()
        params = {"update_speed": update_speed}
        async for obj in runner.run(spec=spec, adapter=adapter, symbols=symbols, params=params):
            yield obj

    # --- Mark Price ---
    async def stream_mark_price(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[MarkPrice]:
        runner = StreamRunner()
        spec = mark_price_spec(self.market_type)
        adapter = MarkPriceAdapter()
        params = {"update_speed": update_speed}
        async for obj in runner.run(spec=spec, adapter=adapter, symbols=symbols, params=params):
            yield obj

    # --- Order Book ---
    async def stream_order_book(
        self, symbol: str, update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        runner = StreamRunner()
        spec = order_book_spec(self.market_type)
        adapter = OrderBookAdapter()
        params = {"update_speed": update_speed}
        async for obj in runner.run(spec=spec, adapter=adapter, symbols=[symbol], params=params):
            yield obj
