"""Kraken mark price WebSocket endpoint specification and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.kraken.config import WS_COMBINED_URLS, WS_SINGLE_URLS
from laakhay.data.core import MarketType
from laakhay.data.models import MarkPrice
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(market_type: MarketType) -> WSEndpointSpec:
    """Build mark price WebSocket endpoint specification.

    Args:
        market_type: Market type (spot or futures)

    Returns:
        WSEndpointSpec for mark price streaming
    """
    ws_single = WS_SINGLE_URLS.get(market_type)
    ws_combined = WS_COMBINED_URLS.get(market_type)
    if not ws_single:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        update_speed: str = params.get("update_speed", "1s")
        # Kraken uses mark_price-{symbol}-{speed} format
        return f"mark_price-{symbol}-{update_speed}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        return ws_combined

    def build_single_url(name: str) -> str:
        return ws_single

    max_streams = 50 if market_type == MarketType.FUTURES else 100
    return WSEndpointSpec(
        id="mark_price",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Kraken mark price WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant mark price message."""
        if isinstance(payload, dict):
            feed = payload.get("feed")
            return feed and "mark_price" in str(feed).lower()
        return False

    def parse(self, payload: Any) -> list[MarkPrice]:
        """Parse Kraken mark price WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of MarkPrice objects
        """
        out: list[MarkPrice] = []
        if not isinstance(payload, dict):
            return out

        try:
            # Kraken Futures format: {"feed": "mark_price", "symbol": "...", "markPrice": ..., "indexPrice": ..., "time": ...}
            symbol = str(payload.get("symbol", ""))
            mark_price_str = payload.get("markPrice") or payload.get("mark_price")
            time_ms = payload.get("time", 0)

            if symbol and mark_price_str:
                out.append(
                    MarkPrice(
                        symbol=symbol,
                        mark_price=Decimal(str(mark_price_str)),
                        index_price=(
                            Decimal(str(payload.get("indexPrice")))
                            if payload.get("indexPrice")
                            else None
                        ),
                        estimated_settle_price=(
                            Decimal(str(payload.get("estimatedSettlePrice")))
                            if payload.get("estimatedSettlePrice")
                            else None
                        ),
                        last_funding_rate=(
                            Decimal(str(payload.get("fundingRate")))
                            if payload.get("fundingRate")
                            else None
                        ),
                        next_funding_time=(
                            datetime.fromtimestamp(payload.get("nextFundingTime") / 1000, tz=UTC)
                            if payload.get("nextFundingTime")
                            else None
                        ),
                        timestamp=(
                            datetime.fromtimestamp(time_ms / 1000, tz=UTC)
                            if time_ms
                            else datetime.now(UTC)
                        ),
                    )
                )
        except Exception:
            return []
        return out
