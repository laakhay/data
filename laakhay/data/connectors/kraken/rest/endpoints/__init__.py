"""Kraken REST endpoint registry.

This module discovers and exports all endpoint specifications and adapters
from the modular endpoint structure.
"""

from __future__ import annotations

from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec

# Import all endpoint modules
from .common.exchange_info import SPEC as ExchangeInfoSpec  # noqa: N811
from .common.exchange_info import Adapter as ExchangeInfoAdapter
from .common.historical_trades import (
    SPEC as HistoricalTradesSpec,  # noqa: N811
)
from .common.historical_trades import (
    Adapter as HistoricalTradesAdapter,
)
from .common.ohlcv import SPEC as OHLCVSpec  # noqa: N811
from .common.ohlcv import Adapter as OHLCVAdapter
from .common.order_book import SPEC as OrderBookSpec  # noqa: N811
from .common.order_book import Adapter as OrderBookAdapter
from .common.trades import SPEC as TradesSpec  # noqa: N811
from .common.trades import Adapter as TradesAdapter
from .futures.funding_rate import SPEC as FundingRateSpec  # noqa: N811
from .futures.funding_rate import Adapter as FundingRateAdapter
from .futures.open_interest_current import (
    SPEC as OpenInterestCurrentSpec,  # noqa: N811
)
from .futures.open_interest_current import (
    Adapter as OpenInterestCurrentAdapter,
)
from .futures.open_interest_hist import (
    SPEC as OpenInterestHistSpec,  # noqa: N811
)
from .futures.open_interest_hist import (
    Adapter as OpenInterestHistAdapter,
)

# Registry mapping endpoint IDs to specs and adapters
_ENDPOINT_REGISTRY: dict[str, tuple[RestEndpointSpec, type[ResponseAdapter]]] = {
    "ohlcv": (OHLCVSpec, OHLCVAdapter),
    "exchange_info": (ExchangeInfoSpec, ExchangeInfoAdapter),
    "order_book": (OrderBookSpec, OrderBookAdapter),
    "recent_trades": (TradesSpec, TradesAdapter),
    "historical_trades": (HistoricalTradesSpec, HistoricalTradesAdapter),
    "open_interest_current": (OpenInterestCurrentSpec, OpenInterestCurrentAdapter),
    "open_interest_hist": (OpenInterestHistSpec, OpenInterestHistAdapter),
    "funding_rate": (FundingRateSpec, FundingRateAdapter),
}


def get_endpoint_spec(endpoint_id: str) -> RestEndpointSpec | None:
    """Get endpoint specification by ID.

    Args:
        endpoint_id: Endpoint identifier (e.g., "ohlcv", "order_book")

    Returns:
        RestEndpointSpec if found, None otherwise
    """
    entry = _ENDPOINT_REGISTRY.get(endpoint_id)
    return entry[0] if entry else None


def get_endpoint_adapter(endpoint_id: str) -> type[ResponseAdapter] | None:
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


# Legacy compatibility functions for tests
def candles_spec() -> RestEndpointSpec:
    """Legacy function for test compatibility."""
    return OHLCVSpec


def exchange_info_spec() -> RestEndpointSpec:
    """Legacy function for test compatibility."""
    return ExchangeInfoSpec


def order_book_spec() -> RestEndpointSpec:
    """Legacy function for test compatibility."""
    return OrderBookSpec


def recent_trades_spec() -> RestEndpointSpec:
    """Legacy function for test compatibility."""
    return TradesSpec


def historical_trades_spec() -> RestEndpointSpec:
    """Legacy function for test compatibility."""
    return HistoricalTradesSpec


def open_interest_current_spec() -> RestEndpointSpec:
    """Legacy function for test compatibility."""
    return OpenInterestCurrentSpec


def open_interest_hist_spec() -> RestEndpointSpec:
    """Legacy function for test compatibility."""
    return OpenInterestHistSpec


def funding_rate_spec() -> RestEndpointSpec:
    """Legacy function for test compatibility."""
    return FundingRateSpec


# Legacy adapter exports for test compatibility
CandlesResponseAdapter = OHLCVAdapter
ExchangeInfoSymbolsAdapter = ExchangeInfoAdapter
OrderBookResponseAdapter = OrderBookAdapter
RecentTradesAdapter = TradesAdapter
FundingRateAdapter = FundingRateAdapter
OpenInterestCurrentAdapter = OpenInterestCurrentAdapter
OpenInterestHistAdapter = OpenInterestHistAdapter


# Helper function for extracting result (used by adapters)
def _extract_result(response: Any, market_type: MarketType) -> Any:
    """Extract result from Kraken API response.

    Args:
        response: Raw API response
        market_type: Market type (spot or futures)

    Returns:
        Extracted result data
    """
    if market_type == MarketType.FUTURES:
        # Futures format: {"result": "ok", "serverTime": ..., "data": {...}}
        if isinstance(response, dict) and "result" in response:
            return response.get("data", response)
        return response
    else:
        # Spot format: {"error": [], "result": {...}}
        if isinstance(response, dict) and "result" in response:
            return response["result"]
        return response


__all__ = [
    "get_endpoint_spec",
    "get_endpoint_adapter",
    "list_endpoints",
    # Export all specs and adapters for discovery
    "OHLCVSpec",
    "OHLCVAdapter",
    "ExchangeInfoSpec",
    "ExchangeInfoAdapter",
    "OrderBookSpec",
    "OrderBookAdapter",
    "TradesSpec",
    "TradesAdapter",
    "HistoricalTradesSpec",
    "HistoricalTradesAdapter",
    "OpenInterestCurrentSpec",
    "OpenInterestCurrentAdapter",
    "OpenInterestHistSpec",
    "OpenInterestHistAdapter",
    "FundingRateSpec",
    "FundingRateAdapter",
    # Legacy compatibility exports
    "candles_spec",
    "exchange_info_spec",
    "order_book_spec",
    "recent_trades_spec",
    "historical_trades_spec",
    "open_interest_current_spec",
    "open_interest_hist_spec",
    "funding_rate_spec",
    "CandlesResponseAdapter",
    "ExchangeInfoSymbolsAdapter",
    "OrderBookResponseAdapter",
    "RecentTradesAdapter",
    "FundingRateAdapter",
    "OpenInterestCurrentAdapter",
    "OpenInterestHistAdapter",
    "_extract_result",
]
