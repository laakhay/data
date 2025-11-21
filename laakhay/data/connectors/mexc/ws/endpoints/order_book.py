"""MEXC order book WebSocket endpoint specification and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.mexc.config import WS_COMBINED_URLS, WS_SINGLE_URLS
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
        # MEXC uses format: spot@public.increase.depth.<symbol> or similar
        # Note: update_speed parameter is accepted but not used in MEXC stream name format
        return f"spot@public.increase.depth.{symbol.lower()}"

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
    """Adapter for parsing MEXC order book WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant order book message."""
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            # MEXC may use "depthUpdate" or "depth" as event type
            return isinstance(data, dict) and (
                data.get("e") == "depthUpdate"
                or data.get("e") == "depth"
                or "b" in data
                or "bids" in data
            )
        return False

    def parse(self, payload: Any) -> list[OrderBook]:
        """Parse MEXC order book WebSocket message.

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
            # MEXC may use different field names, try both
            symbol = str(d.get("s") or d.get("symbol") or payload.get("symbol", ""))
            last_update_id = int(
                d.get("u") or d.get("lastUpdateId") or d.get("last_update_id") or 0
            )
            timestamp_ms = int(d.get("E") or d.get("time") or d.get("timestamp") or 0)

            # Try both "b"/"a" format and "bids"/"asks" format
            bids_data = d.get("b", d.get("bids", []))
            asks_data = d.get("a", d.get("asks", []))

            bids = (
                [(Decimal(str(price)), Decimal(str(qty))) for price, qty in bids_data]
                if bids_data
                else []
            )
            asks = (
                [(Decimal(str(price)), Decimal(str(qty))) for price, qty in asks_data]
                if asks_data
                else []
            )

            out.append(
                OrderBook(
                    symbol=symbol,
                    last_update_id=last_update_id,
                    bids=bids if bids else [(Decimal("0"), Decimal("0"))],
                    asks=asks if asks else [(Decimal("0"), Decimal("0"))],
                    timestamp=datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
                    if timestamp_ms > 0
                    else datetime.now(UTC),
                )
            )
        except Exception:
            return []
        return out
