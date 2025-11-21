"""Chunking metadata definitions and policy structures.

This module defines the data structures used to describe chunking behavior
for endpoints, including policies, hints, and results.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from ..rest.runner import RestEndpointSpec


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
        weight_per_request: Request weight/rate limit cost per chunk (for telemetry)
    """

    max_points: int
    max_chunks: int | None = None
    requires_start_time: bool = False
    supports_auto_chunking: bool = True
    weight_per_request: int = 1


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
        start_time: Start time for this chunk (None if cursor-based)
        end_time: End time for this chunk (None if cursor-based)
        limit: Limit for this chunk
        cursor: Cursor for this chunk (None if time-based)
        chunk_index: Zero-based index of this chunk in the overall plan
    """

    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int
    cursor: dict[str, Any] | None = None
    chunk_index: int = 0


def extract_chunk_policy(spec: RestEndpointSpec) -> ChunkPolicy | None:
    """Extract chunk policy from endpoint specification.

    This function looks for chunk metadata in the endpoint spec. If the spec
    has a `chunk_policy` attribute, it returns it. Otherwise, it returns None
    indicating the endpoint doesn't support chunking.

    Args:
        spec: REST endpoint specification

    Returns:
        ChunkPolicy if endpoint supports chunking, None otherwise
    """
    if hasattr(spec, "chunk_policy") and spec.chunk_policy is not None:
        return spec.chunk_policy
    return None


def extract_chunk_hint(spec: RestEndpointSpec) -> ChunkHint | None:
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
