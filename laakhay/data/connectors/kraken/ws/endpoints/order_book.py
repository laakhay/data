"""Kraken order book WebSocket endpoint specification and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.kraken.config import WS_COMBINED_URLS, WS_SINGLE_URLS
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
        # Map update_speed to depth for Kraken
        depth = "10" if update_speed == "100ms" else "25" if update_speed == "1000ms" else "10"
        # Kraken uses book-{symbol}-{depth} format
        return f"book-{symbol}-{depth}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        return ws_combined

    def build_single_url(name: str) -> str:
        return ws_single

    max_streams = 50 if market_type == MarketType.FUTURES else 100
    return WSEndpointSpec(
        id="order_book",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Kraken order book WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant order book message."""
        if isinstance(payload, dict):
            channel = payload.get("channel") or payload.get("feed")
            return channel and ("book" in str(channel).lower() or "orderbook" in str(channel).lower())
        return False

    def parse(self, payload: Any) -> list[OrderBook]:
        """Parse Kraken order book WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of OrderBook objects
        """
        out: list[OrderBook] = []
        if not isinstance(payload, dict):
            return out

        try:
            # Kraken Spot format: {"channel": "book", "data": {bids: [...], asks: [...]}, "symbol": "..."}
            # Kraken Futures format: {"feed": "book", "symbol": "...", "bids": [...], "asks": [...], "time": ...}
            data = payload.get("data")
            feed = payload.get("feed")
            symbol = str(payload.get("symbol", ""))

            if feed and "book" in feed.lower():
                # Futures format
                bids_data = payload.get("bids", [])
                asks_data = payload.get("asks", [])
                time_ms = payload.get("time", 0)

                bids: list[tuple[Decimal, Decimal]] = [
                    (Decimal(str(b[0])), Decimal(str(b[1]))) for b in bids_data if isinstance(b, list) and len(b) >= 2
                ]
                asks: list[tuple[Decimal, Decimal]] = [
                    (Decimal(str(a[0])), Decimal(str(a[1]))) for a in asks_data if isinstance(a, list) and len(a) >= 2
                ]

                if bids or asks:
                    out.append(
                        OrderBook(
                            symbol=symbol,
                            last_update_id=payload.get("sequenceNumber", 0),
                            bids=bids if bids else [(Decimal("0"), Decimal("0"))],
                            asks=asks if asks else [(Decimal("0"), Decimal("0"))],
                            timestamp=(
                                datetime.fromtimestamp(time_ms / 1000, tz=UTC)
                                if time_ms
                                else datetime.now(UTC)
                            ),
                        )
                    )
            elif data and isinstance(data, dict):
                # Spot format
                bids_data = data.get("bids", [])
                asks_data = data.get("asks", [])

                bids: list[tuple[Decimal, Decimal]] = [
                    (Decimal(str(b[0])), Decimal(str(b[1])))
                    for b in bids_data
                    if isinstance(b, list) and len(b) >= 2
                ]
                asks: list[tuple[Decimal, Decimal]] = [
                    (Decimal(str(a[0])), Decimal(str(a[1])))
                    for a in asks_data
                    if isinstance(a, list) and len(a) >= 2
                ]

                if bids or asks:
                    out.append(
                        OrderBook(
                            symbol=symbol,
                            last_update_id=0,
                            bids=bids if bids else [(Decimal("0"), Decimal("0"))],
                            asks=asks if asks else [(Decimal("0"), Decimal("0"))],
                            timestamp=datetime.now(UTC),
                        )
                    )
        except Exception:
            return []
        return out

