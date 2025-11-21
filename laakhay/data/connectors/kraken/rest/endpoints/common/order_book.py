"""Kraken order book endpoint definition and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.core.exceptions import DataError
from laakhay.data.models import OrderBook
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def build_path(params: dict[str, Any]) -> str:
    """Build the orderBook path based on market type."""
    market: MarketType = params["market_type"]
    if market == MarketType.FUTURES:
        # Kraken Futures API
        return "/orderbook"
    else:
        # Kraken Spot API
        return "/0/public/Depth"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for orderBook endpoint."""
    market_type: MarketType = params["market_type"]
    symbol = params["symbol"]  # Already in exchange format from router
    limit = int(params.get("limit", 100))

    if market_type == MarketType.FUTURES:
        # Kraken Futures API
        # Map limit to supported depths: 10, 25, 50, 100, 500, 1000
        if limit <= 10:
            depth = 10
        elif limit <= 25:
            depth = 25
        elif limit <= 50:
            depth = 50
        elif limit <= 100:
            depth = 100
        elif limit <= 500:
            depth = 500
        else:
            depth = 1000

        return {
            "symbol": symbol,
            "depth": depth,
        }
    else:
        # Kraken Spot API
        return {
            "pair": symbol,
            "count": min(limit, 500),  # Kraken Spot max is 500
        }


# Endpoint specification
SPEC = RestEndpointSpec(
    id="order_book",
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
    """Adapter for parsing Kraken orderBook response into OrderBook."""

    def parse(self, response: Any, params: dict[str, Any]) -> OrderBook:
        """Parse Kraken orderBook response.

        Args:
            response: Raw response from Kraken API
            params: Request parameters containing symbol

        Returns:
            OrderBook object with bids and asks
        """
        market_type: MarketType = params["market_type"]
        symbol = params["symbol"]  # Already in exchange format

        result = _extract_result(response, market_type)

        bids: list[tuple[Decimal, Decimal]] = []
        asks: list[tuple[Decimal, Decimal]] = []

        if market_type == MarketType.FUTURES:
            # Kraken Futures format: {result: "ok", orderBook: {bids: [[price, qty], ...], asks: [[price, qty], ...]}}
            orderbook_data = result.get("orderBook", result) if isinstance(result, dict) else result

            bids_data = orderbook_data.get("bids", []) if isinstance(orderbook_data, dict) else []
            asks_data = orderbook_data.get("asks", []) if isinstance(orderbook_data, dict) else []

            if isinstance(bids_data, list):
                for bid in bids_data:
                    if isinstance(bid, list) and len(bid) >= 2:
                        bids.append((Decimal(str(bid[0])), Decimal(str(bid[1]))))

            if isinstance(asks_data, list):
                for ask in asks_data:
                    if isinstance(ask, list) and len(ask) >= 2:
                        asks.append((Decimal(str(ask[0])), Decimal(str(ask[1]))))

            timestamp_ms = (
                orderbook_data.get("serverTime", 0) if isinstance(orderbook_data, dict) else 0
            )
            last_update_id = (
                orderbook_data.get("sequenceNumber", 0) if isinstance(orderbook_data, dict) else 0
            )

        else:
            # Kraken Spot format: {result: {PAIR: {bids: [[price, volume, timestamp], ...], asks: [[price, volume, timestamp], ...]}}}
            pair_data = None
            if isinstance(result, dict):
                # Find first key that looks like a pair
                for key in result:
                    pair_data = result[key]
                    break

            if isinstance(pair_data, dict):
                bids_data = pair_data.get("bids", [])
                asks_data = pair_data.get("asks", [])

                if isinstance(bids_data, list):
                    # Kraken Spot: [price, volume, timestamp]
                    bids = [
                        (Decimal(str(row[0])), Decimal(str(row[1])))
                        for row in bids_data
                        if isinstance(row, list) and len(row) >= 2
                    ]

                if isinstance(asks_data, list):
                    asks = [
                        (Decimal(str(row[0])), Decimal(str(row[1])))
                        for row in asks_data
                        if isinstance(row, list) and len(row) >= 2
                    ]

            timestamp_ms = 0
            last_update_id = 0

        timestamp = (
            datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
            if timestamp_ms
            else datetime.now(UTC)
        )

        # OrderBook requires at least one level - use default if empty
        if not bids and not asks:
            bids = [(Decimal("0"), Decimal("0"))]
            asks = [(Decimal("0"), Decimal("0"))]
        elif not bids:
            bids = [(Decimal("0"), Decimal("0"))]
        elif not asks:
            asks = [(Decimal("0"), Decimal("0"))]

        return OrderBook(
            symbol=symbol,
            last_update_id=last_update_id,
            bids=bids,
            asks=asks,
            timestamp=timestamp,
        )
