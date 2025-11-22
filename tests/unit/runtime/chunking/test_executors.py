"""Unit tests for chunk execution logic."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from laakhay.data.models import OHLCV, Bar, SeriesMeta
from laakhay.data.runtime.chunking import (
    ChunkExecutor,
    ChunkHint,
    ChunkPlan,
    ChunkPolicy,
    WeightPolicy,
)


class TestChunkExecutor:
    """Test ChunkExecutor functionality."""

    @pytest.mark.asyncio
    async def test_execute_single_chunk(self):
        """Test executing a single chunk."""
        policy = ChunkPolicy(max_points=1000)
        executor = ChunkExecutor(policy=policy)

        bars = [
            Bar(
                timestamp=datetime(2024, 1, 1, i, tzinfo=UTC),
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100.5"),
                volume=Decimal("10"),
                is_closed=True,
            )
            for i in range(10)
        ]
        ohlcv = OHLCV(meta=SeriesMeta(symbol="BTCUSDT", timeframe="1m"), bars=bars)

        async def fetch_chunk(plan: ChunkPlan) -> OHLCV:
            return ohlcv

        plans = [ChunkPlan(limit=10, chunk_index=0)]
        result = await executor.execute(plans=plans, fetch_chunk=fetch_chunk)

        assert result.chunks_used == 1
        assert result.total_points == 10
        assert isinstance(result.data, list)
        assert len(result.data) == 10

    @pytest.mark.asyncio
    async def test_execute_multiple_chunks_with_deduplication(self):
        """Test executing multiple chunks with deduplication."""
        policy = ChunkPolicy(max_points=1000)
        hint = ChunkHint(timestamp_key="timestamp")
        executor = ChunkExecutor(policy=policy, hint=hint)

        base_time = datetime(2024, 1, 1, tzinfo=UTC)

        async def fetch_chunk(plan: ChunkPlan) -> OHLCV:
            # First chunk: bars 0-9
            # Second chunk: bars 8-17 (overlap at 8, 9)
            start_idx = 0 if plan.chunk_index == 0 else 8
            end_idx = 10 if plan.chunk_index == 0 else 18

            bars = [
                Bar(
                    timestamp=base_time.replace(hour=i),
                    open=Decimal("100"),
                    high=Decimal("101"),
                    low=Decimal("99"),
                    close=Decimal("100.5"),
                    volume=Decimal("10"),
                    is_closed=True,
                )
                for i in range(start_idx, end_idx)
            ]
            return OHLCV(meta=SeriesMeta(symbol="BTCUSDT", timeframe="1m"), bars=bars)

        plans = [
            ChunkPlan(limit=10, chunk_index=0),
            ChunkPlan(limit=10, chunk_index=1),
        ]
        result = await executor.execute(plans=plans, fetch_chunk=fetch_chunk)

        assert result.chunks_used == 2
        # Should have 18 unique bars (0-17, with 8-9 deduplicated)
        assert result.total_points == 18

    @pytest.mark.asyncio
    async def test_execute_stops_early_on_empty_chunk(self):
        """Test that executor stops early when chunk returns no data."""
        policy = ChunkPolicy(max_points=1000)
        executor = ChunkExecutor(policy=policy)

        call_count = 0

        async def fetch_chunk(plan: ChunkPlan) -> OHLCV:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First chunk returns full limit (10 bars)
                bars = [
                    Bar(
                        timestamp=datetime(2024, 1, 1, i, tzinfo=UTC),
                        open=Decimal("100"),
                        high=Decimal("101"),
                        low=Decimal("99"),
                        close=Decimal("100.5"),
                        volume=Decimal("10"),
                        is_closed=True,
                    )
                    for i in range(10)
                ]
                return OHLCV(meta=SeriesMeta(symbol="BTCUSDT", timeframe="1m"), bars=bars)
            # Second chunk returns empty
            return OHLCV(meta=SeriesMeta(symbol="BTCUSDT", timeframe="1m"), bars=[])

        plans = [
            ChunkPlan(limit=10, chunk_index=0),
            ChunkPlan(limit=10, chunk_index=1),
        ]
        result = await executor.execute(plans=plans, fetch_chunk=fetch_chunk)

        # Executor processes first chunk (has data), then second chunk (empty), then stops
        assert result.chunks_used == 2  # Both chunks were attempted
        assert result.total_points == 10
        assert call_count == 2  # Both chunks were fetched

    @pytest.mark.asyncio
    async def test_execute_stops_early_on_fewer_points(self):
        """Test that executor stops early when chunk returns fewer than requested."""
        policy = ChunkPolicy(max_points=1000)
        executor = ChunkExecutor(policy=policy)

        async def fetch_chunk(plan: ChunkPlan) -> OHLCV:
            # Return fewer bars than requested (end of data)
            bars = [
                Bar(
                    timestamp=datetime(2024, 1, 1, i, tzinfo=UTC),
                    open=Decimal("100"),
                    high=Decimal("101"),
                    low=Decimal("99"),
                    close=Decimal("100.5"),
                    volume=Decimal("10"),
                    is_closed=True,
                )
                for i in range(5)  # Only 5 bars, but limit is 10
            ]
            return OHLCV(meta=SeriesMeta(symbol="BTCUSDT", timeframe="1m"), bars=bars)

        plans = [
            ChunkPlan(limit=10, chunk_index=0),
            ChunkPlan(limit=10, chunk_index=1),
        ]
        result = await executor.execute(plans=plans, fetch_chunk=fetch_chunk)

        assert result.chunks_used == 1  # Should stop after first chunk
        assert result.total_points == 5

    @pytest.mark.asyncio
    async def test_execute_tracks_weight(self):
        """Test that executor tracks request weight."""
        policy = ChunkPolicy(max_points=1000)
        weight_policy = WeightPolicy(static_weight=5)
        executor = ChunkExecutor(policy=policy, weight_policy=weight_policy)

        async def fetch_chunk(plan: ChunkPlan) -> OHLCV:
            bars = [
                Bar(
                    timestamp=datetime(2024, 1, 1, i, tzinfo=UTC),
                    open=Decimal("100"),
                    high=Decimal("101"),
                    low=Decimal("99"),
                    close=Decimal("100.5"),
                    volume=Decimal("10"),
                    is_closed=True,
                )
                for i in range(10)
            ]
            return OHLCV(meta=SeriesMeta(symbol="BTCUSDT", timeframe="1m"), bars=bars)

        plans = [
            ChunkPlan(limit=10, chunk_index=0),
            ChunkPlan(limit=10, chunk_index=1),
        ]
        result = await executor.execute(plans=plans, fetch_chunk=fetch_chunk)

        assert result.weight_consumed == 10  # 2 chunks * 5 weight each
