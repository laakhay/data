"""OKX recent trades endpoint definition and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.models import Trade
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec

from ...config import to_okx_symbol


def build_path(params: dict[str, Any]) -> str:
    """Build the trades path."""
    return "/api/v5/market/trades"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for trades endpoint."""
    limit = min(int(params.get("limit", 100)), 500)  # OKX max is 500

    return {
        "instId": to_okx_symbol(params["symbol"]),
        "limit": limit,
    }


# Endpoint specification
SPEC = RestEndpointSpec(
    id="recent_trades",
    method="GET",
    build_path=build_path,
    build_query=build_query,
)


def _extract_result(response: Any) -> Any:
    """Extract result from OKX's response wrapper.

    OKX API v5 returns: {code: "0", msg: "", data: [...]}
    """
    if not isinstance(response, dict):
        raise ValueError(f"Invalid response format: expected dict, got {type(response)}")

    code = response.get("code", "-1")
    msg = response.get("msg", "Unknown error")

    if code != "0":
        raise ValueError(f"OKX API error: {msg} (code: {code})")

    data = response.get("data")
    if data is None:
        raise ValueError("OKX API response missing 'data' field")

    return data


class Adapter(ResponseAdapter):
    """Adapter for parsing OKX trades response into Trade list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Trade]:
        """Parse OKX trades response.

        Args:
            response: Raw response from OKX API (list of trade objects)
            params: Request parameters containing symbol

        Returns:
            List of Trade objects
        """
        data = _extract_result(response)
        symbol = params["symbol"].upper()

        if not isinstance(data, list):
            return []

        out: list[Trade] = []
        for row in data:
            if not isinstance(row, dict):
                continue

            try:
                # OKX format: {instId, tradeId, px, sz, side, ts, count}
                trade_id = row.get("tradeId", "")
                price_str = row.get("px")
                qty_str = row.get("sz")
                side = row.get("side", "")  # "buy" or "sell"
                time_ms = row.get("ts", 0)

                if not price_str or not qty_str:
                    continue

                price = Decimal(str(price_str))
                quantity = Decimal(str(qty_str))
                quote_quantity = price * quantity

                # OKX side: "buy" means buyer is taker, "sell" means seller is taker
                # So "buy" means buyer is NOT maker (is_buyer_maker = False)
                is_buyer_maker = side == "sell"

                out.append(
                    Trade(
                        symbol=symbol,
                        trade_id=int(trade_id) if trade_id else 0,
                        price=price,
                        quantity=quantity,
                        quote_quantity=quote_quantity,
                        timestamp=datetime.fromtimestamp(int(time_ms) / 1000, tz=UTC)
                        if time_ms
                        else datetime.now(UTC),
                        is_buyer_maker=is_buyer_maker,
                        is_best_match=None,
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue

        return out
