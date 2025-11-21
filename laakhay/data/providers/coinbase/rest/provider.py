"""Coinbase REST-only provider (shim for backward compatibility).

This module is a shim that wraps the connector-based REST provider.
The actual implementation has been moved to connectors/coinbase/rest/provider.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from laakhay.data.connectors.coinbase.config import INTERVAL_MAP
from laakhay.data.connectors.coinbase.rest.provider import CoinbaseRESTConnector

from ....core import MarketType, Timeframe
from ....models import OHLCV, OrderBook, Symbol, Trade
from ....runtime.rest import RESTProvider


class CoinbaseRESTProvider(RESTProvider):
    """REST-only provider for Coinbase Spot (shim)."""

    _MAX_CANDLES_PER_REQUEST = 300  # Coinbase max is 300 candles per request
    _DEFAULT_MAX_CANDLE_CHUNKS = 5

    def __init__(
        self,
        *,
        market_type: MarketType = MarketType.SPOT,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        """Initialize REST provider shim.

        Args:
            market_type: Market type (only SPOT supported for Coinbase)
            api_key: Optional API key
            api_secret: Optional API secret
        """
        self.market_type = market_type
        self._connector = CoinbaseRESTConnector(
            market_type=market_type, api_key=api_key, api_secret=api_secret
        )
        # Expose _transport for backward compatibility with tests
        self._transport = self._connector._transport

    async def fetch(self, endpoint_id: str, params: dict[str, Any]) -> Any:
        """Fetch data from a Coinbase REST endpoint (for backward compatibility).

        Args:
            endpoint_id: Endpoint identifier
            params: Request parameters

        Returns:
            Parsed response
        """
        return await self._connector.fetch(endpoint_id, params)

    async def fetch_health(self) -> dict[str, object]:
        """Ping Coinbase REST API to verify connectivity."""
        return await self._connector.fetch_health()

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str | Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
        max_chunks: int | None = None,
    ) -> OHLCV:
        """Fetch OHLCV bars with chunking support.

        Coinbase returns up to 300 candles per request. If more are needed,
        requests are chunked automatically.
        """
        # Validate max_chunks
        if max_chunks is not None and max_chunks <= 0:
            raise ValueError("max_chunks must be None or a positive integer")

        # Convert string timeframe to Timeframe if needed
        if isinstance(timeframe, str):
            tf = Timeframe.from_str(timeframe)
            if tf is None:
                raise ValueError(f"Invalid timeframe: {timeframe}")
            timeframe = tf

        if timeframe not in INTERVAL_MAP:
            raise ValueError(f"Invalid timeframe: {timeframe}")

        chunk_cap = max_chunks or self._DEFAULT_MAX_CANDLE_CHUNKS
        interval_delta = (
            timedelta(seconds=timeframe.seconds) if timeframe.seconds else timedelta(minutes=1)
        )

        async def _fetch_chunk(
            *,
            chunk_start: datetime | None,
            chunk_end: datetime | None,
            chunk_limit: int | None,
        ) -> OHLCV:
            params = {
                "market_type": self.market_type,
                "symbol": symbol,
                "interval": timeframe,
                "interval_str": INTERVAL_MAP[timeframe],
                "start_time": chunk_start,
                "end_time": chunk_end,
                "limit": chunk_limit,
            }
            result: OHLCV = await self.fetch("ohlcv", params)
            return result

        # Fast path: single request is enough.
        if (limit is None or limit <= self._MAX_CANDLES_PER_REQUEST) and chunk_cap == 1:
            return await _fetch_chunk(chunk_start=start_time, chunk_end=end_time, chunk_limit=limit)

        # Multi-chunk path: aggregate results
        aggregated: list[Any] = []
        meta = None
        remaining = limit
        current_start = start_time
        chunks_used = 0
        last_timestamp: datetime | None = None

        while True:
            if chunk_cap is not None and chunks_used >= chunk_cap:
                break

            chunk_limit = self._MAX_CANDLES_PER_REQUEST
            if remaining is not None:
                if remaining <= 0:
                    break
                chunk_limit = min(chunk_limit, remaining)

            chunk_ohlcv = await _fetch_chunk(
                chunk_start=current_start,
                chunk_end=end_time,
                chunk_limit=chunk_limit,
            )
            meta = meta or chunk_ohlcv.meta
            bars = chunk_ohlcv.bars

            if not bars:
                break

            if last_timestamp is not None:
                bars = [bar for bar in bars if bar.timestamp > last_timestamp]
                if not bars:
                    break

            aggregated.extend(bars)
            last_timestamp = bars[-1].timestamp

            if remaining is not None:
                remaining -= len(bars)
                if remaining <= 0:
                    break

            current_start = last_timestamp + interval_delta
            if end_time is not None and current_start >= end_time:
                break

            chunks_used += 1

            if len(bars) < self._MAX_CANDLES_PER_REQUEST:
                break

        if not aggregated and meta is None:
            return await _fetch_chunk(chunk_start=start_time, chunk_end=end_time, chunk_limit=limit)

        if meta is None:
            raise ValueError("meta cannot be None when aggregated is provided")
        return OHLCV(meta=meta, bars=aggregated)

    async def get_symbols(
        self, quote_asset: str | None = None, use_cache: bool = True
    ) -> list[Symbol]:
        """Get trading symbols."""
        # Use shim's fetch method so tests can mock it
        params = {"quote_asset": quote_asset}
        data = await self.fetch("exchange_info", params)
        return list(data) if use_cache else data

    async def get_exchange_info(self) -> dict:
        """Return raw exchange info payload."""
        return await self._connector.get_exchange_info()

    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        """Fetch order book."""
        return await self._connector.get_order_book(symbol=symbol, limit=limit)

    async def get_recent_trades(self, symbol: str, limit: int = 500) -> list[Trade]:
        """Fetch recent trades."""
        return await self._connector.get_recent_trades(symbol=symbol, limit=limit)

    async def get_funding_rate(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list:
        """Fetch funding rates - NOT SUPPORTED by Coinbase Advanced Trade API."""
        raise NotImplementedError(
            "Coinbase Advanced Trade API does not support funding rates "
            "(Futures feature, not available on Spot markets)"
        )

    async def get_open_interest(
        self,
        symbol: str,
        historical: bool = False,
        period: str = "5m",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 30,
    ) -> list:
        """Fetch open interest - NOT SUPPORTED by Coinbase Advanced Trade API."""
        raise NotImplementedError(
            "Coinbase Advanced Trade API does not support open interest "
            "(Futures feature, not available on Spot markets)"
        )

    async def close(self) -> None:
        """Close underlying resources."""
        await self._connector.close()
