"""Unit tests for DataFeed behavior with a fake provider."""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from laakhay.data import DataFeed
from laakhay.data.core import MarketType, Timeframe
from laakhay.data.models import Bar, StreamingBar


class FakeProvider:
    """Minimal provider that mimics BinanceWebSocketMixin interface."""

    def __init__(self) -> None:
        self.market_type = MarketType.FUTURES
        self._events: dict[str, list[StreamingBar]] = {}

    def queue(self, symbol: str, bars: list[Bar]) -> None:
        streaming_bars = [
            StreamingBar(
                symbol=symbol,
                timestamp=bar.timestamp,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                is_closed=bar.is_closed,
            )
            for bar in bars
        ]
        self._events.setdefault(symbol.upper(), []).extend(streaming_bars)

    async def stream_candles_multi(
        self,
        symbols: list[str],
        interval: Timeframe,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        # Yield queued streaming bars for requested symbols, then sleep forever
        for s in symbols:
            for sb in self._events.get(s.upper(), []):
                yield sb
        while True:
            await asyncio.sleep(3600)


@pytest.mark.asyncio
async def test_data_feed_cache_and_subscribe_dynamic_symbols():
    fp = FakeProvider()
    feed = DataFeed(fp)

    # Prepare bars for BTC and ETH
    btc_bar = Bar(
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        open=Decimal("1"),
        high=Decimal("2"),
        low=Decimal("1"),
        close=Decimal("1.5"),
        volume=Decimal("10"),
    )
    eth_bar = Bar(
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        open=Decimal("1"),
        high=Decimal("2"),
        low=Decimal("1"),
        close=Decimal("1.25"),
        volume=Decimal("5"),
    )
    fp.queue("BTCUSDT", [btc_bar])
    fp.queue("ETHUSDT", [eth_bar])

    received: list[StreamingBar] = []

    async def on_bar(sb: StreamingBar):
        received.append(sb)

    # Start with BTC only
    await feed.start(symbols=["BTCUSDT"], interval=Timeframe.M1, only_closed=True)
    feed.subscribe(on_bar, symbols=["BTCUSDT"], interval=Timeframe.M1, only_closed=True)

    # Let the stream loop process queued events
    await asyncio.sleep(0.05)

    # Cache hit for BTC
    b = feed.get_latest_bar("BTCUSDT", interval=Timeframe.M1)
    assert b is not None
    assert any(x.close == Decimal("1.5") for x in received)  # Check by close price

    # Dynamically add ETH
    await feed.add_symbols(["ETHUSDT"])
    await asyncio.sleep(0.05)

    # Subscribe for ETH and ensure cache gets populated
    feed.subscribe(on_bar, symbols=["ETHUSDT"], interval=Timeframe.M1, only_closed=True)
    await asyncio.sleep(0.05)
    b2 = feed.get_latest_bar("ETHUSDT", interval=Timeframe.M1)
    assert b2 is not None

    await feed.stop()
