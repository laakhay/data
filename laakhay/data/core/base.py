"""Base provider abstract class.

Architecture:
    This module defines the BaseProvider abstract base class that all data
    providers must implement. It provides:
    - Abstract methods for core operations (fetch_ohlcv, get_symbols, close)
    - Validation hooks (validate_interval, validate_symbol)
    - Capability discovery interface (describe_capabilities)
    - Async context manager support

Design Decisions:
    - Abstract base class: Enforces consistent interface across providers
    - Async context manager: Ensures proper resource cleanup
    - Validation hooks: Allow providers to add custom validation
    - Capability discovery: Optional runtime capability checking

Note:
    This is a minimal base class. Actual provider implementations may extend
    this or use provider-specific base classes that implement the full routing
    interface (feature handlers, URM mappers, etc.).

See Also:
    - ProviderRegistry: Manages provider instances
    - DataRouter: Routes requests to providers
    - register_feature_handler: Decorator for registering provider methods
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

from ..models import OHLCV
from .enums import Timeframe

if TYPE_CHECKING:
    from ..capability.registry import CapabilityStatus
    from .enums import DataFeature, InstrumentType, MarketType, TransportKind


class BaseProvider(ABC):
    """Abstract base class for all data providers.

    Architecture:
        All providers must inherit from this class and implement abstract methods.
        The class provides a minimal interface that ensures providers can be
        managed by the ProviderRegistry and used by the DataRouter.

    Design Decision:
        Minimal interface allows flexibility for provider-specific implementations.
        Providers can add additional methods beyond the abstract interface.
    """

    def __init__(self, name: str) -> None:
        """Initialize provider.

        Architecture:
            Providers are identified by name. Session management is left to
            subclasses (HTTP sessions, WebSocket connections, etc.).
        """
        self.name = name
        # Architecture: Session storage for HTTP/WebSocket connections
        # Subclasses manage their own session lifecycle
        self._session: object | None = None

    async def fetch_health(self) -> dict[str, object]:
        """Fetch provider health information."""
        raise NotImplementedError("fetch_health is not implemented for this provider")

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
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

    def validate_timeframe(self, timeframe: Timeframe) -> None:
        """Validate if timeframe is supported by provider. Override if needed."""
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

        Architecture:
            This method allows providers to discover capabilities at runtime
            (e.g., by querying exchange API). Default implementation defers to
            static capability registry. Providers can override to provide
            dynamic capability discovery.
        """
        from ..capability.registry import CapabilityStatus

        # Architecture: Default implementation defers to static registry
        # Providers can override to provide runtime discovery (e.g., API queries)
        return CapabilityStatus(
            supported=False,
            reason="Runtime capability discovery not implemented for this provider",
        )

    async def __aenter__(self) -> BaseProvider:
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()
