"""Capabilities API for discovering supported exchanges, market types, timeframes, and data types.

This module provides a consistent API for querying laakhay-data capabilities without
instantiating providers. Capabilities are discovered from actual provider code implementations.

Architecture:
    This module implements a hierarchical capability registry that maps:
    Exchange → MarketType → InstrumentType → DataFeature → TransportKind → CapabilityStatus

    The registry is built from code discovery (inspecting provider implementations) into a hierarchical
    structure that includes instrument types and stream metadata.

Design Decisions:
    - Discovery-based registry: Capabilities are derived from actual code, ensuring accuracy
    - Lazy initialization: Registry is built on first access, after providers are registered
    - Hierarchical structure: Supports fine-grained capability queries
    - Stream metadata: Includes symbol scope, combo support, constraints
    - Fallback options: Provides alternative suggestions when capability unsupported
    - Source tracking: Distinguishes static vs runtime discovery

Capability Hierarchy:
    The registry supports queries at multiple levels:
    - Exchange level: What exchanges are supported?
    - Market type level: What market types per exchange?
    - Feature level: What features per exchange/market/instrument?
    - Transport level: REST vs WebSocket support?

See Also:
    - CapabilityService: Service layer that uses this registry
    - DataRouter: Uses capability validation before routing
    - ADR-003: Architecture Decision Record for capability system
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypedDict

from ..core.enums import DataFeature, InstrumentType, MarketType, Timeframe, TransportKind


# Capability primitives
@dataclass(frozen=True)
class CapabilityKey:
    """Unique identifier for a capability combination."""

    exchange: str
    market_type: MarketType
    instrument_type: InstrumentType
    feature: DataFeature
    transport: TransportKind
    stream_variant: str | None = None  # e.g., "symbol", "global", "combo:trades+liquidations"


@dataclass(frozen=True)
class FallbackOption:
    """Suggested alternative when a capability is unsupported."""

    exchange: str
    market_type: MarketType
    instrument_type: InstrumentType
    feature: DataFeature
    transport: TransportKind
    note: str | None = None


@dataclass
class CapabilityStatus:
    """Status and metadata for a capability."""

    supported: bool
    reason: str | None = None
    constraints: dict[str, Any] = field(default_factory=dict)  # e.g., {"max_depth": 500}
    recommendations: list[FallbackOption] = field(default_factory=list)
    last_verified_at: datetime | None = None
    stream_metadata: dict[str, Any] = field(
        default_factory=dict
    )  # {"symbol_scope": "global", "timeframes": [...], "combo": ["trades","liquidations"]}


# Type definitions
class ExchangeCapability(TypedDict):
    """Capability information for a single exchange."""

    name: str
    display_name: str
    supported_market_types: list[str]  # ["spot", "futures"]
    default_market_type: str | None  # Default when not specified
    supported_timeframes: list[str]  # From Timeframe enum
    data_types: dict[str, dict[str, bool]]  # {"ohlcv": {"rest": True, "ws": True}, ...}
    notes: str | None  # Additional notes or restrictions


# EXCHANGE_METADATA removed - capabilities are now discovered from code
# Use get_exchange_capability() or get_all_capabilities() to get capability information


def get_all_exchanges() -> list[str]:
    """Get list of all supported exchange names.

    Returns:
        List of exchange names (e.g., ["binance", "bybit", "okx", ...])
    """
    _ensure_registry_initialized()
    return list(_CAPABILITY_REGISTRY.keys())


def get_exchange_capability(exchange: str) -> ExchangeCapability | None:
    """Get capability information for a specific exchange.

    Args:
        exchange: Exchange name (e.g., "binance", "bybit")

    Returns:
        ExchangeCapability dict if exchange exists, None otherwise
    """
    _ensure_registry_initialized()
    exchange_lower = exchange.lower()
    if exchange_lower not in _CAPABILITY_REGISTRY:
        return None

    # Build ExchangeCapability from registry
    exchange_data = _CAPABILITY_REGISTRY[exchange_lower]
    market_types = [mt.value for mt in exchange_data]

    # Collect all features and transports
    data_types: dict[str, dict[str, bool]] = {}
    for _market_type, instrument_data in exchange_data.items():
        for _instrument_type, feature_data in instrument_data.items():
            for feature, transport_data in feature_data.items():
                feature_key = _feature_to_data_type_key(feature)
                if feature_key not in data_types:
                    data_types[feature_key] = {"rest": False, "ws": False}

                for transport, status in transport_data.items():
                    if status.supported:
                        transport_str = "rest" if transport == TransportKind.REST else "ws"
                        data_types[feature_key][transport_str] = True

    return ExchangeCapability(
        name=exchange_lower,
        display_name=exchange_lower.capitalize(),
        supported_market_types=market_types,
        default_market_type=market_types[0] if market_types else None,
        supported_timeframes=[tf.value for tf in Timeframe],
        data_types=data_types,
        notes=None,
    )


def _feature_to_data_type_key(feature: DataFeature) -> str:
    """Convert DataFeature to data_type key for ExchangeCapability."""
    mapping = {
        DataFeature.OHLCV: "ohlcv",
        DataFeature.HEALTH: "health",
        DataFeature.ORDER_BOOK: "order_book",
        DataFeature.TRADES: "trades",
        DataFeature.HISTORICAL_TRADES: "historical_trades",
        DataFeature.LIQUIDATIONS: "liquidations",
        DataFeature.OPEN_INTEREST: "open_interest",
        DataFeature.FUNDING_RATE: "funding_rates",
        DataFeature.MARK_PRICE: "mark_price",
        DataFeature.SYMBOL_METADATA: "symbol_metadata",
    }
    return mapping.get(feature, feature.value)


def get_all_capabilities() -> dict[str, ExchangeCapability]:
    """Get capability information for all supported exchanges.

    Returns:
        Dictionary mapping exchange names to their capabilities
    """
    _ensure_registry_initialized()
    result: dict[str, ExchangeCapability] = {}
    for exchange in _CAPABILITY_REGISTRY:
        capability = get_exchange_capability(exchange)
        if capability:
            result[exchange] = capability
    return result


def get_supported_market_types(exchange: str) -> list[str] | None:
    """Get supported market types for a specific exchange.

    Args:
        exchange: Exchange name (e.g., "binance", "coinbase")

    Returns:
        List of supported market types (e.g., ["spot", "futures"]) or None if exchange not found
    """
    capability = get_exchange_capability(exchange)
    return capability["supported_market_types"] if capability else None


def get_supported_timeframes(exchange: str | None = None) -> list[str]:
    """Get supported timeframes.

    Args:
        exchange: Optional exchange name. If None, returns all timeframes from enum.
                 If provided, returns exchange-specific timeframes (currently same for all).

    Returns:
        List of timeframe strings (e.g., ["1m", "3m", "5m", ...])
    """
    # Currently all exchanges support the full Timeframe enum
    # This could be made exchange-specific in the future if needed
    return [tf.value for tf in Timeframe]


def get_supported_data_types(exchange: str) -> dict[str, dict[str, bool]] | None:
    """Get supported data types for a specific exchange.

    Args:
        exchange: Exchange name (e.g., "binance", "coinbase")

    Returns:
        Dictionary mapping data type names to REST/WS support, or None if exchange not found.
        Example: {"ohlcv": {"rest": True, "ws": True}, ...}
    """
    capability = get_exchange_capability(exchange)
    return capability["data_types"] if capability else None


def get_all_supported_market_types() -> list[str]:
    """Get all market types supported by any exchange.

    Returns:
        List of unique market types (e.g., ["spot", "futures"])
    """
    _ensure_registry_initialized()
    all_types = set()
    for exchange_data in _CAPABILITY_REGISTRY.values():
        all_types.update(mt.value for mt in exchange_data)
    return sorted(all_types)


def is_exchange_supported(exchange: str) -> bool:
    """Check if an exchange is supported by laakhay-data.

    Args:
        exchange: Exchange name (e.g., "binance", "bybit")

    Returns:
        True if exchange is supported, False otherwise
    """
    _ensure_registry_initialized()
    return exchange.lower() in _CAPABILITY_REGISTRY


def supports_market_type(exchange: str, market_type: str) -> bool:
    """Check if an exchange supports a specific market type.

    Args:
        exchange: Exchange name (e.g., "binance", "coinbase")
        market_type: Market type (e.g., "spot", "futures")

    Returns:
        True if exchange supports the market type, False otherwise
    """
    capability = get_exchange_capability(exchange)
    if not capability:
        return False
    return market_type.lower() in capability["supported_market_types"]


def supports_data_type(exchange: str, data_type: str, method: str = "rest") -> bool:
    """Check if an exchange supports a specific data type via REST or WebSocket.

    Args:
        exchange: Exchange name (e.g., "binance", "coinbase")
        data_type: Data type (e.g., "ohlcv", "liquidations", "funding_rates")
        method: Method to check ("rest" or "ws")

    Returns:
        True if exchange supports the data type via the specified method, False otherwise
    """
    capability = get_exchange_capability(exchange)
    if not capability:
        return False
    data_types = capability["data_types"]
    if data_type not in data_types:
        return False
    return data_types[data_type].get(method, False)


# Architecture: Hierarchical capability registry
# Structure: exchange -> market_type -> instrument_type -> feature -> transport -> CapabilityStatus
# This nested structure allows O(1) lookups at each level while supporting fine-grained queries
# Built from code discovery via _build_capability_registry_from_discovery()
_CAPABILITY_REGISTRY: dict[
    str,
    dict[
        MarketType, dict[InstrumentType, dict[DataFeature, dict[TransportKind, CapabilityStatus]]]
    ],
] = {}


# _build_capability_registry() removed - capabilities are now discovered from code
# Use _build_capability_registry_from_discovery() instead


def _build_capability_registry_from_discovery() -> None:
    """Build the hierarchical capability registry from code discovery.

    This function uses CapabilityDiscovery to inspect provider code and
    build capabilities from actual implementations instead of static metadata.

    Architecture:
        This function discovers capabilities by:
        1. Inspecting provider registrations (feature handlers)
        2. Inspecting endpoint modules (rest/endpoints.py, ws/endpoints.py)
        3. Building hierarchical registry from discovered capabilities

    Design Decision:
        Discovery-based building derives capabilities from actual code,
        eliminating the need for manual EXCHANGE_METADATA maintenance.
        This ensures capabilities always match implementation.
    """
    global _CAPABILITY_REGISTRY

    # Lazy import to avoid circular dependency
    from .discovery import CapabilityDiscovery

    discovery = CapabilityDiscovery()
    discovered = discovery.discover_all()

    # Build hierarchical registry from discovered capabilities
    for cap in discovered:
        exchange_name = cap.exchange
        market_type = cap.market_type
        instrument_type = cap.instrument_type
        feature = cap.feature
        transport = cap.transport

        # Initialize exchange registry if needed
        if exchange_name not in _CAPABILITY_REGISTRY:
            _CAPABILITY_REGISTRY[exchange_name] = {}

        # Initialize market type registry if needed
        if market_type not in _CAPABILITY_REGISTRY[exchange_name]:
            _CAPABILITY_REGISTRY[exchange_name][market_type] = {}

        # Initialize instrument type registry if needed
        if instrument_type not in _CAPABILITY_REGISTRY[exchange_name][market_type]:
            _CAPABILITY_REGISTRY[exchange_name][market_type][instrument_type] = {}

        # Initialize feature registry if needed
        if feature not in _CAPABILITY_REGISTRY[exchange_name][market_type][instrument_type]:
            _CAPABILITY_REGISTRY[exchange_name][market_type][instrument_type][feature] = {}

        # Build stream metadata
        stream_metadata: dict[str, Any] = {}
        if transport == TransportKind.WS:
            # Extract stream metadata from constraints
            if "max_streams" in cap.constraints:
                stream_metadata["max_streams"] = cap.constraints["max_streams"]
            if "combined_streams" in cap.constraints:
                stream_metadata["combined_supported"] = cap.constraints["combined_streams"]

            # Add feature-specific metadata
            if feature == DataFeature.OHLCV:
                stream_metadata["symbol_scope"] = "symbol"
                stream_metadata["timeframe_options"] = [tf.value for tf in Timeframe]
            elif feature == DataFeature.TRADES:
                stream_metadata["symbol_scope"] = "symbol"
            elif feature == DataFeature.LIQUIDATIONS:
                stream_metadata["symbol_scope"] = (
                    "global" if exchange_name == "binance" else "symbol"
                )
            elif feature == DataFeature.ORDER_BOOK:
                stream_metadata["symbol_scope"] = "symbol"
            else:
                stream_metadata["symbol_scope"] = "symbol"

        # Validate feature/instrument compatibility
        reason: str | None = None
        supported = True
        if feature == DataFeature.LIQUIDATIONS and instrument_type == InstrumentType.SPOT:
            supported = False
            reason = "Liquidations are only available for futures/perpetual markets"
        elif feature in (
            DataFeature.OPEN_INTEREST,
            DataFeature.FUNDING_RATE,
            DataFeature.MARK_PRICE,
        ):
            if instrument_type == InstrumentType.SPOT:
                supported = False
                reason = f"{feature.value} is only available for futures/perpetual markets"

        status = CapabilityStatus(
            supported=supported,
            reason=reason,
            constraints=cap.constraints.copy(),
            recommendations=[],
            stream_metadata=stream_metadata,
        )

        _CAPABILITY_REGISTRY[exchange_name][market_type][instrument_type][feature][transport] = (
            status
        )


# Architecture: Lazy registry initialization
# Registry is built on first access, allowing discovery to work after providers are registered
# This enables code-driven capability discovery without requiring providers at import time
_REGISTRY_INITIALIZED = False


def _ensure_registry_initialized() -> None:
    """Ensure the capability registry is initialized.

    This function lazily initializes the registry from discovery if providers
    are registered, otherwise builds an empty registry.

    Architecture:
        Lazy initialization allows the registry to be built after providers
        are registered, enabling code-driven capability discovery. The registry
        is built on first access rather than at import time.
    """
    global _CAPABILITY_REGISTRY, _REGISTRY_INITIALIZED

    if _REGISTRY_INITIALIZED:
        return

    # Try to build from discovery first (code-driven)
    try:
        from ..runtime.provider_registry import get_provider_registry

        registry = get_provider_registry()
        # Check if any providers are registered
        if registry.list_exchanges():
            _build_capability_registry_from_discovery()
            _REGISTRY_INITIALIZED = True
            return
    except Exception:
        # If discovery fails, continue to build empty registry
        pass

    # If no providers registered or discovery fails, build empty registry
    # This allows the module to import even if providers aren't registered yet
    _CAPABILITY_REGISTRY = {}
    _REGISTRY_INITIALIZED = True


def rebuild_registry_from_discovery() -> None:
    """Rebuild the capability registry from code discovery.

    This function should be called after providers are registered to rebuild
    the registry from actual code instead of static metadata.

    Architecture:
        This allows the registry to be rebuilt after providers are registered,
        enabling code-driven capability discovery. The registry is cleared and
        rebuilt from discovery results.
    """
    global _CAPABILITY_REGISTRY, _REGISTRY_INITIALIZED

    _CAPABILITY_REGISTRY.clear()
    _build_capability_registry_from_discovery()
    _REGISTRY_INITIALIZED = True


def supports(
    feature: DataFeature,
    transport: TransportKind,
    *,
    exchange: str,
    market_type: MarketType,
    instrument_type: InstrumentType | None = None,
    stream_variant: str | None = None,
) -> CapabilityStatus:
    """Check if a capability is supported.

    Args:
        feature: The data feature to check
        transport: The transport mechanism
        exchange: Exchange name
        market_type: Market type (spot/futures)
        instrument_type: Instrument type (spot/perpetual/future/etc.)
        stream_variant: Optional stream variant (e.g., "symbol", "global", "combo:trades+liquidations")

    Returns:
        CapabilityStatus indicating support status and metadata
    """
    _ensure_registry_initialized()
    # Architecture: Hierarchical lookup with early exit on unsupported levels
    # Each level is O(1) dictionary lookup, total complexity is O(1)
    exchange_lower = exchange.lower()
    if exchange_lower not in _CAPABILITY_REGISTRY:
        # Architecture: Exchange not registered - return unsupported status
        return CapabilityStatus(
            supported=False,
            reason=f"Exchange '{exchange}' not found in capability registry",
        )

    exchange_data = _CAPABILITY_REGISTRY[exchange_lower]
    if market_type not in exchange_data:
        # Architecture: Market type not supported for this exchange
        return CapabilityStatus(
            supported=False,
            reason=f"Market type '{market_type.value}' not supported for exchange '{exchange}'",
        )

    instrument_data = exchange_data[market_type]
    if instrument_type is not None and instrument_type not in instrument_data:
        # Architecture: Specific instrument type not supported
        return CapabilityStatus(
            supported=False,
            reason=f"Instrument type '{instrument_type.value}' not supported for {exchange}/{market_type.value}",
        )
    # Architecture: Auto-select instrument type if not specified
    # For SPOT markets, selects SPOT. For FUTURES, selects first available (PERPETUAL or FUTURE)
    if instrument_type is None:
        if not instrument_data:
            return CapabilityStatus(
                supported=False,
                reason=f"No instrument types available for {exchange}/{market_type.value}",
            )
        instrument_type = next(iter(instrument_data.keys()))

    feature_data = instrument_data[instrument_type]
    if feature not in feature_data:
        # Architecture: Feature not supported for this exchange/market/instrument combo
        return CapabilityStatus(
            supported=False,
            reason=f"Feature '{feature.value}' not supported for {exchange}/{market_type.value}/{instrument_type.value}",
        )

    transport_data = feature_data[feature]
    if transport not in transport_data:
        # Architecture: Transport not supported for this feature
        return CapabilityStatus(
            supported=False,
            reason=f"Transport '{transport.value}' not supported for {feature.value} on {exchange}/{market_type.value}/{instrument_type.value}",
        )

    # Architecture: Return capability status with full metadata
    # Status includes support flag, reason, constraints, and stream metadata
    return transport_data[transport]


def describe_exchange(exchange: str) -> ExchangeCapability | None:
    """Describe all capabilities for an exchange.

    Args:
        exchange: Exchange name

    Returns:
        ExchangeCapability dict if exchange exists, None otherwise
    """
    return get_exchange_capability(exchange)


def list_features(
    exchange: str, market_type: MarketType, instrument_type: InstrumentType
) -> dict[DataFeature, dict[TransportKind, CapabilityStatus]]:
    """List all features supported for a given exchange/market/instrument combination.

    Args:
        exchange: Exchange name
        market_type: Market type
        instrument_type: Instrument type

    Returns:
        Dictionary mapping features to transport capabilities
    """
    exchange_lower = exchange.lower()
    if exchange_lower not in _CAPABILITY_REGISTRY:
        return {}

    exchange_data = _CAPABILITY_REGISTRY[exchange_lower]
    if market_type not in exchange_data:
        return {}

    instrument_data = exchange_data[market_type]
    if instrument_type not in instrument_data:
        return {}

    return instrument_data[instrument_type].copy()
