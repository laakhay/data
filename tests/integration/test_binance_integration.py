"""Integration tests for BinanceProvider."""

import asyncio
from datetime import datetime, timedelta

from laakhay.data.core import Timeframe
from laakhay.data.providers import BinanceProvider


def test_binance_sync_wrapper():
    """Test synchronous wrapper for get_candles."""

    async def fetch():
        async with BinanceProvider() as provider:
            return await provider.get_candles(symbol="BTCUSDT", interval=Timeframe.M1, limit=2)

    candles = asyncio.run(fetch())
    assert len(candles) == 2
    assert candles[0].symbol == "BTCUSDT"


def test_binance_fetch_symbols_sync():
    """Test fetching symbols synchronously."""

    async def fetch():
        async with BinanceProvider() as provider:
            return await provider.get_symbols()

    symbols = asyncio.run(fetch())
    assert len(symbols) > 0

    symbol_names = [s.symbol for s in symbols]
    assert "BTCUSDT" in symbol_names
    assert "ETHUSDT" in symbol_names


def test_binance_fetch_with_timeframe_sync():
    """Test fetching candles with time range synchronously."""

    async def fetch():
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=30)

        async with BinanceProvider() as provider:
            return await provider.get_candles(
                symbol="ETHUSDT",
                interval=Timeframe.M5,
                start_time=start_time,
                end_time=end_time,
                limit=10,
            )

    candles = asyncio.run(fetch())
    assert len(candles) > 0
    assert all(c.symbol == "ETHUSDT" for c in candles)
