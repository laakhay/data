"""Capabilities API for discovering supported exchanges, market types, timeframes, and data types.

This module provides a consistent API for querying laakhay-data capabilities without
instantiating providers. All metadata is static and based on the library's supported features.
"""

from typing import TypedDict

from .enums import MarketType, Timeframe

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
    return sorted(list(all_types))


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

