"""Capabilities API for discovering supported exchanges, market types, timeframes, and data types.

This module provides a consistent API for querying laakhay-data capabilities without
instantiating providers. All metadata is static and based on the library's supported features.

Architecture:
    This module implements a hierarchical capability registry that maps:
    Exchange → MarketType → InstrumentType → DataFeature → TransportKind → CapabilityStatus

    The registry is built from EXCHANGE_METADATA (flat structure) into a hierarchical
    structure that includes instrument types and stream metadata.

Design Decisions:
    - Static registry: Fast lookups, no provider instantiation needed
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
from typing import Any, Literal, TypedDict

from .enums import DataFeature, InstrumentType, MarketType, Timeframe, TransportKind


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
    source: Literal["static", "runtime"] = "static"
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


# Exchange metadata registry
# Based on actual provider implementations and README.md
EXCHANGE_METADATA: dict[str, ExchangeCapability] = {
    "binance": {
        "name": "binance",
        "display_name": "Binance",
        "supported_market_types": ["spot", "futures"],
        "default_market_type": "spot",
        "supported_timeframes": [tf.value for tf in Timeframe],
        "data_types": {
            "ohlcv": {"rest": True, "ws": True},
            "health": {"rest": True, "ws": False},
            "order_book": {"rest": True, "ws": True},
            "trades": {"rest": True, "ws": True},
            "liquidations": {"rest": False, "ws": True},
            "open_interest": {"rest": True, "ws": True},
            "funding_rates": {"rest": True, "ws": True},
            "mark_price": {"rest": False, "ws": True},
            "symbol_metadata": {"rest": True, "ws": False},
        },
        "notes": None,
    },
    "bybit": {
        "name": "bybit",
        "display_name": "Bybit",
        "supported_market_types": ["spot", "futures"],
        "default_market_type": "spot",
        "supported_timeframes": [tf.value for tf in Timeframe],
        "data_types": {
            "ohlcv": {"rest": True, "ws": True},
            "order_book": {"rest": True, "ws": True},
            "trades": {"rest": True, "ws": True},
            "liquidations": {"rest": False, "ws": True},
            "open_interest": {"rest": True, "ws": True},
            "funding_rates": {"rest": True, "ws": True},
            "mark_price": {"rest": False, "ws": True},
            "symbol_metadata": {"rest": True, "ws": False},
        },
        "notes": None,
    },
    "okx": {
        "name": "okx",
        "display_name": "OKX",
        "supported_market_types": ["spot", "futures"],
        "default_market_type": "spot",
        "supported_timeframes": [tf.value for tf in Timeframe],
        "data_types": {
            "ohlcv": {"rest": True, "ws": True},
            "order_book": {"rest": True, "ws": True},
            "trades": {"rest": True, "ws": True},
            "liquidations": {"rest": False, "ws": True},
            "open_interest": {"rest": True, "ws": True},
            "funding_rates": {"rest": True, "ws": True},
            "mark_price": {"rest": False, "ws": True},
            "symbol_metadata": {"rest": True, "ws": False},
        },
        "notes": None,
    },
    "hyperliquid": {
        "name": "hyperliquid",
        "display_name": "Hyperliquid",
        "supported_market_types": ["futures"],  # Primarily futures-focused
        "default_market_type": "futures",
        "supported_timeframes": [tf.value for tf in Timeframe],
        "data_types": {
            "ohlcv": {"rest": True, "ws": True},
            "order_book": {"rest": True, "ws": True},
            "trades": {"rest": True, "ws": True},
            "liquidations": {"rest": False, "ws": True},
            "open_interest": {"rest": True, "ws": True},
            "funding_rates": {"rest": True, "ws": True},
            "mark_price": {"rest": False, "ws": True},
            "symbol_metadata": {"rest": True, "ws": False},
        },
        "notes": "Futures-focused exchange. Library supports both spot and futures, but futures is primary.",
    },
    "kraken": {
        "name": "kraken",
        "display_name": "Kraken",
        "supported_market_types": ["spot", "futures"],
        "default_market_type": "spot",
        "supported_timeframes": [tf.value for tf in Timeframe],
        "data_types": {
            "ohlcv": {"rest": True, "ws": True},
            "order_book": {"rest": True, "ws": True},
            "trades": {"rest": True, "ws": True},
            "liquidations": {"rest": False, "ws": True},
            "open_interest": {"rest": True, "ws": True},
            "funding_rates": {"rest": True, "ws": True},
            "mark_price": {"rest": False, "ws": True},
            "symbol_metadata": {"rest": True, "ws": False},
        },
        "notes": None,
    },
    "coinbase": {
        "name": "coinbase",
        "display_name": "Coinbase",
        "supported_market_types": ["spot"],  # Coinbase Advanced Trade API only supports Spot
        "default_market_type": "spot",
        "supported_timeframes": [tf.value for tf in Timeframe],
        "data_types": {
            "ohlcv": {"rest": True, "ws": True},
            "order_book": {"rest": True, "ws": True},
            "trades": {"rest": True, "ws": True},
            "liquidations": {"rest": False, "ws": False},  # Not supported (spot only)
            "open_interest": {"rest": False, "ws": False},  # Not supported (spot only)
            "funding_rates": {"rest": False, "ws": False},  # Not supported (spot only)
            "mark_price": {"rest": False, "ws": False},  # Not supported (spot only)
            "symbol_metadata": {"rest": True, "ws": False},
        },
        "notes": "Coinbase Advanced Trade API only supports Spot markets. Futures features are not available.",
    },
}


def get_all_exchanges() -> list[str]:
    """Get list of all supported exchange names.

    Returns:
        List of exchange names (e.g., ["binance", "bybit", "okx", ...])
    """
    return list(EXCHANGE_METADATA.keys())


def get_exchange_capability(exchange: str) -> ExchangeCapability | None:
    """Get capability information for a specific exchange.

    Args:
        exchange: Exchange name (e.g., "binance", "bybit")

    Returns:
        ExchangeCapability dict if exchange exists, None otherwise
    """
    return EXCHANGE_METADATA.get(exchange.lower())


def get_all_capabilities() -> dict[str, ExchangeCapability]:
    """Get capability information for all supported exchanges.

    Returns:
        Dictionary mapping exchange names to their capabilities
    """
    return EXCHANGE_METADATA.copy()


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
    all_types = set()
    for capability in EXCHANGE_METADATA.values():
        all_types.update(capability["supported_market_types"])
    return sorted(all_types)


def is_exchange_supported(exchange: str) -> bool:
    """Check if an exchange is supported by laakhay-data.

    Args:
        exchange: Exchange name (e.g., "binance", "bybit")

    Returns:
        True if exchange is supported, False otherwise
    """
    return exchange.lower() in EXCHANGE_METADATA


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
# Built from EXCHANGE_METADATA at module import time via _build_capability_registry()
_CAPABILITY_REGISTRY: dict[
    str,
    dict[
        MarketType, dict[InstrumentType, dict[DataFeature, dict[TransportKind, CapabilityStatus]]]
    ],
] = {}


def _build_capability_registry() -> None:
    """Build the hierarchical capability registry from EXCHANGE_METADATA.

    This function converts the flat EXCHANGE_METADATA structure into the new
    hierarchical format that includes instrument types and stream descriptors.

    Architecture:
        This function is called at module import time to build the hierarchical registry.
        It transforms the flat EXCHANGE_METADATA into a nested structure that supports:
        - Instrument type differentiation (SPOT, PERPETUAL, FUTURE)
        - Stream metadata (symbol scope, combo support, constraints)
        - Feature/instrument validation (e.g., liquidations only for futures)

    Design Decision:
        Building at import time trades memory for lookup speed. The registry is
        read-only after initialization, making it safe for concurrent access.
    """
    global _CAPABILITY_REGISTRY

    # Architecture: Map flat data_types keys to DataFeature enum
    # This allows EXCHANGE_METADATA to use string keys while registry uses enums
    feature_map = {
        "ohlcv": DataFeature.OHLCV,
        "order_book": DataFeature.ORDER_BOOK,
        "trades": DataFeature.TRADES,
        "liquidations": DataFeature.LIQUIDATIONS,
        "open_interest": DataFeature.OPEN_INTEREST,
        "funding_rates": DataFeature.FUNDING_RATE,
        "mark_price": DataFeature.MARK_PRICE,
        "symbol_metadata": DataFeature.SYMBOL_METADATA,
    }

    # Transport mapping
    transport_map = {"rest": TransportKind.REST, "ws": TransportKind.WS}

    for exchange_name, capability in EXCHANGE_METADATA.items():
        exchange_registry: dict[
            MarketType,
            dict[InstrumentType, dict[DataFeature, dict[TransportKind, CapabilityStatus]]],
        ] = {}

        for market_type_str in capability["supported_market_types"]:
            market_type = MarketType(market_type_str)
            instrument_type_map: dict[
                InstrumentType, dict[DataFeature, dict[TransportKind, CapabilityStatus]]
            ] = {}

            # Architecture: Infer instrument types from market type
            # SPOT markets only have SPOT instruments
            # FUTURES markets have both PERPETUAL and FUTURE instruments
            # This allows capability queries to distinguish between perpetuals and futures
            if market_type == MarketType.SPOT:
                instrument_types = [InstrumentType.SPOT]
            else:  # FUTURES
                instrument_types = [InstrumentType.PERPETUAL, InstrumentType.FUTURE]

            for instrument_type in instrument_types:
                feature_registry: dict[DataFeature, dict[TransportKind, CapabilityStatus]] = {}

                for data_type_key, transport_dict in capability["data_types"].items():
                    feature = feature_map.get(data_type_key)
                    if not feature:
                        continue

                    transport_status: dict[TransportKind, CapabilityStatus] = {}

                    for transport_str, supported in transport_dict.items():
                        transport = transport_map.get(transport_str)
                        if not transport:
                            continue

                        # Architecture: Validate feature/instrument compatibility
                        # Some features are only available for specific instrument types
                        # This enforces logical constraints (e.g., liquidations only for futures)
                        if (
                            feature == DataFeature.LIQUIDATIONS
                            and instrument_type == InstrumentType.SPOT
                        ):
                            # Liquidations don't exist in spot markets
                            supported = False
                            reason = "Liquidations are only available for futures/perpetual markets"
                        elif feature in (
                            DataFeature.OPEN_INTEREST,
                            DataFeature.FUNDING_RATE,
                            DataFeature.MARK_PRICE,
                        ):
                            # Futures-specific features
                            if instrument_type == InstrumentType.SPOT:
                                supported = False
                                reason = f"{feature.value} is only available for futures/perpetual markets"
                            else:
                                reason = None
                        else:
                            reason = None

                        # Architecture: Build stream metadata for WebSocket features
                        # Stream metadata includes symbol scope, combo support, and constraints
                        # This information helps users understand streaming capabilities
                        stream_metadata: dict[str, Any] = {}
                        if feature == DataFeature.OHLCV:
                            stream_metadata["symbol_scope"] = "symbol"
                            stream_metadata["timeframe_options"] = [tf.value for tf in Timeframe]
                            stream_metadata["combo"] = []  # OHLCV doesn't support combos
                            stream_metadata["combo_exchanges"] = []
                        elif feature == DataFeature.TRADES:
                            stream_metadata["symbol_scope"] = "symbol"
                            # Architecture: Combo streams allow multiple features in one connection
                            # Some exchanges support trades+liquidations combo streams
                            if exchange_name in ("binance", "bybit", "okx"):
                                stream_metadata["combo"] = ["trades", "liquidations"]
                                stream_metadata["combo_exchanges"] = ["binance", "bybit", "okx"]
                            else:
                                stream_metadata["combo"] = []
                                stream_metadata["combo_exchanges"] = []
                        elif feature == DataFeature.LIQUIDATIONS:
                            # Architecture: Symbol scope varies by exchange
                            # Binance has global liquidations (all symbols), others are symbol-scoped
                            stream_metadata["symbol_scope"] = (
                                "global" if exchange_name == "binance" else "symbol"
                            )
                            # Liquidations can be combined with trades on some exchanges
                            if exchange_name in ("binance", "bybit", "okx"):
                                stream_metadata["combo"] = ["trades", "liquidations"]
                                stream_metadata["combo_exchanges"] = ["binance", "bybit", "okx"]
                            else:
                                stream_metadata["combo"] = []
                                stream_metadata["combo_exchanges"] = []
                        elif feature == DataFeature.ORDER_BOOK:
                            stream_metadata["symbol_scope"] = "symbol"
                            # Architecture: Constraints provide limits (e.g., max depth)
                            stream_metadata["max_depth"] = 500  # Example constraint
                            stream_metadata["combo"] = []
                            stream_metadata["combo_exchanges"] = []
                        elif feature in (
                            DataFeature.OPEN_INTEREST,
                            DataFeature.FUNDING_RATE,
                            DataFeature.MARK_PRICE,
                        ):
                            # Architecture: Some features can be combined in single stream
                            # Reduces connection overhead when subscribing to multiple features
                            stream_metadata["symbol_scope"] = "symbol"
                            if exchange_name in ("binance", "bybit", "okx"):
                                stream_metadata["combo"] = [
                                    "open_interest",
                                    "funding_rates",
                                    "mark_price",
                                ]
                                stream_metadata["combo_exchanges"] = ["binance", "bybit", "okx"]
                            else:
                                stream_metadata["combo"] = []
                                stream_metadata["combo_exchanges"] = []
                        else:
                            # Architecture: Default metadata for features without special requirements
                            stream_metadata["symbol_scope"] = "symbol"
                            stream_metadata["combo"] = []
                            stream_metadata["combo_exchanges"] = []

                        status = CapabilityStatus(
                            supported=supported,
                            reason=reason,
                            constraints={},
                            recommendations=[],
                            source="static",
                            stream_metadata=stream_metadata,
                        )

                        transport_status[transport] = status

                    if transport_status:
                        feature_registry[feature] = transport_status

                if feature_registry:
                    instrument_type_map[instrument_type] = feature_registry

            if instrument_type_map:
                exchange_registry[market_type] = instrument_type_map

        if exchange_registry:
            _CAPABILITY_REGISTRY[exchange_name] = exchange_registry


# Architecture: Initialize registry at module import time
# This builds the hierarchical structure once, allowing fast O(1) lookups
# Registry is read-only after initialization, safe for concurrent access
_build_capability_registry()


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
    # Architecture: Hierarchical lookup with early exit on unsupported levels
    # Each level is O(1) dictionary lookup, total complexity is O(1)
    exchange_lower = exchange.lower()
    if exchange_lower not in _CAPABILITY_REGISTRY:
        # Architecture: Exchange not registered - return unsupported status
        return CapabilityStatus(
            supported=False,
            reason=f"Exchange '{exchange}' not found in capability registry",
            source="static",
        )

    exchange_data = _CAPABILITY_REGISTRY[exchange_lower]
    if market_type not in exchange_data:
        # Architecture: Market type not supported for this exchange
        return CapabilityStatus(
            supported=False,
            reason=f"Market type '{market_type.value}' not supported for exchange '{exchange}'",
            source="static",
        )

    instrument_data = exchange_data[market_type]
    if instrument_type is not None and instrument_type not in instrument_data:
        # Architecture: Specific instrument type not supported
        return CapabilityStatus(
            supported=False,
            reason=f"Instrument type '{instrument_type.value}' not supported for {exchange}/{market_type.value}",
            source="static",
        )
    # Architecture: Auto-select instrument type if not specified
    # For SPOT markets, selects SPOT. For FUTURES, selects first available (PERPETUAL or FUTURE)
    if instrument_type is None:
        if not instrument_data:
            return CapabilityStatus(
                supported=False,
                reason=f"No instrument types available for {exchange}/{market_type.value}",
                source="static",
            )
        instrument_type = next(iter(instrument_data.keys()))

    feature_data = instrument_data[instrument_type]
    if feature not in feature_data:
        # Architecture: Feature not supported for this exchange/market/instrument combo
        return CapabilityStatus(
            supported=False,
            reason=f"Feature '{feature.value}' not supported for {exchange}/{market_type.value}/{instrument_type.value}",
            source="static",
        )

    transport_data = feature_data[feature]
    if transport not in transport_data:
        # Architecture: Transport not supported for this feature
        return CapabilityStatus(
            supported=False,
            reason=f"Transport '{transport.value}' not supported for {feature.value} on {exchange}/{market_type.value}/{instrument_type.value}",
            source="static",
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
