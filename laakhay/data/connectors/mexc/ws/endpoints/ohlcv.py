"""MEXC OHLCV WebSocket endpoint specification and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.mexc.config import INTERVAL_MAP, WS_COMBINED_URLS, WS_SINGLE_URLS
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
        # MEXC uses format: spot@kline.<symbol>.<interval> or similar
        return f"spot@kline.{symbol.lower()}.{INTERVAL_MAP[interval]}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        return f"{ws_combined}?streams={'/'.join(names)}"

    def build_single_url(name: str) -> str:
        return f"{ws_single}/{name}"

    max_streams = 200 if market_type == MarketType.FUTURES else 1024
    return WSEndpointSpec(
        id="ohlcv",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing MEXC OHLCV WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant OHLCV message."""
        if isinstance(payload, dict):
            if "data" in payload:
                return isinstance(payload.get("data"), dict) and "k" in payload.get("data", {})
            return "k" in payload or "c" in payload  # MEXC may use "c" for candle
        return False

    def parse(self, payload: Any) -> list[StreamingBar]:
        """Parse MEXC OHLCV WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of StreamingBar objects
        """
        out: list[StreamingBar] = []
        if not isinstance(payload, dict):
            return out
        data = payload.get("data", payload)
        k = data.get("k") if isinstance(data, dict) else None
        if not isinstance(k, dict):
            # Try alternative MEXC format
            k = data if isinstance(data, dict) and ("o" in data or "open" in data) else None
        if not isinstance(k, dict):
            return out
        try:
            # MEXC may use different field names, try both
            symbol = str(k.get("s") or data.get("s") or payload.get("symbol", ""))
            timestamp_ms = int(k.get("t") or k.get("T") or data.get("t") or 0)
            open_price = Decimal(str(k.get("o") or k.get("open") or 0))
            high_price = Decimal(str(k.get("h") or k.get("high") or 0))
            low_price = Decimal(str(k.get("l") or k.get("low") or 0))
            close_price = Decimal(str(k.get("c") or k.get("close") or 0))
            volume = Decimal(str(k.get("v") or k.get("volume") or 0))
            is_closed = bool(k.get("x") or k.get("is_closed") or False)

            out.append(
                StreamingBar(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC),
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                    is_closed=is_closed,
                )
            )
        except Exception:
            return []
        return out
