"""MEXC open interest (current) endpoint definition and adapter.

This endpoint is Futures-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.models import OpenInterest
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def build_path(params: dict[str, Any]) -> str:
    """Build the openInterest path (futures only)."""
    market: MarketType = params["market_type"]
    if market != MarketType.FUTURES:
        raise ValueError("Open interest current endpoint is Futures-only on MEXC")
    return "/api/v1/contract/open_interest"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for openInterest endpoint."""
    return {"symbol": params["symbol"].upper()}


# Endpoint specification
SPEC = RestEndpointSpec(
    id="open_interest_current",
    method="GET",
    build_path=build_path,
    build_query=build_query,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing MEXC openInterest response into OpenInterest list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        """Parse MEXC openInterest response.

        Args:
            response: Raw response from MEXC API
            params: Request parameters containing symbol

        Returns:
            List containing single OpenInterest object
        """
        symbol = params["symbol"].upper()
        oi_str = response.get("openInterest", response.get("open_interest"))
        ts_ms = response.get("time", response.get("timestamp"))
        if oi_str is None or ts_ms is None:
            return []
        return [
            OpenInterest(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                open_interest=Decimal(str(oi_str)),
                open_interest_value=None,
            )
        ]
