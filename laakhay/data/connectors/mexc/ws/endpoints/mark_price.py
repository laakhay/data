"""MEXC mark price WebSocket endpoint specification and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.mexc.config import WS_COMBINED_URLS, WS_SINGLE_URLS
from laakhay.data.core import MarketType
from laakhay.data.models import MarkPrice
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(market_type: MarketType) -> WSEndpointSpec:
    """Build mark price WebSocket endpoint specification.

    Args:
        market_type: Market type (spot or futures)

    Returns:
        WSEndpointSpec for mark price streaming
    """
    ws_single = WS_SINGLE_URLS.get(market_type)
    ws_combined = WS_COMBINED_URLS.get(market_type)
    if not ws_single:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        update_speed: str = params.get("update_speed", "1s")
        # MEXC uses format: futures@markPrice.<symbol>.<speed> or similar
        return f"futures@markPrice.{symbol.lower()}.{update_speed}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        return f"{ws_combined}?streams={'/'.join(names)}"

    def build_single_url(name: str) -> str:
        return f"{ws_single}/{name}"

    max_streams = 200 if market_type == MarketType.FUTURES else 1024
    return WSEndpointSpec(
        id="mark_price",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing MEXC mark price WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant mark price message."""
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            return isinstance(data, dict) and (
                data.get("e") == "markPriceUpdate" or "p" in data or "markPrice" in data
            )
        return False

    def parse(self, payload: Any) -> list[MarkPrice]:
        """Parse MEXC mark price WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of MarkPrice objects
        """
        out: list[MarkPrice] = []
        if not isinstance(payload, dict):
            return out
        d = payload.get("data", payload)
        try:
            symbol = str(d.get("s") or d.get("symbol"))
            mark_price = Decimal(str(d.get("p") or d.get("markPrice") or d.get("mark_price") or 0))
            index_price = (
                Decimal(str(d.get("i") or d.get("indexPrice") or d.get("index_price")))
                if (d.get("i") or d.get("indexPrice") or d.get("index_price"))
                else None
            )
            estimated_settle_price = (
                Decimal(
                    str(
                        d.get("P")
                        or d.get("estimatedSettlePrice")
                        or d.get("estimated_settle_price")
                    )
                )
                if (d.get("P") or d.get("estimatedSettlePrice") or d.get("estimated_settle_price"))
                else None
            )
            last_funding_rate = (
                Decimal(str(d.get("r") or d.get("lastFundingRate") or d.get("last_funding_rate")))
                if (d.get("r") or d.get("lastFundingRate") or d.get("last_funding_rate"))
                else None
            )
            next_funding_time = (
                datetime.fromtimestamp(
                    int(d.get("T") or d.get("nextFundingTime") or 0) / 1000, tz=UTC
                )
                if (d.get("T") or d.get("nextFundingTime"))
                else None
            )
            timestamp_ms = int(d.get("E") or d.get("time") or d.get("timestamp") or 0)

            out.append(
                MarkPrice(
                    symbol=symbol,
                    mark_price=mark_price,
                    index_price=index_price,
                    estimated_settle_price=estimated_settle_price,
                    last_funding_rate=last_funding_rate,
                    next_funding_time=next_funding_time,
                    timestamp=datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC),
                )
            )
        except Exception:
            return []
        return out
