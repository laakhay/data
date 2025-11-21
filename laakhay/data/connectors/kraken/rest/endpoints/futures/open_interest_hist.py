"""Kraken open interest (historical) endpoint definition and adapter.

This endpoint is Futures-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.core.exceptions import DataError
from laakhay.data.models import OpenInterest
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def build_path(params: dict[str, Any]) -> str:
    """Build the openInterestHist path (futures only)."""
    market: MarketType = params["market_type"]
    if market != MarketType.FUTURES:
        raise ValueError("Open interest history endpoint is Futures-only on Kraken")
    # Kraken Futures API - check if historical OI endpoint exists
    return "/open_interest"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for openInterestHist endpoint."""
    symbol = params["symbol"]  # Already in exchange format from router
    q: dict[str, Any] = {
        "symbol": symbol,
        "limit": min(int(params.get("limit", 200)), 1000),
    }
    if params.get("start_time"):
        q["start_time"] = int(params["start_time"].timestamp() * 1000)
    if params.get("end_time"):
        q["end_time"] = int(params["end_time"].timestamp() * 1000)
    return q


# Endpoint specification
SPEC = RestEndpointSpec(
    id="open_interest_hist",
    method="GET",
    build_path=build_path,
    build_query=build_query,
)


def _extract_result(response: Any, market_type: MarketType) -> Any:
    """Extract result from Kraken's response wrapper."""
    if not isinstance(response, dict):
        raise DataError(f"Invalid response format: expected dict, got {type(response)}")

    # Check for errors
    errors = response.get("error", [])
    if errors and len(errors) > 0:
        error_msg = errors[0] if isinstance(errors, list) else str(errors)
        raise DataError(f"Kraken API error: {error_msg}")

    # Kraken Futures wraps in "result" field
    if "result" in response:
        result_value = response["result"]
        # If result is "ok", return the full response (data is in other fields)
        if result_value == "ok":
            return response
        return result_value

    # Check for error field
    if "error" in response and response["error"]:
        raise DataError(f"Kraken API error: {response.get('error', 'Unknown error')}")

    # Return response itself if no wrapper
    return response


class Adapter(ResponseAdapter):
    """Adapter for parsing Kraken openInterestHist response into OpenInterest list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        """Parse Kraken openInterestHist response.

        Args:
            response: Raw response from Kraken API (list of OI data)
            params: Request parameters containing symbol

        Returns:
            List of OpenInterest objects
        """
        market_type: MarketType = params["market_type"]
        if market_type != MarketType.FUTURES:
            return []

        symbol = params["symbol"]  # Already in exchange format
        result = _extract_result(response, market_type)

        # Kraken Futures format: {result: "ok", openInterest: [{time, openInterest, openInterestValue}, ...]}
        oi_list = result.get("openInterest", []) if isinstance(result, dict) else result
        if not isinstance(oi_list, list):
            return []

        out: list[OpenInterest] = []
        for row in oi_list:
            if not isinstance(row, dict):
                continue

            try:
                ts_ms = row.get("time", 0)
                oi_str = row.get("openInterest")
                oi_value_str = row.get("openInterestValue")

                if ts_ms is None or oi_str is None:
                    continue

                out.append(
                    OpenInterest(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                        open_interest=Decimal(str(oi_str)),
                        open_interest_value=(Decimal(str(oi_value_str)) if oi_value_str else None),
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue

        return out
