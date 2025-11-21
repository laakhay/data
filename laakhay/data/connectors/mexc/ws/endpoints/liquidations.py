"""MEXC liquidations WebSocket endpoint specification and adapter.

This endpoint is Futures-only and uses a global stream (not symbol-specific).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.mexc.config import WS_SINGLE_URLS
from laakhay.data.core import MarketType
from laakhay.data.models import Liquidation
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(market_type: MarketType) -> WSEndpointSpec:
    """Build liquidations WebSocket endpoint specification.

    Args:
        market_type: Market type (must be futures)

    Returns:
        WSEndpointSpec for liquidations streaming

    Raises:
        ValueError: If market_type is not FUTURES
    """
    if market_type != MarketType.FUTURES:
        raise ValueError("Liquidations WebSocket is Futures-only on MEXC")

    ws_single = WS_SINGLE_URLS.get(market_type)
    if not ws_single:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    # MEXC liquidations stream is global: futures@public.liquidation or similar
    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:  # symbol ignored
        return "futures@public.liquidation"

    def build_combined_url(names: list[str]) -> str:
        # Not applicable; single global stream
        raise ValueError("Combined stream not supported for liquidations")

    def build_single_url(name: str) -> str:
        return f"{ws_single}/{name}"

    return WSEndpointSpec(
        id="liquidations",
        combined_supported=False,
        max_streams_per_connection=1,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing MEXC liquidations WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant liquidations message."""
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            return isinstance(data, dict) and (
                data.get("e") == "forceOrder"
                or data.get("e") == "liquidation"
                or ("o" in data and "s" in data.get("o", {}))
            )
        return False

    def parse(self, payload: Any) -> list[Liquidation]:
        """Parse MEXC liquidations WebSocket message.

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
            o = d.get("o", d)
            event_time_ms = int(d.get("E") or o.get("T") or o.get("time") or d.get("time") or 0)
            out.append(
                Liquidation(
                    symbol=str(o.get("s") or o.get("symbol")),
                    timestamp=datetime.fromtimestamp(event_time_ms / 1000, tz=UTC),
                    side=o.get("S") or o.get("side"),
                    order_type=o.get("o") or o.get("orderType") or o.get("order_type"),
                    time_in_force=o.get("f") or o.get("timeInForce") or o.get("time_in_force"),
                    original_quantity=Decimal(str(o.get("q") or o.get("quantity") or 0)),
                    price=Decimal(str(o.get("p") or o.get("price") or 0)),
                    average_price=Decimal(
                        str(o.get("ap") or o.get("averagePrice") or o.get("average_price") or 0)
                    ),
                    order_status=o.get("X") or o.get("orderStatus") or o.get("order_status"),
                    last_filled_quantity=Decimal(
                        str(
                            o.get("l")
                            or o.get("lastFilledQuantity")
                            or o.get("last_filled_quantity")
                            or 0
                        )
                    ),
                    accumulated_quantity=Decimal(
                        str(
                            o.get("z")
                            or o.get("accumulatedQuantity")
                            or o.get("accumulated_quantity")
                            or 0
                        )
                    ),
                    commission=None,
                    commission_asset=None,
                    trade_id=None,
                )
            )
        except Exception:
            return []
        return out
