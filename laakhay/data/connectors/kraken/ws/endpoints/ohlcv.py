"""Kraken OHLCV WebSocket endpoint specification and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.kraken.config import INTERVAL_MAP, WS_COMBINED_URLS, WS_SINGLE_URLS
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
        # Kraken uses ohlc-{symbol}-{interval} format
        # Symbol is already in exchange format from router
        return f"ohlc-{symbol}-{interval_str}"

    def build_combined_url(names: list[str]) -> str:
        # Kraken uses single URL, subscriptions sent via JSON messages
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        return ws_combined

    def build_single_url(name: str) -> str:
        # Kraken uses single URL, subscriptions sent via JSON messages
        return ws_single

    # Kraken supports multiple subscriptions per connection
    max_streams = 50 if market_type == MarketType.FUTURES else 100
    return WSEndpointSpec(
        id="ohlcv",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Kraken OHLCV WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant OHLCV message."""
        if isinstance(payload, dict):
            # Kraken messages have different structure for spot vs futures
            # Spot: {"channel": "ohlc", "data": [...]}
            # Futures: {"feed": "ohlc_snapshot" or "ohlc", ...}
            channel = payload.get("channel") or payload.get("feed")
            return channel and "ohlc" in str(channel).lower()
        return False

    def parse(self, payload: Any) -> list[StreamingBar]:
        """Parse Kraken OHLCV WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of StreamingBar objects
        """
        out: list[StreamingBar] = []
        if not isinstance(payload, dict):
            return out

        try:
            # Kraken Spot format: {"channel": "ohlc", "data": [[time, etime, open, high, low, close, vwap, volume, count], symbol]}
            # Kraken Futures format: {"feed": "ohlc", "symbol": "...", "time": ..., "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...}
            data = payload.get("data")
            feed = payload.get("feed")

            if feed and "ohlc" in feed.lower():
                # Futures format
                symbol = str(payload.get("symbol", ""))
                time_ms = payload.get("time", 0)
                if time_ms and symbol:
                    out.append(
                        StreamingBar(
                            symbol=symbol,
                            timestamp=datetime.fromtimestamp(time_ms / 1000, tz=UTC),
                            open=Decimal(str(payload.get("open", "0"))),
                            high=Decimal(str(payload.get("high", "0"))),
                            low=Decimal(str(payload.get("low", "0"))),
                            close=Decimal(str(payload.get("close", "0"))),
                            volume=Decimal(str(payload.get("volume", "0"))),
                            is_closed=bool(payload.get("closed", False)),
                        )
                    )
            elif data and isinstance(data, list) and len(data) >= 8:
                # Spot format: [time, etime, open, high, low, close, vwap, volume, count]
                symbol = str(payload.get("symbol", ""))
                if symbol:
                    time_seconds = int(data[0])
                    out.append(
                        StreamingBar(
                            symbol=symbol,
                            timestamp=datetime.fromtimestamp(time_seconds, tz=UTC),
                            open=Decimal(str(data[2])),
                            high=Decimal(str(data[3])),
                            low=Decimal(str(data[4])),
                            close=Decimal(str(data[5])),
                            volume=Decimal(str(data[7])),
                            is_closed=bool(data[1]),  # etime indicates if closed
                        )
                    )
        except Exception:
            return []
        return out
