"""OKX current open interest endpoint definition and adapter.

This endpoint is Futures-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.models import OpenInterest
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec

from ....config import to_okx_symbol


def build_path(params: dict[str, Any]) -> str:
    """Build the open-interest path (futures only)."""
    market: MarketType = params["market_type"]
    if market != MarketType.FUTURES:
        raise ValueError("Open interest endpoint is Futures-only on OKX")
    return "/api/v5/public/open-interest"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for open-interest endpoint."""
    return {
        "instId": to_okx_symbol(params["symbol"]),
    }


# Endpoint specification
SPEC = RestEndpointSpec(
    id="open_interest_current",
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
    """Adapter for parsing OKX open-interest response into OpenInterest list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        """Parse OKX open-interest response.

        Args:
            response: Raw response from OKX API
            params: Request parameters containing symbol

        Returns:
            List of OpenInterest objects
        """
        data = _extract_result(response)
        symbol = params["symbol"].upper()

        # OKX returns list with single OI object
        if not isinstance(data, list) or len(data) == 0:
            return []

        oi_data = data[0]
        if not isinstance(oi_data, dict):
            return []

        oi_str = oi_data.get("oi")
        oi_value_str = oi_data.get("oiCcy")
        timestamp_ms = oi_data.get("ts", 0)

        if oi_str is None:
            return []

        try:
            return [
                OpenInterest(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=UTC)
                    if timestamp_ms
                    else datetime.now(UTC),
                    open_interest=Decimal(str(oi_str)),
                    open_interest_value=Decimal(str(oi_value_str)) if oi_value_str else None,
                )
            ]
        except (ValueError, TypeError):
            return []
