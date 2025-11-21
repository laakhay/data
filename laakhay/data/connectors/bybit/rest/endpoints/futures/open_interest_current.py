"""Bybit open interest (current) endpoint definition and adapter.

This endpoint is Futures-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.bybit.config import CATEGORY_MAP
from laakhay.data.core import MarketType
from laakhay.data.core.exceptions import DataError
from laakhay.data.models import OpenInterest
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


def build_path(params: dict[str, Any]) -> str:
    """Build the open-interest path (futures only)."""
    market: MarketType = params["market_type"]
    if market != MarketType.FUTURES:
        raise ValueError("Open interest current endpoint is Futures-only on Bybit")
    return "/v5/market/open-interest"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for open-interest endpoint."""
    market: MarketType = params["market_type"]
    category = CATEGORY_MAP[market]
    return {
        "category": category,
        "symbol": params["symbol"].upper(),
        "intervalTime": "5min",  # Bybit requires intervalTime for current OI
    }


# Endpoint specification
SPEC = RestEndpointSpec(
    id="open_interest_current",
    method="GET",
    build_path=build_path,
    build_query=build_query,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing Bybit open-interest response into OpenInterest list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        """Parse Bybit open-interest response.

        Args:
            response: Raw response from Bybit API
            params: Request parameters containing symbol

        Returns:
            List containing single OpenInterest object
        """
        result = _extract_result(response)
        symbol = params["symbol"].upper()

        # Bybit returns list in "list" field
        oi_list = result.get("list", []) if isinstance(result, dict) else result
        if not isinstance(oi_list, list) or len(oi_list) == 0:
            return []

        # Get the first (most recent) entry
        row = oi_list[0]
        if not isinstance(row, dict):
            return []

        try:
            open_interest_str = row.get("openInterest", "0")
            timestamp_ms = int(row.get("timestamp", 0))

            return [
                OpenInterest(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC),
                    open_interest=Decimal(str(open_interest_str)),
                    open_interest_value=None,  # Bybit doesn't provide value in current OI
                )
            ]
        except (ValueError, KeyError, TypeError):
            return []
