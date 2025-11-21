"""Bybit OHLCV WebSocket endpoint specification and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.bybit.config import INTERVAL_MAP, WS_COMBINED_URLS, WS_SINGLE_URLS
from laakhay.data.core import MarketType, Timeframe
from laakhay.data.models.streaming_bar import StreamingBar
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(market_type: MarketType) -> WSEndpointSpec:
    """Build OHLCV WebSocket endpoint specification.

    Args:
        market_type: Market type (spot or futures)

    Returns:
        WSEndpointSpec for OHLCV streaming
    """
    ws_single = WS_SINGLE_URLS.get(market_type)
    ws_combined = WS_COMBINED_URLS.get(market_type)
    if not ws_single:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        interval: Timeframe = params["interval"]
        interval_str = INTERVAL_MAP[interval]
        # Bybit format: kline.{interval}.{symbol}
        return f"kline.{interval_str}.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        # Bybit uses topic subscription format
        topics = ",".join(names)
        return f"{ws_combined}?topic={topics}"

    def build_single_url(name: str) -> str:
        # Bybit uses topic subscription format
        return f"{ws_single}?topic={name}"

    max_streams = 50  # Bybit supports up to 50 topics per connection
    return WSEndpointSpec(
        id="ohlcv",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Bybit OHLCV WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant OHLCV message."""
        if isinstance(payload, dict):
            topic = payload.get("topic", "")
            return topic.startswith("kline.")
        return False

    def parse(self, payload: Any) -> list[StreamingBar]:
        """Parse Bybit OHLCV WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of StreamingBar objects
        """
        out: list[StreamingBar] = []
        if not isinstance(payload, dict):
            return out

        try:
            topic = payload.get("topic", "")
            data = payload.get("data", {})
            if not isinstance(data, dict):
                return out

            # Extract symbol from topic: kline.{interval}.{symbol}
            topic_parts = topic.split(".")
            if len(topic_parts) < 3:
                return out
            symbol = topic_parts[2]

            # Bybit kline data structure
            kline = data.get("k", {})
            if not isinstance(kline, dict):
                return out

            out.append(
                StreamingBar(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(int(kline.get("t", 0)) / 1000, tz=UTC),
                    open=Decimal(str(kline.get("o", "0"))),
                    high=Decimal(str(kline.get("h", "0"))),
                    low=Decimal(str(kline.get("l", "0"))),
                    close=Decimal(str(kline.get("c", "0"))),
                    volume=Decimal(str(kline.get("v", "0"))),
                    is_closed=bool(kline.get("x", False)),
                )
            )
        except Exception:
            return []
        return out
