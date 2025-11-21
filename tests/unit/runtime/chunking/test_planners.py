"""Unit tests for chunk planning logic."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from laakhay.data.core import Timeframe
from laakhay.data.runtime.chunking import ChunkPlanner, ChunkPolicy


class TestChunkPlanner:
    """Test ChunkPlanner functionality."""

    def test_plan_single_chunk_under_limit(self):
        """Test planning when limit is under max_points."""
        policy = ChunkPolicy(max_points=1000)
        planner = ChunkPlanner(policy=policy)

        plans = planner.plan(limit=500, max_chunks=1)

        assert len(plans) == 1
        assert plans[0].limit == 500
        assert plans[0].chunk_index == 0

    def test_plan_multiple_chunks_limit_based(self):
        """Test planning multiple chunks for limit-based requests."""
        policy = ChunkPolicy(max_points=1000)
        planner = ChunkPlanner(policy=policy)

        plans = planner.plan(limit=2500, max_chunks=None)

        assert len(plans) == 3
        assert plans[0].limit == 1000
        assert plans[1].limit == 1000
        assert plans[2].limit == 500
        assert plans[0].chunk_index == 0
        assert plans[1].chunk_index == 1
        assert plans[2].chunk_index == 2

    def test_plan_respects_max_chunks(self):
        """Test that planner respects max_chunks limit."""
        policy = ChunkPolicy(max_points=1000, max_chunks=2)
        planner = ChunkPlanner(policy=policy)

        plans = planner.plan(limit=5000, max_chunks=2)

        assert len(plans) == 2
        assert all(plan.limit == 1000 for plan in plans)

    def test_plan_time_based_with_timeframe(self):
        """Test time-based planning with timeframe."""
        policy = ChunkPolicy(max_points=1000)
        planner = ChunkPlanner(policy=policy)

        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 1, 2, tzinfo=UTC)  # 24 hours = 1440 minutes

        plans = planner.plan(
            limit=2000,
            start_time=start,
            end_time=end,
            timeframe=Timeframe.M1,
            max_chunks=None,
        )

        # Should create 2 chunks (1000 minutes each)
        assert len(plans) >= 1
        assert plans[0].start_time == start
        assert plans[0].limit == 1000

    def test_plan_requires_start_time(self):
        """Test that planner raises error when start_time required but missing."""
        policy = ChunkPolicy(max_points=1000, requires_start_time=True)
        planner = ChunkPlanner(policy=policy)

        with pytest.raises(ValueError, match="start_time is required"):
            planner.plan(limit=500)

    def test_plan_timeframe_required_for_time_based(self):
        """Test that timeframe is required for time-based chunking."""
        policy = ChunkPolicy(max_points=1000)
        planner = ChunkPlanner(policy=policy)

        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 1, 2, tzinfo=UTC)

        with pytest.raises(ValueError, match="timeframe is required"):
            planner.plan(limit=2000, start_time=start, end_time=end)

    def test_plan_no_limit_or_time_range(self):
        """Test that planner raises error when no limit or time range provided."""
        policy = ChunkPolicy(max_points=1000)
        planner = ChunkPlanner(policy=policy)

        with pytest.raises(ValueError, match="Cannot plan chunks"):
            planner.plan()
