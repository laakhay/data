"""Coinbase recent trades endpoint definition and adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.coinbase.config import normalize_symbol_to_coinbase
from laakhay.data.core import MarketType
from laakhay.data.models import Trade
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def build_path(params: dict[str, Any]) -> str:
    """Build the trades path."""
    market: MarketType = params["market_type"]
    if market != MarketType.SPOT:
        raise ValueError("Coinbase Advanced Trade API only supports Spot markets")

    symbol = params["symbol"]
    product_id = normalize_symbol_to_coinbase(symbol)
    return f"/products/{product_id}/trades"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for trades endpoint."""
    # Coinbase uses limit parameter (default 100, max 1000)
    limit = int(params.get("limit", 100))
    return {
        "limit": min(limit, 1000),
    }


# Endpoint specification
SPEC = RestEndpointSpec(
    id="recent_trades",
    method="GET",
    build_path=build_path,
    build_query=build_query,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing Coinbase trades response."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Trade]:
        """Parse Coinbase Exchange API trades response.

        Exchange API returns array directly:
        [
            {
                "trade_id": 123456,
                "side": "buy",  # or "sell" (lowercase)
                "size": "0.5",
                "price": "42800.00",
                "time": "2024-01-01T12:00:00Z"
            },
            ...
        ]

        Advanced Trade API returns: {
            "trades": [
                {
                    "trade_id": "123456",
                    "side": "BUY",
                    ...
                }
            ]
        }
        """
        symbol = params["symbol"].upper()

        # Exchange API returns array directly, Advanced Trade wraps in "trades"
        trades_data = response if isinstance(response, list) else response.get("trades", [])
        if not isinstance(trades_data, list):
            trades_data = []

        out: list[Trade] = []

        for trade_data in trades_data:
            if not isinstance(trade_data, dict):
                continue

            try:
                # Extract trade ID (Exchange API uses int, Advanced Trade uses string)
                trade_id_raw = trade_data.get("trade_id", 0)
                trade_id = 0
                if trade_id_raw:
                    try:
                        trade_id = int(trade_id_raw)
                    except (ValueError, TypeError):
                        # Use hash if not numeric
                        trade_id = abs(hash(str(trade_id_raw))) % (10**10)

                # Extract price and size
                price_str = trade_data.get("price")
                size_str = trade_data.get("size")

                if not price_str or not size_str:
                    continue

                price = Decimal(str(price_str))
                quantity = Decimal(str(size_str))
                quote_quantity = price * quantity

                # Extract timestamp
                time_str = trade_data.get("time", "")
                if time_str:
                    # Parse ISO 8601 timestamp
                    if isinstance(time_str, str):
                        ts_str = time_str.replace("Z", "+00:00")
                        timestamp = datetime.fromisoformat(ts_str)
                    else:
                        timestamp = datetime.fromtimestamp(float(time_str), tz=UTC)
                else:
                    timestamp = datetime.now(UTC)

                # Extract side - Exchange API uses "buy"/"sell" (lowercase), Advanced Trade uses "BUY"/"SELL"
                side = trade_data.get("side", "").upper()
                # "BUY" means buyer is taker (not maker), so is_buyer_maker = False
                # "SELL" means seller is taker (not maker), so is_buyer_maker = True
                is_buyer_maker = side == "SELL"

                out.append(
                    Trade(
                        symbol=symbol,
                        trade_id=trade_id,
                        price=price,
                        quantity=quantity,
                        quote_quantity=quote_quantity,
                        timestamp=timestamp,
                        is_buyer_maker=is_buyer_maker,
                        is_best_match=None,  # Coinbase doesn't provide this
                    )
                )
            except (ValueError, TypeError, KeyError):
                # Skip invalid trades
                continue

        return out
