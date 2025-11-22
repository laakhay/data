"""Binance open interest (current) endpoint definition and adapter.

This endpoint is Futures-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.binance.config import get_api_path_prefix
from laakhay.data.core import MarketType
from laakhay.data.models import OpenInterest
from laakhay.data.runtime.chunking import WeightPolicy
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def build_path(params: dict[str, Any]) -> str:
    """Build the openInterest path (futures only)."""
    market: MarketType = params["market_type"]
    if market != MarketType.FUTURES:
        raise ValueError("Open interest current endpoint is Futures-only on Binance")
    prefix = get_api_path_prefix(market, params.get("market_variant"))
    return f"{prefix}/openInterest"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for openInterest endpoint."""
    return {"symbol": params["symbol"].upper()}


OPEN_INTEREST_CURRENT_WEIGHT_POLICY = WeightPolicy(static_weight=1)


SPEC = RestEndpointSpec(
    id="open_interest_current",
    method="GET",
    build_path=build_path,
    build_query=build_query,
    weight_policy=OPEN_INTEREST_CURRENT_WEIGHT_POLICY,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing Binance openInterest response into OpenInterest list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        """Parse Binance openInterest response.

        Args:
            response: Raw response from Binance API
            params: Request parameters containing symbol

        Returns:
            List containing single OpenInterest object

        """
        symbol = params["symbol"].upper()
        oi_str = response.get("openInterest")
        ts_ms = response.get("time")
        if oi_str is None or ts_ms is None:
            return []
        return [
            OpenInterest(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                open_interest=Decimal(str(oi_str)),
                open_interest_value=None,
            ),
        ]
