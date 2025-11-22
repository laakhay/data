"""Binance WebSocket endpoint registry.

This module discovers and exports all WebSocket endpoint specifications and adapters
from the modular endpoint structure.
"""

from __future__ import annotations

from laakhay.data.core import MarketType, MarketVariant
from laakhay.data.runtime.ws import MessageAdapter, WSEndpointSpec

# Import all endpoint modules from common folder (available for spot and futures)
from .common.ohlcv import Adapter as OHLCVAdapter
from .common.ohlcv import build_spec as build_ohlcv_spec
from .common.order_book import Adapter as OrderBookAdapter
from .common.order_book import build_spec as build_order_book_spec
from .common.trades import Adapter as TradesAdapter
from .common.trades import build_spec as build_trades_spec

# Import futures-only endpoints
from .futures.liquidations import Adapter as LiquidationsAdapter
from .futures.liquidations import build_spec as build_liquidations_spec
from .futures.mark_price import Adapter as MarkPriceAdapter
from .futures.mark_price import build_spec as build_mark_price_spec
from .futures.open_interest import Adapter as OpenInterestAdapter
from .futures.open_interest import build_spec as build_open_interest_spec

# Registry mapping endpoint IDs to spec builders and adapters
_ENDPOINT_REGISTRY: dict[str, tuple[callable, type[MessageAdapter]]] = {
    "ohlcv": (build_ohlcv_spec, OHLCVAdapter),
    "order_book": (build_order_book_spec, OrderBookAdapter),
    "trades": (build_trades_spec, TradesAdapter),
    "open_interest": (build_open_interest_spec, OpenInterestAdapter),
    "mark_price": (build_mark_price_spec, MarkPriceAdapter),
    "liquidations": (build_liquidations_spec, LiquidationsAdapter),
}


def get_endpoint_spec(
    endpoint_id: str, market_type: MarketType, market_variant: MarketVariant | None = None
) -> WSEndpointSpec | None:
    """Get endpoint specification by ID.

    Args:
        endpoint_id: Endpoint identifier (e.g., "ohlcv", "order_book")
        market_type: Market type (spot or futures)
        market_variant: Optional market variant (for FUTURES: linear_perp or inverse_perp)

    Returns:
        WSEndpointSpec if found, None otherwise
    """
    entry = _ENDPOINT_REGISTRY.get(endpoint_id)
    if entry is None:
        return None
    spec_builder, _ = entry
    try:
        # Pass market_variant to builders that support it, fallback for older builders
        import inspect

        sig = inspect.signature(spec_builder)
        if "market_variant" in sig.parameters:
            return spec_builder(market_type, market_variant)
        return spec_builder(market_type)
    except (ValueError, TypeError):
        return None


def get_endpoint_adapter(endpoint_id: str) -> type[MessageAdapter] | None:
    """Get endpoint adapter class by ID.

    Args:
        endpoint_id: Endpoint identifier (e.g., "ohlcv", "order_book")

    Returns:
        Adapter class if found, None otherwise
    """
    entry = _ENDPOINT_REGISTRY.get(endpoint_id)
    return entry[1] if entry else None


def list_endpoints() -> list[str]:
    """List all available endpoint IDs.

    Returns:
        List of endpoint identifiers
    """
    return list(_ENDPOINT_REGISTRY.keys())


__all__ = [
    "get_endpoint_spec",
    "get_endpoint_adapter",
    "list_endpoints",
]
