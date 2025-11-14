"""Data router coordinating URM, capabilities, and provider registry.

The DataRouter is the central coordinator that:
1. Resolves symbols via URM
2. Validates capabilities
3. Looks up providers and feature handlers
4. Invokes the appropriate provider methods
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from .capability_service import CapabilityService
from .exceptions import ProviderError
from .request import DataRequest
from .urm import get_urm_registry

if TYPE_CHECKING:
    from .registry import ProviderRegistry

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
        """
        from .registry import get_provider_registry

        self._provider_registry = provider_registry or get_provider_registry()
        self._capability_service = capability_service or CapabilityService()
        self._urm_registry = get_urm_registry()

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

        # Step 6: Invoke provider method
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
        from .enums import TransportKind

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
        logger.debug("Starting stream", extra={"method": handler.method_name})
        method = getattr(provider, handler.method_name)
        item_count = 0
        async for item in method(**method_args):
            item_count += 1
            if item_count % 100 == 0:
                logger.debug(
                    "Stream progress",
                    extra={"items_yielded": item_count},
                )
            yield item
        logger.debug("Stream completed", extra={"total_items": item_count})

    def _resolve_symbols(self, request: DataRequest) -> str | list[str] | None:
        """Resolve symbol(s) via URM to exchange-native format.

        Args:
            request: DataRequest containing symbol information

        Returns:
            Exchange-native symbol string or list of strings

        Raises:
            SymbolResolutionError: If symbol cannot be resolved
        """
        # Get URM mapper for the exchange
        mapper = self._provider_registry.get_urm_mapper(request.exchange)
        if mapper is None:
            # If no URM mapper, assume symbol is already in exchange format
            if request.symbol:
                return request.symbol
            if request.symbols:
                return request.symbols
            return []

        # Resolve single symbol
        if request.symbol:
            spec = mapper.to_spec(request.symbol, market_type=request.market_type)
            exchange_symbol = mapper.to_exchange_symbol(spec, market_type=request.market_type)
            return exchange_symbol

        # Resolve multiple symbols
        if request.symbols:
            exchange_symbols = []
            for symbol in request.symbols:
                spec = mapper.to_spec(symbol, market_type=request.market_type)
                exchange_symbol = mapper.to_exchange_symbol(spec, market_type=request.market_type)
                exchange_symbols.append(exchange_symbol)
            return exchange_symbols

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
            args["limit"] = request.depth  # Order book uses 'limit' parameter

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

        # Add any extra parameters
        args.update(request.extra_params)

        return args
