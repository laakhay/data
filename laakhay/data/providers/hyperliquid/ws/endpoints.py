"""Endpoint specifications for Hyperliquid WebSocket streams.

Based on official API documentation:
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions

Subscription format: {"method": "subscribe", "subscription": {"type": "candle", "coin": "BTC", "interval": "15m"}}
"""

from __future__ import annotations

from typing import Any

from ....core import MarketType, Timeframe
from ....io import WSEndpointSpec
from ..constants import INTERVAL_MAP, WS_PUBLIC_URLS


def ohlcv_spec(market_type: MarketType) -> WSEndpointSpec:
    """OHLCV/Kline WebSocket endpoint spec.

    Subscription: {"method": "subscribe", "subscription": {"type": "candle", "coin": "BTC", "interval": "15m"}}
    """

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        interval: Timeframe = params["interval"]
        interval_str = INTERVAL_MAP[interval]
        # Format: "candle.{symbol}.{interval}" for topic identification
        # Actual subscription uses separate JSON message
        return f"candle.{symbol.upper()}.{interval_str}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    # Hyperliquid supports multiple subscriptions on same connection
    max_streams = 100  # Reasonable limit
    return WSEndpointSpec(
        id="ohlcv",
        combined_supported=True,
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


def trades_spec(market_type: MarketType) -> WSEndpointSpec:
    """Trade WebSocket endpoint spec.

    Subscription: {"method": "subscribe", "subscription": {"type": "trades", "coin": "BTC"}}
    """

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        return f"trades.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 100
    return WSEndpointSpec(
        id="trades",
        combined_supported=True,
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


def order_book_spec(market_type: MarketType) -> WSEndpointSpec:
    """Order book WebSocket endpoint spec.

    Subscription: {"method": "subscribe", "subscription": {"type": "l2Book", "coin": "BTC"}}
    """

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        return f"l2Book.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 100
    return WSEndpointSpec(
        id="order_book",
        combined_supported=True,
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


def open_interest_spec(market_type: MarketType) -> WSEndpointSpec:
    """Open interest WebSocket endpoint spec (Futures only).

    Note: Hyperliquid doesn't have direct OI subscription.
    OI is available via activeAssetCtx subscription.
    """

    if market_type != MarketType.FUTURES:
        raise ValueError("Open interest WebSocket is Futures-only on Hyperliquid")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # Use activeAssetCtx subscription: {"type": "activeAssetCtx", "coin": "BTC"}
        return f"activeAssetCtx.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 100
    return WSEndpointSpec(
        id="open_interest",
        combined_supported=True,
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


def funding_rate_spec(market_type: MarketType) -> WSEndpointSpec:
    """Funding rate WebSocket endpoint spec (Futures only).

    Note: Hyperliquid doesn't have direct funding rate subscription.
    Funding rates are in activeAssetCtx or userFundings (requires user address).
    """

    if market_type != MarketType.FUTURES:
        raise ValueError("Funding rate WebSocket is Futures-only on Hyperliquid")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # Use activeAssetCtx for funding rate data
        return f"activeAssetCtx.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 100
    return WSEndpointSpec(
        id="funding_rate",
        combined_supported=True,
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


def mark_price_spec(market_type: MarketType) -> WSEndpointSpec:
    """Mark price WebSocket endpoint spec (Futures only).

    Note: Hyperliquid doesn't have direct mark price subscription.
    Mark price is available via activeAssetCtx subscription.
    """

    if market_type != MarketType.FUTURES:
        raise ValueError("Mark price WebSocket is Futures-only on Hyperliquid")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # Use activeAssetCtx for mark price data
        return f"activeAssetCtx.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 100
    return WSEndpointSpec(
        id="mark_price",
        combined_supported=True,
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


def liquidations_spec(market_type: MarketType) -> WSEndpointSpec:
    """Liquidations WebSocket endpoint spec (Futures only).

    Note: Hyperliquid doesn't have public liquidation subscription.
    Liquidations are available via userEvents subscription (requires user address).
    For public liquidations, may need to monitor userEvents for multiple addresses.
    """

    if market_type != MarketType.FUTURES:
        raise ValueError("Liquidations WebSocket is Futures-only on Hyperliquid")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # Note: Liquidations require user address, not symbol-based
        # This is a placeholder - actual implementation may need user addresses
        return f"userEvents.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 100
    return WSEndpointSpec(
        id="liquidations",
        combined_supported=True,
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )
