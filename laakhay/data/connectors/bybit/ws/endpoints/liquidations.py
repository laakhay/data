"""Bybit liquidations WebSocket endpoint specification and adapter.

This endpoint is Futures-only and uses a global stream (not symbol-specific).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.bybit.config import WS_SINGLE_URLS
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
        raise ValueError("Liquidations WebSocket is Futures-only on Bybit")

    ws_single = WS_SINGLE_URLS.get(market_type)
    if not ws_single:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    # Bybit liquidations stream is global: liquidation.{symbol} or all symbols
    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # Bybit supports both symbol-specific and global liquidation streams
        # For global, use "liquidation" without symbol
        # For symbol-specific, use "liquidation.{symbol}"
        if symbol and symbol != "!global":
            return f"liquidation.{symbol.upper()}"
        return "liquidation"  # Global stream

    def build_combined_url(names: list[str]) -> str:
        # Not applicable for liquidations; single global stream
        raise ValueError("Combined stream not supported for liquidations")

    def build_single_url(name: str) -> str:
        return f"{ws_single}?topic={name}"

    return WSEndpointSpec(
        id="liquidations",
        combined_supported=False,
        max_streams_per_connection=1,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Bybit liquidations WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant liquidations message."""
        if isinstance(payload, dict):
            topic = payload.get("topic", "")
            return topic.startswith("liquidation")
        return False

    def parse(self, payload: Any) -> list[Liquidation]:
        """Parse Bybit liquidations WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of Liquidation objects
        """
        out: list[Liquidation] = []
        if not isinstance(payload, dict):
            return out

        try:
            data = payload.get("data", {})
            if not isinstance(data, dict):
                return out

            # Bybit liquidation structure
            symbol = str(data.get("symbol", ""))
            side = str(data.get("side", "")).lower()  # "Buy" or "Sell" -> "long" or "short"
            price = Decimal(str(data.get("price", "0")))
            quantity = Decimal(str(data.get("qty", "0")))
            timestamp_ms = int(data.get("time", 0))

            # Convert Bybit side to our format
            liquidation_side = "long" if side.upper() == "SELL" else "short"

            out.append(
                Liquidation(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC),
                    side=liquidation_side,
                    order_type="LIMIT",  # Bybit doesn't specify
                    time_in_force="GTC",  # Bybit doesn't specify
                    original_quantity=quantity,
                    price=price,
                    average_price=price,  # Use price as average
                    order_status="FILLED",
                    last_filled_quantity=quantity,
                    accumulated_quantity=quantity,
                    commission=None,
                    commission_asset=None,
                    trade_id=None,
                )
            )
        except Exception:
            return []
        return out
