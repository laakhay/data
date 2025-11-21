"""Binance open interest (historical) endpoint definition and adapter.

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
    """Build the openInterestHist path (futures only)."""
    market: MarketType = params["market_type"]
    if market != MarketType.FUTURES:
        raise ValueError("Open interest history endpoint is Futures-only on Binance")
    return "/futures/data/openInterestHist"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for openInterestHist endpoint."""
    q: dict[str, Any] = {
        "symbol": params["symbol"].upper(),
        "period": params.get("period", "5m"),
        "limit": min(int(params.get("limit", 30)), 500),
    }
    if params.get("start_time"):
        q["startTime"] = int(params["start_time"].timestamp() * 1000)
    if params.get("end_time"):
        q["endTime"] = int(params["end_time"].timestamp() * 1000)
    return q


# Endpoint specification
SPEC = RestEndpointSpec(
    id="open_interest_hist",
    method="GET",
    build_path=build_path,
    build_query=build_query,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing Binance openInterestHist response into OpenInterest list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        """Parse Binance openInterestHist response.

        Args:
            response: Raw response from Binance API (list of OI data)
            params: Request parameters containing symbol

        Returns:
            List of OpenInterest objects
        """
        symbol = params["symbol"].upper()
        out: list[OpenInterest] = []
        for row in response or []:
            ts_ms = row.get("timestamp")
            oi_str = row.get("sumOpenInterest")
            if ts_ms is None or oi_str is None:
                continue
            out.append(
                OpenInterest(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                    open_interest=Decimal(str(oi_str)),
                    open_interest_value=None,
                )
            )
        return out
