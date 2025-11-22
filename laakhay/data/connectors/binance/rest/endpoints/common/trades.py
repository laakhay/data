"""Binance recent trades endpoint definition and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.binance.config import get_api_path_prefix
from laakhay.data.core import MarketType
from laakhay.data.models import Trade
from laakhay.data.runtime.chunking import WeightPolicy
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def build_path(params: dict[str, Any]) -> str:
    """Build the trades path based on market type."""
    market: MarketType = params["market_type"]
    prefix = get_api_path_prefix(market, params.get("market_variant"))
    return f"{prefix}/trades"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for trades endpoint."""
    limit = params.get("limit", 500)
    max_limit = 1000
    return {
        "symbol": params["symbol"].upper(),
        "limit": min(int(limit), max_limit),
    }


SPOT_TRADES_WEIGHT_POLICY = WeightPolicy(static_weight=25)
FUTURES_TRADES_WEIGHT_POLICY = WeightPolicy(static_weight=5)


def _get_weight_policy(params: dict[str, Any]) -> WeightPolicy:
    """Get weight policy for recent trades based on market type.

    Args:
        params: Request parameters containing market_type

    Returns:
        WeightPolicy for the market type

    """
    market_type: MarketType = params.get("market_type", MarketType.SPOT)
    if market_type == MarketType.SPOT:
        return SPOT_TRADES_WEIGHT_POLICY
    return FUTURES_TRADES_WEIGHT_POLICY


# Endpoint specification
SPEC = RestEndpointSpec(
    id="recent_trades",
    method="GET",
    build_path=build_path,
    build_query=build_query,
    weight_policy=_get_weight_policy,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing Binance trades response into Trade list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Trade]:
        """Parse Binance trades response.

        Args:
            response: Raw response from Binance API (list of trade objects)
            params: Request parameters containing symbol

        Returns:
            List of Trade objects

        """
        symbol = params["symbol"].upper()
        out: list[Trade] = []
        for row in response or []:
            out.append(
                Trade(
                    symbol=symbol,
                    trade_id=int(row.get("id")),
                    price=Decimal(str(row.get("price"))),
                    quantity=Decimal(str(row.get("qty"))),
                    quote_quantity=(
                        Decimal(str(row.get("quoteQty")))
                        if row.get("quoteQty") is not None
                        else None
                    ),
                    timestamp=datetime.fromtimestamp(int(row.get("time", 0)) / 1000, tz=UTC),
                    is_buyer_maker=bool(row.get("isBuyerMaker")),
                    is_best_match=row.get("isBestMatch"),
                ),
            )
        return out
