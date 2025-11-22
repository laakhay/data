"""Chunking metadata definitions and policy structures.

This module defines the data structures used to describe chunking behavior
for endpoints, including policies, hints, and results.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class WeightTier:
    """Weight tier definition for tiered rate limiting.

    Attributes:
        min_limit: Minimum limit value (inclusive)
        max_limit: Maximum limit value (exclusive, or None for unbounded)
        weight: Weight for this tier
    """

    min_limit: int
    max_limit: int | None  # None means unbounded
    weight: int


@dataclass(frozen=True)
class WeightPolicy:
    """Declarative weight policy for API rate limiting.

    Supports both static weights (same for all limits) and tiered weights
    based on limit values.

    Examples:
        # Static weight (always 2)
        WeightPolicy(static_weight=2)

        # Tiered weights
        WeightPolicy(tiers=[
            WeightTier(1, 100, 1),
            WeightTier(100, 500, 2),
            WeightTier(500, 1000, 5),
            WeightTier(1000, None, 10),  # None = unbounded
        ])
    """

    static_weight: int | None = None
    tiers: list[WeightTier] | None = None

    def __post_init__(self) -> None:
        """Validate weight policy configuration."""
        if self.static_weight is None and self.tiers is None:
            raise ValueError("WeightPolicy must have either static_weight or tiers")
        if self.static_weight is not None and self.tiers is not None:
            raise ValueError("WeightPolicy cannot have both static_weight and tiers")
        if self.tiers and not self.tiers:
            raise ValueError("WeightPolicy tiers cannot be empty")

    def calculate(self, limit: int) -> int:
        """Calculate weight for a given limit.

        Args:
            limit: Request limit value

        Returns:
            Weight for the request
        """
        if self.static_weight is not None:
            return self.static_weight

        if self.tiers:
            for tier in self.tiers:
                if tier.min_limit <= limit and (tier.max_limit is None or limit < tier.max_limit):
                    return tier.weight
            # If no tier matches, use the last tier's weight (fallback)
            return self.tiers[-1].weight

        return 1  # Default fallback


@dataclass(frozen=True)
class ChunkPolicy:
    """Chunking policy for an endpoint.

    This policy describes how an endpoint should be chunked when users
    request more data than the endpoint's per-request limit.

    Attributes:
        max_points: Maximum number of data points per request (e.g., 1000 bars)
        max_chunks: Maximum number of chunks to fetch (None = unlimited)
        requires_start_time: Whether start_time is required for chunking
        supports_auto_chunking: Whether the endpoint supports automatic chunking
    """

    max_points: int
    max_chunks: int | None = None
    requires_start_time: bool = False
    supports_auto_chunking: bool = True


@dataclass(frozen=True)
class ChunkHint:
    """Hints for how to extract pagination information from responses.

    These hints help the chunk executor understand how to paginate through
    results and deduplicate data.

    Attributes:
        cursor_field: Field name in response that contains next page cursor (None if time-based)
        timestamp_key: Field name in data points that contains timestamp (for deduplication)
        limit_field: Query parameter name for limit (default: "limit")
        start_time_field: Query parameter name for start time (default: "start_time")
        end_time_field: Query parameter name for end time (default: "end_time")
        timeframe_field: Query parameter name for timeframe (for time-based chunking)
    """

    cursor_field: str | None = None
    timestamp_key: str = "timestamp"
    limit_field: str = "limit"
    start_time_field: str = "start_time"
    end_time_field: str = "end_time"
    timeframe_field: str | None = None


@dataclass
class ChunkResult:
    """Result of chunked execution.

    Attributes:
        data: Aggregated data from all chunks
        chunks_used: Number of chunks that were fetched
        weight_consumed: Total request weight consumed
        throttle_applied: Whether throttling was applied
        total_points: Total number of data points aggregated
        start_timestamp: Timestamp of first data point
        end_timestamp: Timestamp of last data point
    """

    data: Any
    chunks_used: int
    weight_consumed: int = 0
    throttle_applied: bool = False
    total_points: int = 0
    start_timestamp: datetime | None = None
    end_timestamp: datetime | None = None


@dataclass(frozen=True)
class ChunkPlan:
    """Plan for a single chunk.

    Attributes:
        limit: Limit for this chunk
        start_time: Start time for this chunk (None if cursor-based)
        end_time: End time for this chunk (None if cursor-based)
        cursor: Cursor for this chunk (None if time-based)
        chunk_index: Zero-based index of this chunk in the overall plan
    """

    limit: int
    start_time: datetime | None = None
    end_time: datetime | None = None
    cursor: dict[str, Any] | None = None
    chunk_index: int = 0


def extract_chunk_policy(spec: Any, params: dict[str, Any] | None = None) -> ChunkPolicy | None:
    """Extract chunk policy from endpoint specification.

    This function looks for chunk metadata in the endpoint spec. If the spec
    has a `chunk_policy` attribute, it returns it (or calls it as a factory if it's callable).
    Otherwise, it returns None indicating the endpoint doesn't support chunking.

    Args:
        spec: REST endpoint specification
        params: Optional request params for dynamic policy creation

    Returns:
        ChunkPolicy if endpoint supports chunking, None otherwise
    """
    if hasattr(spec, "chunk_policy") and spec.chunk_policy is not None:
        policy = spec.chunk_policy
        # If policy is a callable factory, call it with params to create dynamic policy
        if callable(policy) and not isinstance(policy, ChunkPolicy):
            if params is None:
                params = {}
            return policy(params)
        return policy
    return None


def extract_weight_policy(spec: Any, params: dict[str, Any] | None = None) -> WeightPolicy | None:
    """Extract weight policy from endpoint specification.

    This function looks for weight policy in the endpoint spec. If the spec
    has a `weight_policy` attribute, it returns it (or calls it as a factory if it's callable).
    Otherwise, it returns None indicating no weight tracking.

    Args:
        spec: REST endpoint specification
        params: Optional request params for dynamic policy creation

    Returns:
        WeightPolicy if available, None otherwise
    """
    if hasattr(spec, "weight_policy") and spec.weight_policy is not None:
        policy = spec.weight_policy
        # If policy is a callable factory, call it with params to create dynamic policy
        if callable(policy) and not isinstance(policy, WeightPolicy):
            if params is None:
                params = {}
            return policy(params)
        # If it's already a WeightPolicy instance, return it directly
        if isinstance(policy, WeightPolicy):
            return policy
        # Otherwise return as-is (should be WeightPolicy or None)
        return policy
    return None


def extract_chunk_hint(spec: Any) -> ChunkHint | None:
    """Extract chunk hints from endpoint specification.

    This function looks for chunk hints in the endpoint spec. If the spec
    has a `chunk_hint` attribute, it returns it. Otherwise, it returns a
    default hint for time-based chunking.

    Args:
        spec: REST endpoint specification

    Returns:
        ChunkHint if available, None otherwise
    """
    if hasattr(spec, "chunk_hint") and spec.chunk_hint is not None:
        return spec.chunk_hint
    # Default to time-based chunking if no hint provided
    return ChunkHint()


def calculate_chunk_window_size(timeframe_seconds: int | None, max_points: int) -> timedelta | None:
    """Calculate chunk window size based on timeframe and max points.

    Args:
        timeframe_seconds: Timeframe in seconds (None if not applicable)
        max_points: Maximum points per chunk

    Returns:
        Timedelta representing chunk window size, or None if not time-based
    """
    if timeframe_seconds is None:
        return None
    return timedelta(seconds=timeframe_seconds * max_points)
