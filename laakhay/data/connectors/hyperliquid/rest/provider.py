"""Hyperliquid REST-only provider.

Implements the RESTProvider interface for Hyperliquid API.
Hyperliquid supports both Spot and Perpetual Futures markets.
API documentation: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import datetime
from typing import Any

from ....core import MarketType, Timeframe
from ....models import (
    OHLCV,
    FundingRate,
    OpenInterest,
    OrderBook,
    Symbol,
    Trade,
)
from ....runtime.chunking import (
    OHLCVChunkService,
)
from ....runtime.rest import (
    ResponseAdapter,
    RESTProvider,
    RestRunner,
    RESTTransport,
)
from .adapters import (
    CandlesResponseAdapter,
    ExchangeInfoSymbolsAdapter,
    FundingRateAdapter,
    OpenInterestCurrentAdapter,
    OpenInterestHistAdapter,
    OrderBookResponseAdapter,
    RecentTradesAdapter,
)
from .endpoints import (
    candles_spec,
    exchange_info_raw_spec,
    exchange_info_spec,
    funding_rate_spec,
    open_interest_current_spec,
    open_interest_hist_spec,
    order_book_spec,
    recent_trades_spec,
)


class HyperliquidRESTProvider(RESTProvider):
    """REST-only provider for Hyperliquid Spot or Futures."""

    def __init__(
        self,
        *,
        market_type: MarketType = MarketType.FUTURES,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        self.market_type = market_type
        from ..constants import BASE_URLS

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
            "exchange_info_raw": (exchange_info_raw_spec, ExchangeInfoSymbolsAdapter),
        }

    async def fetch(self, endpoint: str, params: dict[str, Any]) -> Any:
        if endpoint not in self._ENDPOINTS:
            raise ValueError(f"Unknown REST endpoint: {endpoint}")
        spec_fn, adapter_cls = self._ENDPOINTS[endpoint]
        spec = spec_fn()
        adapter = adapter_cls()
        # Add market_type to params if not present
        if "market_type" not in params:
            params["market_type"] = self.market_type
        return await self._runner.run(spec=spec, adapter=adapter, params=params)

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str | Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
        max_chunks: int | None = None,
    ) -> OHLCV:
        from ..constants import INTERVAL_MAP as HYPERLIQUID_INTERVAL_MAP

        if isinstance(timeframe, str):
            timeframe = Timeframe(timeframe)
        if not isinstance(timeframe, Timeframe) or timeframe not in HYPERLIQUID_INTERVAL_MAP:
            raise ValueError(f"Invalid timeframe: {timeframe}")

        spec = candles_spec()
        params = {
            "market_type": self.market_type,
            "symbol": symbol,
            "interval": timeframe,
            "interval_str": HYPERLIQUID_INTERVAL_MAP[timeframe],
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
        }

        async def fetch_chunk(
            chunk_start: datetime | None,
            chunk_end: datetime | None,
            chunk_limit: int | None,
        ) -> OHLCV:
            chunk_params = {
                "market_type": self.market_type,
                "symbol": symbol,
                "interval": timeframe,
                "interval_str": HYPERLIQUID_INTERVAL_MAP[timeframe],
                "start_time": chunk_start,
                "end_time": chunk_end,
                "limit": chunk_limit,
            }
            return await self.fetch("ohlcv", chunk_params)

        service = OHLCVChunkService.from_endpoint_spec(
            exchange="hyperliquid",
            market_type=self.market_type,
            spec=spec,
            params=params,
            fetch_chunk=fetch_chunk,
        )
        return await service.fetch(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            max_chunks=max_chunks,
        )

    async def iterate_ohlcv(
        self,
        symbol: str,
        timeframe: str | Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
        max_chunks: int | None = None,
        *,
        fetch_concurrency: int = 1,
        yield_chunk_size: int | None = None,
    ) -> AsyncIterator[OHLCV]:
        """Iterate OHLCV bars with optional parallel fetch and coalesced yields."""
        from ..constants import INTERVAL_MAP as HYPERLIQUID_INTERVAL_MAP

        if isinstance(timeframe, str):
            timeframe = Timeframe(timeframe)
        if timeframe not in HYPERLIQUID_INTERVAL_MAP:
            raise ValueError(f"Invalid timeframe: {timeframe}")

        spec = candles_spec()
        params = {
            "market_type": self.market_type,
            "symbol": symbol,
            "interval": timeframe,
            "interval_str": HYPERLIQUID_INTERVAL_MAP[timeframe],
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
        }

        async def fetch_chunk(
            chunk_start: datetime | None,
            chunk_end: datetime | None,
            chunk_limit: int | None,
        ) -> OHLCV:
            chunk_params = {
                "market_type": self.market_type,
                "symbol": symbol,
                "interval": timeframe,
                "interval_str": HYPERLIQUID_INTERVAL_MAP[timeframe],
                "start_time": chunk_start,
                "end_time": chunk_end,
                "limit": chunk_limit,
            }
            return await self.fetch("ohlcv", chunk_params)

        service = OHLCVChunkService.from_endpoint_spec(
            exchange="hyperliquid",
            market_type=self.market_type,
            spec=spec,
            params=params,
            fetch_chunk=fetch_chunk,
        )
        async for chunk in service.iterate(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            max_chunks=max_chunks,
            fetch_concurrency=fetch_concurrency,
            yield_chunk_size=yield_chunk_size,
        ):
            yield chunk

    async def get_symbols(
        self, quote_asset: str | None = None, use_cache: bool = True
    ) -> list[Symbol]:
        params = {"market_type": self.market_type, "quote_asset": quote_asset}
        data = await self.fetch("symbols", params)
        return list(data) if use_cache else data

    async def get_exchange_info(self) -> dict:
        """Return raw exchange info payload."""
        params = {"market_type": self.market_type}
        # Adapter returns symbols list; but for raw we can just reuse and reassemble dict
        # Better: have a Passthrough adapter; for now fetch via runner directly
        spec = exchange_info_raw_spec()

        class _Passthrough(ResponseAdapter):
            def parse(self, response: Any, params: dict[str, Any]) -> Any:
                return response

        adapter = _Passthrough()
        result: dict[Any, Any] = await self._runner.run(spec=spec, adapter=adapter, params=params)
        return result

    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        params = {"market_type": self.market_type, "symbol": symbol, "limit": limit}
        result: OrderBook = await self.fetch("order_book", params)
        return result

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
