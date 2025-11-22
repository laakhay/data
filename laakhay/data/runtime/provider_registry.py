"""Provider registry for managing provider lifecycles and feature routing.

The ProviderRegistry centralizes provider instance management and maps
(DataFeature, TransportKind) pairs to concrete provider methods.

Architecture:
    This module implements the Registry pattern to manage provider instances
    and feature routing. Key responsibilities:
    - Provider instance pooling (one per exchange + market_type)
    - Feature handler mapping (decorator-based registration)
    - URM mapper registration per exchange
    - Async context lifecycle management

Design Decisions:
    - Instance pooling: Reuse providers to avoid expensive initialization
    - Thread-safe pooling: Locks prevent race conditions in async context
    - Decorator-based handlers: Self-documenting, type-safe feature mapping
    - Singleton pattern: Global registry for convenience, injection for testing
    - Lazy instantiation: Providers created on-demand, not at registration

Pooling Strategy:
    - Key: (exchange, market_type) tuple
    - One instance per key (shared across requests)
    - Instances entered into async context automatically
    - Closed instances removed and recreated

Feature Handler Registration:
    - Decorators store metadata on methods
    - collect_feature_handlers() scans provider class
    - Handlers mapped to (DataFeature, TransportKind) tuples
    - DataRouter uses handlers for dynamic method dispatch

See Also:
    - DataRouter: Uses registry for provider lookup and feature routing
    - BaseProvider: Provider interface that all providers implement
    - register_feature_handler: Decorator for registering feature handlers
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from functools import wraps
from typing import TYPE_CHECKING, Any

from ..core.enums import DataFeature, MarketType, MarketVariant, TransportKind
from ..core.exceptions import ProviderError

if TYPE_CHECKING:
    from ..core.base import BaseProvider
    from ..core.urm import UniversalRepresentationMapper


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
        """Initialize the registry.

        Architecture:
            Registry maintains three key data structures:
            - _registrations: Provider class metadata and feature handlers
            - _provider_pools: Cached provider instances (one per key)
            - _pool_locks: Async locks for thread-safe instance creation
        """
        # Architecture: Registration metadata (class, handlers, URM mapper)
        self._registrations: dict[str, ProviderRegistration] = {}
        # Architecture: Instance pool - key is (exchange, market_type, market_variant)
        # Performance: Reuse instances to avoid expensive initialization
        # Note: market_variant can be None for backward compatibility
        self._provider_pools: dict[tuple[str, MarketType, MarketVariant | None], BaseProvider] = {}
        # Architecture: Locks for thread-safe instance creation
        # Prevents race conditions when multiple requests create same provider
        self._pool_locks: dict[tuple[str, MarketType, MarketVariant | None], asyncio.Lock] = {}
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

        # Architecture: Pre-initialize locks for each market type
        # This ensures locks exist before any get_provider() calls
        # Performance: Lock creation is cheap, avoids lazy initialization overhead
        # Note: Locks created with market_variant=None for backward compatibility
        for market_type in market_types:
            key = (exchange, market_type, None)
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

        # Architecture: Cleanup active provider instances
        # Unregistering removes registration but must also close pooled instances
        keys_to_remove = [key for key in self._provider_pools if key[0] == exchange]
        for key in keys_to_remove:
            provider = self._provider_pools.pop(key, None)
            if provider:
                # Architecture: Async cleanup in sync method
                # Schedule task but don't await (sync method can't await)
                # Task will run in background and clean up resources
                asyncio.create_task(provider.close())

        del self._registrations[exchange]

    async def get_provider(
        self,
        exchange: str,
        market_type: MarketType,
        *,
        market_variant: MarketVariant | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> BaseProvider:
        """Get or create a provider instance.

        Uses a pool to reuse instances for the same (exchange, market_type, market_variant) combination.
        Providers are managed as async context managers.

        Args:
            exchange: Exchange name
            market_type: Market type (spot/futures)
            market_variant: Optional market variant (e.g., linear_perp, inverse_perp)
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

        # Architecture: Pool key includes market_variant if provided
        # This ensures different variants get different provider instances
        # Backward compatible: if market_variant is None, pool by (exchange, market_type) only
        key = (
            (exchange, market_type, market_variant)
            if market_variant is not None
            else (exchange, market_type, None)
        )

        # Architecture: Check pool first (fast path)
        # Performance: Most requests hit cached instance, avoiding creation overhead
        if key in self._provider_pools:
            provider = self._provider_pools[key]
            # Architecture: Validate provider is still alive
            # Closed providers are removed and recreated
            if hasattr(provider, "_closed") and provider._closed:
                # Remove closed provider and create new one
                del self._provider_pools[key]
            else:
                return provider

        # Architecture: Ensure lock exists for this key (lazy initialization)
        # This handles keys with market_variant that weren't pre-initialized in register()
        if key not in self._pool_locks:
            self._pool_locks[key] = asyncio.Lock()

        # Architecture: Thread-safe instance creation
        # Lock prevents multiple concurrent requests from creating duplicate instances
        async with self._pool_locks[key]:
            # Architecture: Double-check pattern (check-then-act)
            # Another request may have created instance while we waited for lock
            if key in self._provider_pools:
                return self._provider_pools[key]

            # Architecture: Lazy instantiation
            # Provider created on-demand, not at registration time
            # This defers expensive initialization until actually needed
            # Pass market_variant only if provider supports it (checked via try/except)
            provider_kwargs: dict[str, Any] = {
                "market_type": market_type,
                "api_key": api_key,
                "api_secret": api_secret,
            }
            if market_variant is not None:
                provider_kwargs["market_variant"] = market_variant

            # Try to create provider with market_variant, fallback without if not supported
            try:
                provider = registration.provider_class(**provider_kwargs)
            except TypeError:
                # Provider doesn't accept market_variant, create without it
                provider_kwargs.pop("market_variant", None)
                provider = registration.provider_class(**provider_kwargs)

            # Architecture: Enter async context automatically
            # Providers are async context managers (HTTP sessions, WebSocket connections)
            # Registry ensures proper initialization before returning instance
            provider = await provider.__aenter__()

            # Architecture: Cache instance in pool
            # Future requests for same (exchange, market_type) will reuse this instance
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

        Architecture:
            Feature handlers are registered via @register_feature_handler decorators.
            This method looks up the handler metadata, which DataRouter uses for
            dynamic method dispatch. Returns None if handler not registered (should
            be caught by capability validation).
        """
        if exchange not in self._registrations:
            return None

        registration = self._registrations[exchange]
        # Architecture: O(1) lookup using (feature, transport) tuple as key
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

        await self.shutdown_instances()
        self._pool_locks.clear()

    async def shutdown_instances(self) -> None:
        """Close all provider instances without tearing down the registry."""
        if not self._provider_pools:
            return

        for provider in list(self._provider_pools.values()):
            with suppress(Exception):
                await provider.__aexit__(None, None, None)

        self._provider_pools.clear()

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

    Architecture:
        Singleton pattern provides convenient global access to registry.
        For testing, DataRouter accepts registry injection to use mocks.
        Lazy initialization: registry created on first access.
    """
    global _default_registry
    # Architecture: Lazy singleton initialization
    # Registry created on first access, not at module import time
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
        async def fetch_ohlcv(self, ...):
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
        # Architecture: Store metadata on function for later collection
        # Decorator attaches metadata without modifying function behavior
        # collect_feature_handlers() scans class and collects all decorated methods
        if not hasattr(func, "_feature_handlers"):
            func._feature_handlers = []  # type: ignore[attr-defined]

        handler_metadata = {
            "feature": feature,
            "transport": transport,
            "method_name": method_name or func.__name__,
            "constraints": constraints or {},
        }

        func._feature_handlers.append(handler_metadata)  # type: ignore[attr-defined]

        # Architecture: Wrapper preserves function signature
        # @wraps ensures metadata (docstring, annotations) preserved
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # Architecture: Copy metadata to wrapper
        # Wrapper needs metadata for collect_feature_handlers() to find it
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

    # Architecture: Scan provider class for decorated methods
    # Uses dir() to find all attributes, filters to callables with _feature_handlers
    for name in dir(provider_class):
        obj = getattr(provider_class, name)
        if not callable(obj):
            continue

        # Architecture: Check for decorator metadata
        # Methods decorated with @register_feature_handler have _feature_handlers attribute
        if hasattr(obj, "_feature_handlers"):
            for metadata in obj._feature_handlers:
                feature = metadata["feature"]
                transport = metadata["transport"]
                method_name = metadata["method_name"]
                constraints = metadata["constraints"]

                # Architecture: Get actual method from class
                # Handles both unbound methods (from class) and bound methods (from instance)
                method = getattr(provider_class, method_name, obj)

                # Architecture: Build handler mapping
                # Key is (feature, transport) tuple, value is FeatureHandler metadata
                handlers[(feature, transport)] = FeatureHandler(
                    method_name=method_name,
                    method=method,
                    feature=feature,
                    transport=transport,
                    constraints=constraints,
                )

    return handlers
