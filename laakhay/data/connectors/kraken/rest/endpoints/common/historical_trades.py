"""Kraken historical trades endpoint definition and adapter.

This endpoint is available for both Spot and Futures (may require API key).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.core.exceptions import DataError
from laakhay.data.models import Trade
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def build_path(params: dict[str, Any]) -> str:
    """Build the historicalTrades path based on market type."""
    market: MarketType = params["market_type"]
    if market == MarketType.FUTURES:
        # Kraken Futures API - check if historical trades endpoint exists
        return "/history"
    else:
        # Kraken Spot API - historical trades might use same endpoint as recent trades
        return "/0/public/Trades"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for historicalTrades endpoint."""
    market_type: MarketType = params["market_type"]
    symbol = params["symbol"]  # Already in exchange format from router
    q: dict[str, Any] = {}

    if market_type == MarketType.FUTURES:
        # Kraken Futures API
        q["symbol"] = symbol
        if params.get("limit") is not None:
            q["limit"] = min(int(params["limit"]), 1000)
        if params.get("from_id") is not None:
            q["since"] = int(params["from_id"])
    else:
        # Kraken Spot API - uses same endpoint as recent trades but with since parameter
        q["pair"] = symbol
        if params.get("limit") is not None:
            q["count"] = min(int(params["limit"]), 1000)
        if params.get("from_id") is not None:
            # Kraken uses Unix timestamp (seconds) for since parameter
            q["since"] = int(params["from_id"])

    return q


# Endpoint specification
SPEC = RestEndpointSpec(
    id="historical_trades",
    method="GET",
    build_path=build_path,
    build_query=build_query,
)


def _extract_result(response: Any, market_type: MarketType) -> Any:
    """Extract result from Kraken's response wrapper."""
    if not isinstance(response, dict):
        raise DataError(f"Invalid response format: expected dict, got {type(response)}")

    # Check for errors in Kraken Spot format
    errors = response.get("error", [])
    if errors and len(errors) > 0:
        error_msg = errors[0] if isinstance(errors, list) else str(errors)
        raise DataError(f"Kraken API error: {error_msg}")

    # Kraken Spot wraps in "result" field
    if "result" in response:
        result_value = response["result"]
        # For Futures, if result is "ok", return the full response (data is in other fields)
        if result_value == "ok" and market_type == MarketType.FUTURES:
            return response
        return result_value

    # Kraken Futures may return direct result or wrapped
    if "error" in response and response["error"]:
        raise DataError(f"Kraken API error: {response.get('error', 'Unknown error')}")

    # Return response itself if no wrapper
    return response


class Adapter(ResponseAdapter):
    """Adapter for parsing Kraken historicalTrades response into Trade list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Trade]:
        """Parse Kraken historicalTrades response.

        Args:
            response: Raw response from Kraken API (list of trade objects)
            params: Request parameters containing symbol

        Returns:
            List of Trade objects
        """
        market_type: MarketType = params["market_type"]
        symbol = params["symbol"]  # Already in exchange format

        result = _extract_result(response, market_type)
        out: list[Trade] = []

        if market_type == MarketType.FUTURES:
            # Kraken Futures format: {result: "ok", history: [{time, trade_id, price, size, side}, ...]}
            trades_list = result.get("history", []) if isinstance(result, dict) else result
            if not isinstance(trades_list, list):
                return out

            for row in trades_list:
                if not isinstance(row, dict):
                    continue

                try:
                    time_ms = row.get("time", 0)
                    price_str = row.get("price")
                    qty_str = row.get("size")
                    side = row.get("side", "")  # "buy" or "sell"
                    trade_id = row.get("trade_id", "")

                    if not all([time_ms, price_str, qty_str]):
                        continue

                    price = Decimal(str(price_str))
                    quantity = Decimal(str(qty_str))
                    quote_quantity = price * quantity

                    # Kraken side: "buy" means buyer is maker
                    is_buyer_maker = side.lower() == "buy"

                    out.append(
                        Trade(
                            symbol=symbol,
                            trade_id=(
                                int(trade_id)
                                if trade_id and str(trade_id).isdigit()
                                else int(hash(str(trade_id)))
                            ),
                            price=price,
                            quantity=quantity,
                            quote_quantity=quote_quantity,
                            timestamp=(
                                datetime.fromtimestamp(time_ms / 1000, tz=UTC)
                                if time_ms
                                else datetime.now(UTC)
                            ),
                            is_buyer_maker=is_buyer_maker,
                            is_best_match=None,
                        )
                    )
                except (ValueError, TypeError, KeyError):
                    continue

        else:
            # Kraken Spot format: {result: {PAIR: [[price, volume, time, buy/sell, market/limit, misc], ...]}}
            pair_data = None
            if isinstance(result, dict):
                for key in result:
                    pair_data = result[key]
                    break

            if not isinstance(pair_data, list):
                return out

            for row in pair_data:
                if not isinstance(row, list) or len(row) < 4:
                    continue

                try:
                    # Kraken Spot: [price, volume, time, buy/sell, market/limit, misc]
                    price_str = row[0]
                    qty_str = row[1]
                    time_float = float(row[2])
                    side_str = row[3] if len(row) > 3 else ""

                    price = Decimal(str(price_str))
                    quantity = Decimal(str(qty_str))
                    quote_quantity = price * quantity

                    # Kraken side: "b" means buy, "s" means sell
                    is_buyer_maker = side_str.lower() == "b"

                    out.append(
                        Trade(
                            symbol=symbol,
                            trade_id=int(hash(f"{time_float}{price_str}{qty_str}")),
                            price=price,
                            quantity=quantity,
                            quote_quantity=quote_quantity,
                            timestamp=datetime.fromtimestamp(time_float, tz=UTC),
                            is_buyer_maker=is_buyer_maker,
                            is_best_match=None,
                        )
                    )
                except (ValueError, TypeError, IndexError):
                    continue

        return out
