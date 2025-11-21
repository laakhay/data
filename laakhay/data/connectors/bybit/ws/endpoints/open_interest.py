"""Bybit open interest WebSocket endpoint specification and adapter.

This endpoint is Futures-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.bybit.config import WS_COMBINED_URLS, WS_SINGLE_URLS
from laakhay.data.core import MarketType
from laakhay.data.models import OpenInterest
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(market_type: MarketType) -> WSEndpointSpec:
    """Build open interest WebSocket endpoint specification.

    Args:
        market_type: Market type (must be futures)

    Returns:
        WSEndpointSpec for open interest streaming

    Raises:
        ValueError: If market_type is not FUTURES
    """
    if market_type != MarketType.FUTURES:
        raise ValueError("Open interest WebSocket is Futures-only on Bybit")

    ws_single = WS_SINGLE_URLS.get(market_type)
    ws_combined = WS_COMBINED_URLS.get(market_type)
    if not ws_single:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, _params: dict[str, Any]) -> str:
        # Bybit format: openInterest.{symbol}
        return f"openInterest.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        topics = ",".join(names)
        return f"{ws_combined}?topic={topics}"

    def build_single_url(name: str) -> str:
        return f"{ws_single}?topic={name}"

    max_streams = 50  # Bybit supports up to 50 topics per connection
    return WSEndpointSpec(
        id="open_interest",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Bybit open interest WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant open interest message."""
        if isinstance(payload, dict):
            topic = payload.get("topic", "")
            return topic.startswith("openInterest.")
        return False

    def parse(self, payload: Any) -> list[OpenInterest]:
        """Parse Bybit open interest WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of OpenInterest objects
        """
        out: list[OpenInterest] = []
        if not isinstance(payload, dict):
            return out

        try:
            topic = payload.get("topic", "")
            data = payload.get("data", {})

            # Extract symbol from topic: openInterest.{symbol}
            topic_parts = topic.split(".")
            if len(topic_parts) < 2:
                return out
            symbol = topic_parts[1]

            if not isinstance(data, dict):
                return out

            open_interest_str = data.get("openInterest", "0")
            timestamp_ms = data.get("timestamp", 0)

            out.append(
                OpenInterest(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC),
                    open_interest=Decimal(str(open_interest_str)),
                    open_interest_value=None,  # Bybit doesn't provide value
                )
            )
        except Exception:
            return []
        return out

