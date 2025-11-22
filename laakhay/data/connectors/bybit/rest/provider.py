"""Bybit REST connector for direct use by researchers.

This connector provides direct access to Bybit REST endpoints without
going through the DataRouter or capability validation. It's designed for
research use cases where developers want full control.

Architecture:
    This connector uses the endpoint registry to look up specs and adapters,
    then uses RestRunner to execute requests. It implements RESTProvider
    interface for compatibility with the router system.
"""

from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import Any

from laakhay.data.connectors.bybit.config import BASE_URLS, INTERVAL_MAP
from laakhay.data.core import MarketType, MarketVariant, Timeframe
from laakhay.data.models import (
    OHLCV,
    FundingRate,
    OpenInterest,
    OrderBook,
    Symbol,
    Trade,
)
from laakhay.data.runtime.rest import (
    RESTProvider,
    RestRunner,
    RESTTransport,
)

from .endpoints import get_endpoint_adapter, get_endpoint_spec


class BybitRESTConnector(RESTProvider):
    """Bybit REST connector for direct research use.

    This connector can be used directly without going through DataRouter.
    It provides full access to Bybit REST endpoints with automatic
    endpoint spec and adapter resolution.
    """

    _MAX_CANDLES_PER_REQUEST = 200  # Bybit max is 200

    def __init__(
        self,
        market_type: MarketType,
        *,
        market_variant: MarketVariant | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,  # noqa: ARG002
    ) -> None:
        """Initialize Bybit REST connector.

        Args:
            market_type: Market type (spot or futures)
            market_variant: Optional market variant. If not provided, derived from
                          market_type with smart defaults:
                          - SPOT → SPOT
                          - FUTURES → LINEAR_PERP (can be overridden)
                          - OPTIONS → OPTIONS
            api_key: Optional API key for authenticated endpoints
            api_secret: Optional API secret (not currently used)
        """
        self.market_type = market_type
        # Derive market_variant from market_type if not provided (backward compatibility)
        if market_variant is None:
            self.market_variant = MarketVariant.from_market_type(market_type)
        else:
            self.market_variant = market_variant
        self._api_key = api_key
        self._transport = RESTTransport(base_url=BASE_URLS[market_type])
        self._runner = RestRunner(self._transport)

    async def fetch_health(self) -> dict[str, object]:
        """Ping Bybit REST API to verify connectivity."""
        path = "/v5/market/time"
        start = perf_counter()
        await self._transport.get(path)
        latency_ms = (perf_counter() - start) * 1000.0
        return {
            "exchange": "bybit",
            "market_type": self.market_type.value,
            "status": "ok",
            "latency_ms": latency_ms,
            "endpoint": path,
        }

    async def fetch(self, endpoint_id: str, params: dict[str, Any]) -> Any:
        """Fetch data from a Bybit REST endpoint.

        Args:
            endpoint_id: Endpoint identifier (e.g., "ohlcv", "order_book")
            params: Request parameters

        Returns:
            Parsed response from the endpoint adapter

        Raises:
            ValueError: If endpoint_id is not found in registry
        """
        spec = get_endpoint_spec(endpoint_id)
        if spec is None:
            raise ValueError(f"Unknown REST endpoint: {endpoint_id}")

        adapter_cls = get_endpoint_adapter(endpoint_id)
        if adapter_cls is None:
            raise ValueError(f"No adapter found for endpoint: {endpoint_id}")

        # Ensure market_type and market_variant are in params
        params = {
            **params,
            "market_type": self.market_type,
            "market_variant": self.market_variant,
        }

        adapter = adapter_cls()
        return await self._runner.run(spec=spec, adapter=adapter, params=params)

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> OHLCV:
        """Fetch OHLCV bars for a symbol and timeframe.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            timeframe: Timeframe for bars
            start_time: Optional start time
            end_time: Optional end time
            limit: Optional limit on number of bars

        Returns:
            OHLCV object with bars
        """
        if timeframe not in INTERVAL_MAP:
            raise ValueError(f"Invalid timeframe: {timeframe}")

        params = {
            "symbol": symbol,
            "interval": timeframe,  # Exchange API uses "interval"
            "interval_str": INTERVAL_MAP[timeframe],
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
        }
        result: OHLCV = await self.fetch("ohlcv", params)
        return result

    async def get_symbols(
        self, quote_asset: str | None = None, use_cache: bool = True
    ) -> list[Symbol]:
        """List trading symbols, optionally filtered by quote asset.

        Args:
            quote_asset: Optional quote asset filter (e.g., "USDT")
            use_cache: Whether to use cached results (not implemented yet)

        Returns:
            List of Symbol objects
        """
        params = {"quote_asset": quote_asset}
        data = await self.fetch("exchange_info", params)
        return list(data) if use_cache else data

    async def get_order_book(self, symbol: str, limit: int = 50) -> OrderBook:
        """Fetch current order book.

        Args:
            symbol: Trading symbol
            limit: Depth limit (default 50, Bybit supports: 1, 25, 50, 100, 200)

        Returns:
            OrderBook object
        """
        params = {"symbol": symbol, "limit": limit}
        result: OrderBook = await self.fetch("order_book", params)
        return result

    async def get_recent_trades(self, symbol: str, limit: int = 50) -> list[Trade]:
        """Fetch recent trades.

        Args:
            symbol: Trading symbol
            limit: Number of trades to fetch (default 50, max 1000)

        Returns:
            List of Trade objects
        """
        params = {"symbol": symbol, "limit": limit}
        data = await self.fetch("recent_trades", params)
        return list(data)

    async def get_funding_rate(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[FundingRate]:
        """Fetch historical applied funding rates (Futures-only).

        Args:
            symbol: Trading symbol
            start_time: Optional start time
            end_time: Optional end time
            limit: Number of records (default 100, max 200)

        Returns:
            List of FundingRate objects

        Raises:
            ValueError: If not futures market
        """
        if self.market_type != MarketType.FUTURES:
            raise ValueError("Funding rates are only available for Futures on Bybit")

        params: dict[str, Any] = {
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
        """Fetch open interest (current or historical, Futures-only).

        Args:
            symbol: Trading symbol
            historical: If True, fetch historical data
            period: Period for historical data (default "5m")
            start_time: Optional start time for historical
            end_time: Optional end time for historical
            limit: Number of records (default 30, max 200 for historical)

        Returns:
            List of OpenInterest objects

        Raises:
            ValueError: If not futures market
        """
        if self.market_type != MarketType.FUTURES:
            raise ValueError("Open interest is only available for Futures on Bybit")

        if historical:
            params: dict[str, Any] = {
                "symbol": symbol,
                "period": period,
                "start_time": start_time,
                "end_time": end_time,
                "limit": limit,
            }
            data = await self.fetch("open_interest_hist", params)
        else:
            params = {"symbol": symbol}
            data = await self.fetch("open_interest_current", params)
        return list(data)

    async def __aenter__(self) -> BybitRESTConnector:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close underlying HTTP resources."""
        await self._transport.close()
