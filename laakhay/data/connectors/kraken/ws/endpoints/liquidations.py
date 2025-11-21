"""Kraken liquidations WebSocket endpoint specification and adapter.

This endpoint is Futures-only and uses a global stream (not symbol-specific).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.kraken.config import WS_SINGLE_URLS
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
        raise ValueError("Liquidations WebSocket is Futures-only on Kraken")

    ws_single = WS_SINGLE_URLS.get(market_type)
    if not ws_single:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    # Kraken liquidations stream is global: liquidations
    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:  # symbol ignored
        return "liquidations"

    def build_combined_url(names: list[str]) -> str:
        # Not applicable; single global stream
        raise ValueError("Combined stream not supported for liquidations")

    def build_single_url(name: str) -> str:
        return ws_single

    return WSEndpointSpec(
        id="liquidations",
        combined_supported=False,
        max_streams_per_connection=1,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Kraken liquidations WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant liquidations message."""
        if isinstance(payload, dict):
            feed = payload.get("feed")
            return feed and "liquidation" in str(feed).lower()
        return False

    def parse(self, payload: Any) -> list[Liquidation]:
        """Parse Kraken liquidations WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of Liquidation objects
        """
        out: list[Liquidation] = []
        if not isinstance(payload, dict):
            return out

        try:
            # Kraken Futures format: {"feed": "liquidation", "symbol": "...", "side": "...", "orderType": "...", "price": ..., "qty": ..., "time": ...}
            symbol = str(payload.get("symbol", ""))
            side = str(payload.get("side", ""))
            order_type = str(payload.get("orderType") or payload.get("order_type", ""))
            price_str = payload.get("price")
            qty_str = payload.get("qty") or payload.get("size")
            time_ms = payload.get("time", 0)

            if symbol and price_str and qty_str:
                out.append(
                    Liquidation(
                        symbol=symbol,
                        timestamp=(
                            datetime.fromtimestamp(time_ms / 1000, tz=UTC)
                            if time_ms
                            else datetime.now(UTC)
                        ),
                        side=side,
                        order_type=order_type,
                        time_in_force=payload.get("timeInForce") or "GTC",
                        original_quantity=Decimal(str(qty_str)),
                        price=Decimal(str(price_str)),
                        average_price=Decimal(str(payload.get("avgPrice", price_str))),
                        order_status=payload.get("status") or "FILLED",
                        last_filled_quantity=Decimal(str(payload.get("filledQty", qty_str))),
                        accumulated_quantity=Decimal(str(payload.get("cumQty", qty_str))),
                        commission=None,
                        commission_asset=None,
                        trade_id=int(hash(f"{symbol}{time_ms}{price_str}")) if time_ms else None,
                    )
                )
        except Exception:
            return []
        return out

