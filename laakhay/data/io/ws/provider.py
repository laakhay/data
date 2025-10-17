"""Abstract base class for WebSocket/streaming data providers.

Defines the minimal streaming surface used by higher-level data feed
components. This interface is transport-agnostic and does not prescribe
implementation details.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from ...core.enums import Timeframe
from ...models.streaming_bar import StreamingBar


class WSProvider(ABC):
    """Pure streaming interface for market data providers."""

    # Optional hint: maximum number of per-connection streams supported by the provider.
    # OHLCVFeed may read this to decide chunking when multiplexing streams.
    max_streams_per_connection: int | None = None

    @abstractmethod
    async def stream_ohlcv(
        self,
        symbol: str,
        interval: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        """Yield streaming OHLCV (bar) updates for a single symbol."""
        raise NotImplementedError

    @abstractmethod
    async def stream_ohlcv_multi(
        self,
        symbols: list[str],
        interval: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        """Yield streaming OHLCV (bar) updates for multiple symbols (fan-in)."""
        raise NotImplementedError

    # Providers may implement close() if they maintain background tasks/sockets
    async def close(self) -> None:  # pragma: no cover
        """Close any underlying streaming resources."""
        return None
