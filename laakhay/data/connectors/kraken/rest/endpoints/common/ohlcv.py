"""Kraken OHLCV (candles) endpoint definition and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.core.exceptions import DataError
from laakhay.data.models import OHLCV, Bar, SeriesMeta
from laakhay.data.runtime.chunking import ChunkHint, ChunkPolicy
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec

from ....config import INTERVAL_MAP
from ....constants import normalize_symbol_to_kraken


def _ohlcv_path(params: dict[str, Any]) -> str:
    """Build the OHLCV path based on market type."""
    market: MarketType = params["market_type"]
    if market == MarketType.FUTURES:
        # Kraken Futures API - use path parameter for symbol
        symbol = params["symbol"]
        # Normalize symbol to Kraken format
        normalized_symbol = normalize_symbol_to_kraken(symbol, market)
        return f"/instruments/{normalized_symbol}/candles"
    else:
        # Kraken Spot API
        return "/0/public/OHLCData"


def _build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for OHLCV endpoint."""
    market_type: MarketType = params["market_type"]
    symbol = params["symbol"]
    # Normalize symbol to Kraken format
    normalized_symbol = normalize_symbol_to_kraken(symbol, market_type)
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
            q["limit"] = min(int(params["limit"]), 1000)
        return q
    else:
        # Kraken Spot API
        q: dict[str, Any] = {
            "pair": normalized_symbol,  # Normalized to Kraken format
            "interval": interval_str,
        }
        if params.get("start_time"):
            q["since"] = int(params["start_time"].timestamp())
        if params.get("limit"):
            q["limit"] = min(int(params["limit"]), 720)  # Kraken Spot max is 720
        return q


# Chunking policy for OHLCV endpoint
# Kraken Spot: max 720 candles per request
# Kraken Futures: max 1000 candles per request (using 720 as conservative limit)
CHUNK_POLICY = ChunkPolicy(
    max_points=720,  # Kraken Spot limit
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
    build_path=_ohlcv_path,
    build_query=_build_query,
    chunk_policy=CHUNK_POLICY,
    chunk_hint=CHUNK_HINT,
)


def _extract_result(response: Any, market_type: MarketType) -> Any:
    """Extract result from Kraken's response wrapper."""
    if not isinstance(response, dict):
        raise DataError(f"Invalid response format: expected dict, got {type(response)}")

    # Check for errors in Kraken Spot format
    errors = response.get("error", [])
    if errors and len(errors) > 0:
        error_msg = errors[0] if isinstance(errors, list) else str(errors)
        raise DataError(f"Kraken API error: {error_msg}")

    # Kraken Spot wraps in "result" field
    if "result" in response:
        result_value = response["result"]
        # For Futures, if result is "ok", return the full response (data is in other fields)
        if result_value == "ok" and market_type == MarketType.FUTURES:
            return response
        return result_value

    # Kraken Futures may return direct result or wrapped
    if "error" in response and response["error"]:
        raise DataError(f"Kraken API error: {response.get('error', 'Unknown error')}")

    # Return response itself if no wrapper
    return response


class Adapter(ResponseAdapter):
    """Adapter for parsing Kraken OHLCV response into OHLCV."""

    def parse(self, response: Any, params: dict[str, Any]) -> OHLCV:
        """Parse Kraken OHLCV response.

        Args:
            response: Raw response from Kraken API
            params: Request parameters containing symbol and interval

        Returns:
            OHLCV object with parsed bars
        """
        market_type: MarketType = params["market_type"]
        symbol = params["symbol"]
        interval = params["interval"]

        result = _extract_result(response, market_type)

        if market_type == MarketType.FUTURES:
            # Kraken Futures format: {result: "ok", candles: [{time, open, high, low, close, volume}, ...]}
            candles_data = result.get("candles", []) if isinstance(result, dict) else result

            if not isinstance(candles_data, list):
                raise DataError(
                    f"Invalid candles response format: expected list, got {type(candles_data)}"
                )

            meta = SeriesMeta(symbol=symbol, timeframe=interval.value)
            bars = []
            for row in candles_data:
                if not isinstance(row, dict):
                    continue
                try:
                    time_ms = row.get("time", 0)
                    open_price = row.get("open")
                    high_price = row.get("high")
                    low_price = row.get("low")
                    close_price = row.get("close")
                    volume = row.get("volume")

                    if not all([time_ms, open_price, high_price, low_price, close_price, volume]):
                        continue

                    bars.append(
                        Bar(
                            timestamp=datetime.fromtimestamp(time_ms / 1000, tz=UTC),
                            open=Decimal(str(open_price)),
                            high=Decimal(str(high_price)),
                            low=Decimal(str(low_price)),
                            close=Decimal(str(close_price)),
                            volume=Decimal(str(volume)),
                            is_closed=True,
                        )
                    )
                except (ValueError, TypeError, KeyError):
                    continue

            # Sort by timestamp (oldest first)
            bars.sort(key=lambda b: b.timestamp)

        else:
            # Kraken Spot format: {result: {PAIR: [[time, open, high, low, close, vwap, volume, count], ...]}}
            pair_data = None
            if isinstance(result, dict):
                # Find first key that looks like a pair
                for key in result:
                    pair_data = result[key]
                    break

            if not isinstance(pair_data, list):
                raise DataError(
                    f"Invalid OHLC response format: expected list, got {type(pair_data)}"
                )

            meta = SeriesMeta(symbol=symbol, timeframe=interval.value)
            bars = []
            for row in pair_data:
                if not isinstance(row, list) or len(row) < 7:
                    continue
                try:
                    # Kraken Spot format: [time, open, high, low, close, vwap, volume, count]
                    ts = int(row[0])
                    bars.append(
                        Bar(
                            timestamp=datetime.fromtimestamp(ts, tz=UTC),
                            open=Decimal(str(row[1])),
                            high=Decimal(str(row[2])),
                            low=Decimal(str(row[3])),
                            close=Decimal(str(row[4])),
                            volume=Decimal(str(row[6])),  # Volume is at index 6
                            is_closed=True,
                        )
                    )
                except (ValueError, IndexError, TypeError):
                    continue

        return OHLCV(meta=meta, bars=bars)
