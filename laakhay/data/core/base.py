"""Base provider abstract class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

from ..models import OHLCV
from .enums import Timeframe

if TYPE_CHECKING:
    from .capabilities import CapabilityStatus
    from .enums import DataFeature, InstrumentType, MarketType, TransportKind


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

    async def describe_capabilities(
        self,
        feature: DataFeature,
        transport: TransportKind,
        *,
        market_type: MarketType,
        instrument_type: InstrumentType,
    ) -> CapabilityStatus:
        """Describe capabilities for a specific feature/transport combination.

        Providers should override this method to return runtime-discovered capabilities.
        The default implementation returns a status indicating static metadata should be used.

        Args:
            feature: The data feature to check
            transport: The transport mechanism
            market_type: Market type (spot/futures)
            instrument_type: Instrument type (spot/perpetual/future/etc.)

        Returns:
            CapabilityStatus indicating support status and metadata
        """
        # Default implementation: return None/unknown status
        # Subclasses should override to provide runtime discovery
        from .capabilities import CapabilityStatus

        return CapabilityStatus(
            supported=False,
            reason="Runtime capability discovery not implemented for this provider",
            source="static",
        )

    async def __aenter__(self) -> BaseProvider:
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()
