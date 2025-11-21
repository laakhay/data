"""Binance order book endpoint definition and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.models import OrderBook
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def build_path(params: dict[str, Any]) -> str:
    """Build the depth path based on market type."""
    market: MarketType = params["market_type"]
    return "/fapi/v1/depth" if market == MarketType.FUTURES else "/api/v3/depth"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for depth endpoint."""
    return {
        "symbol": params["symbol"].upper(),
        "limit": int(params.get("limit", 100)),
    }


# Endpoint specification
SPEC = RestEndpointSpec(
    id="order_book",
    method="GET",
    build_path=build_path,
    build_query=build_query,
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
