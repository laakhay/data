"""MEXC recent trades endpoint definition and adapter.

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
    # MEXC uses /api/v3/trades for spot and /api/v1/contract/deals for futures
    return "/api/v1/contract/deals" if market == MarketType.FUTURES else "/api/v3/trades"


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
    """Adapter for parsing MEXC trades response into Trade list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Trade]:
        """Parse MEXC trades response.

        Args:
            response: Raw response from MEXC API (list of trade objects)
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
                    trade_id=int(row.get("id", row.get("tradeId", 0))),
                    price=Decimal(str(row.get("price"))),
                    quantity=Decimal(str(row.get("qty", row.get("quantity", 0)))),
                    quote_quantity=(
                        Decimal(str(row.get("quoteQty", row.get("quote_quantity"))))
                        if row.get("quoteQty") is not None or row.get("quote_quantity") is not None
                        else None
                    ),
                    timestamp=datetime.fromtimestamp(int(row.get("time", 0)) / 1000, tz=UTC),
                    is_buyer_maker=bool(row.get("isBuyerMaker", row.get("is_buyer_maker", False))),
                    is_best_match=row.get("isBestMatch", row.get("is_best_match")),
                )
            )
        return out
