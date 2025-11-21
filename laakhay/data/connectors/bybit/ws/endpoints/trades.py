"""Bybit trades WebSocket endpoint specification and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.bybit.config import WS_COMBINED_URLS, WS_SINGLE_URLS
from laakhay.data.core import MarketType
from laakhay.data.models import Trade
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(market_type: MarketType) -> WSEndpointSpec:
    """Build trades WebSocket endpoint specification.

    Args:
        market_type: Market type (spot or futures)

    Returns:
        WSEndpointSpec for trades streaming
    """
    ws_single = WS_SINGLE_URLS.get(market_type)
    ws_combined = WS_COMBINED_URLS.get(market_type)
    if not ws_single:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # Bybit format: publicTrade.{symbol}
        return f"publicTrade.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        topics = ",".join(names)
        return f"{ws_combined}?topic={topics}"

    def build_single_url(name: str) -> str:
        return f"{ws_single}?topic={name}"

    max_streams = 50  # Bybit supports up to 50 topics per connection
    return WSEndpointSpec(
        id="trades",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Bybit trades WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant trades message."""
        if isinstance(payload, dict):
            topic = payload.get("topic", "")
            return topic.startswith("publicTrade.")
        return False

    def parse(self, payload: Any) -> list[Trade]:
        """Parse Bybit trades WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of Trade objects
        """
        out: list[Trade] = []
        if not isinstance(payload, dict):
            return out

        try:
            topic = payload.get("topic", "")
            data = payload.get("data", [])

            # Extract symbol from topic: publicTrade.{symbol}
            topic_parts = topic.split(".")
            if len(topic_parts) < 2:
                return out
            symbol = topic_parts[1]

            # Bybit returns array of trades
            if not isinstance(data, list):
                return out

            for trade_data in data:
                if not isinstance(trade_data, dict):
                    continue
                try:
                    out.append(
                        Trade(
                            symbol=symbol,
                            trade_id=str(trade_data.get("T", "")),  # Trade ID
                            price=Decimal(str(trade_data.get("p", "0"))),
                            quantity=Decimal(str(trade_data.get("v", "0"))),
                            quote_quantity=None,  # Bybit doesn't provide directly
                            timestamp=datetime.fromtimestamp(
                                int(trade_data.get("T", 0)) / 1000, tz=UTC
                            ),
                            is_buyer_maker=(trade_data.get("S", "").upper() == "Sell"),
                            is_best_match=None,  # Bybit doesn't provide
                        )
                    )
                except Exception:
                    continue
        except Exception:
            return []
        return out

