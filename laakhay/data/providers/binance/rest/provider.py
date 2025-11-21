"""Binance REST-only provider (shim for backward compatibility).

This module is a shim that wraps the connector-based REST provider.
The actual implementation has been moved to connectors/binance/rest/provider.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from laakhay.data.connectors.binance.config import INTERVAL_MAP
from laakhay.data.connectors.binance.rest.provider import BinanceRESTConnector

from ....core import MarketType, Timeframe
from ....models import OHLCV, Bar, FundingRate, OpenInterest, OrderBook, Symbol, Trade
from ....runtime.rest import RESTProvider


class BinanceRESTProvider(RESTProvider):
    """REST-only provider for Binance Spot or Futures (shim)."""

    def __init__(
        self,
        *,
        market_type: MarketType = MarketType.SPOT,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        """Initialize REST provider shim.

        Args:
            market_type: Market type (spot or futures)
            api_key: Optional API key
            api_secret: Optional API secret
        """
        self.market_type = market_type
        self._connector = BinanceRESTConnector(
            market_type=market_type, api_key=api_key, api_secret=api_secret
        )
        # Expose _transport for backward compatibility with tests
        self._transport = self._connector._transport

    async def fetch(self, endpoint_id: str, params: dict[str, Any]) -> Any:
        """Fetch data from a Binance REST endpoint (for backward compatibility).

        Args:
            endpoint_id: Endpoint identifier
            params: Request parameters

        Returns:
            Parsed response
        """
        return await self._connector.fetch(endpoint_id, params)

    async def fetch_health(self) -> dict[str, object]:
        """Ping Binance REST API to verify connectivity."""
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
        """Fetch OHLCV bars (delegates to connector with chunking support)."""
        # Convert string timeframe to Timeframe if needed
        if isinstance(timeframe, str):
            tf = Timeframe.from_str(timeframe)
            if tf is None:
                raise ValueError(f"Invalid timeframe: {timeframe}")
            timeframe = tf

        # For backward compatibility, support chunking via fetch() method
        # This allows tests to mock fetch() directly
        if max_chunks is not None:
            # Use the old chunking logic for tests that expect it
            max_candles_per_request = 1000
            default_max_candle_chunks = 5

            if max_chunks <= 0:
                raise ValueError("max_chunks must be None or a positive integer")

            chunk_cap = max_chunks or default_max_candle_chunks
            interval_delta = timedelta(seconds=timeframe.seconds)

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

            # Fast path: single request is enough
            if (limit is None or limit <= max_candles_per_request) and chunk_cap == 1:
                return await _fetch_chunk(
                    chunk_start=start_time, chunk_end=end_time, chunk_limit=limit
                )

            aggregated: list[Bar] = []
            meta = None
            remaining = limit
            current_start = start_time
            chunks_used = 0
            last_timestamp: datetime | None = None

            while True:
                if chunk_cap is not None and chunks_used >= chunk_cap:
                    break

                chunk_limit = max_candles_per_request
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

                if len(bars) < max_candles_per_request:
                    break

            if not aggregated and meta is None:
                return await _fetch_chunk(
                    chunk_start=start_time, chunk_end=end_time, chunk_limit=limit
                )

            if meta is None:
                raise ValueError("meta cannot be None when aggregated is provided")
            return OHLCV(meta=meta, bars=aggregated)

        # Simple path: delegate to connector
        return await self._connector.fetch_ohlcv(
            symbol=symbol,
            interval=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    async def get_symbols(
        self, quote_asset: str | None = None, use_cache: bool = True
    ) -> list[Symbol]:
        """Get trading symbols."""
        return await self._connector.get_symbols(quote_asset=quote_asset, use_cache=use_cache)

    async def get_exchange_info(self) -> dict:
        """Return raw exchange info payload."""
        return await self._connector._rest.fetch("exchange_info", {})

    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        """Fetch order book."""
        return await self._connector.get_order_book(symbol=symbol, limit=limit)

    async def get_recent_trades(self, symbol: str, limit: int = 500) -> list[Trade]:
        """Fetch recent trades."""
        return await self._connector.get_recent_trades(symbol=symbol, limit=limit)

    async def fetch_historical_trades(
        self,
        symbol: str,
        *,
        limit: int | None = None,
        from_id: int | None = None,
    ) -> list[Trade]:
        """Fetch historical trades."""
        return await self._connector.fetch_historical_trades(
            symbol=symbol, limit=limit, from_id=from_id
        )

    async def get_funding_rate(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[FundingRate]:
        """Fetch funding rates."""
        return await self._connector.get_funding_rate(
            symbol=symbol, start_time=start_time, end_time=end_time, limit=limit
        )

    async def get_open_interest(
        self,
        symbol: str,
        historical: bool = False,
        period: str = "5m",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 30,
    ) -> list[OpenInterest]:
        """Fetch open interest."""
        return await self._connector.get_open_interest(
            symbol=symbol,
            historical=historical,
            period=period,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    async def close(self) -> None:
        """Close underlying resources."""
        await self._connector.close()
