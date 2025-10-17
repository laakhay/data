"""Binance REST-only provider.

Implements the RESTProvider interface by delegating to the existing
BinanceProvider's HTTP methods. This avoids code duplication while
providing a clean REST-only surface.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from ...core import MarketType, Timeframe
from ...io import RESTProvider, RestRunner, RESTTransport
from ...models import (
    OHLCV,
    FundingRate,
    OpenInterest,
    OrderBook,
    Symbol,
    Trade,
)
from .rest.adapters import (
    CandlesResponseAdapter,
    ExchangeInfoSymbolsAdapter,
    FundingRateAdapter,
    OpenInterestCurrentAdapter,
    OpenInterestHistAdapter,
    OrderBookResponseAdapter,
    RecentTradesAdapter,
)
from .rest.endpoints import (
    candles_spec,
    exchange_info_spec,
    funding_rate_spec,
    open_interest_current_spec,
    open_interest_hist_spec,
    order_book_spec,
    recent_trades_spec,
)


class BinanceRESTProvider(RESTProvider):
    """REST-only provider for Binance Spot or Futures."""

    def __init__(
        self,
        *,
        market_type: MarketType = MarketType.SPOT,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        self.market_type = market_type
        from .constants import BASE_URLS

        self._transport = RESTTransport(base_url=BASE_URLS[market_type])
        self._runner = RestRunner(self._transport)
        # Registry: key -> (spec_builder, adapter_class)
        self._ENDPOINTS: dict[str, tuple[Callable[..., Any], type]] = {
            "ohlcv": (candles_spec, CandlesResponseAdapter),
            "symbols": (exchange_info_spec, ExchangeInfoSymbolsAdapter),
            "order_book": (order_book_spec, OrderBookResponseAdapter),
            "open_interest_current": (open_interest_current_spec, OpenInterestCurrentAdapter),
            "open_interest_hist": (open_interest_hist_spec, OpenInterestHistAdapter),
            "recent_trades": (recent_trades_spec, RecentTradesAdapter),
            "funding_rate": (funding_rate_spec, FundingRateAdapter),
        }

    async def fetch(self, endpoint: str, params: dict[str, Any]) -> Any:
        if endpoint not in self._ENDPOINTS:
            raise ValueError(f"Unknown REST endpoint: {endpoint}")
        spec_fn, adapter_cls = self._ENDPOINTS[endpoint]
        spec = spec_fn()
        adapter = adapter_cls()
        return await self._runner.run(spec=spec, adapter=adapter, params=params)

    async def get_candles(
        self,
        symbol: str,
        timeframe: str | Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> OHLCV:
        from .constants import INTERVAL_MAP as BINANCE_INTERVAL_MAP

        if isinstance(timeframe, str):
            timeframe = Timeframe.from_str(timeframe)
        if timeframe not in BINANCE_INTERVAL_MAP:
            raise ValueError(f"Invalid timeframe: {timeframe}")

        params = {
            "market_type": self.market_type,
            "symbol": symbol,
            "interval": timeframe,
            "interval_str": BINANCE_INTERVAL_MAP[timeframe],
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
        }
        return await self.fetch("ohlcv", params)

    async def get_symbols(
        self, quote_asset: str | None = None, use_cache: bool = True
    ) -> list[Symbol]:
        params = {"market_type": self.market_type, "quote_asset": quote_asset}
        data = await self.fetch("symbols", params)
        return list(data) if use_cache else data

    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        params = {"market_type": self.market_type, "symbol": symbol, "limit": limit}
        return await self.fetch("order_book", params)

    async def get_recent_trades(self, symbol: str, limit: int = 500) -> list[Trade]:
        params = {"market_type": self.market_type, "symbol": symbol, "limit": limit}
        data = await self.fetch("recent_trades", params)
        return list(data)

    async def get_funding_rate(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[FundingRate]:
        params: dict[str, Any] = {
            "market_type": self.market_type,
            "symbol": symbol,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
        }
        data = await self.fetch("funding_rate", params)
        return list(data)

    async def get_open_interest(
        self,
        symbol: str,
        historical: bool = False,
        period: str = "5m",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 30,
    ) -> list[OpenInterest]:
        params: dict[str, Any] = {
            "market_type": self.market_type,
            "symbol": symbol,
            "period": period,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
        }
        if historical:
            data = await self.fetch("open_interest_hist", params)
        else:
            data = await self.fetch("open_interest_current", params)
        return list(data)

    async def close(self) -> None:
        await self._transport.close()
