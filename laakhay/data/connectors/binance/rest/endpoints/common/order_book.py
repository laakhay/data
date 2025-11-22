"""Binance order book endpoint definition and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.binance.config import get_api_path_prefix
from laakhay.data.core import MarketType
from laakhay.data.models import OrderBook
from laakhay.data.runtime.chunking import WeightPolicy
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def build_path(params: dict[str, Any]) -> str:
    """Build the depth path based on market type."""
    market: MarketType = params["market_type"]
    prefix = get_api_path_prefix(market, params.get("market_variant"))
    return f"{prefix}/depth"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for depth endpoint."""
    limit = params.get("limit", 100)
    max_limit = 500
    return {
        "symbol": params["symbol"].upper(),
        "limit": min(int(limit), max_limit),
    }


SPOT_ORDER_BOOK_WEIGHT_POLICY = WeightPolicy(static_weight=25)
FUTURES_ORDER_BOOK_WEIGHT_POLICY = WeightPolicy(static_weight=20)


def _get_weight_policy(params: dict[str, Any]) -> WeightPolicy:
    """Get weight policy for order book based on market type.

    Args:
        params: Request parameters containing market_type

    Returns:
        WeightPolicy for the market type

    """
    market_type: MarketType = params.get("market_type", MarketType.SPOT)
    if market_type == MarketType.SPOT:
        return SPOT_ORDER_BOOK_WEIGHT_POLICY
    return FUTURES_ORDER_BOOK_WEIGHT_POLICY


# Endpoint specification
SPEC = RestEndpointSpec(
    id="order_book",
    method="GET",
    build_path=build_path,
    build_query=build_query,
    weight_policy=_get_weight_policy,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing Binance depth response into OrderBook."""

    def parse(self, response: Any, params: dict[str, Any]) -> OrderBook:
        """Parse Binance depth response.

        Args:
            response: Raw response from Binance API
            params: Request parameters containing symbol

        Returns:
            OrderBook object with bids and asks

        """
        symbol = params["symbol"].upper()
        bids = [(Decimal(str(p)), Decimal(str(q))) for p, q in response.get("bids", [])]
        asks = [(Decimal(str(p)), Decimal(str(q))) for p, q in response.get("asks", [])]
        return OrderBook(
            symbol=symbol,
            last_update_id=response.get("lastUpdateId", 0),
            bids=bids,
            asks=asks,
            timestamp=datetime.now(UTC),
        )
