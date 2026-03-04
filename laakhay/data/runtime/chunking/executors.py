"""Chunk execution logic for fetching and aggregating chunks.

This module provides the ChunkExecutor class that executes chunk plans,
fetches data, parses responses, and aggregates results with deduplication.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime
from time import perf_counter
from typing import Any

from .definitions import ChunkHint, ChunkPlan, ChunkPolicy, ChunkResult, WeightPolicy
from .telemetry import log_chunk_completed, log_chunk_error, log_chunk_execution_complete

logger = logging.getLogger(__name__)


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
        max_concurrency: int = 1,
        max_weight_per_minute: int | None = None,
        assumed_request_latency_seconds: float = 1.0,
    ) -> None:
        """Initialize chunk executor.

        Args:
            policy: Chunking policy for the endpoint
            hint: Optional chunk hints for pagination and deduplication
            weight_policy: Optional weight policy for rate limit telemetry
            max_concurrency: Maximum number of in-flight fetches
            max_weight_per_minute: Optional exchange/API weight budget per minute
            assumed_request_latency_seconds: Assumed average request latency for
                converting weight-per-minute to safe concurrency
        """
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        if max_weight_per_minute is not None and max_weight_per_minute < 1:
            raise ValueError("max_weight_per_minute must be >= 1")
        if assumed_request_latency_seconds <= 0:
            raise ValueError("assumed_request_latency_seconds must be > 0")

        self._policy = policy
        self._hint = hint or ChunkHint()
        self._weight_policy = weight_policy
        self._max_concurrency = max_concurrency
        self._max_weight_per_minute = max_weight_per_minute
        self._assumed_request_latency_seconds = assumed_request_latency_seconds

    async def execute(
        self,
        *,
        plans: list[ChunkPlan],
        fetch_chunk: Callable[[ChunkPlan], Awaitable[Any]],
        aggregate: Callable[[list[Any]], Any] | None = None,
        max_concurrency: int | None = None,
        yield_points: int | None = None,
    ) -> ChunkResult:
        """Execute chunk plans and aggregate results in memory.

        Note: Use iterate() for memory-safe processing of large datasets.
        """
        if not plans:
            raise ValueError("Cannot execute: no chunk plans provided")

        aggregated: list[Any] = []
        chunks_used = 0
        weight_consumed = 0
        start_timestamp: datetime | None = None
        end_timestamp: datetime | None = None

        async for chunk_result in self.iterate(
            plans=plans,
            fetch_chunk=fetch_chunk,
            max_concurrency=max_concurrency,
            yield_points=yield_points,
        ):
            chunks_used += chunk_result.chunks_used
            weight_consumed += chunk_result.weight_consumed

            data_points = chunk_result.data
            # Re-extract if it was wrapped in a container in iterate()
            if hasattr(data_points, "bars"):
                data_points = data_points.bars

            if aggregate:
                aggregated = aggregate([aggregated, data_points])
            else:
                aggregated.extend(data_points)

            if start_timestamp is None or (
                chunk_result.start_timestamp and chunk_result.start_timestamp < start_timestamp
            ):
                start_timestamp = chunk_result.start_timestamp
            if end_timestamp is None or (
                chunk_result.end_timestamp and chunk_result.end_timestamp > end_timestamp
            ):
                end_timestamp = chunk_result.end_timestamp

        # Reconstruction logic (simplified for aggregate results)
        result = ChunkResult(
            data=aggregated,
            chunks_used=chunks_used,
            weight_consumed=weight_consumed,
            total_points=len(aggregated),
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
        )

        log_chunk_execution_complete(
            endpoint_id=getattr(plans[0] if plans else None, "endpoint_id", "unknown"),
            result=result,
        )

        return result

    async def iterate(
        self,
        *,
        plans: list[ChunkPlan],
        fetch_chunk: Callable[[ChunkPlan], Awaitable[Any]],
        max_concurrency: int | None = None,
        yield_points: int | None = None,
    ) -> AsyncIterator[ChunkResult]:
        """Execute chunk plans and yield results one-by-one for memory efficiency.

        Args:
            plans: List of chunk plans to execute
            fetch_chunk: Async function that takes a ChunkPlan and returns parsed data
            max_concurrency: Optional override for max parallel fetches
            yield_points: Optional target size for yielded batches. If set,
                fetched chunks are coalesced until this many points are buffered.

        Yields:
            ChunkResult for each individual chunk
        """
        if not plans:
            return

        if yield_points is not None and yield_points < 1:
            raise ValueError("yield_points must be >= 1 when provided")

        effective_concurrency = self._resolve_fetch_concurrency(
            plans=plans,
            requested=max_concurrency,
            yield_points=yield_points,
        )
        last_timestamp: datetime | None = None
        buffered_points: list[Any] = []
        buffered_chunks = 0
        buffered_weight = 0
        buffered_start_ts: datetime | None = None
        buffered_end_ts: datetime | None = None

        def flush_buffer(*, include_empty: bool = False) -> ChunkResult | None:
            nonlocal buffered_points, buffered_chunks, buffered_weight
            nonlocal buffered_start_ts, buffered_end_ts
            if not buffered_points and not (include_empty and buffered_chunks > 0):
                return None
            result = ChunkResult(
                data=buffered_points,
                chunks_used=buffered_chunks,
                weight_consumed=buffered_weight,
                total_points=len(buffered_points),
                start_timestamp=buffered_start_ts,
                end_timestamp=buffered_end_ts,
            )
            buffered_points = []
            buffered_chunks = 0
            buffered_weight = 0
            buffered_start_ts = None
            buffered_end_ts = None
            return result

        logger.info(
            "ChunkExecutor: Starting iteration for %s plans with concurrency=%s.",
            len(plans),
            effective_concurrency,
        )
        async for plan, chunk_data, weight, chunk_latency_ms in self._iter_fetched_chunks(
            plans=plans,
            fetch_chunk=fetch_chunk,
            max_concurrency=effective_concurrency,
        ):
            is_time_based = plan.start_time is not None or plan.end_time is not None

            if chunk_data is None:
                logger.info(
                    "ChunkExecutor: Chunk %s returned None (cursor end). Breaking.",
                    plan.chunk_index,
                )
                break

            raw_data_points = self._extract_data_points(chunk_data)
            buffered_chunks += 1
            buffered_weight += weight

            if not raw_data_points:
                log_chunk_completed(
                    endpoint_id=getattr(plan, "endpoint_id", "unknown"),
                    chunk_index=plan.chunk_index,
                    rows_aggregated=0,
                    weight=weight,
                    latency_ms=chunk_latency_ms,
                )
                if is_time_based:
                    # Keep scanning for time-based windows; gaps are valid.
                    logger.debug(
                        "ChunkExecutor: Chunk %s (%s - %s) yielded no points. Skipping.",
                        plan.chunk_index,
                        plan.start_time,
                        plan.end_time,
                    )
                    continue
                logger.info(
                    "ChunkExecutor: Chunk %s yielded no points for limit-based fetch. Stopping.",
                    plan.chunk_index,
                )
                break

            log_chunk_completed(
                endpoint_id=getattr(plan, "endpoint_id", "unknown"),
                chunk_index=plan.chunk_index,
                rows_aggregated=len(raw_data_points),
                weight=weight,
                latency_ms=chunk_latency_ms,
            )

            data_points = raw_data_points
            if last_timestamp is not None:
                data_points = self._deduplicate(data_points, last_timestamp)

            if not data_points:
                # Architecture: Skip chunks that only contain duplicate data.
                continue

            # Update timestamps for this chunk
            first_ts = self._extract_timestamp(data_points[0])
            last_ts = self._extract_timestamp(data_points[-1])
            last_timestamp = last_ts

            buffered_points.extend(data_points)
            if buffered_start_ts is None:
                buffered_start_ts = first_ts
            buffered_end_ts = last_ts

            should_flush = False
            if yield_points is None:
                should_flush = bool(buffered_points)
            else:
                should_flush = len(buffered_points) >= yield_points
            if should_flush:
                flushed = flush_buffer()
                if flushed is not None:
                    yield flushed

            # For cursor/limit style pagination, a short page means we reached the end.
            if not is_time_based and len(raw_data_points) < plan.limit:
                break

        flushed = flush_buffer(include_empty=True)
        if flushed is not None:
            yield flushed

    async def _iter_fetched_chunks(
        self,
        *,
        plans: list[ChunkPlan],
        fetch_chunk: Callable[[ChunkPlan], Awaitable[Any]],
        max_concurrency: int,
    ) -> AsyncIterator[tuple[ChunkPlan, Any, int, float]]:
        """Yield fetched chunks in plan order, with bounded parallelism."""
        if max_concurrency <= 1:
            for plan in plans:
                yield await self._fetch_single_chunk(plan=plan, fetch_chunk=fetch_chunk)
            return

        for idx in range(0, len(plans), max_concurrency):
            batch = plans[idx : idx + max_concurrency]
            batch_results = await asyncio.gather(
                *[self._fetch_single_chunk(plan=plan, fetch_chunk=fetch_chunk) for plan in batch]
            )
            for result in batch_results:
                yield result

    async def _fetch_single_chunk(
        self,
        *,
        plan: ChunkPlan,
        fetch_chunk: Callable[[ChunkPlan], Awaitable[Any]],
    ) -> tuple[ChunkPlan, Any, int, float]:
        """Fetch one chunk with telemetry/error logging."""
        chunk_start = perf_counter()
        try:
            chunk_data = await fetch_chunk(plan)
        except Exception as e:
            log_chunk_error(
                endpoint_id=getattr(plan, "endpoint_id", "unknown"),
                chunk_index=plan.chunk_index,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise

        weight = self._weight_policy.calculate(plan.limit) if self._weight_policy else 0
        chunk_latency_ms = (perf_counter() - chunk_start) * 1000.0
        return plan, chunk_data, weight, chunk_latency_ms

    def _resolve_fetch_concurrency(
        self,
        *,
        plans: list[ChunkPlan],
        requested: int | None,
        yield_points: int | None,
    ) -> int:
        """Resolve concurrency, optionally capping it using weight policy."""
        concurrency = self._max_concurrency if requested is None else requested
        if concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        concurrency = min(concurrency, len(plans))
        concurrency = self._cap_concurrency_for_yield_target(
            plans=plans,
            concurrency=concurrency,
            yield_points=yield_points,
        )

        if self._weight_policy is None or self._max_weight_per_minute is None:
            return concurrency

        max_weight_per_request = max(self._weight_policy.calculate(plan.limit) for plan in plans)
        if max_weight_per_request < 1:
            return concurrency

        budget_per_second = self._max_weight_per_minute / 60.0
        # Approximate safe inflight requests = requests/sec * avg request duration.
        safe_by_weight = int(
            (budget_per_second * self._assumed_request_latency_seconds) / max_weight_per_request
        )
        safe_by_weight = max(1, safe_by_weight)
        return min(concurrency, safe_by_weight)

    def _cap_concurrency_for_yield_target(
        self,
        *,
        plans: list[ChunkPlan],
        concurrency: int,
        yield_points: int | None,
    ) -> int:
        """Avoid overfetching by limiting inflight requests to yield demand."""
        if yield_points is None:
            return concurrency

        max_points_per_request = max((plan.limit for plan in plans), default=1)
        if max_points_per_request < 1:
            return concurrency

        chunks_per_yield = max(
            1, (yield_points + max_points_per_request - 1) // max_points_per_request
        )
        return min(concurrency, chunks_per_yield)

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
