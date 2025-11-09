"""Endpoint specifications for Kraken WebSocket streams."""

from __future__ import annotations

from typing import Any

from ....core import MarketType, Timeframe
from ....io import WSEndpointSpec
from ..constants import INTERVAL_MAP, WS_PUBLIC_URLS, normalize_symbol_to_kraken


def ohlcv_spec(market_type: MarketType) -> WSEndpointSpec:
    """OHLCV/Candles WebSocket endpoint spec."""

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        interval: Timeframe = params["interval"]
        interval_str = INTERVAL_MAP[interval]
        kraken_symbol = normalize_symbol_to_kraken(symbol, market_type)

        if market_type == MarketType.FUTURES:
            # Kraken Futures format: ohlc-{symbol}-{interval}
            return f"ohlc-{kraken_symbol}-{interval_str}"
        else:
            # Kraken Spot format: ohlc-{symbol}-{interval}
            return f"ohlc-{kraken_symbol}-{interval_str}"

    def build_combined_url(names: list[str]) -> str:
        # Kraken uses single URL, subscriptions sent via JSON messages
        return ws_url

    def build_single_url(name: str) -> str:
        # Kraken uses single URL, subscriptions sent via JSON messages
        return ws_url

    # Kraken supports multiple subscriptions per connection
    max_streams = 50  # Check Kraken's actual limit
    return WSEndpointSpec(
        id="ohlcv",
        combined_supported=True,  # Kraken supports multiple channels in one subscription
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
        kraken_symbol = normalize_symbol_to_kraken(symbol, market_type)

        if market_type == MarketType.FUTURES:
            # Kraken Futures format: trade-{symbol}
            return f"trade-{kraken_symbol}"
        else:
            # Kraken Spot format: trade-{symbol}
            return f"trade-{kraken_symbol}"

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

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        kraken_symbol = normalize_symbol_to_kraken(symbol, market_type)
        # Kraken order book depth - convert update_speed to depth
        update_speed = params.get("update_speed", "100ms")
        # Map update_speed to depth: "100ms" -> "10", "1000ms" -> "25", etc.
        if update_speed == "100ms":
            depth = "10"
        elif update_speed == "1000ms":
            depth = "25"
        else:
            depth = "10"  # Default

        if market_type == MarketType.FUTURES:
            # Kraken Futures format: book-{symbol}-{depth}
            return f"book-{kraken_symbol}-{depth}"
        else:
            # Kraken Spot format: book-{symbol}-{depth}
            return f"book-{kraken_symbol}-{depth}"

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


def open_interest_spec(market_type: MarketType) -> WSEndpointSpec:
    """Open interest WebSocket endpoint spec (Futures only)."""

    if market_type != MarketType.FUTURES:
        raise ValueError("Open interest WebSocket is Futures-only on Kraken")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        kraken_symbol = normalize_symbol_to_kraken(symbol, market_type)
        # Kraken Futures format: open_interest-{symbol}
        return f"open_interest-{kraken_symbol}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 50
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
        raise ValueError("Funding rate WebSocket is Futures-only on Kraken")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        kraken_symbol = normalize_symbol_to_kraken(symbol, market_type)
        # Kraken Futures format: funding_rate-{symbol}
        return f"funding_rate-{kraken_symbol}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 50
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
        raise ValueError("Mark price WebSocket is Futures-only on Kraken")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        kraken_symbol = normalize_symbol_to_kraken(symbol, market_type)
        # Kraken Futures format: ticker-{symbol} or mark_price-{symbol}
        return f"ticker-{kraken_symbol}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 50
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
        raise ValueError("Liquidations WebSocket is Futures-only on Kraken")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        kraken_symbol = normalize_symbol_to_kraken(symbol, market_type)
        # Kraken Futures format: liquidation-{symbol} (if available)
        return f"liquidation-{kraken_symbol}"

    def build_combined_url(names: list[str]) -> str:
        return ws_url

    def build_single_url(name: str) -> str:
        return ws_url

    max_streams = 50
    return WSEndpointSpec(
        id="liquidations",
        combined_supported=True,
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )
