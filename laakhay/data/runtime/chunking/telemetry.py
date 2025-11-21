"""Structured logging and metrics for chunking operations.

This module provides telemetry hooks for chunking operations, emitting
structured logs and metrics for observability.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any

from .definitions import ChunkPlan, ChunkResult

logger = logging.getLogger(__name__)


def log_chunk_plan(
    *,
    endpoint_id: str,
    total_chunks: int,
    window_size: int | None = None,
    total_limit: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> None:
    """Log chunk plan creation.

    Args:
        endpoint_id: Endpoint identifier
        total_chunks: Total number of chunks planned
        window_size: Size of each chunk window (if time-based)
        total_limit: Total limit requested
        start_time: Start time for time-based chunking
        end_time: End time for time-based chunking
    """
    logger.info(
        "chunk_plan_created",
        extra={
            "endpoint_id": endpoint_id,
            "total_chunks": total_chunks,
            "window_size": window_size,
            "total_limit": total_limit,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
        },
    )


def log_chunk_completed(
    *,
    endpoint_id: str,
    chunk_index: int,
    rows_aggregated: int,
    weight: int,
    latency_ms: float | None = None,
) -> None:
    """Log completion of a single chunk.

    Args:
        endpoint_id: Endpoint identifier
        chunk_index: Zero-based index of the chunk
        rows_aggregated: Number of data points aggregated from this chunk
        weight: Request weight consumed
        latency_ms: Latency in milliseconds (optional)
    """
    logger.info(
        "chunk_completed",
        extra={
            "endpoint_id": endpoint_id,
            "chunk_index": chunk_index,
            "rows_aggregated": rows_aggregated,
            "weight": weight,
            "latency_ms": latency_ms,
        },
    )


def log_chunk_execution_complete(
    *,
    endpoint_id: str,
    result: ChunkResult,
    total_latency_ms: float | None = None,
) -> None:
    """Log completion of chunk execution.

    Args:
        endpoint_id: Endpoint identifier
        result: ChunkResult from execution
        total_latency_ms: Total latency in milliseconds (optional)
    """
    logger.info(
        "chunk_execution_complete",
        extra={
            "endpoint_id": endpoint_id,
            "chunks_used": result.chunks_used,
            "total_points": result.total_points,
            "weight_consumed": result.weight_consumed,
            "throttle_applied": result.throttle_applied,
            "start_timestamp": result.start_timestamp.isoformat()
            if result.start_timestamp
            else None,
            "end_timestamp": result.end_timestamp.isoformat() if result.end_timestamp else None,
            "total_latency_ms": total_latency_ms,
        },
    )


def log_chunk_error(
    *,
    endpoint_id: str,
    chunk_index: int,
    error_type: str,
    error_message: str,
) -> None:
    """Log chunk execution error.

    Args:
        endpoint_id: Endpoint identifier
        chunk_index: Zero-based index of the chunk that failed
        error_type: Type of error (e.g., "NetworkError", "ParseError")
        error_message: Error message
    """
    logger.error(
        "chunk_error",
        extra={
            "endpoint_id": endpoint_id,
            "chunk_index": chunk_index,
            "error_type": error_type,
            "error_message": error_message,
        },
    )
