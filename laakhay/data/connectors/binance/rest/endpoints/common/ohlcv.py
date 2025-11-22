"""Binance OHLCV (candles) endpoint definition and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.binance.config import get_api_path_prefix
from laakhay.data.connectors.binance.rest.schemas import BinanceKline
from laakhay.data.core import MarketType, MarketVariant
from laakhay.data.models import OHLCV, Bar, SeriesMeta
from laakhay.data.runtime.chunking import ChunkHint, ChunkPolicy, WeightPolicy, WeightTier
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def _klines_path(params: dict[str, Any]) -> str:
    """Build the klines path based on market type and variant."""
    market: MarketType = params["market_type"]
    market_variant: MarketVariant | None = params.get("market_variant")
    prefix = get_api_path_prefix(market, market_variant)
    return f"{prefix}/klines"


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


# Weight policies for different market types
SPOT_WEIGHT_POLICY = WeightPolicy(static_weight=2)

FUTURES_WEIGHT_POLICY = WeightPolicy(
    tiers=[
        WeightTier(min_limit=1, max_limit=100, weight=1),
        WeightTier(min_limit=100, max_limit=500, weight=2),
        WeightTier(min_limit=500, max_limit=1000, weight=5),
        WeightTier(min_limit=1000, max_limit=None, weight=10),
    ],
)


def _get_weight_policy(params: dict[str, Any]) -> WeightPolicy:
    """Get weight policy based on market type and variant.

    Args:
        params: Request parameters containing market_type and optional market_variant

    Returns:
        WeightPolicy for the market type

    """
    market_type: MarketType = params.get("market_type", MarketType.SPOT)
    if market_type == MarketType.SPOT:
        return SPOT_WEIGHT_POLICY
    return FUTURES_WEIGHT_POLICY


def _create_chunk_policy(_params: dict[str, Any]) -> ChunkPolicy:
    """Create chunk policy for the endpoint."""
    return ChunkPolicy(
        max_points=1000,
        max_chunks=None,
        requires_start_time=False,
        supports_auto_chunking=True,
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
    chunk_policy=_create_chunk_policy,
    chunk_hint=CHUNK_HINT,
    weight_policy=_get_weight_policy,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing Binance klines response into OHLCV."""

    def parse(self, response: Any, params: dict[str, Any]) -> OHLCV:
        """Parse Binance klines response.

        Args:
            response: Raw response from Binance API (list of kline arrays)
            params: Request parameters containing symbol and interval

        Returns:
            OHLCV object with parsed bars

        """
        symbol = params["symbol"].upper()
        interval = params["interval"]
        meta = SeriesMeta(symbol=symbol, timeframe=interval.value)

        raw_klines = [BinanceKline.from_array(row) for row in response]
        bars = [
            Bar(
                timestamp=datetime.fromtimestamp(kline.open_time / 1000, tz=UTC),
                open=Decimal(kline.open),
                high=Decimal(kline.high),
                low=Decimal(kline.low),
                close=Decimal(kline.close),
                volume=Decimal(kline.volume),
                is_closed=True,
            )
            for kline in raw_klines
        ]
        return OHLCV(meta=meta, bars=bars)
