"""Coinbase trades WebSocket endpoint specification and adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.coinbase.config import WS_PUBLIC_URLS, normalize_symbol_from_coinbase, normalize_symbol_to_coinbase
from laakhay.data.core import MarketType
from laakhay.data.models import Trade
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(market_type: MarketType) -> WSEndpointSpec:
    """Build trades WebSocket endpoint specification.

    Args:
        market_type: Market type (only SPOT supported for Coinbase)

    Returns:
        WSEndpointSpec for trades streaming
    """
    if market_type != MarketType.SPOT:
        raise ValueError("Coinbase Advanced Trade API only supports Spot markets")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        """Build channel name for trades subscription."""
        product_id = normalize_symbol_to_coinbase(symbol)
        # Coinbase format: matches channel
        return f"{product_id}:matches"

    def build_combined_url(names: list[str]) -> str:
        """Build WebSocket URL for combined subscriptions."""
        return ws_url

    def build_single_url(name: str) -> str:
        """Build WebSocket URL for single subscription."""
        return ws_url

    max_streams = 50
    return WSEndpointSpec(
        id="trades",
        combined_supported=True,
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Coinbase trades WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if message is a trade update."""
        if isinstance(payload, dict):
            # Exchange API uses "match" for new trades and "last_match" for the last trade before subscription
            msg_type = payload.get("type", "")
            return msg_type in ("match", "last_match")
        return False

    def parse(self, payload: Any) -> list[Trade]:
        """Parse trade message to Trade."""
        out: list[Trade] = []
        if not isinstance(payload, dict):
            return out

        try:
            # Extract product_id and normalize
            product_id = payload.get("product_id", "")
            if not product_id:
                return out

            symbol = normalize_symbol_from_coinbase(product_id)

            # Coinbase match format (expected):
            # {
            #   "type": "match",
            #   "product_id": "BTC-USD",
            #   "price": "42800.00",
            #   "size": "0.5",
            #   "time": "2024-01-01T12:00:00Z",
            #   "side": "BUY",
            #   "trade_id": "123456"
            # }

            price_str = payload.get("price")
            size_str = payload.get("size")

            if not price_str or not size_str:
                return out

            price = Decimal(str(price_str))
            quantity = Decimal(str(size_str))
            quote_quantity = price * quantity

            # Parse timestamp
            time_str = payload.get("time", "")
            if time_str:
                if isinstance(time_str, str):
                    ts_str = time_str.replace("Z", "+00:00")
                    timestamp = datetime.fromisoformat(ts_str)
                else:
                    timestamp = datetime.fromtimestamp(float(time_str), tz=UTC)
            else:
                timestamp = datetime.now(UTC)

            # Extract trade ID
            trade_id_str = payload.get("trade_id", "")
            trade_id = 0
            if trade_id_str:
                try:
                    trade_id = int(trade_id_str)
                except (ValueError, TypeError):
                    trade_id = abs(hash(trade_id_str)) % (10**10)

            # Extract side - Exchange API uses lowercase "buy"/"sell"
            side = payload.get("side", "").upper()
            # "BUY" means buyer is taker, "SELL" means seller is taker
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
        except Exception:
            return []

        return out

