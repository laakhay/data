"""Binance funding rate endpoint definition and adapter.

This endpoint is Futures-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.models import FundingRate
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def build_path(params: dict[str, Any]) -> str:
    """Build the fundingRate path (futures only)."""
    market: MarketType = params["market_type"]
    if market != MarketType.FUTURES:
        raise ValueError("Funding rate endpoint is Futures-only on Binance")
    return "/fapi/v1/fundingRate"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for fundingRate endpoint."""
    q: dict[str, Any] = {
        "symbol": params["symbol"].upper(),
        "limit": min(int(params.get("limit", 100)), 1000),
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
    """Adapter for parsing Binance fundingRate response into FundingRate list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[FundingRate]:
        """Parse Binance fundingRate response.

        Args:
            response: Raw response from Binance API (list of funding rate data)
            params: Request parameters containing symbol

        Returns:
            List of FundingRate objects
        """
        symbol = params["symbol"].upper()
        out: list[FundingRate] = []
        for row in response or []:
            fr = Decimal(str(row.get("fundingRate")))
            ts_ms = int(row.get("fundingTime", 0))
            out.append(
                FundingRate(
                    symbol=symbol,
                    funding_time=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                    funding_rate=fr,
                    mark_price=(
                        Decimal(str(row.get("markPrice")))
                        if row.get("markPrice") is not None
                        else None
                    ),
                )
            )
        return out
