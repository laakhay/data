"""Bybit order book WebSocket endpoint specification and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.bybit.config import WS_COMBINED_URLS, WS_SINGLE_URLS
from laakhay.data.core import MarketType
from laakhay.data.models import OrderBook
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(market_type: MarketType) -> WSEndpointSpec:
    """Build order book WebSocket endpoint specification.

    Args:
        market_type: Market type (spot or futures)

    Returns:
        WSEndpointSpec for order book streaming
    """
    ws_single = WS_SINGLE_URLS.get(market_type)
    ws_combined = WS_COMBINED_URLS.get(market_type)
    if not ws_single:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # Bybit format: orderbook.{depth}.{symbol}
        depth = params.get("depth", "1")
        return f"orderbook.{depth}.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        topics = ",".join(names)
        return f"{ws_combined}?topic={topics}"

    def build_single_url(name: str) -> str:
        return f"{ws_single}?topic={name}"

    max_streams = 50  # Bybit supports up to 50 topics per connection
    return WSEndpointSpec(
        id="order_book",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Bybit order book WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant order book message."""
        if isinstance(payload, dict):
            topic = payload.get("topic", "")
            return topic.startswith("orderbook.")
        return False

    def parse(self, payload: Any) -> list[OrderBook]:
        """Parse Bybit order book WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of OrderBook objects
        """
        out: list[OrderBook] = []
        if not isinstance(payload, dict):
            return out

        try:
            topic = payload.get("topic", "")
            data = payload.get("data", {})

            # Extract symbol from topic: orderbook.{depth}.{symbol}
            topic_parts = topic.split(".")
            if len(topic_parts) < 3:
                return out
            symbol = topic_parts[2]

            if not isinstance(data, dict):
                return out

            # Bybit orderbook structure
            bids = []
            asks = []

            bids_data = data.get("b", [])
            asks_data = data.get("a", [])

            if isinstance(bids_data, list):
                for item in bids_data:
                    if isinstance(item, list) and len(item) >= 2:
                        bids.append((Decimal(str(item[0])), Decimal(str(item[1]))))

            if isinstance(asks_data, list):
                for item in asks_data:
                    if isinstance(item, list) and len(item) >= 2:
                        asks.append((Decimal(str(item[0])), Decimal(str(item[1]))))

            timestamp_ms = data.get("ts", 0)
            last_update_id = data.get("u", 0)

            out.append(
                OrderBook(
                    symbol=symbol,
                    last_update_id=last_update_id,
                    bids=bids if bids else [(Decimal("0"), Decimal("0"))],
                    asks=asks if asks else [(Decimal("0"), Decimal("0"))],
                    timestamp=(
                        datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
                        if timestamp_ms
                        else datetime.now(UTC)
                    ),
                )
            )
        except Exception:
            return []
        return out
