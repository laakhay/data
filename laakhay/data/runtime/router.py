"""Data router coordinating URM, capabilities, and provider registry.

The DataRouter is the central coordinator that:
1. Resolves symbols via URM
2. Validates capabilities
3. Looks up providers and feature handlers
4. Invokes the appropriate provider methods

Architecture:
    This module implements the Router pattern to coordinate multiple concerns:
    - Capability validation (early failure detection)
    - Symbol normalization (URM resolution)
    - Provider lookup and feature handler routing
    - Method invocation with normalized parameters

Design Decisions:
    - Centralized routing avoids duplication across DataAPI methods
    - Separation of concerns: router doesn't know about defaults/UX
    - Dependency injection for testability (registry, capability service)
    - URM resolution happens after capability validation (fail fast on capabilities)

Request Flow:
    1. Capability validation → fail fast if unsupported
    2. URM resolution → normalize symbols to exchange format
    3. Provider lookup → get or create provider instance
    4. Feature handler lookup → map (feature, transport) to method
    5. Method invocation → call provider method with normalized args

See Also:
    - DataAPI: High-level facade that uses this router
    - ProviderRegistry: Manages provider instances and feature handlers
    - CapabilityService: Validates request capabilities
    - URM Registry: Symbol normalization system
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from ..capability.service import CapabilityService
from ..core.exceptions import ProviderError
from ..core.request import DataRequest
from ..core.urm import get_urm_registry

if TYPE_CHECKING:
    from .provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)


class DataRouter:
    """Router that coordinates URM resolution, capability validation, and provider invocation.

    The router is the central component that ties together:
    - URM Registry: for symbol normalization
    - Capability Service: for validation
    - Provider Registry: for provider lookup and method invocation
    """

    def __init__(
        self,
        *,
        provider_registry: ProviderRegistry | None = None,
        capability_service: CapabilityService | None = None,
    ) -> None:
        """Initialize the data router.

        Args:
            provider_registry: Optional provider registry (defaults to global singleton)
            capability_service: Optional capability service (defaults to new instance)

        Note:
            Dependency injection pattern allows testing with mocks. Defaults use
            singletons for normal operation. URM registry is always a singleton
            (shared across all router instances).
        """
        from .provider_registry import get_provider_registry

        # Architecture: Dependency injection for testability
        # Default to global singleton for normal operation
        self._provider_registry = provider_registry or get_provider_registry()
        # CapabilityService is stateless, so new instance is fine
        self._capability_service = capability_service or CapabilityService()
        # URM registry is always singleton (shared symbol cache)
        self._urm_registry = get_urm_registry()
        self._closed = False

    async def route(self, request: DataRequest) -> Any:
        """Route a data request through the system.

        This method:
        1. Validates capabilities
        2. Resolves symbols via URM
        3. Looks up provider and feature handler
        4. Invokes the provider method

        Args:
            request: DataRequest to route

        Returns:
            Result from provider method (varies by feature)

        Raises:
            CapabilityError: If capability is unsupported
            SymbolResolutionError: If symbol cannot be resolved
            ProviderError: If provider lookup or invocation fails
        """
        logger.debug(
            "Routing request",
            extra={
                "exchange": request.exchange,
                "feature": request.feature.value,
                "transport": request.transport.value,
                "market_type": request.market_type.value,
                "symbol": request.symbol,
            },
        )

        # Step 1: Validate capability (fail fast)
        # Architecture: Validate before expensive operations (URM, provider lookup)
        # This provides early error detection with helpful messages
        self._capability_service.validate_request(request)
        logger.debug("Capability validation passed")

        # Step 2: Resolve symbol(s) via URM
        # Architecture: Symbol normalization happens after capability check
        # This ensures we only resolve symbols for supported features
        exchange_symbols = self._resolve_symbols(request)
        logger.debug(
            "Symbol resolution complete",
            extra={"exchange_symbols": exchange_symbols},
        )

        # Step 3: Get provider instance
        # Architecture: ProviderRegistry handles instance pooling and lifecycle
        # Returns cached instance or creates new one, entered into async context
        provider = await self._provider_registry.get_provider(
            request.exchange,
            request.market_type,
        )
        logger.debug("Provider instance retrieved", extra={"provider": provider.name})

        # Step 4: Get feature handler
        # Architecture: Feature handlers are registered via decorators
        # Maps (DataFeature, TransportKind) to provider method name
        handler = self._provider_registry.get_feature_handler(
            request.exchange,
            request.feature,
            request.transport,
        )

        if handler is None:
            # Architecture: Handler lookup failure indicates registration issue
            # This should not happen if capabilities are correctly registered
            logger.error(
                "No handler found",
                extra={
                    "exchange": request.exchange,
                    "feature": request.feature.value,
                    "transport": request.transport.value,
                },
            )
            raise ProviderError(
                f"No handler found for {request.feature.value} "
                f"({request.transport.value}) on {request.exchange}"
            )

        logger.debug(
            "Feature handler found",
            extra={"method_name": handler.method_name},
        )

        # Step 5: Build method arguments from request
        # Architecture: Transform DataRequest into provider method kwargs
        # Handles symbol normalization, parameter mapping, and feature-specific params
        method_args = self._build_method_args(request, exchange_symbols)

        # Step 6: Invoke provider method
        # Architecture: Dynamic method dispatch based on feature handler
        # Provider methods are called with normalized exchange-native symbols
        logger.debug("Invoking provider method", extra={"method": handler.method_name})
        method = getattr(provider, handler.method_name)
        result = await method(**method_args)
        logger.debug("Request completed successfully")
        return result

    async def route_stream(self, request: DataRequest) -> AsyncIterator[Any]:
        """Route a streaming data request.

        Similar to route() but returns an AsyncIterator for streaming results.

        Args:
            request: DataRequest to route (must have transport=WS)

        Yields:
            Streaming data items

        Raises:
            CapabilityError: If capability is unsupported
            SymbolResolutionError: If symbol cannot be resolved
            ProviderError: If provider lookup or invocation fails
        """
        from ..core.enums import TransportKind

        if request.transport != TransportKind.WS:
            raise ValueError("route_stream() requires transport=TransportKind.WS")

        logger.debug(
            "Routing stream request",
            extra={
                "exchange": request.exchange,
                "feature": request.feature.value,
                "transport": request.transport.value,
                "market_type": request.market_type.value,
                "symbol": request.symbol,
            },
        )

        # Step 1: Validate capability
        self._capability_service.validate_request(request)
        logger.debug("Capability validation passed")

        # Step 2: Resolve symbol(s) via URM
        exchange_symbols = self._resolve_symbols(request)
        logger.debug(
            "Symbol resolution complete",
            extra={"exchange_symbols": exchange_symbols},
        )

        # Step 3: Get provider instance
        provider = await self._provider_registry.get_provider(
            request.exchange,
            request.market_type,
        )
        logger.debug("Provider instance retrieved", extra={"provider": provider.name})

        # Step 4: Get feature handler
        handler = self._provider_registry.get_feature_handler(
            request.exchange,
            request.feature,
            request.transport,
        )

        if handler is None:
            logger.error(
                "No handler found",
                extra={
                    "exchange": request.exchange,
                    "feature": request.feature.value,
                    "transport": request.transport.value,
                },
            )
            raise ProviderError(
                f"No handler found for {request.feature.value} "
                f"({request.transport.value}) on {request.exchange}"
            )

        logger.debug(
            "Feature handler found",
            extra={"method_name": handler.method_name},
        )

        # Step 5: Build method arguments from request
        method_args = self._build_method_args(request, exchange_symbols)

        # Step 6: Invoke provider method and yield results
        # Architecture: Streaming uses async iterator pattern
        # Router yields items as they arrive, with progress logging
        logger.debug("Starting stream", extra={"method": handler.method_name})
        method = getattr(provider, handler.method_name)
        item_count = 0
        async for item in method(**method_args):
            item_count += 1
            # Performance: Log progress every 100 items to avoid log spam
            if item_count % 100 == 0:
                logger.debug(
                    "Stream progress",
                    extra={"items_yielded": item_count},
                )
            yield item
        logger.debug("Stream completed", extra={"total_items": item_count})

    async def close(self) -> None:
        """Close router resources (provider registry instances)."""
        if self._closed:
            return
        self._closed = True
        await self._provider_registry.shutdown_instances()

    def _resolve_symbols(self, request: DataRequest) -> str | list[str] | None:
        """Resolve symbol(s) via URM to exchange-native format.

        Handles multiple symbol formats:
        - URM IDs: urm://*:btc/usdt:perpetual
        - Normalized symbols: BTC/USDT (Laakhay convention)
        - Exchange-native symbols: BTCUSDT (fallback)

        Args:
            request: DataRequest containing symbol information

        Returns:
            Exchange-native symbol string or list of strings

        Raises:
            SymbolResolutionError: If symbol cannot be resolved
        """

        # Architecture: Get URM mapper for symbol normalization
        # Each exchange has a mapper that converts between canonical and exchange-native formats
        mapper = self._provider_registry.get_urm_mapper(request.exchange)
        if mapper is None:
            # Architecture: Fallback for exchanges without URM mapper
            # Assume symbol is already in exchange-native format (backward compatibility)
            if request.symbol:
                return request.symbol
            if request.symbols:
                return request.symbols
            return []

        def resolve_single_symbol(symbol: str) -> str:
            """Resolve a single symbol to exchange-native format.

            Only accepts Laakhay normalized format (BASE/QUOTE, e.g., BTC/USDT).
            Rejects exchange-native formats and URM IDs.

            Architecture:
                This function enforces Laakhay's canonical symbol format (BASE/QUOTE).
                URM IDs are rejected to keep the API surface simple. Exchange-native
                formats are rejected to ensure consistent normalization.

            Design Decision:
                Requiring BASE/QUOTE format ensures all symbols go through URM,
                providing consistent behavior and better error messages.
            """
            from ..core.enums import InstrumentSpec, InstrumentType, MarketType
            from ..core.exceptions import SymbolResolutionError

            # Architecture: Reject URM IDs - require Laakhay format for simplicity
            # URM IDs add complexity without significant benefit for most users
            if symbol.startswith("urm://"):
                raise SymbolResolutionError(
                    f"URM IDs are not accepted. Use Laakhay format (BASE/QUOTE, e.g., BTC/USDT). Got: {symbol}",
                    exchange=request.exchange,
                    value=symbol,
                    market_type=request.market_type,
                )

            # Architecture: Require normalized format (BASE/QUOTE) - Laakhay convention
            # This ensures all symbols go through URM normalization
            if "/" not in symbol:
                raise SymbolResolutionError(
                    f"Symbol must be in Laakhay format (BASE/QUOTE, e.g., BTC/USDT). Got: {symbol}",
                    exchange=request.exchange,
                    value=symbol,
                    market_type=request.market_type,
                )

            # Parse normalized symbol to InstrumentSpec
            parts = symbol.upper().split("/", 1)
            if len(parts) != 2 or not parts[0] or not parts[1]:
                raise SymbolResolutionError(
                    f"Invalid symbol format '{symbol}'. Expected BASE/QUOTE (e.g., BTC/USDT)",
                    exchange=request.exchange,
                    value=symbol,
                    market_type=request.market_type,
                )

            # Architecture: Infer instrument_type from market_type if needed
            # If user specifies SPOT but market_type is FUTURES, assume PERPETUAL
            # This provides sensible defaults while allowing explicit overrides
            instrument_type = request.instrument_type
            if instrument_type == InstrumentType.SPOT and request.market_type == MarketType.FUTURES:
                instrument_type = InstrumentType.PERPETUAL

            # Build InstrumentSpec and convert to exchange-native format
            spec = InstrumentSpec(
                base=parts[0],
                quote=parts[1],
                instrument_type=instrument_type,
            )
            return mapper.to_exchange_symbol(spec, market_type=request.market_type)

        # Resolve single symbol
        if request.symbol:
            return resolve_single_symbol(request.symbol)

        # Resolve multiple symbols
        if request.symbols:
            return [resolve_single_symbol(symbol) for symbol in request.symbols]

        # No symbols required (e.g., global liquidations)
        return None

    def _build_method_args(
        self, request: DataRequest, exchange_symbols: str | list[str] | None
    ) -> dict[str, Any]:
        """Build method arguments from DataRequest.

        Args:
            request: DataRequest
            exchange_symbols: Resolved exchange-native symbol(s)

        Returns:
            Dictionary of method arguments
        """
        args: dict[str, Any] = {}

        # Add symbol(s) if provided
        if exchange_symbols is not None:
            if isinstance(exchange_symbols, list):
                if len(exchange_symbols) == 1:
                    args["symbol"] = exchange_symbols[0]
                else:
                    args["symbols"] = exchange_symbols
            else:
                args["symbol"] = exchange_symbols

        # Add feature-specific parameters
        if request.timeframe is not None:
            args["timeframe"] = request.timeframe

        if request.start_time is not None:
            args["start_time"] = request.start_time

        if request.end_time is not None:
            args["end_time"] = request.end_time

        if request.limit is not None:
            args["limit"] = request.limit

        if request.depth is not None:
            # Architecture: Map 'depth' to 'limit' for order book
            # Provider methods use 'limit' parameter name for consistency
            args["limit"] = request.depth

        if request.period is not None:
            args["period"] = request.period

        if request.update_speed is not None:
            args["update_speed"] = request.update_speed

        if request.only_closed:
            args["only_closed"] = request.only_closed

        if request.throttle_ms is not None:
            args["throttle_ms"] = request.throttle_ms

        if request.dedupe_same_candle:
            args["dedupe_same_candle"] = request.dedupe_same_candle

        if request.historical:
            args["historical"] = request.historical

        if request.max_chunks is not None:
            args["max_chunks"] = request.max_chunks

        if request.from_id is not None:
            args["from_id"] = request.from_id

        # Add any extra parameters
        args.update(request.extra_params)

        return args
