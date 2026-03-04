"""Unit tests for OHLCV chunk service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from laakhay.data.core.enums import MarketType, Timeframe
from laakhay.data.models import OHLCV, Bar, SeriesMeta
from laakhay.data.runtime.chunking import ChunkPolicy, OHLCVChunkService, WeightPolicy


def _build_bars(start_index: int, count: int) -> list[Bar]:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    bars: list[Bar] = []
    for i in range(start_index, start_index + count):
        ts = base + timedelta(minutes=i)
        bars.append(
            Bar(
                timestamp=ts,
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100.5"),
                volume=Decimal("10"),
                is_closed=True,
            )
        )
    return bars


class TestOHLCVChunkService:
    """Test OHLCVChunkService execution behavior."""

    @pytest.mark.asyncio
    async def test_iterate_without_limit_or_range_uses_single_fetch(self):
        """No limit and no time range should avoid planner and do one fetch."""
        calls: list[tuple[datetime | None, datetime | None, int | None]] = []

        async def fetch_chunk(
            chunk_start: datetime | None,
            chunk_end: datetime | None,
            chunk_limit: int | None,
        ) -> OHLCV:
            calls.append((chunk_start, chunk_end, chunk_limit))
            return OHLCV(meta=SeriesMeta(symbol="BTCUSDT", timeframe="1m"), bars=_build_bars(0, 10))

        service = OHLCVChunkService(
            exchange="coinbase",
            market_type=MarketType.SPOT,
            fetch_chunk=fetch_chunk,
            chunk_policy=ChunkPolicy(max_points=1000, supports_auto_chunking=True),
            chunk_hint=None,
            weight_policy=WeightPolicy(static_weight=1),
        )

        chunks = []
        async for chunk in service.iterate(
            symbol="BTCUSDT",
            timeframe=Timeframe.M1,
            start_time=None,
            end_time=None,
            limit=None,
            max_chunks=10,
            fetch_concurrency=20,
            yield_chunk_size=20000,
        ):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert len(chunks[0].bars) == 10
        assert calls == [(None, None, None)]

    @pytest.mark.asyncio
    async def test_iterate_limit_inferred_from_max_chunks_for_binance_backfill(self):
        """For Binance limit-only flow, infer limit from max_chunks and backfill pages."""
        calls: list[tuple[datetime | None, datetime | None, int | None]] = []

        async def fetch_chunk(
            chunk_start: datetime | None,
            chunk_end: datetime | None,
            chunk_limit: int | None,
        ) -> OHLCV:
            calls.append((chunk_start, chunk_end, chunk_limit))

            # Return latest page first, then older pages.
            call_index = len(calls) - 1
            if call_index == 0:
                bars = _build_bars(200, 100)
            elif call_index == 1:
                bars = _build_bars(100, 100)
            elif call_index == 2:
                bars = _build_bars(0, 100)
            else:
                bars = []

            return OHLCV(meta=SeriesMeta(symbol="BTCUSDT", timeframe="1m"), bars=bars)

        service = OHLCVChunkService(
            exchange="binance",
            market_type=MarketType.SPOT,
            fetch_chunk=fetch_chunk,
            chunk_policy=ChunkPolicy(max_points=100, supports_auto_chunking=True),
            chunk_hint=None,
            weight_policy=WeightPolicy(static_weight=1),
        )

        chunks = []
        async for chunk in service.iterate(
            symbol="BTCUSDT",
            timeframe=Timeframe.M1,
            start_time=None,
            end_time=None,
            limit=None,
            max_chunks=3,
            fetch_concurrency=5,
            yield_chunk_size=None,
        ):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert len(chunks[0].bars) == 300
        assert chunks[0].bars[0].timestamp < chunks[0].bars[-1].timestamp
        assert [c[2] for c in calls] == [100, 100, 100]
        assert calls[0][1] is None
        assert calls[1][1] is not None
        assert calls[2][1] is not None
