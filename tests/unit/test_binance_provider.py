"""Unit tests for Binance REST/WS providers (decoupled)."""

import asyncio

from laakhay.data.core import MarketType, Timeframe
from laakhay.data.providers import BinanceProvider, BinanceRESTProvider, BinanceWSProvider
from laakhay.data.providers.binance.constants import INTERVAL_MAP


def test_binance_rest_provider_instantiation_defaults_to_spot():
    provider = BinanceRESTProvider()
    assert provider.market_type == MarketType.SPOT


def test_binance_rest_provider_instantiation_futures():
    provider = BinanceRESTProvider(market_type=MarketType.FUTURES)
    assert provider.market_type == MarketType.FUTURES


def test_binance_interval_mapping_constants():
    assert INTERVAL_MAP[Timeframe.M1] == "1m"
    assert INTERVAL_MAP[Timeframe.H1] == "1h"
    assert INTERVAL_MAP[Timeframe.D1] == "1d"
    assert INTERVAL_MAP[Timeframe.W1] == "1w"


def test_binance_ws_provider_instantiation():
    ws = BinanceWSProvider()
    assert ws.market_type == MarketType.SPOT

    ws_fut = BinanceWSProvider(market_type=MarketType.FUTURES)
    assert ws_fut.market_type == MarketType.FUTURES


def test_binance_provider_instantiation_defaults_to_spot():
    provider = BinanceProvider()
    assert provider.market_type == MarketType.SPOT


def test_binance_provider_instantiation_futures():
    provider = BinanceProvider(market_type=MarketType.FUTURES)
    assert provider.market_type == MarketType.FUTURES


def test_binance_provider_context_manager_closes():
    async def run() -> bool:
        async with BinanceProvider() as provider:
            return provider.market_type == MarketType.SPOT

    assert asyncio.run(run())
