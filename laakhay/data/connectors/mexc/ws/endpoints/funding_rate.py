"""MEXC funding rate WebSocket endpoint specification and adapter.

This endpoint is Futures-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.mexc.config import WS_COMBINED_URLS, WS_SINGLE_URLS
from laakhay.data.core import MarketType
from laakhay.data.models import FundingRate
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(market_type: MarketType) -> WSEndpointSpec:
    """Build funding rate WebSocket endpoint specification.

    Args:
        market_type: Market type (must be futures)

    Returns:
        WSEndpointSpec for funding rate streaming

    Raises:
        ValueError: If market_type is not FUTURES
    """
    if market_type != MarketType.FUTURES:
        raise ValueError("Funding rate WebSocket is Futures-only on MEXC")

    ws_single = WS_SINGLE_URLS.get(market_type)
    ws_combined = WS_COMBINED_URLS.get(market_type)
    if not ws_single:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        update_speed: str = params.get("update_speed", "1s")
        # MEXC uses format: futures@fundingRate.<symbol>.<speed> or similar
        return f"futures@fundingRate.{symbol.lower()}.{update_speed}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        return f"{ws_combined}?streams={'/'.join(names)}"

    def build_single_url(name: str) -> str:
        return f"{ws_single}/{name}"

    return WSEndpointSpec(
        id="funding_rate",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=200,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing MEXC funding rate WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant funding rate message."""
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            return isinstance(data, dict) and (
                data.get("e") == "fundingRate" or "fundingRate" in data or "funding_rate" in data
            )
        return False

    def parse(self, payload: Any) -> list[FundingRate]:
        """Parse MEXC funding rate WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of FundingRate objects
        """
        out: list[FundingRate] = []
        if not isinstance(payload, dict):
            return out
        d = payload.get("data", payload)
        try:
            symbol = str(d.get("s") or d.get("symbol"))
            funding_time_ms = int(
                d.get("fundingTime") or d.get("funding_time") or d.get("T") or d.get("time") or 0
            )
            funding_rate = Decimal(
                str(d.get("fundingRate") or d.get("funding_rate") or d.get("r") or 0)
            )
            mark_price = (
                Decimal(str(d.get("markPrice") or d.get("mark_price") or d.get("p")))
                if (d.get("markPrice") or d.get("mark_price") or d.get("p"))
                else None
            )

            out.append(
                FundingRate(
                    symbol=symbol,
                    funding_time=datetime.fromtimestamp(funding_time_ms / 1000, tz=UTC),
                    funding_rate=funding_rate,
                    mark_price=mark_price,
                )
            )
        except Exception:
            return []
        return out
