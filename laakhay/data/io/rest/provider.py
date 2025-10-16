"""Abstract base class for REST (HTTP) data providers.

This module defines the minimal REST surface used across the data layer.
It is intentionally decoupled from any WebSocket/streaming concepts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ...core.enums import Timeframe
from ...models import OHLCV, FundingRate, OpenInterest, OrderBook, Symbol, Trade


class RESTProvider(ABC):
    """Pure REST interface for market data providers."""

    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        interval: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> OHLCV:
        """Fetch OHLCV bars for a symbol and timeframe."""
        raise NotImplementedError

    @abstractmethod
    async def get_symbols(
        self, quote_asset: str | None = None, use_cache: bool = True
    ) -> list[Symbol]:
        """List trading symbols, optionally filtered by quote asset."""
        raise NotImplementedError

    # Optional but commonly supported REST endpoints
    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:  # pragma: no cover
        """Fetch current order book. Optional; implement if provider supports it."""
        raise NotImplementedError

    async def get_recent_trades(
        self, symbol: str, limit: int = 500
    ) -> list[Trade]:  # pragma: no cover
        """Fetch recent trades. Optional; implement if provider supports it."""
        raise NotImplementedError

    async def get_funding_rate(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[FundingRate]:  # pragma: no cover
        """Fetch historical applied funding rates. Futures-only providers typically implement this."""
        raise NotImplementedError

    async def get_open_interest(
        self,
        symbol: str,
        historical: bool = False,
        period: str = "5m",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 30,
    ) -> list[OpenInterest]:  # pragma: no cover
        """Fetch open interest (current or historical). Futures-only providers typically implement this."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Close any underlying HTTP resources/sessions."""
        raise NotImplementedError
