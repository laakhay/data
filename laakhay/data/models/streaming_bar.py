"""Streaming bar that includes symbol context."""

from pydantic import Field

from .bar import Bar


class StreamingBar(Bar):
    """Bar with symbol context for streaming scenarios."""

    symbol: str = Field(..., min_length=1, description="Trading symbol")
