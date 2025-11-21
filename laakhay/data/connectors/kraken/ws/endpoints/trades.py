"""Kraken trades WebSocket endpoint specification and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.kraken.config import WS_COMBINED_URLS, WS_SINGLE_URLS
from laakhay.data.connectors.kraken.constants import (
    normalize_symbol_from_kraken,
    normalize_symbol_to_kraken,
)
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
        # Normalize symbol to Kraken format for stream name
        # The symbol passed in should be in standard format (e.g., "BTCUSD")
        # and needs to be converted to Kraken format (e.g., "XBT/USD" for spot or "PI_XBTUSD" for futures)
        normalized_symbol = normalize_symbol_to_kraken(symbol, market_type)
        # Kraken uses trade-{symbol} format
        return f"trade-{normalized_symbol}"

    def build_combined_url(names: list[str]) -> str:
        if not ws_combined:
            raise ValueError(f"Combined WS not supported for market type: {market_type}")
        return ws_combined

    def build_single_url(name: str) -> str:
        return ws_single

    max_streams = 50 if market_type == MarketType.FUTURES else 100
    return WSEndpointSpec(
        id="trades",
        combined_supported=bool(ws_combined),
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Kraken trades WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if payload is a relevant trades message."""
        if isinstance(payload, dict):
            channel = payload.get("channel") or payload.get("feed")
            return channel and "trade" in str(channel).lower()
        return False

    def parse(self, payload: Any) -> list[Trade]:
        """Parse Kraken trades WebSocket message.

        Args:
            payload: Raw WebSocket message

        Returns:
            List of Trade objects
        """
        out: list[Trade] = []
        if not isinstance(payload, dict):
            return out

        try:
            # Kraken Spot format: {"channel": "trade", "data": [[price, volume, time, buy/sell, market/limit, misc], ...], "symbol": "..."}
            # Kraken Futures format: {"feed": "trade", "symbol": "...", "price": ..., "qty": ..., "side": ..., "time": ...}
            # Or: {"channel": "trade", "symbol": "...", "data": [{"time": ..., "price": ..., "size": ..., "side": ...}, ...]}
            data = payload.get("data")
            feed = payload.get("feed")
            raw_symbol = str(payload.get("symbol", ""))
            # Infer market type from symbol format and normalize
            market_type = MarketType.FUTURES if raw_symbol.startswith("PI_") else MarketType.SPOT
            symbol = normalize_symbol_from_kraken(raw_symbol, market_type) if raw_symbol else ""

            # Check if it's a single trade message (Futures format without data array)
            if feed and "trade" in feed.lower():
                # Futures format - single trade in payload
                price_str = payload.get("price")
                qty_str = payload.get("qty") or payload.get("size")
                time_ms = payload.get("time", 0)
                side = payload.get("side", "")

                if price_str and qty_str and symbol:
                    out.append(
                        Trade(
                            symbol=symbol,
                            trade_id=int(hash(f"{symbol}{time_ms}{price_str}")),
                            price=Decimal(str(price_str)),
                            quantity=Decimal(str(qty_str)),
                            quote_quantity=Decimal(str(price_str)) * Decimal(str(qty_str)),
                            timestamp=(
                                datetime.fromtimestamp(time_ms / 1000, tz=UTC)
                                if time_ms
                                else datetime.now(UTC)
                            ),
                            is_buyer_maker=side.lower() == "buy",
                            is_best_match=None,
                        )
                    )
            elif data and isinstance(data, list):
                # Check if data is list of dicts (Futures format) or list of lists (Spot format)
                for row in data:
                    if isinstance(row, dict):
                        # Futures format: {"time": ..., "price": ..., "size": ..., "side": ...}
                        price_str = row.get("price")
                        qty_str = row.get("size") or row.get("qty")
                        time_ms = row.get("time", 0)
                        side = row.get("side", "")

                        if price_str and qty_str:
                            out.append(
                                Trade(
                                    symbol=symbol,
                                    trade_id=int(hash(f"{symbol}{time_ms}{price_str}")),
                                    price=Decimal(str(price_str)),
                                    quantity=Decimal(str(qty_str)),
                                    quote_quantity=Decimal(str(price_str)) * Decimal(str(qty_str)),
                                    timestamp=(
                                        datetime.fromtimestamp(time_ms / 1000, tz=UTC)
                                        if time_ms
                                        else datetime.now(UTC)
                                    ),
                                    is_buyer_maker=side.lower() == "buy",
                                    is_best_match=None,
                                )
                            )
                    elif isinstance(row, list) and len(row) >= 3:
                        # Spot format: [price, volume, time, buy/sell, ...]
                        price = Decimal(str(row[0]))
                        quantity = Decimal(str(row[1]))
                        time_float = float(row[2])
                        side_str = row[3] if len(row) > 3 else ""

                        out.append(
                            Trade(
                                symbol=symbol,
                                trade_id=int(hash(f"{symbol}{time_float}{row[0]}")),
                                price=price,
                                quantity=quantity,
                                quote_quantity=price * quantity,
                                timestamp=datetime.fromtimestamp(time_float, tz=UTC),
                                is_buyer_maker=side_str.lower() == "b",
                                is_best_match=None,
                            )
                        )
        except Exception:
            return []
        return out
