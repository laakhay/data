"""Bybit order book endpoint definition and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.bybit.config import get_category
from laakhay.data.core.exceptions import DataError
from laakhay.data.models import OrderBook
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def _extract_result(response: Any) -> Any:
    """Extract result from Bybit's response wrapper."""
    if not isinstance(response, dict):
        raise DataError(f"Invalid response format: expected dict, got {type(response)}")

    ret_code = response.get("retCode", -1)
    ret_msg = response.get("retMsg", "Unknown error")

    if ret_code != 0:
        raise DataError(f"Bybit API error: {ret_msg} (code: {ret_code})")

    result = response.get("result")
    if result is None:
        raise DataError("Bybit API response missing 'result' field")

    return result


def build_path(_params: dict[str, Any]) -> str:
    """Build the orderbook path (same for both market types)."""
    return "/v5/market/orderbook"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for orderbook endpoint."""
    category = get_category(params)
    limit = int(params.get("limit", 50))
    # Bybit supports: 1, 25, 50, 100, 200
    # Map to nearest supported value
    if limit <= 1:
        limit = 1
    elif limit <= 25:
        limit = 25
    elif limit <= 50:
        limit = 50
    elif limit <= 100:
        limit = 100
    else:
        limit = 200

    return {
        "category": category,
        "symbol": params["symbol"].upper(),
        "limit": limit,
    }


# Endpoint specification
SPEC = RestEndpointSpec(
    id="order_book",
    method="GET",
    build_path=build_path,
    build_query=build_query,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing Bybit orderbook response into OrderBook."""

    def parse(self, response: Any, params: dict[str, Any]) -> OrderBook:
        """Parse Bybit orderbook response.

        Args:
            response: Raw response from Bybit API
            params: Request parameters containing symbol

        Returns:
            OrderBook object with bids and asks
        """
        result = _extract_result(response)
        symbol = params["symbol"].upper()

        # Bybit returns orderbook in result
        bids = []
        asks = []

        # Extract bids and asks
        bids_data = result.get("b", [])
        asks_data = result.get("a", [])

        if isinstance(bids_data, list) and len(bids_data) > 0:
            bids = []
            for item in bids_data:
                if isinstance(item, list) and len(item) >= 2:
                    bids.append((Decimal(str(item[0])), Decimal(str(item[1]))))

        if isinstance(asks_data, list) and len(asks_data) > 0:
            asks = []
            for item in asks_data:
                if isinstance(item, list) and len(item) >= 2:
                    asks.append((Decimal(str(item[0])), Decimal(str(item[1]))))

        # Bybit uses "ts" for timestamp, "u" for update ID
        timestamp_ms = result.get("ts", 0)
        last_update_id = result.get("u", 0)

        timestamp = (
            datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
            if timestamp_ms
            else datetime.now(UTC)
        )

        return OrderBook(
            symbol=symbol,
            last_update_id=last_update_id,
            bids=bids,
            asks=asks,
            timestamp=timestamp,
        )
