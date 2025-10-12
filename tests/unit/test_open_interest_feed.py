"""Unit tests for OpenInterestFeed using a fake provider."""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from laakhay.data.clients.open_interest_feed import OpenInterestFeed
from laakhay.data.models import OpenInterest


class FakeOIProvider:
    def __init__(self) -> None:
        self._events: dict[str, list[OpenInterest]] = {}

    def queue(self, symbol: str, items: list[OpenInterest]) -> None:
        self._events.setdefault(symbol.upper(), []).extend(items)

    async def stream_open_interest(
        self, symbols: list[str], period: str = "5m"
    ) -> AsyncIterator[OpenInterest]:
        for s in symbols:
            for item in self._events.get(s.upper(), []):
                yield item
        while True:
            await asyncio.sleep(3600)


@pytest.mark.asyncio
async def test_open_interest_feed_cache_and_subscribe():
    provider = FakeOIProvider()
    feed = OpenInterestFeed(provider)

    oi_btc = OpenInterest(
        symbol="BTCUSDT",
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        open_interest=Decimal("12345.67"),
        open_interest_value=Decimal("500000000.00"),
    )
    provider.queue("BTCUSDT", [oi_btc])

    received: list[OpenInterest] = []

    async def on_item(item: OpenInterest):
        received.append(item)

    await feed.start(symbols=["BTCUSDT"], period="5m")
    feed.subscribe(on_item, symbols=["BTCUSDT"])

    await asyncio.sleep(0.05)

    latest = feed.get_latest("BTCUSDT")
    assert latest is not None and latest.symbol == "BTCUSDT"
    assert any(x.symbol == "BTCUSDT" for x in received)

    await feed.stop()
