"""Bybit recent trades endpoint definition and adapter.

This endpoint works across all market types (spot, linear, inverse) via the
category parameter. The endpoint path, query parameters, and response format
are identical across all categories.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.bybit.config import get_category
from laakhay.data.core import MarketType
from laakhay.data.core.exceptions import DataError
from laakhay.data.models import Trade
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


def build_path(_params: dict[str, Any]) -> str:
    """Build the recent-trade path (same for both market types)."""
    return "/v5/market/recent-trade"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for recent-trade endpoint."""
    market: MarketType = params["market_type"]
    futures_category = params.get("futures_category", "linear")
    category = get_category(market, futures_category=futures_category)
    limit = min(int(params.get("limit", 50)), 1000)  # Bybit max is 1000

    return {
        "category": category,
        "symbol": params["symbol"].upper(),
        "limit": limit,
    }


# Endpoint specification
SPEC = RestEndpointSpec(
    id="recent_trades",
    method="GET",
    build_path=build_path,
    build_query=build_query,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing Bybit recent-trade response into Trade list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Trade]:
        """Parse Bybit recent-trade response.

        Args:
            response: Raw response from Bybit API
            params: Request parameters containing symbol

        Returns:
            List of Trade objects
        """
        result = _extract_result(response)
        symbol = params["symbol"].upper()

        # Bybit returns list in "list" field
        trades_list = result.get("list", []) if isinstance(result, dict) else result
        if not isinstance(trades_list, list):
            trades_list = []

        out: list[Trade] = []
        for row in trades_list:
            if not isinstance(row, dict):
                continue
            try:
                # Bybit format: {execId, symbol, price, size, side, time, isBlockTrade}
                trade_id = row.get("execId", "")
                price = Decimal(str(row.get("price", "0")))
                quantity = Decimal(str(row.get("size", "0")))
                side = row.get("side", "").upper()  # "Buy" or "Sell"
                timestamp_ms = int(row.get("time", 0))

                out.append(
                    Trade(
                        symbol=symbol,
                        trade_id=trade_id,
                        price=price,
                        quantity=quantity,
                        quote_quantity=None,  # Bybit doesn't provide this directly
                        timestamp=datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC),
                        is_buyer_maker=(side == "Sell"),  # If side is Sell, buyer is maker
                        is_best_match=None,  # Bybit doesn't provide this
                    )
                )
            except (ValueError, KeyError, TypeError):
                # Skip invalid rows
                continue

        return out
