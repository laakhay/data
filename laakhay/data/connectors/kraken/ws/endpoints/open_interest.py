"""Kraken open interest WebSocket endpoint specification and adapter.

This endpoint is Futures-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.kraken.config import WS_COMBINED_URLS, WS_SINGLE_URLS
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
        raise ValueError("Open interest WebSocket is Futures-only on Kraken")

    ws_single = WS_SINGLE_URLS.get(market_type)
    ws_combined = WS_COMBINED_URLS.get(market_type)
    if not ws_single:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        period: str = params.get("period", "5m")
        # Kraken uses open_interest-{symbol}-{period} format
        return f"open_interest-{symbol}-{period}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        return ws_combined

    def build_single_url(name: str) -> str:
        return ws_single

    return WSEndpointSpec(
        id="open_interest",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=50,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Kraken open interest WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant open interest message."""
        if isinstance(payload, dict):
            feed = payload.get("feed")
            return feed and "open_interest" in str(feed).lower()
        return False

    def parse(self, payload: Any) -> list[OpenInterest]:
        """Parse Kraken open interest WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of OpenInterest objects
        """
        out: list[OpenInterest] = []
        if not isinstance(payload, dict):
            return out

        try:
            # Kraken Futures format: {"feed": "open_interest", "symbol": "...", "openInterest": ..., "time": ...}
            symbol = str(payload.get("symbol", ""))
            oi_str = payload.get("openInterest") or payload.get("open_interest")
            time_ms = payload.get("time", 0)
            oi_value_str = payload.get("openInterestValue")

            if symbol and oi_str is not None:
                out.append(
                    OpenInterest(
                        symbol=symbol,
                        timestamp=(
                            datetime.fromtimestamp(time_ms / 1000, tz=UTC)
                            if time_ms
                            else datetime.now(UTC)
                        ),
                        open_interest=Decimal(str(oi_str)),
                        open_interest_value=(Decimal(str(oi_value_str)) if oi_value_str else None),
                    )
                )
        except Exception:
            return []
        return out
