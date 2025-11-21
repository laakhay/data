"""OKX OHLCV (candles) endpoint definition and adapter.

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

from ...config import INTERVAL_MAP, to_okx_symbol


def build_path(params: dict[str, Any]) -> str:
    """Build the candles path."""
    return "/api/v5/market/candles"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for candles endpoint."""
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


# Chunking policy: OKX allows max 300 bars per request
CHUNK_POLICY = ChunkPolicy(
    max_points=300,
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
    build_path=build_path,
    build_query=build_query,
    chunk_policy=CHUNK_POLICY,
    chunk_hint=CHUNK_HINT,
)


def _extract_result(response: Any) -> Any:
    """Extract result from OKX's response wrapper.

    OKX API v5 returns: {code: "0", msg: "", data: [...]}
    """
    if not isinstance(response, dict):
        raise ValueError(f"Invalid response format: expected dict, got {type(response)}")

    code = response.get("code", "-1")
    msg = response.get("msg", "Unknown error")

    if code != "0":
        raise ValueError(f"OKX API error: {msg} (code: {code})")

    data = response.get("data")
    if data is None:
        raise ValueError("OKX API response missing 'data' field")

    return data


class Adapter(ResponseAdapter):
    """Adapter for parsing OKX candles response into OHLCV."""

    def parse(self, response: Any, params: dict[str, Any]) -> OHLCV:
        """Parse OKX candles response.

        Args:
            response: Raw response from OKX API
            params: Request parameters containing symbol and interval

        Returns:
            OHLCV object with parsed bars
        """
        data = _extract_result(response)
        symbol = params["symbol"].upper()
        interval = params["interval"]

        # OKX returns list of candle arrays: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
        if not isinstance(data, list):
            raise ValueError(f"Invalid candles response format: expected list, got {type(data)}")

        meta = SeriesMeta(symbol=symbol, timeframe=interval.value)
        bars = []
        for row in data:
            if not isinstance(row, list) or len(row) < 6:
                continue
            try:
                # OKX format: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
                # Timestamp is in milliseconds (ISO format string)
                ts_str = str(row[0])
                # OKX returns ISO timestamp string, convert to ms
                if "T" in ts_str:
                    # ISO format: "2024-01-01T00:00:00.000Z"
                    ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    ts_ms = int(ts_dt.timestamp() * 1000)
                else:
                    ts_ms = int(ts_str)

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

        # OKX returns newest first, reverse to get chronological order
        bars.reverse()

        return OHLCV(meta=meta, bars=bars)

