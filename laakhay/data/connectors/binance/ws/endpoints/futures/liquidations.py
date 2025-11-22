"""Binance liquidations WebSocket endpoint specification and adapter.

This endpoint is Futures-only and uses a global stream (not symbol-specific).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.binance.config import get_ws_base_url
from laakhay.data.core import MarketType, MarketVariant
from laakhay.data.models import Liquidation
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(
    market_type: MarketType, market_variant: MarketVariant | None = None
) -> WSEndpointSpec:
    """Build liquidations WebSocket endpoint specification.

    Args:
        market_type: Market type (must be futures)

    Returns:
        WSEndpointSpec for liquidations streaming

    Raises:
        ValueError: If market_type is not FUTURES
    """
    if market_type != MarketType.FUTURES:
        raise ValueError("Liquidations WebSocket is Futures-only on Binance")

    ws_base = get_ws_base_url(market_type, market_variant)
    if not ws_base:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    # Binance liquidations stream is global: !forceOrder@arr
    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:  # symbol ignored
        return "!forceOrder@arr"

    def build_combined_url(names: list[str]) -> str:
        # Not applicable; single global stream
        raise ValueError("Combined stream not supported for liquidations")

    def build_single_url(name: str) -> str:
        return f"{ws_base}/{name}"

    return WSEndpointSpec(
        id="liquidations",
        combined_supported=False,
        max_streams_per_connection=1,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Binance liquidations WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant liquidations message."""
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            return isinstance(data, dict) and data.get("e") == "forceOrder" and "o" in data
        return False

    def parse(self, payload: Any) -> list[Liquidation]:
        """Parse Binance liquidations WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of Liquidation objects
        """
        out: list[Liquidation] = []
        if not isinstance(payload, dict):
            return out
        d = payload.get("data", payload)
        try:
            o = d["o"]
            event_time_ms = int(d.get("E") or o.get("T"))
            out.append(
                Liquidation(
                    symbol=str(o["s"]),
                    timestamp=datetime.fromtimestamp(event_time_ms / 1000, tz=UTC),
                    side=o["S"],
                    order_type=o["o"],
                    time_in_force=o["f"],
                    original_quantity=Decimal(str(o["q"])),
                    price=Decimal(str(o["p"])),
                    average_price=Decimal(str(o.get("ap", "0"))),
                    order_status=o["X"],
                    last_filled_quantity=Decimal(str(o.get("l", "0"))),
                    accumulated_quantity=Decimal(str(o.get("z", "0"))),
                    commission=None,
                    commission_asset=None,
                    trade_id=None,
                )
            )
        except Exception:
            return []
        return out
