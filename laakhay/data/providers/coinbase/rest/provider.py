"""Coinbase REST-only provider.

Implements the RESTProvider interface for Coinbase Advanced Trade API.
Coinbase Advanced Trade API only supports Spot markets.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from ....core import MarketType, Timeframe
from ....io import RESTProvider, RestRunner, RESTTransport
from ....models import OHLCV, OrderBook, Symbol, Trade
from .adapters import (
    CandlesResponseAdapter,
    ExchangeInfoSymbolsAdapter,
    OrderBookResponseAdapter,
    RecentTradesAdapter,
)
from .endpoints import (
    candles_spec,
    exchange_info_raw_spec,
    exchange_info_spec,
    order_book_spec,
    recent_trades_spec,
)


class CoinbaseRESTProvider(RESTProvider):
    """REST-only provider for Coinbase Advanced Trade API (Spot markets only)."""

    def __init__(
        self,
        *,
        market_type: MarketType = MarketType.SPOT,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        # Coinbase Advanced Trade API only supports Spot markets
        if market_type != MarketType.SPOT:
            raise ValueError(
                "Coinbase Advanced Trade API only supports Spot markets. "
                f"Got market_type={market_type}"
            )

        self.market_type = MarketType.SPOT  # Force to SPOT
        from ..constants import BASE_URLS

        self._transport = RESTTransport(base_url=BASE_URLS[MarketType.SPOT])
        self._runner = RestRunner(self._transport)

        # Registry: key -> (spec_builder, adapter_class)
        self._ENDPOINTS: dict[str, tuple[Callable[..., Any], type]] = {
            "ohlcv": (candles_spec, CandlesResponseAdapter),
            "symbols": (exchange_info_spec, ExchangeInfoSymbolsAdapter),
            "order_book": (order_book_spec, OrderBookResponseAdapter),
            "recent_trades": (recent_trades_spec, RecentTradesAdapter),
            "exchange_info_raw": (exchange_info_raw_spec, ExchangeInfoSymbolsAdapter),
        }

        # Note: Coinbase doesn't support Futures features:
        # - funding_rate
        # - open_interest
        # These are intentionally omitted

    _MAX_CANDLES_PER_REQUEST = 300  # Coinbase max is 300 candles per request
    _DEFAULT_MAX_CANDLE_CHUNKS = 5

    async def fetch(self, endpoint: str, params: dict[str, Any]) -> Any:
        """Fetch data from a registered endpoint."""
        if endpoint not in self._ENDPOINTS:
            raise ValueError(f"Unknown REST endpoint: {endpoint}")
        spec_fn, adapter_cls = self._ENDPOINTS[endpoint]
        spec = spec_fn()
        adapter = adapter_cls()
        # Ensure market_type is set
        if "market_type" not in params:
            params["market_type"] = self.market_type
        return await self._runner.run(spec=spec, adapter=adapter, params=params)

    async def get_candles(
        self,
        symbol: str,
        timeframe: str | Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
        max_chunks: int | None = None,
    ) -> OHLCV:
        """Fetch OHLCV candles for a symbol.

        Coinbase returns up to 300 candles per request. If more are needed,
        requests are chunked automatically.
        """
        from ..constants import INTERVAL_MAP as COINBASE_INTERVAL_MAP

        if isinstance(timeframe, str):
            parsed_timeframe = Timeframe.from_str(timeframe)
            if parsed_timeframe is None:
                raise ValueError(f"Invalid timeframe: {timeframe}")
            timeframe = parsed_timeframe
        if not isinstance(timeframe, Timeframe) or timeframe not in COINBASE_INTERVAL_MAP:
            raise ValueError(f"Invalid timeframe: {timeframe}")

        if max_chunks is not None and max_chunks <= 0:
            raise ValueError("max_chunks must be None or a positive integer")

        chunk_cap = max_chunks or self._DEFAULT_MAX_CANDLE_CHUNKS
        interval_delta = timedelta(seconds=timeframe.seconds)

        async def _fetch_chunk(
            *,
            chunk_start: datetime | None,
            chunk_end: datetime | None,
            chunk_limit: int | None,
        ) -> OHLCV:
            if not isinstance(timeframe, Timeframe):
                raise ValueError(f"Invalid timeframe: {timeframe}")
            params = {
                "market_type": self.market_type,
                "symbol": symbol,
                "interval": timeframe,
                "interval_str": COINBASE_INTERVAL_MAP[timeframe],
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
        """List trading symbols, optionally filtered by quote asset."""
        params = {"market_type": self.market_type, "quote_asset": quote_asset}
        data = await self.fetch("symbols", params)
        return list(data) if use_cache else data

    async def get_exchange_info(self) -> dict:
        """Return raw exchange info payload."""
        params = {"market_type": self.market_type}
        # Use passthrough adapter for raw data
        spec = exchange_info_raw_spec()
        from ....io import ResponseAdapter

        class _Passthrough(ResponseAdapter):
            def parse(self, response: Any, params: dict[str, Any]) -> Any:
                return response

        adapter = _Passthrough()
        result: dict[Any, Any] = await self._runner.run(spec=spec, adapter=adapter, params=params)
        return result

    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        """Fetch current order book."""
        params = {"market_type": self.market_type, "symbol": symbol, "limit": limit}
        result: OrderBook = await self.fetch("order_book", params)
        return result

    async def get_recent_trades(self, symbol: str, limit: int = 500) -> list[Trade]:
        """Fetch recent trades."""
        params = {"market_type": self.market_type, "symbol": symbol, "limit": limit}
        data = await self.fetch("recent_trades", params)
        return list(data)

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
        """Close HTTP transport."""
        await self._transport.close()
