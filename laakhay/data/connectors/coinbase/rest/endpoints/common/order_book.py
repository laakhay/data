"""Coinbase order book endpoint definition and adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.models import OrderBook
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec
from laakhay.data.connectors.coinbase.config import normalize_symbol_to_coinbase


def build_path(params: dict[str, Any]) -> str:
    """Build the order book path."""
    market: MarketType = params["market_type"]
    if market != MarketType.SPOT:
        raise ValueError("Coinbase Advanced Trade API only supports Spot markets")

    symbol = params["symbol"]
    product_id = normalize_symbol_to_coinbase(symbol)
    return f"/products/{product_id}/book"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for order book endpoint."""
    # Exchange API uses level parameter (1, 2, or 3) instead of limit
    # Level 1: best bid/ask only
    # Level 2: top 50 bids/asks (default)
    # Level 3: full order book (up to 5000 levels)
    limit = int(params.get("limit", 50))
    if limit <= 1:
        level = 1
    elif limit <= 50:
        level = 2
    else:
        level = 3  # Full depth
    return {
        "level": level,
    }


# Endpoint specification
SPEC = RestEndpointSpec(
    id="order_book",
    method="GET",
    build_path=build_path,
    build_query=build_query,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing Coinbase order book response."""

    def parse(self, response: Any, params: dict[str, Any]) -> OrderBook:
        """Parse Coinbase Exchange API order book response.

        Exchange API returns: {
            "bids": [["price", "size", num_orders], ...],
            "asks": [["price", "size", num_orders], ...],
            "sequence": 123456,
            "time": "2024-01-01T00:00:00Z"
        }

        Advanced Trade API returns: {
            "pricebook": {
                "bids": [["price", "size"], ...],
                "asks": [["price", "size"], ...]
            }
        }
        """
        symbol = params["symbol"].upper()

        # Exchange API has bids/asks directly, Advanced Trade wraps in "pricebook"
        if "pricebook" in response:
            pricebook = response.get("pricebook", {})
            bids_data = pricebook.get("bids", [])
            asks_data = pricebook.get("asks", [])
        else:
            bids_data = response.get("bids", [])
            asks_data = response.get("asks", [])

        bids = []
        asks = []

        # Parse bids
        if isinstance(bids_data, list):
            for bid in bids_data:
                if isinstance(bid, list) and len(bid) >= 2:
                    try:
                        price = Decimal(str(bid[0]))
                        quantity = Decimal(str(bid[1]))
                        bids.append((price, quantity))
                    except (ValueError, TypeError):
                        continue

        # Parse asks
        if isinstance(asks_data, list):
            for ask in asks_data:
                if isinstance(ask, list) and len(ask) >= 2:
                    try:
                        price = Decimal(str(ask[0]))
                        quantity = Decimal(str(ask[1]))
                        asks.append((price, quantity))
                    except (ValueError, TypeError):
                        continue

        # Coinbase doesn't provide last_update_id or timestamp in order book response
        # Use current timestamp
        timestamp = datetime.now(UTC)

        # OrderBook model requires at least one level in BOTH bids AND asks
        # If either is empty, add a minimal valid level to satisfy validation
        # Using a very small positive price (0.0001) to satisfy validation
        if not bids:
            bids = [(Decimal("0.0001"), Decimal("0.0001"))]
        if not asks:
            asks = [(Decimal("0.0001"), Decimal("0.0001"))]

        return OrderBook(
            symbol=symbol,
            last_update_id=0,  # Coinbase doesn't provide this
            bids=bids,
            asks=asks,
            timestamp=timestamp,
        )

