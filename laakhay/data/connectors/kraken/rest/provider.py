"""Kraken REST connector for direct use by researchers.

This connector provides direct access to Kraken REST endpoints without
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

from laakhay.data.connectors.kraken.config import BASE_URLS, INTERVAL_MAP
from laakhay.data.core import MarketType, Timeframe
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


class KrakenRESTConnector(RESTProvider):
    """Kraken REST connector for direct research use.

    This connector can be used directly without going through DataRouter.
    It provides full access to Kraken REST endpoints with automatic
    endpoint spec and adapter resolution.
    """

    _MAX_CANDLES_PER_REQUEST = 720  # Kraken Spot limit is 720, Futures is higher

    def __init__(
        self,
        market_type: MarketType,
        *,
        api_key: str | None = None,
        api_secret: str | None = None,  # noqa: ARG002
    ) -> None:
        """Initialize Kraken REST connector.

        Args:
            market_type: Market type (spot or futures)
            api_key: Optional API key for authenticated endpoints
            api_secret: Optional API secret (not currently used)
        """
        self.market_type = market_type
        self._api_key = api_key
        self._transport = RESTTransport(base_url=BASE_URLS[market_type])
        self._runner = RestRunner(self._transport)

    async def fetch_health(self) -> dict[str, object]:
        """Ping Kraken REST API to verify connectivity."""
        path = "/0/public/SystemStatus" if self.market_type == MarketType.SPOT else "/instruments"
        start = perf_counter()
        await self._transport.get(path)
        latency_ms = (perf_counter() - start) * 1000.0
        return {
            "exchange": "kraken",
            "market_type": self.market_type.value,
            "status": "ok",
            "latency_ms": latency_ms,
            "endpoint": path,
        }

    async def fetch(self, endpoint_id: str, params: dict[str, Any]) -> Any:
        """Fetch data from a Kraken REST endpoint.

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

        # Ensure market_type is in params
        params = {**params, "market_type": self.market_type}

        adapter = adapter_cls()
        return await self._runner.run(spec=spec, adapter=adapter, params=params)

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> OHLCV:
        """Fetch OHLCV bars for a symbol and timeframe.

        Args:
            symbol: Trading symbol (e.g., "BTCUSD")
            interval: Timeframe for bars
            start_time: Optional start time
            end_time: Optional end time
            limit: Optional limit on number of bars

        Returns:
            OHLCV object with bars
        """
        if interval not in INTERVAL_MAP:
            raise ValueError(f"Invalid timeframe: {interval}")

        params = {
            "symbol": symbol,
            "interval": interval,
            "interval_str": INTERVAL_MAP[interval],
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
        }
        result: OHLCV = await self.fetch("ohlcv", params)
        return result

    async def get_symbols(
        self,
        quote_asset: str | None = None,
        use_cache: bool = True,  # noqa: ARG002
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
        return list(data)

    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        """Fetch current order book.

        Args:
            symbol: Trading symbol
            limit: Depth limit (default 100)

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
            limit: Number of trades to fetch (default 50)

        Returns:
            List of Trade objects
        """
        params = {"symbol": symbol, "limit": limit}
        data = await self.fetch("recent_trades", params)
        return list(data)

    async def fetch_historical_trades(
        self,
        symbol: str,
        *,
        limit: int | None = None,
        from_id: int | None = None,  # noqa: ARG002
    ) -> list[Trade]:
        """Fetch historical trades (requires API key for Futures).

        Args:
            symbol: Trading symbol
            limit: Optional limit on number of trades
            from_id: Optional trade ID to start from (not used for Kraken)

        Returns:
            List of Trade objects

        Raises:
            ValueError: If API key missing for Futures
        """
        if self.market_type == MarketType.FUTURES and not self._api_key:
            raise ValueError("api_key is required to use Kraken Futures historical trades endpoint")

        params = {
            "symbol": symbol,
            "limit": limit,
            "api_key": self._api_key,
        }
        data = await self.fetch("historical_trades", params)
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
            limit: Number of records (default 100)

        Returns:
            List of FundingRate objects

        Raises:
            ValueError: If not futures market
        """
        if self.market_type != MarketType.FUTURES:
            raise ValueError("Funding rates are only available for Futures on Kraken")

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
        period: str = "5m",  # noqa: ARG002
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 30,
    ) -> list[OpenInterest]:
        """Fetch open interest (current or historical, Futures-only).

        Args:
            symbol: Trading symbol
            historical: If True, fetch historical data
            period: Period for historical data (not used, kept for compatibility)
            start_time: Optional start time for historical
            end_time: Optional end time for historical
            limit: Number of records (default 30)

        Returns:
            List of OpenInterest objects

        Raises:
            ValueError: If not futures market
        """
        if self.market_type != MarketType.FUTURES:
            raise ValueError("Open interest is only available for Futures on Kraken")

        if historical:
            params: dict[str, Any] = {
                "symbol": symbol,
                "start_time": start_time,
                "end_time": end_time,
                "limit": limit,
            }
            data = await self.fetch("open_interest_hist", params)
        else:
            params = {"symbol": symbol}
            data = await self.fetch("open_interest_current", params)
        return list(data)

    async def close(self) -> None:
        """Close underlying HTTP resources."""
        await self._transport.close()
