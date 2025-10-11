"""Unit tests for LiquidationFeed using a fake provider."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List

import pytest

from laakhay.data.clients.liquidation_feed import LiquidationFeed
from laakhay.data.models import Liquidation


class FakeLiqProvider:
    def __init__(self) -> None:
        self._events: Dict[str, List[Liquidation]] = {}

    def queue(self, symbol: str, items: List[Liquidation]) -> None:
        self._events.setdefault(symbol.upper(), []).extend(items)

    async def stream_liquidations(self):
        for sym_items in self._events.values():
            for item in sym_items:
                yield item
        while True:
            await asyncio.sleep(3600)


@pytest.mark.asyncio
async def test_liquidation_feed_cache_and_subscribe():
    provider = FakeLiqProvider()
    feed = LiquidationFeed(provider)

    liq = Liquidation(
        symbol="BTCUSDT",
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        side="SELL",
        order_type="LIQUIDATION",
        time_in_force="IOC",
        original_quantity=Decimal("1.0"),
        price=Decimal("50000.00"),
        average_price=Decimal("49950.00"),
        order_status="FILLED",
        last_filled_quantity=Decimal("1.0"),
        accumulated_quantity=Decimal("1.0"),
    )
    provider.queue("BTCUSDT", [liq])

    received: list[Liquidation] = []

    async def on_item(item: Liquidation):
        received.append(item)

    await feed.start()
    feed.subscribe(on_item, symbols=["BTCUSDT"])

    await asyncio.sleep(0.05)

    latest = feed.get_latest("BTCUSDT")
    assert latest is not None and latest.symbol == "BTCUSDT"
    assert any(x.symbol == "BTCUSDT" for x in received)

    await feed.stop()
