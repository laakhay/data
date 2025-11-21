"""Unit tests for OKX REST/WS providers (decoupled)."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from laakhay.data.connectors.okx.config import INTERVAL_MAP
from laakhay.data.connectors.okx.provider import OKXProvider
from laakhay.data.connectors.okx.rest.provider import OKXRESTConnector
from laakhay.data.connectors.okx.ws.provider import OKXWSConnector
from laakhay.data.core import MarketType, Timeframe
from laakhay.data.models import OHLCV, Bar, SeriesMeta


def test_okx_rest_provider_instantiation_defaults_to_spot():
    provider = OKXRESTConnector(market_type=MarketType.SPOT)
    assert provider.market_type == MarketType.SPOT


def test_okx_rest_provider_instantiation_futures():
    provider = OKXRESTConnector(market_type=MarketType.FUTURES)
    assert provider.market_type == MarketType.FUTURES


def test_okx_interval_mapping_constants():
    assert INTERVAL_MAP[Timeframe.M1] == "1m"
    assert INTERVAL_MAP[Timeframe.H1] == "1H"
    assert INTERVAL_MAP[Timeframe.D1] == "1D"
    assert INTERVAL_MAP[Timeframe.W1] == "1W"


def test_okx_ws_provider_instantiation():
    ws = OKXWSConnector(market_type=MarketType.SPOT)
    assert ws.market_type == MarketType.SPOT

    ws_fut = OKXWSConnector(market_type=MarketType.FUTURES)
    assert ws_fut.market_type == MarketType.FUTURES


def test_okx_provider_instantiation_defaults_to_spot():
    provider = OKXProvider()
    assert provider.market_type == MarketType.SPOT


def test_okx_provider_instantiation_futures():
    provider = OKXProvider(market_type=MarketType.FUTURES)
    assert provider.market_type == MarketType.FUTURES


def test_okx_provider_context_manager_closes():
    async def run() -> bool:
        async with OKXProvider() as provider:
            return provider.market_type == MarketType.SPOT

    assert asyncio.run(run())


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Chunk executor aggregation needs investigation")
async def test_okx_rest_fetch_ohlcv_chunking(monkeypatch):
    provider = OKXRESTConnector(market_type=MarketType.SPOT)
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

    responses = [make_chunk(0, 300), make_chunk(300, 200)]
    calls: list[dict[str, Any]] = []

    async def fake_fetch(endpoint: str, params: dict[str, Any]) -> OHLCV:
        calls.append(params)
        return responses.pop(0)

    monkeypatch.setattr(provider, "fetch", fake_fetch)

    result = await provider.fetch_ohlcv(
        "BTC-USDT",
        Timeframe.M1,
        start_time=base_time,
        limit=500,
        max_chunks=3,
    )

    assert len(result.bars) == 500
    assert result.bars[0].timestamp == base_time
    assert result.bars[-1].timestamp == base_time + timedelta(minutes=499)
    assert result.bars == sorted(result.bars, key=lambda b: b.timestamp)

    assert calls[0]["limit"] == 300
    assert calls[1]["limit"] == 200
    assert calls[1]["start_time"] == base_time + timedelta(minutes=300)


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Chunk executor aggregation needs investigation")
async def test_okx_rest_fetch_ohlcv_respects_max_chunks(monkeypatch):
    provider = OKXRESTConnector(market_type=MarketType.SPOT)
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

    responses = [make_chunk(0, 300), make_chunk(300, 300), make_chunk(600, 200)]
    calls: list[dict[str, Any]] = []

    async def fake_fetch(endpoint: str, params: dict[str, Any]) -> OHLCV:
        calls.append(params)
        return responses.pop(0)

    monkeypatch.setattr(provider, "fetch", fake_fetch)

    result = await provider.fetch_ohlcv(
        "BTC-USDT",
        Timeframe.M1,
        start_time=base_time,
        limit=1000,
        max_chunks=2,
    )

    assert len(result.bars) == 600
    assert len(calls) == 2
