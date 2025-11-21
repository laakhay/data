"""Generic chunking layer for pagination and limit extension.

This module provides reusable chunking logic that can handle pagination,
limit extension, and deduplication for any endpoint based on metadata.

Architecture:
    The chunking layer consists of:
    - definitions.py: Chunk metadata structures (ChunkPolicy, ChunkHint, ChunkResult)
    - planners.py: Chunk planning logic (determines chunk windows)
    - executors.py: Chunk execution logic (fetches and aggregates chunks)
    - telemetry.py: Structured logging and metrics

Usage:
    The chunking layer reads endpoint metadata to automatically determine
    chunking strategy. Endpoints can opt into chunking by providing chunk
    metadata in their endpoint specifications.
"""

from __future__ import annotations

from .definitions import (
    ChunkHint,
    ChunkPlan,
    ChunkPolicy,
    ChunkResult,
    extract_chunk_hint,
    extract_chunk_policy,
)
from .executors import ChunkExecutor
from .planners import ChunkPlanner

__all__ = [
    "ChunkPolicy",
    "ChunkHint",
    "ChunkResult",
    "ChunkPlan",
    "ChunkPlanner",
    "ChunkExecutor",
    "extract_chunk_policy",
    "extract_chunk_hint",
]
