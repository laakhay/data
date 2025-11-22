"""Chunk execution logic for fetching and aggregating chunks.

This module provides the ChunkExecutor class that executes chunk plans,
fetches data, parses responses, and aggregates results with deduplication.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from time import perf_counter
from typing import Any

from .definitions import ChunkHint, ChunkPlan, ChunkPolicy, ChunkResult, WeightPolicy
from .telemetry import log_chunk_completed, log_chunk_error, log_chunk_execution_complete


class ChunkExecutor:
    """Executes chunk plans and aggregates results.

    The executor takes chunk plans and a fetch function, then executes
    each chunk, parses responses, deduplicates data, and aggregates results.
    """

    def __init__(
        self,
        policy: ChunkPolicy,
        hint: ChunkHint | None = None,
        weight_policy: WeightPolicy | None = None,
    ) -> None:
        """Initialize chunk executor.

        Args:
            policy: Chunking policy for the endpoint
            hint: Optional chunk hints for pagination and deduplication
            weight_policy: Optional weight policy for rate limit telemetry
        """
        self._policy = policy
        self._hint = hint or ChunkHint()
        self._weight_policy = weight_policy

    async def execute(
        self,
        *,
        plans: list[ChunkPlan],
        fetch_chunk: Callable[[ChunkPlan], Awaitable[Any]],
        aggregate: Callable[[list[Any]], Any] | None = None,
    ) -> ChunkResult:
        """Execute chunk plans and aggregate results.

        Args:
            plans: List of chunk plans to execute
            fetch_chunk: Async function that takes a ChunkPlan and returns parsed data
            aggregate: Optional function to aggregate chunks (default: list.extend)

        Returns:
            ChunkResult with aggregated data and metadata
        """
        if not plans:
            raise ValueError("Cannot execute: no chunk plans provided")

        aggregated: list[Any] = []
        chunks_used = 0
        weight_consumed = 0
        last_timestamp: datetime | None = None
        start_timestamp: datetime | None = None
        end_timestamp: datetime | None = None

        for plan in plans:
            # Fetch chunk with timing
            chunk_start = perf_counter()
            try:
                chunk_data = await fetch_chunk(plan)
                chunks_used += 1
                # Calculate weight from weight policy if available
                weight = self._weight_policy.calculate(plan.limit) if self._weight_policy else 0
                weight_consumed += weight
                chunk_latency_ms = (perf_counter() - chunk_start) * 1000.0
            except Exception as e:
                log_chunk_error(
                    endpoint_id=getattr(plan, "endpoint_id", "unknown"),
                    chunk_index=plan.chunk_index,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                raise

            # Handle empty chunks
            if chunk_data is None:
                break

            # Extract data points from chunk
            data_points = self._extract_data_points(chunk_data)

            if not data_points:
                # No data in this chunk, stop early
                break

            # Log chunk completion
            log_chunk_completed(
                endpoint_id=getattr(plan, "endpoint_id", "unknown"),
                chunk_index=plan.chunk_index,
                rows_aggregated=len(data_points),
                weight=weight,
                latency_ms=chunk_latency_ms,
            )

            # Deduplicate if we have a previous timestamp
            if last_timestamp is not None:
                data_points = self._deduplicate(data_points, last_timestamp)

            if not data_points:
                # All points were duplicates, stop
                break

            # Aggregate data points
            if aggregate:
                aggregated = aggregate([aggregated, data_points])
            else:
                aggregated.extend(data_points)

            # Update timestamps
            first_point = data_points[0]
            last_point = data_points[-1]
            first_ts = self._extract_timestamp(first_point)
            last_ts = self._extract_timestamp(last_point)

            if start_timestamp is None or (first_ts and first_ts < start_timestamp):
                start_timestamp = first_ts
            if end_timestamp is None or (last_ts and last_ts > end_timestamp):
                end_timestamp = last_ts

            last_timestamp = last_ts

            # Check if we got fewer points than requested (end of data)
            if len(data_points) < plan.limit:
                break

        # If we have a container structure (like OHLCV), preserve it
        if hasattr(chunk_data, "__class__") and not isinstance(aggregated, list):
            # Try to reconstruct the container with aggregated data
            if hasattr(chunk_data, "bars"):
                # OHLCV-like structure
                chunk_data.bars = aggregated
                aggregated = chunk_data
            elif hasattr(chunk_data, "meta"):
                # Preserve metadata
                pass

        result = ChunkResult(
            data=aggregated,
            chunks_used=chunks_used,
            weight_consumed=weight_consumed,
            total_points=len(aggregated)
            if isinstance(aggregated, list)
            else len(getattr(aggregated, "bars", [])),
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
        )

        # Log execution completion
        log_chunk_execution_complete(
            endpoint_id=getattr(plans[0] if plans else None, "endpoint_id", "unknown"),
            result=result,
        )

        return result

    def _extract_data_points(self, chunk_data: Any) -> list[Any]:
        """Extract list of data points from chunk data.

        Args:
            chunk_data: Parsed chunk data (could be list, OHLCV, etc.)

        Returns:
            List of data points
        """
        if isinstance(chunk_data, list):
            return chunk_data

        # Handle OHLCV-like structures
        if hasattr(chunk_data, "bars"):
            return chunk_data.bars

        # Handle single item
        return [chunk_data]

    def _extract_timestamp(self, point: Any) -> datetime | None:
        """Extract timestamp from a data point.

        Args:
            point: Data point (Bar, Trade, etc.)

        Returns:
            Timestamp if found, None otherwise
        """
        if hasattr(point, self._hint.timestamp_key):
            ts = getattr(point, self._hint.timestamp_key)
            if isinstance(ts, datetime):
                return ts
        return None

    def _deduplicate(self, data_points: list[Any], last_timestamp: datetime) -> list[Any]:
        """Remove data points that are older than or equal to last_timestamp.

        Args:
            data_points: List of data points
            last_timestamp: Timestamp to filter against

        Returns:
            Filtered list of data points
        """
        if not data_points:
            return []

        filtered = []
        for point in data_points:
            ts = self._extract_timestamp(point)
            if ts is None:
                # No timestamp, include it
                filtered.append(point)
            elif ts > last_timestamp:
                # Newer than last, include it
                filtered.append(point)
            # Otherwise, skip (duplicate or older)

        return filtered
