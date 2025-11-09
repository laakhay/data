"""Kraken REST endpoint specs."""

from __future__ import annotations

from typing import Any

from ....core import MarketType
from ....io import RestEndpointSpec
from ..constants import INTERVAL_MAP, normalize_symbol_to_kraken


def candles_spec() -> RestEndpointSpec:
    """OHLCV/Candles endpoint spec.

    Note: Kraken Futures API may use different endpoint structure.
    For Spot: /0/public/OHLCData
    For Futures: Check if available in Futures API
    """

    def build_path(params: dict[str, Any]) -> str:
        market_type: MarketType = params["market_type"]
        if market_type == MarketType.FUTURES:
            # Kraken Futures API - use path parameter for symbol
            symbol = params["symbol"]
            kraken_symbol = normalize_symbol_to_kraken(symbol, market_type)
            return f"/instruments/{kraken_symbol}/candles"
        else:
            # Kraken Spot API
            return "/0/public/OHLCData"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        market_type: MarketType = params["market_type"]
        symbol = params["symbol"]
        kraken_symbol = normalize_symbol_to_kraken(symbol, market_type)
        interval_str = INTERVAL_MAP[params["interval"]]

        if market_type == MarketType.FUTURES:
            # Kraken Futures uses path parameter for symbol
            # Query params for interval, start, end, limit
            q: dict[str, Any] = {
                "interval": interval_str,
            }
            if params.get("start_time"):
                q["start"] = int(params["start_time"].timestamp() * 1000)
            if params.get("end_time"):
                q["end"] = int(params["end_time"].timestamp() * 1000)
            if params.get("limit"):
                q["limit"] = min(int(params["limit"]), 1000)  # Check Kraken's max limit
            return q
        else:
            # Kraken Spot API
            q: dict[str, Any] = {  # type: ignore[no-redef]
                "pair": kraken_symbol,
                "interval": interval_str,
            }
            if params.get("start_time"):
                q["since"] = int(params["start_time"].timestamp())
            if params.get("limit"):
                q["limit"] = min(int(params["limit"]), 720)  # Kraken Spot max is 720
            return q

    return RestEndpointSpec(
        id="ohlcv",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


def exchange_info_spec() -> RestEndpointSpec:
    """Symbols/Instruments info endpoint spec."""

    def build_path(params: dict[str, Any]) -> str:
        market_type: MarketType = params["market_type"]
        if market_type == MarketType.FUTURES:
            # Kraken Futures API
            return "/instruments"
        else:
            # Kraken Spot API
            return "/0/public/AssetPairs"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        # Kraken doesn't use query params for filtering, we'll filter in adapter
        return {}

    return RestEndpointSpec(
        id="exchange_info",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


def exchange_info_raw_spec() -> RestEndpointSpec:
    """Raw exchange info (same as exchange_info but kept separate)."""

    def build_path(params: dict[str, Any]) -> str:
        market_type: MarketType = params["market_type"]
        if market_type == MarketType.FUTURES:
            return "/instruments"
        else:
            return "/0/public/AssetPairs"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        return {}

    return RestEndpointSpec(
        id="exchange_info_raw",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


def order_book_spec() -> RestEndpointSpec:
    """Order book endpoint spec."""

    def build_path(params: dict[str, Any]) -> str:
        market_type: MarketType = params["market_type"]
        if market_type == MarketType.FUTURES:
            return "/orderbook"
        else:
            return "/0/public/Depth"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        market_type: MarketType = params["market_type"]
        symbol = params["symbol"]
        kraken_symbol = normalize_symbol_to_kraken(symbol, market_type)
        limit = int(params.get("limit", 100))

        if market_type == MarketType.FUTURES:
            # Kraken Futures API
            # Map limit to supported depths: 10, 25, 50, 100, 500, 1000
            if limit <= 10:
                depth = 10
            elif limit <= 25:
                depth = 25
            elif limit <= 50:
                depth = 50
            elif limit <= 100:
                depth = 100
            elif limit <= 500:
                depth = 500
            else:
                depth = 1000

            return {
                "symbol": kraken_symbol,
                "depth": depth,
            }
        else:
            # Kraken Spot API
            return {
                "pair": kraken_symbol,
                "count": min(limit, 500),  # Kraken Spot max is 500
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
        market_type: MarketType = params["market_type"]
        if market_type == MarketType.FUTURES:
            return "/history"
        else:
            return "/0/public/Trades"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        market_type: MarketType = params["market_type"]
        symbol = params["symbol"]
        kraken_symbol = normalize_symbol_to_kraken(symbol, market_type)
        limit = min(int(params.get("limit", 50)), 1000)  # Check Kraken's max

        if market_type == MarketType.FUTURES:
            # Kraken Futures API
            return {
                "symbol": kraken_symbol,
                "limit": limit,
            }
        else:
            # Kraken Spot API
            return {
                "pair": kraken_symbol,
                "count": limit,
            }

    return RestEndpointSpec(
        id="recent_trades",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


def funding_rate_spec() -> RestEndpointSpec:
    """Funding rate history endpoint spec (Futures only)."""

    def build_path(params: dict[str, Any]) -> str:
        market_type: MarketType = params["market_type"]
        if market_type != MarketType.FUTURES:
            raise ValueError("Funding rate endpoint is Futures-only on Kraken")
        # Kraken Futures API - check if this endpoint exists
        # May need to use ticker endpoint or separate funding endpoint
        return "/funding_rates"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        symbol = params["symbol"]
        kraken_symbol = normalize_symbol_to_kraken(symbol, MarketType.FUTURES)
        q: dict[str, Any] = {
            "symbol": kraken_symbol,
            "limit": min(int(params.get("limit", 100)), 1000),
        }
        if params.get("start_time"):
            q["start_time"] = int(params["start_time"].timestamp() * 1000)
        if params.get("end_time"):
            q["end_time"] = int(params["end_time"].timestamp() * 1000)
        return q

    return RestEndpointSpec(
        id="funding_rate",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


def open_interest_current_spec() -> RestEndpointSpec:
    """Current open interest endpoint spec (Futures only)."""

    def build_path(params: dict[str, Any]) -> str:
        market_type: MarketType = params["market_type"]
        if market_type != MarketType.FUTURES:
            raise ValueError("Open interest endpoint is Futures-only on Kraken")
        # Kraken Futures API - may use ticker endpoint
        return "/tickers"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        symbol = params["symbol"]
        kraken_symbol = normalize_symbol_to_kraken(symbol, MarketType.FUTURES)
        return {
            "symbol": kraken_symbol,
        }

    return RestEndpointSpec(
        id="open_interest_current",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


def open_interest_hist_spec() -> RestEndpointSpec:
    """Historical open interest endpoint spec (Futures only)."""

    def build_path(params: dict[str, Any]) -> str:
        market_type: MarketType = params["market_type"]
        if market_type != MarketType.FUTURES:
            raise ValueError("Open interest history endpoint is Futures-only on Kraken")
        # Kraken Futures API - check if historical OI endpoint exists
        return "/open_interest"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        symbol = params["symbol"]
        kraken_symbol = normalize_symbol_to_kraken(symbol, MarketType.FUTURES)
        q: dict[str, Any] = {
            "symbol": kraken_symbol,
            "limit": min(int(params.get("limit", 200)), 1000),
        }
        if params.get("start_time"):
            q["start_time"] = int(params["start_time"].timestamp() * 1000)
        if params.get("end_time"):
            q["end_time"] = int(params["end_time"].timestamp() * 1000)
        return q

    return RestEndpointSpec(
        id="open_interest_hist",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )
