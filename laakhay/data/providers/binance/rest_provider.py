"""Binance REST-only provider.

Implements the RESTProvider interface by delegating to the existing
BinanceProvider's HTTP methods. This avoids code duplication while
providing a clean REST-only surface.
"""

from __future__ import annotations

from datetime import datetime

from ...core import MarketType, Timeframe
from ...io import RESTProvider
from ...models import (
    OHLCV,
    FundingRate,
    OpenInterest,
    OrderBook,
    Symbol,
    Trade,
)
from .provider import BinanceProvider


class BinanceRESTProvider(RESTProvider):
    """REST-only provider for Binance Spot or Futures."""

    def __init__(
        self,
        *,
        market_type: MarketType = MarketType.SPOT,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        # Internally reuse the mature HTTP implementation
        self._rest = BinanceProvider(
            market_type=market_type, api_key=api_key, api_secret=api_secret
        )

    async def get_candles(
        self,
        symbol: str,
        interval: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> OHLCV:
        return await self._rest.get_candles(symbol, interval, start_time, end_time, limit)

    async def get_symbols(
        self, quote_asset: str | None = None, use_cache: bool = True
    ) -> list[Symbol]:
        return await self._rest.get_symbols(quote_asset=quote_asset, use_cache=use_cache)

    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        return await self._rest.get_order_book(symbol, limit)

    async def get_recent_trades(self, symbol: str, limit: int = 500) -> list[Trade]:
        return await self._rest.get_recent_trades(symbol, limit)

    async def get_funding_rate(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[FundingRate]:
        return await self._rest.get_funding_rate(symbol, start_time, end_time, limit)

    async def get_open_interest(
        self,
        symbol: str,
        historical: bool = False,
        period: str = "5m",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 30,
    ) -> list[OpenInterest]:
        return await self._rest.get_open_interest(
            symbol,
            historical=historical,
            period=period,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    async def close(self) -> None:
        await self._rest.close()
