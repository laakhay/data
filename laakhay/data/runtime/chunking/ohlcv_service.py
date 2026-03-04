"""Reusable OHLCV chunk orchestration service.

This service centralizes chunk planning/execution for OHLCV so connectors only
need to provide endpoint specs and a single-request fetch callback.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any

from ...core.enums import MarketType, Timeframe
from ...models import OHLCV, SeriesMeta
from .definitions import (
    ChunkHint,
    ChunkPolicy,
    WeightPolicy,
    extract_chunk_hint,
    extract_chunk_policy,
    extract_weight_policy,
)
from .executors import ChunkExecutor
from .planners import ChunkPlanner

FetchOHLCVChunk = Callable[[datetime | None, datetime | None, int | None], Awaitable[OHLCV]]


class OHLCVChunkService:
    """Core chunk service used by both fetch_ohlcv and iterate_ohlcv APIs."""

    _DEFAULT_WEIGHT_BUDGETS_PER_MINUTE: dict[str, dict[MarketType, int]] = {
        "binance": {
            MarketType.SPOT: 1200,
            MarketType.FUTURES: 1200,
        },
        # Conservative defaults for other exchanges; can be tightened per endpoint.
        "bybit": {
            MarketType.SPOT: 600,
            MarketType.FUTURES: 600,
        },
        "coinbase": {
            MarketType.SPOT: 600,
        },
        "kraken": {
            MarketType.SPOT: 600,
            MarketType.FUTURES: 600,
        },
        "mexc": {
            MarketType.SPOT: 600,
            MarketType.FUTURES: 600,
        },
        "okx": {
            MarketType.SPOT: 600,
            MarketType.FUTURES: 600,
        },
        "hyperliquid": {
            MarketType.SPOT: 1200,
            MarketType.FUTURES: 1200,
        },
    }
    _LIMIT_ONLY_BACKFILL_EXCHANGES: set[str] = {"binance"}

    def __init__(
        self,
        *,
        exchange: str,
        market_type: MarketType,
        fetch_chunk: FetchOHLCVChunk,
        chunk_policy: ChunkPolicy | None,
        chunk_hint: ChunkHint | None,
        weight_policy: WeightPolicy | None,
        max_weight_per_minute: int | None = None,
        assumed_request_latency_seconds: float = 1.0,
    ) -> None:
        self._exchange = exchange
        self._market_type = market_type
        self._fetch_chunk = fetch_chunk
        self._chunk_policy = chunk_policy
        self._chunk_hint = chunk_hint
        self._weight_policy = weight_policy
        self._max_weight_per_minute = (
            max_weight_per_minute
            if max_weight_per_minute is not None
            else self._resolve_weight_budget_per_minute(exchange=exchange, market_type=market_type)
        )
        self._assumed_request_latency_seconds = assumed_request_latency_seconds

    @classmethod
    def from_endpoint_spec(
        cls,
        *,
        exchange: str,
        market_type: MarketType,
        spec: Any,
        params: dict[str, Any],
        fetch_chunk: FetchOHLCVChunk,
        max_weight_per_minute: int | None = None,
        assumed_request_latency_seconds: float = 1.0,
    ) -> OHLCVChunkService:
        """Build a service from endpoint metadata and a chunk fetch callback."""
        return cls(
            exchange=exchange,
            market_type=market_type,
            fetch_chunk=fetch_chunk,
            chunk_policy=extract_chunk_policy(spec, params),
            chunk_hint=extract_chunk_hint(spec),
            weight_policy=extract_weight_policy(spec, params),
            max_weight_per_minute=max_weight_per_minute,
            assumed_request_latency_seconds=assumed_request_latency_seconds,
        )

    async def iterate(
        self,
        *,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
        max_chunks: int | None = None,
        fetch_concurrency: int = 1,
        yield_chunk_size: int | None = None,
    ) -> AsyncIterator[OHLCV]:
        """Iterate OHLCV chunks with optional parallel fetch and coalesced yields."""
        if fetch_concurrency < 1:
            raise ValueError("fetch_concurrency must be >= 1")

        effective_limit = self._infer_effective_limit(
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            max_chunks=max_chunks,
        )

        if self._should_use_limit_only_backfill(
            start_time=start_time,
            end_time=end_time,
            limit=effective_limit,
        ):
            backfilled = await self._fetch_limit_only_backfill(
                symbol=symbol,
                timeframe=timeframe,
                limit=effective_limit,
                max_chunks=max_chunks,
            )
            for chunk in self._split_single_result(backfilled, yield_chunk_size):
                yield chunk
            return

        if not self._should_use_chunking(
            start_time=start_time,
            end_time=end_time,
            limit=effective_limit,
            max_chunks=max_chunks,
        ):
            single = await self._fetch_chunk(start_time, end_time, effective_limit)
            for chunk in self._split_single_result(single, yield_chunk_size):
                yield chunk
            return

        if self._chunk_policy is None:
            single = await self._fetch_chunk(start_time, end_time, effective_limit)
            for chunk in self._split_single_result(single, yield_chunk_size):
                yield chunk
            return

        planner = ChunkPlanner(policy=self._chunk_policy, hint=self._chunk_hint)
        plans = planner.plan(
            limit=effective_limit,
            start_time=start_time,
            end_time=end_time,
            timeframe=timeframe,
            max_chunks=max_chunks,
        )

        executor = ChunkExecutor(
            policy=self._chunk_policy,
            hint=self._chunk_hint,
            weight_policy=self._weight_policy,
            max_concurrency=fetch_concurrency,
            max_weight_per_minute=self._max_weight_per_minute,
            assumed_request_latency_seconds=self._assumed_request_latency_seconds,
        )

        async def fetch_plan(plan: Any) -> OHLCV:
            return await self._fetch_chunk(plan.start_time, plan.end_time, plan.limit)

        meta = SeriesMeta(symbol=symbol, timeframe=timeframe.value)
        async for chunk_result in executor.iterate(
            plans=plans,
            fetch_chunk=fetch_plan,
            yield_points=yield_chunk_size,
        ):
            bars = chunk_result.data
            if isinstance(bars, OHLCV):
                yield bars
                continue
            if not isinstance(bars, list):
                continue
            if not bars:
                continue
            yield OHLCV(meta=meta, bars=bars)

    async def fetch(
        self,
        *,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
        max_chunks: int | None = None,
        fetch_concurrency: int | None = None,
    ) -> OHLCV:
        """Fetch OHLCV by aggregating the chunk iterator path."""
        # Fetch path uses a larger default concurrency than iterate() since it
        # aggregates in memory and benefits from maximizing throughput.
        effective_concurrency = fetch_concurrency
        if effective_concurrency is None:
            effective_concurrency = self._default_fetch_concurrency(limit)

        aggregated_bars = []
        meta: SeriesMeta | None = None

        async for chunk in self.iterate(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            max_chunks=max_chunks,
            fetch_concurrency=effective_concurrency,
            yield_chunk_size=None,
        ):
            if meta is None:
                meta = chunk.meta
            aggregated_bars.extend(chunk.bars)

        if meta is None:
            fallback = await self._fetch_chunk(start_time, end_time, limit)
            return fallback

        if limit is not None and len(aggregated_bars) > limit:
            aggregated_bars = aggregated_bars[:limit]

        return OHLCV(meta=meta, bars=aggregated_bars)

    def _split_single_result(self, result: OHLCV, chunk_size: int | None) -> list[OHLCV]:
        """Split a single OHLCV response into yield-sized chunks when requested."""
        if chunk_size is None or chunk_size < 1 or len(result.bars) <= chunk_size:
            return [result]

        return [
            OHLCV(meta=result.meta, bars=result.bars[i : i + chunk_size])
            for i in range(0, len(result.bars), chunk_size)
        ]

    def _should_use_chunking(
        self,
        *,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int | None,
        max_chunks: int | None,
    ) -> bool:
        """Determine if planner/executor chunking should be used."""
        if self._chunk_policy is None or not self._chunk_policy.supports_auto_chunking:
            return False

        if max_chunks == 1:
            return False

        # A start-only request with no limit has an unbounded upper range,
        # so use a single fetch instead of attempting to auto-plan windows.
        if start_time is not None and end_time is None and limit is None:
            return False

        # If caller is asking above max_points, we should chunk.
        if limit is not None and limit > self._chunk_policy.max_points:
            return not (start_time is None and end_time is None)

        # Explicit bounded time windows can be chunked for throughput.
        return start_time is not None and end_time is not None

    def _infer_effective_limit(
        self,
        *,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int | None,
        max_chunks: int | None,
    ) -> int | None:
        """Infer a bounded limit for limit-only backfill flows when none is provided."""
        if limit is not None:
            return limit
        if self._chunk_policy is None:
            return None
        if start_time is not None or end_time is not None:
            return None
        if max_chunks is None or max_chunks < 1:
            return None
        if self._exchange.lower() not in self._LIMIT_ONLY_BACKFILL_EXCHANGES:
            return None
        return self._chunk_policy.max_points * max_chunks

    def _default_fetch_concurrency(self, limit: int | None) -> int:
        """Choose a reasonable default fetch concurrency for aggregate fetch calls."""
        if limit is None or self._chunk_policy is None:
            return 1
        if limit <= self._chunk_policy.max_points:
            return 1

        chunks_needed = (limit + self._chunk_policy.max_points - 1) // self._chunk_policy.max_points
        return max(1, min(16, chunks_needed))

    def _should_use_limit_only_backfill(
        self,
        *,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int | None,
    ) -> bool:
        """Return True if this request should use backward limit-only pagination."""
        if self._chunk_policy is None:
            return False
        if self._exchange.lower() not in self._LIMIT_ONLY_BACKFILL_EXCHANGES:
            return False
        if start_time is not None or end_time is not None:
            return False
        if limit is None:
            return False
        return limit > self._chunk_policy.max_points

    async def _fetch_limit_only_backfill(
        self,
        *,
        symbol: str,
        timeframe: Timeframe,
        limit: int | None,
        max_chunks: int | None,
    ) -> OHLCV:
        """Backfill latest bars by paging backwards via end_time cursor."""
        if self._chunk_policy is None:
            return await self._fetch_chunk(None, None, limit)
        if limit is None:
            return await self._fetch_chunk(None, None, limit)

        remaining = limit
        current_end_time: datetime | None = None
        chunks_used = 0
        aggregated_bars: list[Any] = []
        meta: SeriesMeta | None = None

        while remaining > 0:
            if max_chunks is not None and chunks_used >= max_chunks:
                break

            chunk_limit = min(self._chunk_policy.max_points, remaining)
            chunk = await self._fetch_chunk(None, current_end_time, chunk_limit)
            if meta is None:
                meta = chunk.meta
            if not chunk.bars:
                break

            bars = chunk.bars
            if aggregated_bars:
                oldest_ts = aggregated_bars[0].timestamp
                bars = [bar for bar in bars if bar.timestamp < oldest_ts]
                if not bars:
                    break

            aggregated_bars = bars + aggregated_bars
            remaining -= len(bars)
            chunks_used += 1

            oldest_chunk_ts = bars[0].timestamp
            current_end_time = oldest_chunk_ts - timedelta(milliseconds=1)

            if len(chunk.bars) < chunk_limit:
                break

        if meta is None:
            fallback = await self._fetch_chunk(
                None, None, min(limit, self._chunk_policy.max_points)
            )
            return fallback

        if len(aggregated_bars) > limit:
            aggregated_bars = aggregated_bars[-limit:]
        return OHLCV(meta=meta, bars=aggregated_bars)

    @classmethod
    def _resolve_weight_budget_per_minute(
        cls,
        *,
        exchange: str,
        market_type: MarketType,
    ) -> int | None:
        exchange_budget = cls._DEFAULT_WEIGHT_BUDGETS_PER_MINUTE.get(exchange.lower())
        if exchange_budget is None:
            return None
        return exchange_budget.get(market_type)
