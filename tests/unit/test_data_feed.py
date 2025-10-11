"""Unit tests for DataFeed behavior with a fake provider."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import AsyncIterator, Dict, List, Optional

import pytest

from laakhay.data import DataFeed
from laakhay.data.core import TimeInterval, MarketType
from laakhay.data.models import Candle


class FakeProvider:
    """Minimal provider that mimics BinanceWebSocketMixin interface."""

    def __init__(self) -> None:
        self.market_type = MarketType.FUTURES
        self._events: Dict[str, List[Candle]] = {}

    def queue(self, symbol: str, candles: List[Candle]) -> None:
        self._events.setdefault(symbol.upper(), []).extend(candles)

    async def stream_candles_multi(
        self,
        symbols: List[str],
        interval: TimeInterval,
        only_closed: bool = False,
    throttle_ms: Optional[int] = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[Candle]:
        # Yield queued candles for requested symbols, then sleep forever
        for s in symbols:
            for c in self._events.get(s.upper(), []):
                yield c
        while True:
            await asyncio.sleep(3600)


@pytest.mark.asyncio
async def test_data_feed_cache_and_subscribe_dynamic_symbols():
    fp = FakeProvider()
    feed = DataFeed(fp)

    # Prepare candles for BTC and ETH
    btc = Candle(
        symbol="BTCUSDT",
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        open=Decimal("1"), high=Decimal("2"), low=Decimal("1"), close=Decimal("1.5"), volume=Decimal("10"),
    )
    eth = Candle(
        symbol="ETHUSDT",
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        open=Decimal("1"), high=Decimal("2"), low=Decimal("1"), close=Decimal("1.25"), volume=Decimal("5"),
    )
    fp.queue("BTCUSDT", [btc])
    fp.queue("ETHUSDT", [eth])

    received: list[Candle] = []

    async def on_candle(c: Candle):
        received.append(c)

    # Start with BTC only
    await feed.start(symbols=["BTCUSDT"], interval=TimeInterval.M1, only_closed=True)
    feed.subscribe(on_candle, symbols=["BTCUSDT"], interval=TimeInterval.M1, only_closed=True)

    # Let the stream loop process queued events
    await asyncio.sleep(0.05)

    # Cache hit for BTC
    c = feed.get_latest_candle("BTCUSDT", interval=TimeInterval.M1)
    assert c is not None and c.symbol == "BTCUSDT"
    assert any(x.symbol == "BTCUSDT" for x in received)

    # Dynamically add ETH
    await feed.add_symbols(["ETHUSDT"]) 
    await asyncio.sleep(0.05)

    # Subscribe for ETH and ensure cache gets populated
    feed.subscribe(on_candle, symbols=["ETHUSDT"], interval=TimeInterval.M1, only_closed=True)
    await asyncio.sleep(0.05)
    c2 = feed.get_latest_candle("ETHUSDT", interval=TimeInterval.M1)
    assert c2 is not None and c2.symbol == "ETHUSDT"

    await feed.stop()
