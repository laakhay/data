"""Endpoint specifications for Bybit WebSocket streams."""

from __future__ import annotations

from typing import Any

from ....core import MarketType, Timeframe
from ....io import WSEndpointSpec
from ..constants import INTERVAL_MAP, WS_PUBLIC_URLS


def ohlcv_spec(market_type: MarketType) -> WSEndpointSpec:
    """OHLCV/Kline WebSocket endpoint spec."""

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        interval: Timeframe = params["interval"]
        interval_str = INTERVAL_MAP[interval]
        # Bybit format: kline.{interval}.{symbol}
        return f"kline.{interval_str}.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        # Bybit uses single URL, subscriptions sent via JSON messages
        # Return URL - subscriptions handled in provider
        return ws_url

    def build_single_url(name: str) -> str:
        # Bybit uses single URL, subscriptions sent via JSON messages
        return ws_url

    # Bybit supports up to 10 subscriptions per connection
    max_streams = 10
    return WSEndpointSpec(
        id="ohlcv",
        combined_supported=True,  # Bybit supports multiple topics in one subscription
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


def trades_spec(market_type: MarketType) -> WSEndpointSpec:
    """Trade WebSocket endpoint spec."""

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # Bybit format: publicTrade.{symbol}
        return f"publicTrade.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 10
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

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # Bybit format: orderbook.{depth}.{symbol}
        # Default depth is 50
        depth = params.get("update_speed", "50")  # Actually depth, not speed
        if depth == "100ms":
            depth = "50"  # Default depth
        elif depth == "1000ms":
            depth = "200"  # Higher depth
        return f"orderbook.{depth}.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 10
    return WSEndpointSpec(
        id="order_book",
        combined_supported=True,
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


def open_interest_spec(market_type: MarketType) -> WSEndpointSpec:
    """Open interest WebSocket endpoint spec (Futures only)."""

    if market_type != MarketType.FUTURES:
        raise ValueError("Open interest WebSocket is Futures-only on Bybit")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # Bybit format: openInterest.{symbol}
        return f"openInterest.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 10
    return WSEndpointSpec(
        id="open_interest",
        combined_supported=True,
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


def funding_rate_spec(market_type: MarketType) -> WSEndpointSpec:
    """Funding rate WebSocket endpoint spec (Futures only)."""

    if market_type != MarketType.FUTURES:
        raise ValueError("Funding rate WebSocket is Futures-only on Bybit")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # Bybit format: funding.{symbol}
        return f"funding.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 10
    return WSEndpointSpec(
        id="funding_rate",
        combined_supported=True,
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


def mark_price_spec(market_type: MarketType) -> WSEndpointSpec:
    """Mark price WebSocket endpoint spec (Futures only)."""

    if market_type != MarketType.FUTURES:
        raise ValueError("Mark price WebSocket is Futures-only on Bybit")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # Bybit format: markPrice.{symbol}
        return f"markPrice.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 10
    return WSEndpointSpec(
        id="mark_price",
        combined_supported=True,
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


def liquidations_spec(market_type: MarketType) -> WSEndpointSpec:
    """Liquidations WebSocket endpoint spec (Futures only)."""

    if market_type != MarketType.FUTURES:
        raise ValueError("Liquidations WebSocket is Futures-only on Bybit")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # Bybit format: liquidation.{symbol}
        # Must subscribe to specific symbols
        return f"liquidation.{symbol.upper()}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 10  # Can subscribe to multiple symbols
    return WSEndpointSpec(
        id="liquidations",
        combined_supported=True,  # Can combine multiple liquidation streams
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )
