"""Binance historical trades endpoint definition and adapter.

This endpoint is Spot-only (requires API key).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.models import Trade
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def build_path(params: dict[str, Any]) -> str:
    """Build the historicalTrades path (spot only)."""
    market: MarketType = params["market_type"]
    if market != MarketType.SPOT:
        raise ValueError("Historical trades endpoint is Spot-only on Binance")
    return "/api/v3/historicalTrades"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for historicalTrades endpoint."""
    q: dict[str, Any] = {"symbol": params["symbol"].upper()}
    if params.get("limit") is not None:
        limit = int(params["limit"])
        q["limit"] = max(1, min(limit, 1000))
    if params.get("from_id") is not None:
        q["fromId"] = int(params["from_id"])
    return q


def build_headers(params: dict[str, Any]) -> dict[str, str]:
    """Build headers for historicalTrades endpoint (requires API key)."""
    api_key = params.get("api_key")
    if not api_key:
        raise ValueError("API key required for Binance historical trades endpoint")
    return {"X-MBX-APIKEY": api_key}


# Endpoint specification
SPEC = RestEndpointSpec(
    id="historical_trades",
    method="GET",
    build_path=build_path,
    build_query=build_query,
    build_headers=build_headers,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing Binance historicalTrades response into Trade list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Trade]:
        """Parse Binance historicalTrades response.

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
                )
            )
        return out
