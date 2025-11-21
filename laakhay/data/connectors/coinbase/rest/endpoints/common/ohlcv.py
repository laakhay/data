"""Coinbase OHLCV (candles) endpoint definition and adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.coinbase.config import normalize_symbol_to_coinbase
from laakhay.data.core import MarketType
from laakhay.data.models import OHLCV, Bar, SeriesMeta
from laakhay.data.runtime.chunking import ChunkHint, ChunkPolicy
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def build_path(params: dict[str, Any]) -> str:
    """Build the candles path."""
    # Coinbase only supports Spot markets
    market: MarketType = params["market_type"]
    if market != MarketType.SPOT:
        raise ValueError("Coinbase Advanced Trade API only supports Spot markets")

    symbol = params["symbol"]
    product_id = normalize_symbol_to_coinbase(symbol)
    return f"/products/{product_id}/candles"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for candles endpoint."""
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


# Chunking policy for OHLCV endpoint
# Coinbase returns up to 300 candles per request
CHUNK_POLICY = ChunkPolicy(
    max_points=300,  # Coinbase limit
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


class Adapter(ResponseAdapter):
    """Adapter for parsing Coinbase candles response into OHLCV."""

    def parse(self, response: Any, params: dict[str, Any]) -> OHLCV:
        """Parse Coinbase Exchange API candles response.

        Coinbase Exchange API returns array of arrays:
        [
            [timestamp, low, high, open, close, volume],
            ...
        ]
        Note: Format is [timestamp, low, high, open, close, volume] - low comes before high!
        """
        symbol = params["symbol"].upper()
        interval = params["interval"]

        # Exchange API returns array directly (not wrapped in "candles")
        candles_data = response if isinstance(response, list) else response.get("candles", [])
        if not isinstance(candles_data, list):
            candles_data = []

        meta = SeriesMeta(symbol=symbol, timeframe=interval.value)
        bars = []

        for candle in candles_data:
            if not isinstance(candle, list | tuple) or len(candle) < 6:
                # Try dict format (Advanced Trade API) as fallback
                if isinstance(candle, dict):
                    try:
                        start_str = candle.get("start")
                        if not start_str:
                            continue
                        if isinstance(start_str, str):
                            ts_str = start_str.replace("Z", "+00:00")
                            timestamp = datetime.fromisoformat(ts_str)
                        else:
                            timestamp = datetime.fromtimestamp(float(start_str), tz=UTC)
                        bars.append(
                            Bar(
                                timestamp=timestamp,
                                open=Decimal(str(candle.get("open", "0"))),
                                high=Decimal(str(candle.get("high", "0"))),
                                low=Decimal(str(candle.get("low", "0"))),
                                close=Decimal(str(candle.get("close", "0"))),
                                volume=Decimal(str(candle.get("volume", "0"))),
                                is_closed=True,
                            )
                        )
                    except (ValueError, TypeError, KeyError):
                        continue
                continue

            try:
                # Exchange API format: [timestamp, low, high, open, close, volume]
                timestamp_sec = int(candle[0])
                timestamp = datetime.fromtimestamp(timestamp_sec, tz=UTC)

                low_price = Decimal(str(candle[1]))
                high_price = Decimal(str(candle[2]))
                open_price = Decimal(str(candle[3]))
                close_price = Decimal(str(candle[4]))
                volume = Decimal(str(candle[5]))

                bars.append(
                    Bar(
                        timestamp=timestamp,
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=close_price,
                        volume=volume,
                        is_closed=True,
                    )
                )
            except (ValueError, TypeError, IndexError):
                # Skip invalid candles
                continue

        # Sort bars by timestamp (required by OHLCV model)
        bars.sort(key=lambda b: b.timestamp)

        return OHLCV(meta=meta, bars=bars)
