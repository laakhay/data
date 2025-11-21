"""Kraken mark price WebSocket endpoint specification and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.kraken.config import WS_COMBINED_URLS, WS_SINGLE_URLS
from laakhay.data.connectors.kraken.constants import normalize_symbol_from_kraken
from laakhay.data.core import MarketType
from laakhay.data.models import FundingRate, MarkPrice
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
        # Kraken uses mark_price-{symbol}-{speed} format
        return f"mark_price-{symbol}-{update_speed}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        return ws_combined

    def build_single_url(name: str) -> str:
        return ws_single

    max_streams = 50 if market_type == MarketType.FUTURES else 100
    return WSEndpointSpec(
        id="mark_price",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Kraken mark price WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant mark price or funding rate message."""
        if isinstance(payload, dict):
            feed = payload.get("feed")
            channel = payload.get("channel")
            return (feed and "mark_price" in str(feed).lower()) or (
                channel and "funding_rate" in str(channel).lower()
            )
        return False

    def parse(self, payload: Any) -> list[MarkPrice | FundingRate]:
        """Parse Kraken mark price WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of MarkPrice or FundingRate objects
        """
        out: list[MarkPrice | FundingRate] = []
        if not isinstance(payload, dict):
            return out

        try:
            # Kraken Futures format: {"feed": "mark_price", "symbol": "...", "markPrice": ..., "indexPrice": ..., "time": ...}
            # Or: {"channel": "ticker", "symbol": "...", "data": {"markPrice": ..., ...}}
            # Or: {"channel": "funding_rate", "symbol": "...", "data": {"fundingRate": ..., ...}}
            raw_symbol = str(payload.get("symbol", ""))
            # Infer market type and normalize symbol
            market_type = MarketType.FUTURES if raw_symbol.startswith("PI_") else MarketType.SPOT
            symbol = normalize_symbol_from_kraken(raw_symbol, market_type) if raw_symbol else ""
            channel = payload.get("channel")
            feed = payload.get("feed")

            # Check if data is in nested "data" field
            data = payload.get("data")
            time_ms = payload.get("time", 0)

            # Check if this is a funding_rate message
            is_funding_rate = (channel and "funding_rate" in str(channel).lower()) or (
                feed and "funding_rate" in str(feed).lower()
            )

            if is_funding_rate:
                # Parse as FundingRate
                funding_rate_str = None
                mark_price_str = None

                if isinstance(data, dict):
                    funding_rate_str = data.get("fundingRate") or data.get("funding_rate")
                    mark_price_str = data.get("markPrice") or data.get("mark_price")
                    time_ms = time_ms or data.get("time", 0)
                else:
                    funding_rate_str = payload.get("fundingRate") or payload.get("funding_rate")
                    mark_price_str = payload.get("markPrice") or payload.get("mark_price")

                if symbol and funding_rate_str is not None:
                    timestamp = (
                        datetime.fromtimestamp(time_ms / 1000, tz=UTC)
                        if time_ms
                        else datetime.now(UTC)
                    )
                    out.append(
                        FundingRate(
                            symbol=symbol,
                            funding_rate=Decimal(str(funding_rate_str)),
                            mark_price=(Decimal(str(mark_price_str)) if mark_price_str else None),
                            funding_time=timestamp,
                            next_funding_time=(
                                datetime.fromtimestamp(
                                    (
                                        data.get("nextFundingTime")
                                        if isinstance(data, dict)
                                        else payload.get("nextFundingTime")
                                    )
                                    / 1000,
                                    tz=UTC,
                                )
                                if (
                                    data.get("nextFundingTime")
                                    if isinstance(data, dict)
                                    else payload.get("nextFundingTime")
                                )
                                else None
                            ),
                        )
                    )
            else:
                # Parse as MarkPrice
                mark_price_str = payload.get("markPrice") or payload.get("mark_price")

                if isinstance(data, dict):
                    mark_price_str = (
                        mark_price_str or data.get("markPrice") or data.get("mark_price")
                    )
                    time_ms = time_ms or data.get("time", 0)

                if symbol and mark_price_str:
                    out.append(
                        MarkPrice(
                            symbol=symbol,
                            mark_price=Decimal(str(mark_price_str)),
                            index_price=(
                                Decimal(
                                    str(
                                        data.get("indexPrice")
                                        if isinstance(data, dict)
                                        else payload.get("indexPrice")
                                    )
                                )
                                if (
                                    data.get("indexPrice")
                                    if isinstance(data, dict)
                                    else payload.get("indexPrice")
                                )
                                else None
                            ),
                            estimated_settle_price=(
                                Decimal(
                                    str(
                                        data.get("estimatedSettlePrice")
                                        if isinstance(data, dict)
                                        else payload.get("estimatedSettlePrice")
                                    )
                                )
                                if (
                                    data.get("estimatedSettlePrice")
                                    if isinstance(data, dict)
                                    else payload.get("estimatedSettlePrice")
                                )
                                else None
                            ),
                            last_funding_rate=(
                                Decimal(
                                    str(
                                        data.get("fundingRate")
                                        if isinstance(data, dict)
                                        else payload.get("fundingRate")
                                    )
                                )
                                if (
                                    data.get("fundingRate")
                                    if isinstance(data, dict)
                                    else payload.get("fundingRate")
                                )
                                else None
                            ),
                            next_funding_time=(
                                datetime.fromtimestamp(
                                    (
                                        data.get("nextFundingTime")
                                        if isinstance(data, dict)
                                        else payload.get("nextFundingTime")
                                    )
                                    / 1000,
                                    tz=UTC,
                                )
                                if (
                                    data.get("nextFundingTime")
                                    if isinstance(data, dict)
                                    else payload.get("nextFundingTime")
                                )
                                else None
                            ),
                            timestamp=(
                                datetime.fromtimestamp(time_ms / 1000, tz=UTC)
                                if time_ms
                                else datetime.now(UTC)
                            ),
                        )
                    )
        except Exception:
            return []
        return out
