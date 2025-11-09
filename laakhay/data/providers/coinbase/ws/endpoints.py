"""Endpoint specifications for Coinbase WebSocket streams.

Coinbase Advanced Trade API uses channel-based WebSocket subscriptions.
Subscriptions are sent via JSON messages with product_ids and channels.
"""

from __future__ import annotations

from typing import Any

from ....core import MarketType, Timeframe
from ....io import WSEndpointSpec
from ..constants import INTERVAL_MAP, WS_PUBLIC_URLS, normalize_symbol_to_coinbase


def ohlcv_spec(market_type: MarketType) -> WSEndpointSpec:
    """OHLCV/Candles WebSocket endpoint spec."""

    if market_type != MarketType.SPOT:
        raise ValueError("Coinbase Advanced Trade API only supports Spot markets")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        """Build channel name for OHLCV subscription.

        Coinbase format: candles channel with product_id
        Note: Actual subscription uses JSON message, this is for identification
        """
        product_id = normalize_symbol_to_coinbase(symbol)
        interval: Timeframe = params["interval"]
        interval_str = INTERVAL_MAP[interval]
        # Format: {product_id}:{channel}:{granularity}
        return f"{product_id}:candles:{interval_str}"

    def build_combined_url(names: list[str]) -> str:
        """Build WebSocket URL for combined subscriptions.

        Coinbase uses single URL, subscriptions sent via JSON messages.
        """
        return ws_url

    def build_single_url(name: str) -> str:
        """Build WebSocket URL for single subscription."""
        return ws_url

    # Coinbase supports multiple subscriptions per connection
    # Exact limit TBD - using conservative estimate
    max_streams = 50
    return WSEndpointSpec(
        id="ohlcv",
        combined_supported=True,  # Coinbase supports multiple channels in one subscription
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


def trades_spec(market_type: MarketType) -> WSEndpointSpec:
    """Trade WebSocket endpoint spec."""

    if market_type != MarketType.SPOT:
        raise ValueError("Coinbase Advanced Trade API only supports Spot markets")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        """Build channel name for trades subscription."""
        product_id = normalize_symbol_to_coinbase(symbol)
        # Coinbase format: matches channel
        return f"{product_id}:matches"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 50
    return WSEndpointSpec(
        id="trades",
        combined_supported=True,
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


def order_book_spec(market_type: MarketType) -> WSEndpointSpec:
    """Order book WebSocket endpoint spec."""

    if market_type != MarketType.SPOT:
        raise ValueError("Coinbase Advanced Trade API only supports Spot markets")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        """Build channel name for order book subscription."""
        product_id = normalize_symbol_to_coinbase(symbol)
        # Coinbase format: level2 channel
        return f"{product_id}:level2"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 50
    return WSEndpointSpec(
        id="order_book",
        combined_supported=True,
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


# Note: Coinbase Advanced Trade API does not support:
# - Open Interest (Futures feature)
# - Funding Rate (Futures feature)
# - Mark Price (Futures feature)
# - Liquidations (Futures feature)
# These endpoints are intentionally omitted
