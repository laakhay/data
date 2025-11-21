"""Coinbase WebSocket endpoint registry.

This module discovers and exports all endpoint specifications and adapters
from the modular endpoint structure.
"""

from __future__ import annotations

from laakhay.data.core import MarketType
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec

# Import all endpoint modules
from .ohlcv import Adapter as OHLCVAdapter
from .ohlcv import build_spec as build_ohlcv_spec
from .order_book import Adapter as OrderBookAdapter
from .order_book import build_spec as build_order_book_spec
from .trades import Adapter as TradesAdapter
from .trades import build_spec as build_trades_spec


def get_endpoint_spec(endpoint_id: str, market_type: MarketType) -> WSEndpointSpec | None:
    """Get endpoint specification by ID and market type.

    Args:
        endpoint_id: Endpoint identifier (e.g., "ohlcv", "trades")
        market_type: Market type (only SPOT supported for Coinbase)

    Returns:
        WSEndpointSpec if found, None otherwise
    """
    spec_builders = {
        "ohlcv": build_ohlcv_spec,
        "trades": build_trades_spec,
        "order_book": build_order_book_spec,
    }
    builder = spec_builders.get(endpoint_id)
    if builder is None:
        return None
    try:
        return builder(market_type)
    except ValueError:
        return None


def get_endpoint_adapter(endpoint_id: str) -> type[MessageAdapter] | None:
    """Get endpoint adapter class by ID.

    Args:
        endpoint_id: Endpoint identifier (e.g., "ohlcv", "trades")

    Returns:
        Adapter class if found, None otherwise
    """
    adapters = {
        "ohlcv": OHLCVAdapter,
        "trades": TradesAdapter,
        "order_book": OrderBookAdapter,
    }
    return adapters.get(endpoint_id)


def list_endpoints() -> list[str]:
    """List all available endpoint IDs.

    Returns:
        List of endpoint identifiers
    """
    return ["ohlcv", "trades", "order_book"]


__all__ = [
    "get_endpoint_spec",
    "get_endpoint_adapter",
    "list_endpoints",
    # Export all spec builders and adapters for discovery
    "build_ohlcv_spec",
    "OHLCVAdapter",
    "build_trades_spec",
    "TradesAdapter",
    "build_order_book_spec",
    "OrderBookAdapter",
]
