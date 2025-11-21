"""Kraken open interest (current) endpoint definition and adapter.

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
    """Build the openInterest path (futures only)."""
    market: MarketType = params["market_type"]
    if market != MarketType.FUTURES:
        raise ValueError("Open interest current endpoint is Futures-only on Kraken")
    # Kraken Futures API - may use ticker endpoint
    return "/tickers"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for openInterest endpoint."""
    symbol = params["symbol"]  # Already in exchange format from router
    return {
        "symbol": symbol,
    }


# Endpoint specification
SPEC = RestEndpointSpec(
    id="open_interest_current",
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
    """Adapter for parsing Kraken openInterest response into OpenInterest list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        """Parse Kraken openInterest response.

        Args:
            response: Raw response from Kraken API
            params: Request parameters containing symbol

        Returns:
            List containing single OpenInterest object
        """
        market_type: MarketType = params["market_type"]
        if market_type != MarketType.FUTURES:
            return []

        symbol = params["symbol"]  # Already in exchange format
        result = _extract_result(response, market_type)

        # Kraken Futures format: {result: "ok", ticker: {openInterest, openInterestValue, ...}}
        ticker_data = result.get("ticker", result) if isinstance(result, dict) else result

        if not isinstance(ticker_data, dict):
            return []

        oi_str = ticker_data.get("openInterest")
        oi_value_str = ticker_data.get("openInterestValue")
        timestamp_ms = ticker_data.get("serverTime", 0)

        if oi_str is None:
            return []

        try:
            return [
                OpenInterest(
                    symbol=symbol,
                    timestamp=(
                        datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
                        if timestamp_ms
                        else datetime.now(UTC)
                    ),
                    open_interest=Decimal(str(oi_str)),
                    open_interest_value=(Decimal(str(oi_value_str)) if oi_value_str else None),
                )
            ]
        except (ValueError, TypeError):
            return []
