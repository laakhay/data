"""Bybit mark price WebSocket endpoint specification and adapter.

This endpoint is Futures-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.bybit.config import WS_COMBINED_URLS, WS_SINGLE_URLS
from laakhay.data.core import MarketType
from laakhay.data.models import MarkPrice
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(market_type: MarketType) -> WSEndpointSpec:
    """Build mark price WebSocket endpoint specification.

    Args:
        market_type: Market type (must be futures)

    Returns:
        WSEndpointSpec for mark price streaming

    Raises:
        ValueError: If market_type is not FUTURES
    """
    if market_type != MarketType.FUTURES:
        raise ValueError("Mark price WebSocket is Futures-only on Bybit")

    ws_single = WS_SINGLE_URLS.get(market_type)
    ws_combined = WS_COMBINED_URLS.get(market_type)
    if not ws_single:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # Bybit format: markPrice.{symbol}
        return f"markPrice.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        topics = ",".join(names)
        return f"{ws_combined}?topic={topics}"

    def build_single_url(name: str) -> str:
        return f"{ws_single}?topic={name}"

    max_streams = 50  # Bybit supports up to 50 topics per connection
    return WSEndpointSpec(
        id="mark_price",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Bybit mark price WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant mark price message."""
        if isinstance(payload, dict):
            topic = payload.get("topic", "")
            return topic.startswith("markPrice.")
        return False

    def parse(self, payload: Any) -> list[MarkPrice]:
        """Parse Bybit mark price WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of MarkPrice objects
        """
        out: list[MarkPrice] = []
        if not isinstance(payload, dict):
            return out

        try:
            topic = payload.get("topic", "")
            data = payload.get("data", {})

            # Extract symbol from topic: markPrice.{symbol}
            topic_parts = topic.split(".")
            if len(topic_parts) < 2:
                return out
            symbol = topic_parts[1]

            if not isinstance(data, dict):
                return out

            mark_price = Decimal(str(data.get("markPrice", "0")))
            index_price = Decimal(str(data.get("indexPrice", "0"))) if data.get("indexPrice") else None
            timestamp_ms = int(data.get("timestamp", 0))

            out.append(
                MarkPrice(
                    symbol=symbol,
                    mark_price=mark_price,
                    index_price=index_price,
                    estimated_settle_price=None,  # Bybit doesn't provide
                    last_funding_rate=Decimal(str(data.get("fundingRate", "0"))) if data.get("fundingRate") else None,
                    next_funding_time=(
                        datetime.fromtimestamp(int(data["nextFundingTime"]) / 1000, tz=UTC)
                        if data.get("nextFundingTime")
                        else None
                    ),
                    timestamp=datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC),
                )
            )
        except Exception:
            return []
        return out

