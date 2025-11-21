"""Unit tests for Binance REST/WS providers (decoupled)."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from laakhay.data.connectors.binance import (
    BinanceProvider,
    BinanceRESTProvider,
    BinanceWSProvider,
)
from laakhay.data.connectors.binance.config import INTERVAL_MAP
from laakhay.data.core import MarketType, Timeframe
from laakhay.data.models import OHLCV, Bar, SeriesMeta


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
async def test_binance_provider_fetch_health(monkeypatch):
    provider = BinanceProvider()

    async def fake_fetch_health():
        return {"status": "ok"}

    monkeypatch.setattr(provider._rest, "fetch_health", fake_fetch_health)
    result = await provider.fetch_health()
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_binance_rest_fetch_health_paths(monkeypatch):
    provider = BinanceRESTProvider()
    called = []

    async def fake_get(path, *, params=None):
        called.append(path)
        return {}

    monkeypatch.setattr(provider._transport, "get", fake_get)
    result = await provider.fetch_health()
    assert called == ["/api/v3/ping"]
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_binance_rest_fetch_health_futures(monkeypatch):
    provider = BinanceRESTProvider(market_type=MarketType.FUTURES)
    called = []

    async def fake_get(path, *, params=None):
        called.append(path)
        return {}

    monkeypatch.setattr(provider._transport, "get", fake_get)
    result = await provider.fetch_health()
    assert called == ["/fapi/v1/ping"]
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_binance_rest_fetch_historical_trades_requires_api_key():
    provider = BinanceRESTProvider()
    with pytest.raises(ValueError):
        await provider.fetch_historical_trades("BTCUSDT")


@pytest.mark.asyncio
async def test_binance_rest_fetch_historical_trades_params(monkeypatch):
    provider = BinanceRESTProvider(api_key="ABC123")
    captured: dict[str, Any] = {}

    async def fake_fetch(endpoint: str, params: dict[str, Any]) -> list[Any]:
        captured["endpoint"] = endpoint
        captured["params"] = params
        return []

    # Mock the connector's fetch method
    monkeypatch.setattr(provider, "fetch", fake_fetch)

    result = await provider.fetch_historical_trades("BTCUSDT", limit=200, from_id=42)
    assert result == []
    assert captured["endpoint"] == "historical_trades"
    assert captured["params"]["symbol"] == "BTCUSDT"
    assert captured["params"]["from_id"] == 42
    assert captured["params"]["limit"] == 200
    assert captured["params"]["api_key"] == "ABC123"


@pytest.mark.asyncio
async def test_binance_provider_fetch_historical_trades():
    rest = MagicMock()
    rest.fetch_historical_trades = AsyncMock(return_value=["trade"])
    ws = MagicMock()

    provider = BinanceProvider(rest_connector=rest, ws_connector=ws)
    result = await provider.fetch_historical_trades("BTCUSDT", limit=100, from_id=20)
    assert result == ["trade"]
    rest.fetch_historical_trades.assert_awaited_once_with(symbol="BTCUSDT", limit=100, from_id=20)


@pytest.mark.asyncio
async def test_binance_rest_fetch_ohlcv_chunking(monkeypatch):
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

    result = await provider.fetch_ohlcv(
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
async def test_binance_rest_fetch_ohlcv_respects_max_chunks(monkeypatch):
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

    result = await provider.fetch_ohlcv(
        "BTCUSDT",
        Timeframe.M1,
        start_time=base_time,
        limit=5000,
        max_chunks=2,
    )

    assert len(result.bars) == 2000
    assert len(calls) == 2
