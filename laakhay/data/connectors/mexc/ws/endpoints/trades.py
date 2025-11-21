"""MEXC trades WebSocket endpoint specification and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.mexc.config import WS_COMBINED_URLS, WS_SINGLE_URLS
from laakhay.data.core import MarketType
from laakhay.data.models import Trade
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(market_type: MarketType) -> WSEndpointSpec:
    """Build trades WebSocket endpoint specification.

    Args:
        market_type: Market type (spot or futures)

    Returns:
        WSEndpointSpec for trades streaming
    """
    ws_single = WS_SINGLE_URLS.get(market_type)
    ws_combined = WS_COMBINED_URLS.get(market_type)
    if not ws_single:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # MEXC uses format: spot@public.deals.<symbol> or similar
        return f"spot@public.deals.{symbol.lower()}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        return f"{ws_combined}?streams={'/'.join(names)}"

    def build_single_url(name: str) -> str:
        return f"{ws_single}/{name}"

    max_streams = 200 if market_type == MarketType.FUTURES else 1024
    return WSEndpointSpec(
        id="trades",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing MEXC trades WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant trades message."""
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            # MEXC may use "deals" or "trade" as event type
            return isinstance(data, dict) and (
                data.get("e") == "trade" or data.get("e") == "deals" or "p" in data
            )
        return False

    def parse(self, payload: Any) -> list[Trade]:
        """Parse MEXC trades WebSocket message.

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
            # MEXC may use different field names, try both
            symbol = str(d.get("s") or d.get("symbol") or payload.get("symbol", ""))
            trade_id = int(d.get("t") or d.get("tradeId") or d.get("id") or 0)
            price = Decimal(str(d.get("p") or d.get("price") or 0))
            quantity = Decimal(str(d.get("q") or d.get("quantity") or d.get("qty") or 0))
            timestamp_ms = int(d.get("T") or d.get("time") or d.get("timestamp") or 0)
            is_buyer_maker = bool(
                d.get("m") or d.get("isBuyerMaker") or d.get("is_buyer_maker", False)
            )

            # Calculate quote quantity if not provided
            quote_quantity = Decimal(str(d.get("quoteQty") or d.get("quote_quantity") or 0))
            if quote_quantity == 0:
                quote_quantity = price * quantity

            out.append(
                Trade(
                    symbol=symbol,
                    trade_id=trade_id,
                    price=price,
                    quantity=quantity,
                    quote_quantity=quote_quantity,
                    timestamp=datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC),
                    is_buyer_maker=is_buyer_maker,
                    is_best_match=d.get("M") or d.get("isBestMatch"),
                )
            )
        except Exception:
            return []
        return out
