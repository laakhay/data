"""Coinbase REST endpoint specs."""

from __future__ import annotations

from typing import Any

from ....core import MarketType
from ....io import RestEndpointSpec
from ..constants import normalize_symbol_to_coinbase


def candles_spec() -> RestEndpointSpec:
    """OHLCV/Candles endpoint spec for Coinbase Advanced Trade API."""

    def build_path(params: dict[str, Any]) -> str:
        # Coinbase only supports Spot markets
        market: MarketType = params["market_type"]
        if market != MarketType.SPOT:
            raise ValueError("Coinbase Advanced Trade API only supports Spot markets")

        symbol = params["symbol"]
        product_id = normalize_symbol_to_coinbase(symbol)
        return f"/products/{product_id}/candles"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        # Exchange API uses granularity in seconds (60, 300, 900, etc.)
        # Map interval_str to seconds
        interval_str = params["interval_str"]
        granularity_map = {
            "ONE_MINUTE": 60,
            "FIVE_MINUTE": 300,
            "FIFTEEN_MINUTE": 900,
            "THIRTY_MINUTE": 1800,
            "ONE_HOUR": 3600,
            "TWO_HOUR": 7200,
            "SIX_HOUR": 21600,
            "ONE_DAY": 86400,
        }
        granularity_sec = granularity_map.get(interval_str, 60)

        q: dict[str, Any] = {
            "granularity": granularity_sec,
        }
        # Exchange API uses ISO 8601 timestamps for start/end
        if params.get("start_time"):
            q["start"] = params["start_time"].isoformat().replace("+00:00", "Z")
        if params.get("end_time"):
            q["end"] = params["end_time"].isoformat().replace("+00:00", "Z")
        return q

    return RestEndpointSpec(
        id="ohlcv",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


def exchange_info_spec() -> RestEndpointSpec:
    """Products/Symbols endpoint spec."""

    def build_path(params: dict[str, Any]) -> str:
        market: MarketType = params["market_type"]
        if market != MarketType.SPOT:
            raise ValueError("Coinbase Advanced Trade API only supports Spot markets")
        return "/products"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        # Coinbase supports limit and offset for pagination
        # We'll fetch all products and filter by quote_asset if needed
        q: dict[str, Any] = {
            "limit": 250,  # Coinbase max per page
        }
        return q

    return RestEndpointSpec(
        id="exchange_info",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


def exchange_info_raw_spec() -> RestEndpointSpec:
    """Raw products endpoint (same as exchange_info but kept separate)."""

    def build_path(params: dict[str, Any]) -> str:
        market: MarketType = params["market_type"]
        if market != MarketType.SPOT:
            raise ValueError("Coinbase Advanced Trade API only supports Spot markets")
        return "/products"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        return {"limit": 250}

    return RestEndpointSpec(
        id="exchange_info_raw",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


def order_book_spec() -> RestEndpointSpec:
    """Order book endpoint spec."""

    def build_path(params: dict[str, Any]) -> str:
        market: MarketType = params["market_type"]
        if market != MarketType.SPOT:
            raise ValueError("Coinbase Advanced Trade API only supports Spot markets")

        symbol = params["symbol"]
        product_id = normalize_symbol_to_coinbase(symbol)
        return f"/products/{product_id}/book"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        # Exchange API uses level parameter (1, 2, or 3) instead of limit
        # Level 1: best bid/ask only
        # Level 2: top 50 bids/asks (default)
        # Level 3: full order book (up to 5000 levels)
        limit = int(params.get("limit", 50))
        if limit <= 1:
            level = 1
        elif limit <= 50:
            level = 2
        else:
            level = 3  # Full depth
        return {
            "level": level,
        }

    return RestEndpointSpec(
        id="order_book",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


def recent_trades_spec() -> RestEndpointSpec:
    """Recent trades endpoint spec."""

    def build_path(params: dict[str, Any]) -> str:
        market: MarketType = params["market_type"]
        if market != MarketType.SPOT:
            raise ValueError("Coinbase Advanced Trade API only supports Spot markets")

        symbol = params["symbol"]
        product_id = normalize_symbol_to_coinbase(symbol)
        return f"/products/{product_id}/trades"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        # Coinbase uses limit parameter (default 100, max 1000)
        limit = int(params.get("limit", 100))
        return {
            "limit": min(limit, 1000),
        }

    return RestEndpointSpec(
        id="recent_trades",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


# Note: Coinbase Advanced Trade API does not support:
# - Funding Rate (Futures feature, not available on Spot)
# - Open Interest (Futures feature, not available on Spot)
# These endpoints are intentionally omitted
