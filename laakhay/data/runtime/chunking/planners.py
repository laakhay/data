"""Chunk planning logic for determining chunk windows.

This module provides the ChunkPlanner class that determines how to split
a user request into multiple chunks based on endpoint limits and policies.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from ...core.enums import Timeframe
from .definitions import ChunkHint, ChunkPlan, ChunkPolicy, calculate_chunk_window_size
from .telemetry import log_chunk_plan


class ChunkPlanner:
    """Plans chunk windows for paginated requests.

    The planner takes a user request (limit, start_time, end_time) and
    a chunk policy, then determines how to split the request into multiple
    chunks that respect endpoint limits.
    """

    def __init__(self, policy: ChunkPolicy, hint: ChunkHint | None = None) -> None:
        """Initialize chunk planner.

        Args:
            policy: Chunking policy for the endpoint
            hint: Optional chunk hints for pagination
        """
        self._policy = policy
        self._hint = hint or ChunkHint()

    def plan(
        self,
        *,
        limit: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        timeframe: Timeframe | None = None,
        max_chunks: int | None = None,
    ) -> list[ChunkPlan]:
        """Plan chunks for a request.

        Args:
            limit: Total number of data points requested (None = unlimited)
            start_time: Start time for the request
            end_time: End time for the request
            timeframe: Timeframe for time-based chunking (required if time-based)
            max_chunks: Maximum number of chunks (overrides policy max_chunks)

        Returns:
            List of chunk plans

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        # Validate policy requirements
        if self._policy.requires_start_time and start_time is None:
            raise ValueError(
                "start_time is required for chunking this endpoint but was not provided"
            )

        # Determine effective max chunks
        effective_max_chunks = max_chunks or self._policy.max_chunks

        # Log plan creation (will be updated with actual chunk count)
        endpoint_id = getattr(self, "_endpoint_id", "unknown")

        # Fast path: single request is enough
        if (
            limit is not None
            and limit <= self._policy.max_points
            and effective_max_chunks is not None
            and effective_max_chunks == 1
        ):
            return [
                ChunkPlan(
                    start_time=start_time,
                    end_time=end_time,
                    limit=limit,
                    chunk_index=0,
                )
            ]

        # Determine chunk size
        chunk_limit = self._policy.max_points
        if limit is not None:
            chunk_limit = min(chunk_limit, limit)

        # If no time range and no limit, can't plan
        if start_time is None and end_time is None and limit is None:
            raise ValueError("Cannot plan chunks: need at least limit or time range")

        # Time-based chunking
        if start_time is not None or end_time is not None:
            return self._plan_time_based(
                start_time=start_time,
                end_time=end_time,
                limit=limit,
                timeframe=timeframe,
                chunk_limit=chunk_limit,
                max_chunks=effective_max_chunks,
            )

        # Limit-based chunking (no time range)
        plans = self._plan_limit_based(
            limit=limit,
            chunk_limit=chunk_limit,
            max_chunks=effective_max_chunks,
        )

        # Log plan creation
        log_chunk_plan(
            endpoint_id=endpoint_id,
            total_chunks=len(plans),
            total_limit=limit,
        )

        return plans

    def _plan_time_based(
        self,
        *,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int | None,
        timeframe: Timeframe | None,
        chunk_limit: int,
        max_chunks: int | None,
    ) -> list[ChunkPlan]:
        """Plan chunks for time-based requests.

        Args:
            start_time: Start time
            end_time: End time
            limit: Total limit
            timeframe: Timeframe for aligning windows
            chunk_limit: Limit per chunk
            max_chunks: Maximum chunks

        Returns:
            List of chunk plans
        """
        if timeframe is None:
            raise ValueError("timeframe is required for time-based chunking")

        # Calculate window size based on timeframe and chunk limit
        window_size = calculate_chunk_window_size(timeframe.seconds, chunk_limit)
        if window_size is None:
            # Fallback to limit-based if can't calculate window
            return self._plan_limit_based(
                limit=limit, chunk_limit=chunk_limit, max_chunks=max_chunks
            )

        interval_delta = timedelta(seconds=timeframe.seconds)

        plans: list[ChunkPlan] = []
        current_start = start_time
        chunk_index = 0
        remaining = limit

        while True:
            # Check max chunks
            if max_chunks is not None and chunk_index >= max_chunks:
                break

            # Determine chunk end time
            if current_start is None:
                # No start time, use end_time as boundary
                chunk_end = end_time
            else:
                chunk_end = current_start + window_size
                if end_time is not None and chunk_end > end_time:
                    chunk_end = end_time

            # Determine chunk limit
            chunk_limit_for_plan = chunk_limit
            if remaining is not None:
                if remaining <= 0:
                    break
                chunk_limit_for_plan = min(chunk_limit, remaining)

            plans.append(
                ChunkPlan(
                    start_time=current_start,
                    end_time=chunk_end,
                    limit=chunk_limit_for_plan,
                    chunk_index=chunk_index,
                )
            )

            chunk_index += 1

            # Update for next iteration
            if remaining is not None:
                remaining -= chunk_limit_for_plan
                if remaining <= 0:
                    break

            # Move to next window
            if current_start is None:
                break
            if chunk_end is None:
                break
            current_start = chunk_end + interval_delta

            # Check if we've reached the end time
            if end_time is not None and current_start >= end_time:
                break

        # Log plan creation
        log_chunk_plan(
            endpoint_id=getattr(self, "_endpoint_id", "unknown"),
            total_chunks=len(plans),
            window_size=int(window_size.total_seconds()) if window_size else None,
            total_limit=limit,
            start_time=start_time,
            end_time=end_time,
        )

        return plans

    def _plan_limit_based(
        self,
        *,
        limit: int | None,
        chunk_limit: int,
        max_chunks: int | None,
    ) -> list[ChunkPlan]:
        """Plan chunks for limit-based requests (no time range).

        Args:
            limit: Total limit
            chunk_limit: Limit per chunk
            max_chunks: Maximum chunks

        Returns:
            List of chunk plans
        """
        if limit is None:
            raise ValueError("limit is required for limit-based chunking")

        plans: list[ChunkPlan] = []
        remaining = limit
        chunk_index = 0

        while remaining > 0:
            # Check max chunks
            if max_chunks is not None and chunk_index >= max_chunks:
                break

            chunk_limit_for_plan = min(chunk_limit, remaining)
            plans.append(
                ChunkPlan(
                    limit=chunk_limit_for_plan,
                    chunk_index=chunk_index,
                )
            )

            remaining -= chunk_limit_for_plan
            chunk_index += 1

        return plans
