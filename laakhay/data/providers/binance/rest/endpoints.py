"""Binance REST endpoint specs."""

from __future__ import annotations

from typing import Any

from ....core import MarketType
from ....io import RestEndpointSpec


def _klines_path(params: dict[str, Any]) -> str:
    market: MarketType = params["market_type"]
    return "/fapi/v1/klines" if market == MarketType.FUTURES else "/api/v3/klines"


def candles_spec() -> RestEndpointSpec:
    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        q: dict[str, Any] = {
            "symbol": params["symbol"].upper(),
            "interval": params["interval_str"],
        }
        if params.get("start_time"):
            q["startTime"] = int(params["start_time"].timestamp() * 1000)
        if params.get("end_time"):
            q["endTime"] = int(params["end_time"].timestamp() * 1000)
        if params.get("limit"):
            q["limit"] = min(int(params["limit"]), 1000)
        return q

    return RestEndpointSpec(
        id="ohlcv",
        method="GET",
        build_path=_klines_path,
        build_query=build_query,
    )


def exchange_info_spec() -> RestEndpointSpec:
    def build_path(params: dict[str, Any]) -> str:
        market: MarketType = params["market_type"]
        return "/fapi/v1/exchangeInfo" if market == MarketType.FUTURES else "/api/v3/exchangeInfo"

    return RestEndpointSpec(
        id="exchange_info",
        method="GET",
        build_path=build_path,
        build_query=lambda _: {},
    )


def exchange_info_raw_spec() -> RestEndpointSpec:
    # Same as exchange_info_spec but kept separate to emphasize raw passthrough
    def build_path(params: dict[str, Any]) -> str:
        market: MarketType = params["market_type"]
        return "/fapi/v1/exchangeInfo" if market == MarketType.FUTURES else "/api/v3/exchangeInfo"

    return RestEndpointSpec(
        id="exchange_info_raw",
        method="GET",
        build_path=build_path,
        build_query=lambda _: {},
    )


def order_book_spec() -> RestEndpointSpec:
    def build_path(params: dict[str, Any]) -> str:
        market: MarketType = params["market_type"]
        return "/fapi/v1/depth" if market == MarketType.FUTURES else "/api/v3/depth"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        return {
            "symbol": params["symbol"].upper(),
            "limit": int(params.get("limit", 100)),
        }

    return RestEndpointSpec(
        id="order_book",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


def open_interest_current_spec() -> RestEndpointSpec:
    def build_path(params: dict[str, Any]) -> str:
        market: MarketType = params["market_type"]
        # Current OI supported on Futures only
        if market != MarketType.FUTURES:
            raise ValueError("Open interest current endpoint is Futures-only on Binance")
        return "/fapi/v1/openInterest"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        return {"symbol": params["symbol"].upper()}

    return RestEndpointSpec(
        id="open_interest_current",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


def open_interest_hist_spec() -> RestEndpointSpec:
    def build_path(params: dict[str, Any]) -> str:
        market: MarketType = params["market_type"]
        # Historical OI supported on Futures only
        if market != MarketType.FUTURES:
            raise ValueError("Open interest history endpoint is Futures-only on Binance")
        # Binance endpoint for OI history
        return "/futures/data/openInterestHist"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        q: dict[str, Any] = {
            "symbol": params["symbol"].upper(),
            "period": params.get("period", "5m"),
            "limit": min(int(params.get("limit", 30)), 500),
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


def recent_trades_spec() -> RestEndpointSpec:
    def build_path(params: dict[str, Any]) -> str:
        market: MarketType = params["market_type"]
        return "/fapi/v1/trades" if market == MarketType.FUTURES else "/api/v3/trades"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        q: dict[str, Any] = {
            "symbol": params["symbol"].upper(),
            "limit": min(int(params.get("limit", 500)), 1000),
        }
        return q

    return RestEndpointSpec(
        id="recent_trades",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


def funding_rate_spec() -> RestEndpointSpec:
    def build_path(params: dict[str, Any]) -> str:
        market: MarketType = params["market_type"]
        if market != MarketType.FUTURES:
            raise ValueError("Funding rate endpoint is Futures-only on Binance")
        return "/fapi/v1/fundingRate"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        q: dict[str, Any] = {
            "symbol": params["symbol"].upper(),
            "limit": min(int(params.get("limit", 100)), 1000),
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
