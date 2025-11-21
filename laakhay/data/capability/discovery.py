"""Code-driven capability discovery.

This module implements a discovery walker that inspects provider registrations
and endpoint modules to derive capabilities from actual code instead of static
metadata.

Architecture:
    The discovery system walks through:
    1. Provider registrations (from ProviderRegistry) - feature handlers
    2. Endpoint modules (rest/endpoints.py, ws/endpoints.py) - available endpoints
    3. Provider classes - market types and constraints

    It emits capability entries per (exchange, market_type, feature, transport)
    with constraints, weight hints, and metadata.

Design Decisions:
    - Code-driven: Derives capabilities from actual implementation
    - Lazy discovery: Only discovers when needed
    - Cached results: Discovery results are cached to avoid repeated inspection
    - Extensible: Easy to add new discovery sources
"""

from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass, field
from typing import Any

from ..core.enums import DataFeature, InstrumentType, MarketType, TransportKind
from ..runtime.provider_registry import ProviderRegistry, get_provider_registry


@dataclass
class DiscoveredCapability:
    """A capability discovered from code inspection."""

    exchange: str
    market_type: MarketType
    instrument_type: InstrumentType
    feature: DataFeature
    transport: TransportKind
    constraints: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0  # Weight hint for routing (higher = preferred)
    source: str = "discovery"  # "discovery" or "endpoint" or "handler"


