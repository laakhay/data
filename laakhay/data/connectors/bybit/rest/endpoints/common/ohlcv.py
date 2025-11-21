"""Bybit OHLCV (kline) endpoint definition and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.bybit.config import CATEGORY_MAP, INTERVAL_MAP
from laakhay.data.core import MarketType
from laakhay.data.core.exceptions import DataError
from laakhay.data.models import OHLCV, Bar, SeriesMeta
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def _extract_result(response: Any) -> Any:
    """Extract result from Bybit's response wrapper."""
    if not isinstance(response, dict):
        raise DataError(f"Invalid response format: expected dict, got {type(response)}")

    ret_code = response.get("retCode", -1)
    ret_msg = response.get("retMsg", "Unknown error")

    if ret_code != 0:
        raise DataError(f"Bybit API error: {ret_msg} (code: {ret_code})")

    result = response.get("result")
    if result is None:
        raise DataError("Bybit API response missing 'result' field")

    return result


def build_path(_params: dict[str, Any]) -> str:
    """Build the kline path (same for both market types)."""
    return "/v5/market/kline"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for kline endpoint."""
    market: MarketType = params["market_type"]
    category = CATEGORY_MAP[market]
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


# Endpoint specification
SPEC = RestEndpointSpec(
    id="ohlcv",
    method="GET",
    build_path=build_path,
    build_query=build_query,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing Bybit kline response into OHLCV."""

    def parse(self, response: Any, params: dict[str, Any]) -> OHLCV:
        """Parse Bybit kline response.

        Args:
            response: Raw response from Bybit API
            params: Request parameters containing symbol and interval

        Returns:
            OHLCV object with parsed bars
        """
        result = _extract_result(response)
        symbol = params["symbol"].upper()
        interval = params["interval"]

        # Bybit returns list of kline arrays: [timestamp, open, high, low, close, volume, turnover]
        # Or wrapped in "list" field
        klines = result.get("list", result) if isinstance(result, dict) else result

        if not isinstance(klines, list):
            raise DataError(f"Invalid kline response format: expected list, got {type(klines)}")

        meta = SeriesMeta(symbol=symbol, timeframe=interval.value)
        bars = []
        for row in klines:
            if not isinstance(row, list) or len(row) < 6:
                continue
            try:
                # Bybit format: [timestamp, open, high, low, close, volume, turnover]
                # Timestamp is in milliseconds
                ts_ms = int(row[0])
                bars.append(
                    Bar(
                        timestamp=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                        open=Decimal(str(row[1])),
                        high=Decimal(str(row[2])),
                        low=Decimal(str(row[3])),
                        close=Decimal(str(row[4])),
                        volume=Decimal(str(row[5])),
                        is_closed=True,  # Historical data is always closed
                    )
                )
            except (ValueError, IndexError, TypeError):
                # Skip invalid rows
                continue

        # Bybit returns newest first, reverse to get chronological order
        bars.reverse()

        return OHLCV(meta=meta, bars=bars)
