"""Bybit funding rate endpoint definition and adapter.

This endpoint is Futures-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.bybit.config import CATEGORY_MAP
from laakhay.data.core import MarketType
from laakhay.data.core.exceptions import DataError
from laakhay.data.models import FundingRate
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


def build_path(params: dict[str, Any]) -> str:  # noqa: ARG001
    """Build the funding-rate path (futures only)."""
    market: MarketType = params["market_type"]
    if market != MarketType.FUTURES:
        raise ValueError("Funding rate endpoint is Futures-only on Bybit")
    return "/v5/market/funding/history"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for funding-rate endpoint."""
    market: MarketType = params["market_type"]
    category = CATEGORY_MAP[market]
    q: dict[str, Any] = {
        "category": category,
        "symbol": params["symbol"].upper(),
        "limit": min(int(params.get("limit", 100)), 200),  # Bybit max is 200
    }
    if params.get("start_time"):
        q["startTime"] = int(params["start_time"].timestamp() * 1000)
    if params.get("end_time"):
        q["endTime"] = int(params["end_time"].timestamp() * 1000)
    return q


# Endpoint specification
SPEC = RestEndpointSpec(
    id="funding_rate",
    method="GET",
    build_path=build_path,
    build_query=build_query,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing Bybit funding-rate response into FundingRate list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[FundingRate]:
        """Parse Bybit funding-rate response.

        Args:
            response: Raw response from Bybit API
            params: Request parameters containing symbol

        Returns:
            List of FundingRate objects
        """
        result = _extract_result(response)
        symbol = params["symbol"].upper()

        # Bybit returns list in "list" field
        rates_list = result.get("list", []) if isinstance(result, dict) else result
        if not isinstance(rates_list, list):
            rates_list = []

        out: list[FundingRate] = []
        for row in rates_list:
            if not isinstance(row, dict):
                continue
            try:
                # Bybit format: {symbol, fundingRate, fundingRateTimestamp}
                funding_rate = Decimal(str(row.get("fundingRate", "0")))
                timestamp_ms = int(row.get("fundingRateTimestamp", 0))

                out.append(
                    FundingRate(
                        symbol=symbol,
                        funding_time=datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC),
                        funding_rate=funding_rate,
                        mark_price=None,  # Bybit doesn't provide mark price
                    )
                )
            except (ValueError, KeyError, TypeError):
                # Skip invalid rows
                continue

        return out
