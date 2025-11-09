"""OKX REST endpoint specs."""

from __future__ import annotations

from typing import Any

from ....core import MarketType
from ....io import RestEndpointSpec
from ..constants import INST_TYPE_MAP, INTERVAL_MAP, to_okx_symbol


def candles_spec() -> RestEndpointSpec:
    """OHLCV/Candles endpoint spec."""

    def build_path(params: dict[str, Any]) -> str:
        return "/api/v5/market/candles"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        interval_str = INTERVAL_MAP[params["interval"]]

        q: dict[str, Any] = {
            "instId": to_okx_symbol(params["symbol"]),
            "bar": interval_str,
        }
        if params.get("start_time"):
            q["before"] = int(params["start_time"].timestamp() * 1000)
        if params.get("end_time"):
            q["after"] = int(params["end_time"].timestamp() * 1000)
        if params.get("limit"):
            q["limit"] = min(int(params["limit"]), 300)  # OKX max is 300
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
        return "/api/v5/public/instruments"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        market_type: MarketType = params["market_type"]
        inst_type = INST_TYPE_MAP[market_type]
        q: dict[str, Any] = {"instType": inst_type}
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
        return "/api/v5/public/instruments"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        market_type: MarketType = params["market_type"]
        inst_type = INST_TYPE_MAP[market_type]
        return {"instType": inst_type}

    return RestEndpointSpec(
        id="exchange_info_raw",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )


def order_book_spec() -> RestEndpointSpec:
    """Order book endpoint spec."""

    def build_path(params: dict[str, Any]) -> str:
        return "/api/v5/market/books"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        limit = int(params.get("limit", 20))
        # OKX supports: 1, 5, 10, 20, 50, 100, 200, 400
        # Map to nearest supported value
        if limit <= 1:
            limit = 1
        elif limit <= 5:
            limit = 5
        elif limit <= 10:
            limit = 10
        elif limit <= 20:
            limit = 20
        elif limit <= 50:
            limit = 50
        elif limit <= 100:
            limit = 100
        elif limit <= 200:
            limit = 200
        else:
            limit = 400

        return {
            "instId": to_okx_symbol(params["symbol"]),
            "sz": limit,
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
        return "/api/v5/market/trades"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        limit = min(int(params.get("limit", 100)), 500)  # OKX max is 500

        return {
            "instId": to_okx_symbol(params["symbol"]),
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
            raise ValueError("Funding rate endpoint is Futures-only on OKX")
        return "/api/v5/public/funding-rate"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        q: dict[str, Any] = {
            "instId": to_okx_symbol(params["symbol"]),
        }
        if params.get("limit"):
            q["limit"] = min(int(params.get("limit", 100)), 100)  # OKX max is 100
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
            raise ValueError("Open interest endpoint is Futures-only on OKX")
        return "/api/v5/public/open-interest"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        return {
            "instId": params["symbol"].upper(),
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
            raise ValueError("Open interest history endpoint is Futures-only on OKX")
        return "/api/v5/public/open-interest-history"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        from ..constants import OI_PERIOD_MAP

        period = params.get("period", "5m")
        period_str = OI_PERIOD_MAP.get(period, "5m")

        q: dict[str, Any] = {
            "instId": to_okx_symbol(params["symbol"]),
            "period": period_str,
            "limit": min(int(params.get("limit", 100)), 100),  # OKX max is 100
        }
        if params.get("start_time"):
            q["before"] = int(params["start_time"].timestamp() * 1000)
        if params.get("end_time"):
            q["after"] = int(params["end_time"].timestamp() * 1000)
        return q

    return RestEndpointSpec(
        id="open_interest_hist",
        method="GET",
        build_path=build_path,
        build_query=build_query,
    )