class CapabilityDiscovery:
    """Discovers capabilities by inspecting provider code."""

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        """Initialize discovery with a provider registry.

        Args:
            registry: Provider registry to inspect (defaults to global singleton)
        """
        self._registry = registry or get_provider_registry()
        self._cache: dict[str, list[DiscoveredCapability]] = {}

    def discover_all(self) -> list[DiscoveredCapability]:
        """Discover all capabilities from registered providers.

        Returns:
            List of discovered capabilities
        """
        cache_key = "all"
        if cache_key in self._cache:
            return self._cache[cache_key]

        capabilities: list[DiscoveredCapability] = []

        # Walk through all registered exchanges
        for exchange in self._registry.list_exchanges():
            exchange_caps = self.discover_exchange(exchange)
            capabilities.extend(exchange_caps)

        self._cache[cache_key] = capabilities
        return capabilities

    def discover_exchange(self, exchange: str) -> list[DiscoveredCapability]:
        """Discover capabilities for a specific exchange.

        Args:
            exchange: Exchange name (e.g., "binance", "bybit")

        Returns:
            List of discovered capabilities for the exchange
        """
        if exchange in self._cache:
            return self._cache[exchange]

        if not self._registry.is_registered(exchange):
            return []

        capabilities: list[DiscoveredCapability] = []

        # Get registration metadata
        registration = self._registry._registrations[exchange]
        market_types = registration.market_types

        # Discover from feature handlers
        handler_caps = self._discover_from_handlers(exchange, market_types, registration)
        capabilities.extend(handler_caps)

        # Discover from endpoint modules
        endpoint_caps = self._discover_from_endpoints(exchange, market_types)
        capabilities.extend(endpoint_caps)

        self._cache[exchange] = capabilities
        return capabilities

    def _discover_from_handlers(
        self,
        exchange: str,
        market_types: list[MarketType],
        registration: Any,
    ) -> list[DiscoveredCapability]:
        """Discover capabilities from feature handlers.

        Args:
            exchange: Exchange name
            market_types: List of supported market types
            registration: Provider registration metadata

        Returns:
            List of discovered capabilities
        """
        capabilities: list[DiscoveredCapability] = []

        # Walk through feature handlers
        for (feature, transport), handler in registration.feature_handlers.items():
            # Determine instrument types based on market type and feature
            for market_type in market_types:
                instrument_types = self._infer_instrument_types(market_type, feature)

                for instrument_type in instrument_types:
                    # Extract constraints from handler metadata
                    constraints = handler.constraints.copy()

                    capability = DiscoveredCapability(
                        exchange=exchange,
                        market_type=market_type,
                        instrument_type=instrument_type,
                        feature=feature,
                        transport=transport,
                        constraints=constraints,
                        source="handler",
                    )
                    capabilities.append(capability)

        return capabilities

    def _discover_from_endpoints(
        self, exchange: str, market_types: list[MarketType]
    ) -> list[DiscoveredCapability]:
        """Discover capabilities from endpoint modules.

        Args:
            exchange: Exchange name
            market_types: List of supported market types

        Returns:
            List of discovered capabilities
        """
        capabilities: list[DiscoveredCapability] = []

        # Try to import and inspect endpoint modules
        # REST endpoints
        rest_caps = self._discover_rest_endpoints(exchange, market_types)
        capabilities.extend(rest_caps)

        # WS endpoints
        ws_caps = self._discover_ws_endpoints(exchange, market_types)
        capabilities.extend(ws_caps)

        return capabilities

    def _discover_rest_endpoints(
        self, exchange: str, market_types: list[MarketType]
    ) -> list[DiscoveredCapability]:
        """Discover REST endpoints from rest/endpoints.py module.

        Args:
            exchange: Exchange name
            market_types: List of supported market types

        Returns:
            List of discovered capabilities
        """
        capabilities: list[DiscoveredCapability] = []

        try:
            # Try to import the endpoints module
            module_path = f"laakhay.data.providers.{exchange}.rest.endpoints"
            module = importlib.import_module(module_path)

            # Find all endpoint spec functions
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                if name.endswith("_spec"):
                    try:
                        # Call the spec function to get endpoint metadata
                        spec = obj()
                        if hasattr(spec, "id"):
                            endpoint_id = spec.id
                            feature = self._map_endpoint_id_to_feature(endpoint_id)
                            if feature:
                                for market_type in market_types:
                                    instrument_types = self._infer_instrument_types(
                                        market_type, feature
                                    )
                                    for instrument_type in instrument_types:
                                        # Check if this capability already exists from handlers
                                        # If so, skip to avoid duplicates
                                        if not self._has_handler_capability(
                                            exchange,
                                            market_type,
                                            instrument_type,
                                            feature,
                                            TransportKind.REST,
                                        ):
                                            capability = DiscoveredCapability(
                                                exchange=exchange,
                                                market_type=market_type,
                                                instrument_type=instrument_type,
                                                feature=feature,
                                                transport=TransportKind.REST,
                                                source="endpoint",
                                            )
                                            capabilities.append(capability)
                    except Exception:
                        # Skip endpoints that can't be instantiated without params
                        continue

        except ImportError:
            # Endpoint module doesn't exist, skip
            pass

        return capabilities

    def _discover_ws_endpoints(
        self, exchange: str, market_types: list[MarketType]
    ) -> list[DiscoveredCapability]:
        """Discover WebSocket endpoints from ws/endpoints.py module.

        Args:
            exchange: Exchange name
            market_types: List of supported market types

        Returns:
            List of discovered capabilities
        """
        capabilities: list[DiscoveredCapability] = []

        try:
            # Try to import the endpoints module
            module_path = f"laakhay.data.providers.{exchange}.ws.endpoints"
            module = importlib.import_module(module_path)

            # Find all endpoint spec functions
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                if name.endswith("_spec"):
                    try:
                        # WS specs typically take market_type as parameter
                        # Try with each market type
                        for market_type in market_types:
                            try:
                                spec = obj(market_type)
                                if hasattr(spec, "id"):
                                    endpoint_id = spec.id
                                    feature = self._map_endpoint_id_to_feature(endpoint_id)
                                    if feature:
                                        instrument_types = self._infer_instrument_types(
                                            market_type, feature
                                        )
                                        for instrument_type in instrument_types:
                                            # Check if this capability already exists from handlers
                                            if not self._has_handler_capability(
                                                exchange,
                                                market_type,
                                                instrument_type,
                                                feature,
                                                TransportKind.WS,
                                            ):
                                                # Extract stream metadata from spec
                                                constraints: dict[str, Any] = {}
                                                if hasattr(spec, "max_streams_per_connection"):
                                                    constraints["max_streams"] = (
                                                        spec.max_streams_per_connection
                                                    )
                                                if hasattr(spec, "combined_supported"):
                                                    constraints["combined_streams"] = (
                                                        spec.combined_supported
                                                    )

                                                capability = DiscoveredCapability(
                                                    exchange=exchange,
                                                    market_type=market_type,
                                                    instrument_type=instrument_type,
                                                    feature=feature,
                                                    transport=TransportKind.WS,
                                                    constraints=constraints,
                                                    source="endpoint",
                                                )
                                                capabilities.append(capability)
                            except Exception:
                                # Skip if spec function doesn't accept market_type
                                continue
                    except Exception:
                        # Skip endpoints that can't be instantiated
                        continue

        except ImportError:
            # Endpoint module doesn't exist, skip
            pass

        return capabilities

    def _map_endpoint_id_to_feature(self, endpoint_id: str) -> DataFeature | None:
        """Map endpoint ID to DataFeature enum.

        Args:
            endpoint_id: Endpoint ID (e.g., "ohlcv", "order_book")

        Returns:
            DataFeature if mapping exists, None otherwise
        """
        mapping = {
            "ohlcv": DataFeature.OHLCV,
            "candles": DataFeature.OHLCV,
            "order_book": DataFeature.ORDER_BOOK,
            "depth": DataFeature.ORDER_BOOK,
            "trades": DataFeature.TRADES,
            "recent_trades": DataFeature.TRADES,
            "historical_trades": DataFeature.HISTORICAL_TRADES,
            "liquidations": DataFeature.LIQUIDATIONS,
            "open_interest": DataFeature.OPEN_INTEREST,
            "open_interest_current": DataFeature.OPEN_INTEREST,
            "open_interest_hist": DataFeature.OPEN_INTEREST,
            "funding_rate": DataFeature.FUNDING_RATE,
            "funding_rates": DataFeature.FUNDING_RATE,
            "mark_price": DataFeature.MARK_PRICE,
            "exchange_info": DataFeature.SYMBOL_METADATA,
            "exchange_info_raw": DataFeature.SYMBOL_METADATA,
            "health": DataFeature.HEALTH,
        }
        return mapping.get(endpoint_id)

    def _infer_instrument_types(
        self, market_type: MarketType, feature: DataFeature
    ) -> list[InstrumentType]:
        """Infer instrument types from market type and feature.

        Args:
            market_type: Market type (spot/futures)
            feature: Data feature

        Returns:
            List of instrument types
        """
        if market_type == MarketType.SPOT:
            return [InstrumentType.SPOT]
        else:  # FUTURES
            # Futures-specific features only apply to perpetual/future instruments
            if feature in (
                DataFeature.LIQUIDATIONS,
                DataFeature.OPEN_INTEREST,
                DataFeature.FUNDING_RATE,
                DataFeature.MARK_PRICE,
            ):
                return [InstrumentType.PERPETUAL, InstrumentType.FUTURE]
            else:
                # Other features can apply to both
                return [InstrumentType.PERPETUAL, InstrumentType.FUTURE]

    def _has_handler_capability(
        self,
        exchange: str,
        market_type: MarketType,
        instrument_type: InstrumentType,
        feature: DataFeature,
        transport: TransportKind,
    ) -> bool:
        """Check if a capability already exists from handlers.

        Args:
            exchange: Exchange name
            market_type: Market type
            instrument_type: Instrument type
            feature: Data feature
            transport: Transport kind

        Returns:
            True if capability exists from handlers, False otherwise
        """
        if exchange not in self._cache:
            # Not discovered yet, check registry directly
            if not self._registry.is_registered(exchange):
                return False
            registration = self._registry._registrations[exchange]
            return (feature, transport) in registration.feature_handlers

        # Check cached capabilities
        for cap in self._cache[exchange]:
            if (
                cap.market_type == market_type
                and cap.instrument_type == instrument_type
                and cap.feature == feature
                and cap.transport == transport
                and cap.source == "handler"
            ):
                return True
        return False
