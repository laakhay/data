"""Kraken funding rate endpoint definition and adapter.

This endpoint is Futures-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.core.exceptions import DataError
from laakhay.data.models import FundingRate
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def build_path(params: dict[str, Any]) -> str:
    """Build the fundingRate path (futures only)."""
    market: MarketType = params["market_type"]
    if market != MarketType.FUTURES:
        raise ValueError("Funding rate endpoint is Futures-only on Kraken")
    # Kraken Futures API - check if this endpoint exists
    # May need to use ticker endpoint or separate funding endpoint
    return "/funding_rates"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for fundingRate endpoint."""
    symbol = params["symbol"]  # Already in exchange format from router
    q: dict[str, Any] = {
        "symbol": symbol,
        "limit": min(int(params.get("limit", 100)), 1000),
    }
    if params.get("start_time"):
        q["start_time"] = int(params["start_time"].timestamp() * 1000)
    if params.get("end_time"):
        q["end_time"] = int(params["end_time"].timestamp() * 1000)
    return q


# Endpoint specification
SPEC = RestEndpointSpec(
    id="funding_rate",
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
    """Adapter for parsing Kraken fundingRate response into FundingRate list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[FundingRate]:
        """Parse Kraken fundingRate response.

        Args:
            response: Raw response from Kraken API (list of funding rate data)
            params: Request parameters containing symbol

        Returns:
            List of FundingRate objects
        """
        market_type: MarketType = params["market_type"]
        if market_type != MarketType.FUTURES:
            return []

        symbol = params["symbol"]  # Already in exchange format
        result = _extract_result(response, market_type)

        # Kraken Futures format: {result: "ok", fundingRates: [{time, fundingRate, markPrice}, ...]}
        rates_list = result.get("fundingRates", []) if isinstance(result, dict) else result
        if not isinstance(rates_list, list):
            return []

        out: list[FundingRate] = []
        for row in rates_list:
            if not isinstance(row, dict):
                continue

            try:
                fr_str = row.get("fundingRate")
                ts_ms = row.get("time", 0)
                mark_price_str = row.get("markPrice")

                if fr_str is None or ts_ms is None:
                    continue

                funding_rate = Decimal(str(fr_str))
                mark_price = Decimal(str(mark_price_str)) if mark_price_str else None

                out.append(
                    FundingRate(
                        symbol=symbol,
                        funding_time=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                        funding_rate=funding_rate,
                        mark_price=mark_price,
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue

        return out
