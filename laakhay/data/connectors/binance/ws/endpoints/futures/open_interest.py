"""Binance open interest WebSocket endpoint specification and adapter.

This endpoint is Futures-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.binance.config import get_ws_base_url
from laakhay.data.core import MarketType, MarketVariant
from laakhay.data.models import OpenInterest
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(
    market_type: MarketType, market_variant: MarketVariant | None = None
) -> WSEndpointSpec:
    """Build open interest WebSocket endpoint specification.

    Args:
        market_type: Market type (must be futures)

    Returns:
        WSEndpointSpec for open interest streaming

    Raises:
        ValueError: If market_type is not FUTURES
    """
    if market_type != MarketType.FUTURES:
        raise ValueError("Open interest WebSocket is Futures-only on Binance")

    ws_base = get_ws_base_url(market_type, market_variant)
    ws_base_combined = (
        ws_base.replace("/ws", "/stream") if "/ws" in ws_base else f"{ws_base}/stream"
    )
    if not ws_base:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        period: str = params.get("period", "5m")
        return f"{symbol.lower()}@openInterest@{period}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_base_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        return f"{ws_base_combined}?streams={'/'.join(names)}"

    def build_single_url(name: str) -> str:
        return f"{ws_base}/{name}"

    return WSEndpointSpec(
        id="open_interest",
        combined_supported=bool(ws_base_combined),
        max_streams_per_connection=200,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Binance open interest WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant open interest message."""
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            if not isinstance(data, dict):
                return False
            evt = data.get("e")
            return (evt is None) or evt == "openInterest"
        return False

    def parse(self, payload: Any) -> list[OpenInterest]:
        """Parse Binance open interest WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of OpenInterest objects
        """
        out: list[OpenInterest] = []
        if not isinstance(payload, dict):
            return out
        d = payload.get("data", payload)
        try:
            symbol = str(d.get("s") or d.get("symbol"))
            event_time_ms = int(d.get("E") or d.get("t") or d.get("eventTime"))
            oi_str = d.get("oi") or d.get("o") or d.get("openInterest")
            if symbol and oi_str is not None and event_time_ms is not None:
                out.append(
                    OpenInterest(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(event_time_ms / 1000, tz=UTC),
                        open_interest=Decimal(str(oi_str)),
                        open_interest_value=None,
                    )
                )
        except Exception:
            return []
        return out
