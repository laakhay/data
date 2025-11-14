"""Provider registry for managing provider lifecycles and feature routing.

The ProviderRegistry centralizes provider instance management and maps
(DataFeature, TransportKind) pairs to concrete provider methods.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from functools import wraps
from typing import TYPE_CHECKING, Any

from .enums import DataFeature, MarketType, TransportKind
from .exceptions import ProviderError

if TYPE_CHECKING:
    from .base import BaseProvider
    from .urm import UniversalRepresentationMapper


@dataclass
class FeatureHandler:
    """Metadata for a feature handler method."""

    method_name: str
    method: Callable[..., Any]
    feature: DataFeature
    transport: TransportKind
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderRegistration:
    """Registration metadata for a provider."""

    exchange: str
    provider_class: type[BaseProvider]
    market_types: list[MarketType]
    urm_mapper: UniversalRepresentationMapper | None = None
    feature_handlers: dict[tuple[DataFeature, TransportKind], FeatureHandler] = field(
        default_factory=dict
    )


class ProviderRegistry:
    """Central registry for managing provider lifecycles and feature routing.

    The registry:
    - Manages provider instance pools (one per exchange + market_type combination)
    - Maps (DataFeature, TransportKind) pairs to provider methods
    - Handles async context lifecycle (entry/exit)
    - Supports optional dependency injection for testing
    """

    def __init__(self) -> None:
        """Initialize the registry."""
        self._registrations: dict[str, ProviderRegistration] = {}
        self._provider_pools: dict[tuple[str, MarketType], BaseProvider] = {}
        self._pool_locks: dict[tuple[str, MarketType], asyncio.Lock] = {}
        self._closed = False

    def register(
        self,
        exchange: str,
        provider_class: type[BaseProvider],
        *,
        market_types: list[MarketType],
        urm_mapper: UniversalRepresentationMapper | None = None,
        feature_handlers: dict[tuple[DataFeature, TransportKind], FeatureHandler] | None = None,
    ) -> None:
        """Register a provider with the registry.

        Args:
            exchange: Exchange name (e.g., "binance", "bybit")
            provider_class: Provider class to instantiate
            market_types: List of market types this provider supports
            urm_mapper: Optional URM mapper for symbol normalization
            feature_handlers: Optional mapping of (feature, transport) -> handler metadata

        Raises:
            ProviderError: If exchange is already registered
        """
        if exchange in self._registrations:
            raise ProviderError(f"Exchange '{exchange}' is already registered")

        registration = ProviderRegistration(
            exchange=exchange,
            provider_class=provider_class,
            market_types=market_types,
            urm_mapper=urm_mapper,
            feature_handlers=feature_handlers or {},
        )

        self._registrations[exchange] = registration

        # Initialize locks for each market type
        for market_type in market_types:
            key = (exchange, market_type)
            if key not in self._pool_locks:
                self._pool_locks[key] = asyncio.Lock()

    def unregister(self, exchange: str) -> None:
        """Unregister a provider.

        Args:
            exchange: Exchange name to unregister

        Raises:
            ProviderError: If exchange is not registered
        """
        if exchange not in self._registrations:
            raise ProviderError(f"Exchange '{exchange}' is not registered")

        # Close any active provider instances
        keys_to_remove = [key for key in self._provider_pools if key[0] == exchange]
        for key in keys_to_remove:
            provider = self._provider_pools.pop(key, None)
            if provider:
                # Schedule cleanup (don't await in sync method)
                asyncio.create_task(provider.close())

        del self._registrations[exchange]

    async def get_provider(
        self,
        exchange: str,
        market_type: MarketType,
        *,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> BaseProvider:
        """Get or create a provider instance.

        Uses a pool to reuse instances for the same (exchange, market_type) combination.
        Providers are managed as async context managers.

        Args:
            exchange: Exchange name
            market_type: Market type (spot/futures)
            api_key: Optional API key for authenticated providers
            api_secret: Optional API secret for authenticated providers

        Returns:
            Provider instance (entered into async context)

        Raises:
            ProviderError: If exchange is not registered or market type not supported
        """
        if self._closed:
            raise ProviderError("Registry is closed")

        if exchange not in self._registrations:
            raise ProviderError(f"Exchange '{exchange}' is not registered")

        registration = self._registrations[exchange]

        if market_type not in registration.market_types:
            raise ProviderError(
                f"Market type '{market_type.value}' not supported for exchange '{exchange}'"
            )

        key = (exchange, market_type)

        # Check pool first
        if key in self._provider_pools:
            provider = self._provider_pools[key]
            # Verify provider is still valid (not closed)
            if hasattr(provider, "_closed") and provider._closed:
                # Remove closed provider and create new one
                del self._provider_pools[key]
            else:
                return provider

        # Create new provider instance
        async with self._pool_locks[key]:
            # Double-check after acquiring lock
            if key in self._provider_pools:
                return self._provider_pools[key]

            # Instantiate provider
            provider = registration.provider_class(
                market_type=market_type, api_key=api_key, api_secret=api_secret
            )

            # Enter async context
            provider = await provider.__aenter__()

            # Store in pool
            self._provider_pools[key] = provider

            return provider

    def get_feature_handler(
        self,
        exchange: str,
        feature: DataFeature,
        transport: TransportKind,
    ) -> FeatureHandler | None:
        """Get feature handler metadata for a (feature, transport) combination.

        Args:
            exchange: Exchange name
            feature: Data feature
            transport: Transport kind

        Returns:
            FeatureHandler if found, None otherwise
        """
        if exchange not in self._registrations:
            return None

        registration = self._registrations[exchange]
        return registration.feature_handlers.get((feature, transport))

    def get_urm_mapper(self, exchange: str) -> UniversalRepresentationMapper | None:
        """Get URM mapper for an exchange.

        Args:
            exchange: Exchange name

        Returns:
            URM mapper if registered, None otherwise
        """
        if exchange not in self._registrations:
            return None

        return self._registrations[exchange].urm_mapper

    def is_registered(self, exchange: str) -> bool:
        """Check if an exchange is registered.

        Args:
            exchange: Exchange name

        Returns:
            True if registered, False otherwise
        """
        return exchange in self._registrations

    def list_exchanges(self) -> list[str]:
        """List all registered exchanges.

        Returns:
            List of exchange names
        """
        return list(self._registrations.keys())

    async def close_all(self) -> None:
        """Close all provider instances and clear the registry."""
        if self._closed:
            return

        self._closed = True

        # Close all providers
        for provider in self._provider_pools.values():
            with suppress(Exception):
                await provider.__aexit__(None, None, None)

        self._provider_pools.clear()
        self._pool_locks.clear()

    async def __aenter__(self) -> ProviderRegistry:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close_all()


# Global singleton instance
_default_registry: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    """Get the global provider registry singleton.

    Returns:
        ProviderRegistry instance
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = ProviderRegistry()
    return _default_registry


