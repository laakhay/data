"""Bybit REST endpoint specs."""

from __future__ import annotations

from typing import Any

from ....core import MarketType
from ....io import RestEndpointSpec
from ..constants import CATEGORY_MAP, INTERVAL_MAP


def candles_spec() -> RestEndpointSpec:
    """OHLCV/Kline endpoint spec."""

    def build_path(params: dict[str, Any]) -> str:
        return "/v5/market/kline"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        market_type: MarketType = params["market_type"]
        category = CATEGORY_MAP[market_type]
        interval_str = INTERVAL_MAP[params["interval"]]

        q: dict[str, Any] = {
            "category": category,
            "symbol": params["symbol"].upper(),
            "interval": interval_str,
        }
        if params.get("start_time"):
            q["start"] = int(params["start_time"].timestamp() * 1000)
        if params.get("end_time"):
            q["end"] = int(params["end_time"].timestamp() * 1000)
        if params.get("limit"):
            q["limit"] = min(int(params["limit"]), 200)  # Bybit max is 200
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
        return "/v5/market/instruments-info"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        market_type: MarketType = params["market_type"]
        category = CATEGORY_MAP[market_type]
        q: dict[str, Any] = {"category": category}
        # Bybit supports status filter, but we'll filter in adapter
        return q

    return RestEndpointSpec(
        id="exchange_info",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


def exchange_info_raw_spec() -> RestEndpointSpec:
    """Raw exchange info (same as exchange_info but kept separate)."""

    def build_path(params: dict[str, Any]) -> str:
        return "/v5/market/instruments-info"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        market_type: MarketType = params["market_type"]
        category = CATEGORY_MAP[market_type]
        return {"category": category}

    return RestEndpointSpec(
        id="exchange_info_raw",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


def order_book_spec() -> RestEndpointSpec:
    """Order book endpoint spec."""

    def build_path(params: dict[str, Any]) -> str:
        return "/v5/market/orderbook"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        market_type: MarketType = params["market_type"]
        category = CATEGORY_MAP[market_type]
        limit = int(params.get("limit", 50))
        # Bybit supports: 1, 25, 50, 100, 200
        # Map to nearest supported value
        if limit <= 1:
            limit = 1
        elif limit <= 25:
            limit = 25
        elif limit <= 50:
            limit = 50
        elif limit <= 100:
            limit = 100
        else:
            limit = 200

        return {
            "category": category,
            "symbol": params["symbol"].upper(),
            "limit": limit,
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
        return "/v5/market/recent-trade"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        market_type: MarketType = params["market_type"]
        category = CATEGORY_MAP[market_type]
        limit = min(int(params.get("limit", 50)), 1000)  # Bybit max is 1000

        return {
            "category": category,
            "symbol": params["symbol"].upper(),
            "limit": limit,
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
            raise ValueError("Funding rate endpoint is Futures-only on Bybit")
        return "/v5/market/funding/history"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        category = CATEGORY_MAP[MarketType.FUTURES]
        q: dict[str, Any] = {
            "category": category,
            "symbol": params["symbol"].upper(),
            "limit": min(int(params.get("limit", 200)), 200),  # Bybit max is 200
        }
        if params.get("start_time"):
            q["startTime"] = int(params["start_time"].timestamp() * 1000)
        if params.get("end_time"):
            q["endTime"] = int(params["end_time"].timestamp() * 1000)
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
            raise ValueError("Open interest endpoint is Futures-only on Bybit")
        return "/v5/market/open-interest"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        category = CATEGORY_MAP[MarketType.FUTURES]
        return {
            "category": category,
            "symbol": params["symbol"].upper(),
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
            raise ValueError("Open interest history endpoint is Futures-only on Bybit")
        return "/v5/market/open-interest"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        from ..constants import OI_PERIOD_MAP

        category = CATEGORY_MAP[MarketType.FUTURES]
        period = params.get("period", "5m")
        period_str = OI_PERIOD_MAP.get(period, "5min")

        q: dict[str, Any] = {
            "category": category,
            "symbol": params["symbol"].upper(),
            "intervalTime": period_str,
            "limit": min(int(params.get("limit", 200)), 200),  # Bybit max is 200
        }
        if params.get("start_time"):
            q["startTime"] = int(params["start_time"].timestamp() * 1000)
        if params.get("end_time"):
            q["endTime"] = int(params["end_time"].timestamp() * 1000)
        return q

    return RestEndpointSpec(
        id="open_interest_hist",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )
