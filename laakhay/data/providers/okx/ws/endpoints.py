"""Endpoint specifications for OKX WebSocket streams."""

from __future__ import annotations

from typing import Any

from ....core import MarketType, Timeframe
from ....io import WSEndpointSpec
from ..constants import INTERVAL_MAP, WS_PUBLIC_URLS, to_okx_symbol


def ohlcv_spec(market_type: MarketType) -> WSEndpointSpec:
    """OHLCV/Candles WebSocket endpoint spec."""

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        interval: Timeframe = params["interval"]
        interval_str = INTERVAL_MAP[interval]
        # OKX format: candles.{interval}.{symbol} (with hyphenated symbol)
        okx_symbol = to_okx_symbol(symbol)
        return f"candles.{interval_str}.{okx_symbol}"

    def build_combined_url(names: list[str]) -> str:
        # OKX uses single URL, subscriptions sent via JSON messages
        return ws_url

    def build_single_url(name: str) -> str:
        # OKX uses single URL, subscriptions sent via JSON messages
        return ws_url

    # OKX supports up to 20 subscriptions per connection
    max_streams = 20
    return WSEndpointSpec(
        id="ohlcv",
        combined_supported=True,  # OKX supports multiple topics in one subscription
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
        # OKX format: trades.{symbol} (with hyphenated symbol)
        okx_symbol = to_okx_symbol(symbol)
        return f"trades.{okx_symbol}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 20
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
        # OKX format: books.{depth}.{symbol} (with hyphenated symbol)
        # Default depth is 5
        depth = params.get("update_speed", "5")
        if depth == "100ms":
            depth = "5"  # Default depth
        elif depth == "1000ms":
            depth = "20"  # Higher depth
        okx_symbol = to_okx_symbol(symbol)
        return f"books.{depth}.{okx_symbol}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 20
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
        raise ValueError("Open interest WebSocket is Futures-only on OKX")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # OKX format: open-interest.{symbol} (with hyphenated symbol)
        okx_symbol = to_okx_symbol(symbol)
        return f"open-interest.{okx_symbol}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 20
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
        raise ValueError("Funding rate WebSocket is Futures-only on OKX")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # OKX format: funding-rate.{symbol} (with hyphenated symbol)
        okx_symbol = to_okx_symbol(symbol)
        return f"funding-rate.{okx_symbol}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 20
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
        raise ValueError("Mark price WebSocket is Futures-only on OKX")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # OKX format: mark-price.{symbol} (with hyphenated symbol)
        okx_symbol = to_okx_symbol(symbol)
        return f"mark-price.{okx_symbol}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 20
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
        raise ValueError("Liquidations WebSocket is Futures-only on OKX")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        # OKX format: liquidation.{symbol} (with hyphenated symbol)
        # Must subscribe to specific symbols
        okx_symbol = to_okx_symbol(symbol)
        return f"liquidation.{okx_symbol}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 20  # Can subscribe to multiple symbols
    return WSEndpointSpec(
        id="liquidations",
        combined_supported=True,  # Can combine multiple liquidation streams
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )
