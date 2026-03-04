"""Unit tests for chunk execution logic."""

from __future__ import annotations

import asyncio
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

    @pytest.mark.asyncio
    async def test_iterate_parallel_preserves_plan_order(self):
        """Parallel fetch should still yield data in plan order."""
        policy = ChunkPolicy(max_points=1000)
        executor = ChunkExecutor(policy=policy, max_concurrency=2)
        base_time = datetime(2024, 1, 1, tzinfo=UTC)

        async def fetch_chunk(plan: ChunkPlan) -> OHLCV:
            # Intentionally make earlier plans slower to force out-of-order completion.
            await asyncio.sleep(0.02 * (4 - plan.chunk_index))
            ts = base_time.replace(hour=plan.chunk_index)
            bar = Bar(
                timestamp=ts,
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100.5"),
                volume=Decimal("10"),
                is_closed=True,
            )
            return OHLCV(meta=SeriesMeta(symbol="BTCUSDT", timeframe="1m"), bars=[bar])

        plans = [ChunkPlan(limit=1, chunk_index=i) for i in range(4)]

        result_timestamps: list[datetime] = []
        async for result in executor.iterate(
            plans=plans,
            fetch_chunk=fetch_chunk,
            max_concurrency=2,
        ):
            result_timestamps.extend([bar.timestamp for bar in result.data])

        expected = [base_time.replace(hour=i) for i in range(4)]
        assert result_timestamps == expected

    @pytest.mark.asyncio
    async def test_iterate_coalesces_yield_points(self):
        """Executor can yield larger application batches than fetch chunk size."""
        policy = ChunkPolicy(max_points=1000)
        executor = ChunkExecutor(policy=policy)
        base_time = datetime(2024, 1, 1, tzinfo=UTC)

        async def fetch_chunk(plan: ChunkPlan) -> OHLCV:
            start = plan.chunk_index * 2
            bars = [
                Bar(
                    timestamp=base_time.replace(hour=start + i),
                    open=Decimal("100"),
                    high=Decimal("101"),
                    low=Decimal("99"),
                    close=Decimal("100.5"),
                    volume=Decimal("10"),
                    is_closed=True,
                )
                for i in range(2)
            ]
            return OHLCV(meta=SeriesMeta(symbol="BTCUSDT", timeframe="1m"), bars=bars)

        plans = [ChunkPlan(limit=2, chunk_index=i) for i in range(5)]  # 10 total bars
        batch_sizes: list[int] = []

        async for result in executor.iterate(
            plans=plans,
            fetch_chunk=fetch_chunk,
            yield_points=5,
        ):
            batch_sizes.append(len(result.data))

        assert batch_sizes == [6, 4]

    @pytest.mark.asyncio
    async def test_iterate_caps_parallelism_by_yield_target(self):
        """Yield target should reduce unnecessary fetch parallelism."""
        policy = ChunkPolicy(max_points=1000)
        executor = ChunkExecutor(policy=policy)
        base_time = datetime(2024, 1, 1, tzinfo=UTC)

        active = 0
        peak = 0
        lock = asyncio.Lock()

        async def fetch_chunk(plan: ChunkPlan) -> OHLCV:
            nonlocal active, peak
            async with lock:
                active += 1
                peak = max(peak, active)

            await asyncio.sleep(0.01)

            async with lock:
                active -= 1

            bar = Bar(
                timestamp=base_time.replace(hour=plan.chunk_index),
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100.5"),
                volume=Decimal("10"),
                is_closed=True,
            )
            return OHLCV(meta=SeriesMeta(symbol="BTCUSDT", timeframe="1m"), bars=[bar])

        plans = [
            ChunkPlan(
                limit=1000,
                start_time=base_time.replace(hour=i),
                end_time=base_time.replace(hour=i),
                chunk_index=i,
            )
            for i in range(10)
        ]

        # 5k target with 1k fetch chunks means only 5 parallel requests are useful.
        async for _ in executor.iterate(
            plans=plans,
            fetch_chunk=fetch_chunk,
            max_concurrency=10,
            yield_points=5000,
        ):
            pass

        assert peak <= 5
