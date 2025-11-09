"""Unit tests for Binance REST/WS providers (decoupled)."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from laakhay.data.core import MarketType, Timeframe
from laakhay.data.models import OHLCV, Bar, SeriesMeta
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


@pytest.mark.asyncio
async def test_binance_rest_get_candles_chunking(monkeypatch):
    provider = BinanceRESTProvider()
    base_time = datetime(2024, 1, 1, tzinfo=UTC)

    def make_chunk(start_index: int, count: int) -> OHLCV:
        bars = []
        for i in range(count):
            ts = base_time + timedelta(minutes=start_index + i)
            price = Decimal(str(100 + start_index + i))
            bars.append(
                Bar(
                    timestamp=ts,
                    open=price,
                    high=price + Decimal("1"),
                    low=price - Decimal("1"),
                    close=price + Decimal("0.5"),
                    volume=Decimal("10"),
                    is_closed=True,
                )
            )
        return OHLCV(meta=SeriesMeta(symbol="BTCUSDT", timeframe="1m"), bars=bars)

    responses = [make_chunk(0, 1000), make_chunk(1000, 200)]
    calls: list[dict[str, Any]] = []

    async def fake_fetch(endpoint: str, params: dict[str, Any]) -> OHLCV:
        calls.append(params)
        return responses.pop(0)

    monkeypatch.setattr(provider, "fetch", fake_fetch)

    result = await provider.get_candles(
        "BTCUSDT",
        Timeframe.M1,
        start_time=base_time,
        limit=1200,
        max_chunks=3,
    )

    assert len(result.bars) == 1200
    assert result.bars[0].timestamp == base_time
    assert result.bars[-1].timestamp == base_time + timedelta(minutes=1199)
    assert result.bars == sorted(result.bars, key=lambda b: b.timestamp)

    assert calls[0]["limit"] == 1000
    assert calls[1]["limit"] == 200
    assert calls[1]["start_time"] == base_time + timedelta(minutes=1000)


@pytest.mark.asyncio
async def test_binance_rest_get_candles_respects_max_chunks(monkeypatch):
    provider = BinanceRESTProvider()
    base_time = datetime(2024, 1, 1, tzinfo=UTC)

    def make_chunk(start_index: int, count: int) -> OHLCV:
        bars = []
        for i in range(count):
            ts = base_time + timedelta(minutes=start_index + i)
            price = Decimal(str(100 + start_index + i))
            bars.append(
                Bar(
                    timestamp=ts,
                    open=price,
                    high=price + Decimal("1"),
                    low=price - Decimal("1"),
                    close=price + Decimal("0.5"),
                    volume=Decimal("10"),
                    is_closed=True,
                )
            )
        return OHLCV(meta=SeriesMeta(symbol="BTCUSDT", timeframe="1m"), bars=bars)

    responses = [make_chunk(0, 1000), make_chunk(1000, 1000), make_chunk(2000, 500)]
    calls: list[dict[str, Any]] = []

    async def fake_fetch(endpoint: str, params: dict[str, Any]) -> OHLCV:
        calls.append(params)
        return responses.pop(0)

    monkeypatch.setattr(provider, "fetch", fake_fetch)

    result = await provider.get_candles(
        "BTCUSDT",
        Timeframe.M1,
        start_time=base_time,
        limit=5000,
        max_chunks=2,
    )

    assert len(result.bars) == 2000
    assert len(calls) == 2
