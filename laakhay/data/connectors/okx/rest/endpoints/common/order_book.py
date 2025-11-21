"""OKX order book endpoint definition and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.models import OrderBook
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec

from ...config import to_okx_symbol


def build_path(params: dict[str, Any]) -> str:
    """Build the books path."""
    return "/api/v5/market/books"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for books endpoint."""
    limit = int(params.get("limit", 20))
    # OKX supports: 1, 5, 10, 20, 50, 100, 200, 400
    # Map to nearest supported value
    if limit <= 1:
        limit = 1
    elif limit <= 5:
        limit = 5
    elif limit <= 10:
        limit = 10
    elif limit <= 20:
        limit = 20
    elif limit <= 50:
        limit = 50
    elif limit <= 100:
        limit = 100
    elif limit <= 200:
        limit = 200
    else:
        limit = 400

    return {
        "instId": to_okx_symbol(params["symbol"]),
        "sz": limit,
    }


# Endpoint specification
SPEC = RestEndpointSpec(
    id="order_book",
    method="GET",
    build_path=build_path,
    build_query=build_query,
)


def _extract_result(response: Any) -> Any:
    """Extract result from OKX's response wrapper.

    OKX API v5 returns: {code: "0", msg: "", data: [...]}
    """
    if not isinstance(response, dict):
        raise ValueError(f"Invalid response format: expected dict, got {type(response)}")

    code = response.get("code", "-1")
    msg = response.get("msg", "Unknown error")

    if code != "0":
        raise ValueError(f"OKX API error: {msg} (code: {code})")

    data = response.get("data")
    if data is None:
        raise ValueError("OKX API response missing 'data' field")

    return data


class Adapter(ResponseAdapter):
    """Adapter for parsing OKX books response into OrderBook."""

    def parse(self, response: Any, params: dict[str, Any]) -> OrderBook:
        """Parse OKX books response.

        Args:
            response: Raw response from OKX API
            params: Request parameters containing symbol

        Returns:
            OrderBook object with bids and asks
        """
        data = _extract_result(response)
        symbol = params["symbol"].upper()

        # OKX returns list with single orderbook object
        if not isinstance(data, list) or len(data) == 0:
            raise ValueError("OKX orderbook response missing data")

        ob_data = data[0]
        if not isinstance(ob_data, dict):
            raise ValueError("Invalid orderbook data format")

        bids = []
        asks = []

        # Extract bids and asks
        bids_data = ob_data.get("bids", [])
        asks_data = ob_data.get("asks", [])

        if isinstance(bids_data, list):
            bids = [
                (Decimal(str(p)), Decimal(str(q)))
                for item in bids_data
                if isinstance(item, list) and len(item) >= 2
                for p, q in [item[:2]]
            ]

        if isinstance(asks_data, list):
            asks = [
                (Decimal(str(p)), Decimal(str(q)))
                for item in asks_data
                if isinstance(item, list) and len(item) >= 2
                for p, q in [item[:2]]
            ]

        # OKX uses "ts" for timestamp
        timestamp_ms = ob_data.get("ts", 0)

        timestamp = (
            datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=UTC)
            if timestamp_ms
            else datetime.now(UTC)
        )

        return OrderBook(
            symbol=symbol,
            last_update_id=0,  # OKX doesn't provide update ID
            bids=bids,
            asks=asks,
            timestamp=timestamp,
        )