# Registration helpers
def register_feature_handler(
    feature: DataFeature,
    transport: TransportKind,
    *,
    method_name: str | None = None,
    constraints: dict[str, Any] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to register a method as a feature handler.

    Usage:
        @register_feature_handler(DataFeature.OHLCV, TransportKind.REST)
        async def get_candles(self, ...):
            ...

    Args:
        feature: Data feature this method handles
        transport: Transport kind (REST or WS)
        method_name: Optional method name override (defaults to function name)
        constraints: Optional constraints metadata

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Store metadata on the function for later registration
        if not hasattr(func, "_feature_handlers"):
            func._feature_handlers = []  # type: ignore[attr-defined]

        handler_metadata = {
            "feature": feature,
            "transport": transport,
            "method_name": method_name or func.__name__,
            "constraints": constraints or {},
        }

        func._feature_handlers.append(handler_metadata)  # type: ignore[attr-defined]

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # Copy metadata to wrapper
        wrapper._feature_handlers = func._feature_handlers  # type: ignore[attr-defined]

        return wrapper

    return decorator


def collect_feature_handlers(
    provider_class: type[BaseProvider],
) -> dict[tuple[DataFeature, TransportKind], FeatureHandler]:
    """Collect feature handlers from a provider class.

    Scans the provider class for methods decorated with @register_feature_handler
    and returns a mapping of (feature, transport) -> handler metadata.

    Args:
        provider_class: Provider class to scan

    Returns:
        Dictionary mapping (feature, transport) -> FeatureHandler
    """
    handlers: dict[tuple[DataFeature, TransportKind], FeatureHandler] = {}

    for name in dir(provider_class):
        obj = getattr(provider_class, name)
        if not callable(obj):
            continue

        # Check for decorated methods
        if hasattr(obj, "_feature_handlers"):
            for metadata in obj._feature_handlers:
                feature = metadata["feature"]
                transport = metadata["transport"]
                method_name = metadata["method_name"]
                constraints = metadata["constraints"]

                # Get the actual method (handle both unbound and bound)
                method = getattr(provider_class, method_name, obj)

                handlers[(feature, transport)] = FeatureHandler(
                    method_name=method_name,
                    method=method,
                    feature=feature,
                    transport=transport,
                    constraints=constraints,
                )

    return handlers
