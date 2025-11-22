"""Binance trades WebSocket endpoint specification and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.binance.config import get_ws_base_url
from laakhay.data.core import MarketType, MarketVariant
from laakhay.data.models import Trade
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(
    market_type: MarketType, market_variant: MarketVariant | None = None
) -> WSEndpointSpec:
    """Build trades WebSocket endpoint specification.

    Args:
        market_type: Market type (spot or futures)

    Returns:
        WSEndpointSpec for trades streaming
    """
    ws_base = get_ws_base_url(market_type, market_variant)
    ws_base_combined = (
        ws_base.replace("/ws", "/stream") if "/ws" in ws_base else f"{ws_base}/stream"
    )
    if not ws_base:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        return f"{symbol.lower()}@trade"

    def build_combined_url(names: list[str]) -> str:
        if not ws_base_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        return f"{ws_base_combined}?streams={'/'.join(names)}"

    def build_single_url(name: str) -> str:
        return f"{ws_base}/{name}"

    max_streams = 200 if market_type == MarketType.FUTURES else 1024
    return WSEndpointSpec(
        id="trades",
        combined_supported=bool(ws_base_combined),
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Binance trades WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant trades message."""
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            return isinstance(data, dict) and data.get("e") == "trade"
        return False

    def parse(self, payload: Any) -> list[Trade]:
        """Parse Binance trades WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of Trade objects
        """
        out: list[Trade] = []
        if not isinstance(payload, dict):
            return out
        d = payload.get("data", payload)
        try:
            out.append(
                Trade(
                    symbol=str(d["s"]),
                    trade_id=int(d["t"]),
                    price=Decimal(str(d["p"])),
                    quantity=Decimal(str(d["q"])),
                    quote_quantity=Decimal(str(d.get("q", "0"))) * Decimal(str(d["p"])),
                    timestamp=datetime.fromtimestamp(int(d["T"]) / 1000, tz=UTC),
                    is_buyer_maker=bool(d["m"]),
                    is_best_match=d.get("M"),
                )
            )
        except Exception:
            return []
        return out
