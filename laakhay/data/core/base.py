"""Base provider abstract class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ..models import OHLCV
from .enums import Timeframe


class BaseProvider(ABC):
    """Abstract base class for all data providers."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._session: object | None = None

    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        interval: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> OHLCV:
        """Fetch OHLCV bars for a symbol."""
        pass

    @abstractmethod
    async def get_symbols(self) -> list[dict]:
        """Fetch all available trading symbols."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close provider connections and cleanup resources."""
        pass

    def validate_interval(self, interval: Timeframe) -> None:
        """Validate if interval is supported by provider. Override if needed."""
        pass

    def validate_symbol(self, symbol: str) -> None:
        """Validate symbol format. Override if needed."""
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")

    async def __aenter__(self) -> BaseProvider:
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()
