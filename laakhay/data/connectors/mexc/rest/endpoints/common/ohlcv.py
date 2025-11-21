"""MEXC OHLCV (candles) endpoint definition and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.models import OHLCV, Bar, SeriesMeta
from laakhay.data.runtime.chunking import ChunkHint, ChunkPolicy
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def _klines_path(params: dict[str, Any]) -> str:
    """Build the klines path based on market type."""
    market: MarketType = params["market_type"]
    # MEXC uses /api/v3/klines for spot and /api/v1/contract/kline for futures
    return "/api/v1/contract/kline" if market == MarketType.FUTURES else "/api/v3/klines"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for klines endpoint."""
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


# Chunking policy: MEXC allows max 1000 bars per request
CHUNK_POLICY = ChunkPolicy(
    max_points=1000,
    max_chunks=None,  # No hard limit
    requires_start_time=False,
    supports_auto_chunking=True,
    weight_per_request=1,
)

# Chunk hints for time-based chunking
CHUNK_HINT = ChunkHint(
    timestamp_key="timestamp",
    limit_field="limit",
    start_time_field="start_time",
    end_time_field="end_time",
    timeframe_field="interval",
)

# Endpoint specification
SPEC = RestEndpointSpec(
    id="ohlcv",
    method="GET",
    build_path=_klines_path,
    build_query=build_query,
    chunk_policy=CHUNK_POLICY,
    chunk_hint=CHUNK_HINT,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing MEXC klines response into OHLCV."""

    def parse(self, response: Any, params: dict[str, Any]) -> OHLCV:
        """Parse MEXC klines response.

        Args:
            response: Raw response from MEXC API (list of kline arrays)
            params: Request parameters containing symbol and interval

        Returns:
            OHLCV object with parsed bars
        """
        symbol = params["symbol"].upper()
        interval = params["interval"]
        meta = SeriesMeta(symbol=symbol, timeframe=interval.value)
        bars = [
            Bar(
                timestamp=datetime.fromtimestamp(row[0] / 1000, tz=UTC),
                open=Decimal(str(row[1])),
                high=Decimal(str(row[2])),
                low=Decimal(str(row[3])),
                close=Decimal(str(row[4])),
                volume=Decimal(str(row[5])),
                is_closed=True,
            )
            for row in response
        ]
        return OHLCV(meta=meta, bars=bars)
