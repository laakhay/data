"""Binance order book WebSocket endpoint specification and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.binance.config import WS_COMBINED_URLS, WS_SINGLE_URLS
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
        update_speed: str = params.get("update_speed", "100ms")
        return f"{symbol.lower()}@depth@{update_speed}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        return f"{ws_combined}?streams={'/'.join(names)}"

    def build_single_url(name: str) -> str:
        return f"{ws_single}/{name}"

    max_streams = 200 if market_type == MarketType.FUTURES else 1024
    return WSEndpointSpec(
        id="order_book",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Binance order book WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant order book message."""
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            return isinstance(data, dict) and data.get("e") == "depthUpdate"
        return False

    def parse(self, payload: Any) -> list[OrderBook]:
        """Parse Binance order book WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of OrderBook objects
        """
        out: list[OrderBook] = []
        if not isinstance(payload, dict):
            return out
        d = payload.get("data", payload)
        try:
            bids = [(Decimal(str(price)), Decimal(str(qty))) for price, qty in d.get("b", [])]
            asks = [(Decimal(str(price)), Decimal(str(qty))) for price, qty in d.get("a", [])]
            out.append(
                OrderBook(
                    symbol=str(d["s"]),
                    last_update_id=int(d["u"]),
                    bids=bids if bids else [(Decimal("0"), Decimal("0"))],
                    asks=asks if asks else [(Decimal("0"), Decimal("0"))],
                    timestamp=datetime.fromtimestamp(int(d["E"]) / 1000, tz=UTC),
                )
            )
        except Exception:
            return []
        return out
