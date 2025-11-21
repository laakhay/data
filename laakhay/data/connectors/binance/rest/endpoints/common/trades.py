"""Binance recent trades endpoint definition and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.models import Trade
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def build_path(params: dict[str, Any]) -> str:
    """Build the trades path based on market type."""
    market: MarketType = params["market_type"]
    return "/fapi/v1/trades" if market == MarketType.FUTURES else "/api/v3/trades"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for trades endpoint."""
    return {
        "symbol": params["symbol"].upper(),
        "limit": min(int(params.get("limit", 500)), 1000),
    }


# Endpoint specification
SPEC = RestEndpointSpec(
    id="recent_trades",
    method="GET",
    build_path=build_path,
    build_query=build_query,
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
                )
            )
        return out
