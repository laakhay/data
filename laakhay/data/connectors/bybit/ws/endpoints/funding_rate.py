"""Bybit funding rate WebSocket endpoint specification and adapter.

This endpoint is Futures-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.bybit.config import WS_COMBINED_URLS, WS_SINGLE_URLS
from laakhay.data.core import MarketType
from laakhay.data.models import FundingRate
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(market_type: MarketType) -> WSEndpointSpec:
    """Build funding rate WebSocket endpoint specification.

    Args:
        market_type: Market type (must be futures)

    Returns:
        WSEndpointSpec for funding rate streaming

    Raises:
        ValueError: If market_type is not FUTURES
    """
    if market_type != MarketType.FUTURES:
        raise ValueError("Funding rate WebSocket is Futures-only on Bybit")

    ws_single = WS_SINGLE_URLS.get(market_type)
    ws_combined = WS_COMBINED_URLS.get(market_type)
    if not ws_single:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # Bybit format: fundingRate.{symbol}
        return f"fundingRate.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        topics = ",".join(names)
        return f"{ws_combined}?topic={topics}"

    def build_single_url(name: str) -> str:
        return f"{ws_single}?topic={name}"

    max_streams = 50  # Bybit supports up to 50 topics per connection
    return WSEndpointSpec(
        id="funding_rate",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Bybit funding rate WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant funding rate message."""
        if isinstance(payload, dict):
            topic = payload.get("topic", "")
            return topic.startswith("fundingRate.")
        return False

    def parse(self, payload: Any) -> list[FundingRate]:
        """Parse Bybit funding rate WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of FundingRate objects
        """
        out: list[FundingRate] = []
        if not isinstance(payload, dict):
            return out

        try:
            topic = payload.get("topic", "")
            data = payload.get("data", {})

            # Extract symbol from topic: fundingRate.{symbol}
            topic_parts = topic.split(".")
            if len(topic_parts) < 2:
                return out
            symbol = topic_parts[1]

            if not isinstance(data, dict):
                return out

            funding_rate = Decimal(str(data.get("fundingRate", "0")))
            timestamp_ms = int(data.get("fundingRateTimestamp", 0))

            out.append(
                FundingRate(
                    symbol=symbol,
                    funding_time=datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC),
                    funding_rate=funding_rate,
                    mark_price=None,  # Bybit doesn't provide in funding rate stream
                )
            )
        except Exception:
            return []
        return out
