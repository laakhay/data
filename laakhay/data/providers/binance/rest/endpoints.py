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
