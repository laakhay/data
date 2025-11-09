"""Hyperliquid REST endpoint specs.

Based on official API documentation:
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint

All endpoints use POST /info with different type parameters in the request body.
"""

from __future__ import annotations

from typing import Any

from ....core import MarketType
from ....io import RestEndpointSpec
from ..constants import INTERVAL_MAP


def candles_spec() -> RestEndpointSpec:
    """OHLCV/Candles endpoint spec.

    POST /info with {"type": "candleSnapshot", "req": {...}}
    Returns at most 5000 candles. Only the most recent 5000 candles are available.
    """

    def build_path(params: dict[str, Any]) -> str:
        return "/info"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        return {}

    def build_body(params: dict[str, Any]) -> dict[str, Any]:
        """Build POST body for candle snapshot.

        API format: {"type": "candleSnapshot", "req": {"coin": "BTC", "interval": "15m", ...}}
        """
        interval_str = INTERVAL_MAP[params["interval"]]
        req: dict[str, Any] = {
            "coin": params[
                "symbol"
            ].upper(),  # For perps: coin name (e.g., "BTC"). For spot: "@{index}" or "PURR/USDC"
            "interval": interval_str,
        }
        if params.get("start_time"):
            req["startTime"] = int(params["start_time"].timestamp() * 1000)
        if params.get("end_time"):
            req["endTime"] = int(params["end_time"].timestamp() * 1000)
        # Note: API doesn't have explicit limit param, returns up to 5000 candles
        # Pagination uses startTime/endTime

        return {
            "type": "candleSnapshot",
            "req": req,
        }

    return RestEndpointSpec(
        id="ohlcv",
        method="POST",
        build_path=build_path,
        build_query=build_query,
        build_body=build_body,
    )


def exchange_info_spec() -> RestEndpointSpec:
    """Symbols/Meta endpoint spec.

    POST /info with {"type": "meta"}
    Returns exchange metadata including universe (symbols) for both perps and spot.
    """

    def build_path(params: dict[str, Any]) -> str:
        return "/info"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        return {}

    def build_body(params: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "meta",
        }

    return RestEndpointSpec(
        id="exchange_info",
        method="POST",
        build_path=build_path,
        build_query=build_query,
        build_body=build_body,
    )


def exchange_info_raw_spec() -> RestEndpointSpec:
    """Raw exchange info (same as exchange_info but kept separate)."""

    def build_path(params: dict[str, Any]) -> str:
        return "/info"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        return {}

    def build_body(params: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "meta",
        }

    return RestEndpointSpec(
        id="exchange_info_raw",
        method="POST",
        build_path=build_path,
        build_query=build_query,
        build_body=build_body,
    )


def order_book_spec() -> RestEndpointSpec:
    """Order book endpoint spec.

    POST /info with {"type": "l2Book", "coin": "BTC", ...}
    Returns at most 20 levels per side.
    """

    def build_path(params: dict[str, Any]) -> str:
        return "/info"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        return {}

    def build_body(params: dict[str, Any]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "type": "l2Book",
            "coin": params["symbol"].upper(),
        }
        # Optional: nSigFigs (2-5) and mantissa (1, 2, 5) for aggregation
        # Not implementing aggregation for now - can add later if needed
        return body

    return RestEndpointSpec(
        id="order_book",
        method="POST",
        build_path=build_path,
        build_query=build_query,
        build_body=build_body,
    )


def recent_trades_spec() -> RestEndpointSpec:
    """Recent trades endpoint spec.

    Note: Hyperliquid doesn't have a direct "recent trades" REST endpoint.
    Trades are available via WebSocket subscription or userFills endpoint.
    This endpoint is kept for API compatibility but may need to use WebSocket.
    For now, we'll use userFills with a public address or return empty.
    """

    def build_path(params: dict[str, Any]) -> str:
        return "/info"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        return {}

    def build_body(params: dict[str, Any]) -> dict[str, Any]:
        # Hyperliquid doesn't have public recent trades REST endpoint
        # Trades are streamed via WebSocket
        # Return empty body - adapter should handle this gracefully
        return {}

    return RestEndpointSpec(
        id="recent_trades",
        method="POST",
        build_path=build_path,
        build_query=build_query,
        build_body=build_body,
    )


def funding_rate_spec() -> RestEndpointSpec:
    """Funding rate history endpoint spec (Futures only).

    Note: Hyperliquid doesn't have a direct funding rate history REST endpoint.
    Funding rates are available via WebSocket userFundings subscription or in activeAssetCtx.
    This endpoint is kept for API compatibility but may need to use WebSocket.
    """

    def build_path(params: dict[str, Any]) -> str:
        market_type: MarketType = params["market_type"]
        if market_type != MarketType.FUTURES:
            raise ValueError("Funding rate endpoint is Futures-only on Hyperliquid")
        return "/info"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        return {}

    def build_body(params: dict[str, Any]) -> dict[str, Any]:
        # Hyperliquid doesn't have public funding rate history REST endpoint
        # Funding rates are in activeAssetCtx or streamed via WebSocket
        # Return empty body - adapter should handle this gracefully
        return {}

    return RestEndpointSpec(
        id="funding_rate",
        method="POST",
        build_path=build_path,
        build_query=build_query,
        build_body=build_body,
    )


def open_interest_current_spec() -> RestEndpointSpec:
    """Current open interest endpoint spec (Futures only).

    Note: Hyperliquid doesn't have a direct open interest REST endpoint.
    Open interest is available via WebSocket activeAssetCtx subscription.
    This endpoint is kept for API compatibility but may need to use WebSocket.
    """

    def build_path(params: dict[str, Any]) -> str:
        market_type: MarketType = params["market_type"]
        if market_type != MarketType.FUTURES:
            raise ValueError("Open interest endpoint is Futures-only on Hyperliquid")
        return "/info"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        return {}

    def build_body(params: dict[str, Any]) -> dict[str, Any]:
        # Hyperliquid doesn't have public open interest REST endpoint
        # Open interest is in activeAssetCtx or streamed via WebSocket
        # Return empty body - adapter should handle this gracefully
        return {}

    return RestEndpointSpec(
        id="open_interest_current",
        method="POST",
        build_path=build_path,
        build_query=build_query,
        build_body=build_body,
    )


def open_interest_hist_spec() -> RestEndpointSpec:
    """Historical open interest endpoint spec (Futures only).

    Note: Hyperliquid doesn't have a direct open interest history REST endpoint.
    Historical OI data is not available via REST API.
    This endpoint is kept for API compatibility but will return empty.
    """

    def build_path(params: dict[str, Any]) -> str:
        market_type: MarketType = params["market_type"]
        if market_type != MarketType.FUTURES:
            raise ValueError("Open interest history endpoint is Futures-only on Hyperliquid")
        return "/info"

    def build_query(params: dict[str, Any]) -> dict[str, Any]:
        return {}

    def build_body(params: dict[str, Any]) -> dict[str, Any]:
        # Hyperliquid doesn't have public open interest history REST endpoint
        # Return empty body - adapter should handle this gracefully
        return {}

    return RestEndpointSpec(
        id="open_interest_hist",
        method="POST",
        build_path=build_path,
        build_query=build_query,
        build_body=build_body,
    )
