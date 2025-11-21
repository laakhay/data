"""Coinbase order book WebSocket endpoint specification and adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.coinbase.config import WS_PUBLIC_URLS, normalize_symbol_from_coinbase, normalize_symbol_to_coinbase
from laakhay.data.core import MarketType
from laakhay.data.models import OrderBook
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(market_type: MarketType) -> WSEndpointSpec:
    """Build order book WebSocket endpoint specification.

    Args:
        market_type: Market type (only SPOT supported for Coinbase)

    Returns:
        WSEndpointSpec for order book streaming
    """
    if market_type != MarketType.SPOT:
        raise ValueError("Coinbase Advanced Trade API only supports Spot markets")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        """Build channel name for order book subscription."""
        product_id = normalize_symbol_to_coinbase(symbol)
        # Coinbase format: level2 channel
        return f"{product_id}:level2"

    def build_combined_url(names: list[str]) -> str:
        """Build WebSocket URL for combined subscriptions."""
        return ws_url

    def build_single_url(name: str) -> str:
        """Build WebSocket URL for single subscription."""
        return ws_url

    max_streams = 50
    return WSEndpointSpec(
        id="order_book",
        combined_supported=True,
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Coinbase order book WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if message is an order book update."""
        if isinstance(payload, dict):
            # Coinbase format: {"type": "l2update", "product_id": "...", ...}
            msg_type = payload.get("type", "")
            return msg_type in ("l2update", "level2", "snapshot")
        return False

    def parse(self, payload: Any) -> list[OrderBook]:
        """Parse order book message to OrderBook."""
        out: list[OrderBook] = []
        if not isinstance(payload, dict):
            return out

        try:
            # Extract product_id and normalize
            product_id = payload.get("product_id", "")
            if not product_id:
                return out

            symbol = normalize_symbol_from_coinbase(product_id)

            # Coinbase level2 format (expected):
            # {
            #   "type": "l2update",
            #   "product_id": "BTC-USD",
            #   "changes": [
            #     ["buy", "42800.00", "1.5"],
            #     ["sell", "42810.00", "2.0"]
            #   ],
            #   "time": "2024-01-01T12:00:00Z"
            # }

            # For order book updates, we need to maintain state
            # This adapter returns the update, but the provider should maintain full book
            changes = payload.get("changes", [])
            if not isinstance(changes, list):
                return out

            bids = []
            asks = []

            for change in changes:
                if not isinstance(change, list) or len(change) < 3:
                    continue

                side = change[0]  # "buy" or "sell"
                price_str = change[1]
                size_str = change[2]

                try:
                    price = Decimal(str(price_str))
                    quantity = Decimal(str(size_str))

                    if side == "buy":
                        bids.append((price, quantity))
                    elif side == "sell":
                        asks.append((price, quantity))
                except (ValueError, TypeError):
                    continue

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

            # Note: This returns only the changes, not full book
            # Provider should maintain full order book state
            out.append(
                OrderBook(
                    symbol=symbol,
                    last_update_id=0,  # Coinbase doesn't provide sequence numbers
                    bids=bids,
                    asks=asks,
                    timestamp=timestamp,
                )
            )
        except Exception:
            return []

        return out

