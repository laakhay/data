"""Coinbase REST connector for direct use by researchers.

This connector provides direct access to Coinbase REST endpoints without
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

from laakhay.data.connectors.coinbase.config import BASE_URLS, INTERVAL_MAP
from laakhay.data.core import MarketType, Timeframe
from laakhay.data.models import OHLCV, OrderBook, Symbol, Trade
from laakhay.data.runtime.rest import RESTProvider, RestRunner, RESTTransport

from .endpoints import get_endpoint_adapter, get_endpoint_spec


class CoinbaseRESTConnector(RESTProvider):
    """Coinbase REST connector for direct research use.

    This connector can be used directly without going through DataRouter.
    It provides full access to Coinbase REST endpoints with automatic
    endpoint spec and adapter resolution.
    """

    _MAX_CANDLES_PER_REQUEST = 300  # Coinbase max is 300 candles per request
    _DEFAULT_MAX_CANDLE_CHUNKS = 5

    def __init__(
        self,
        *,
        market_type: MarketType = MarketType.SPOT,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        """Initialize Coinbase REST connector.

        Args:
            market_type: Market type (only SPOT supported for Coinbase)
            api_key: Optional API key (not currently used)
            api_secret: Optional API secret (not currently used)
        """
        # Coinbase Advanced Trade API only supports Spot markets
        if market_type != MarketType.SPOT:
            raise ValueError(
                "Coinbase Advanced Trade API only supports Spot markets. "
                f"Got market_type={market_type}"
            )

        self.market_type = MarketType.SPOT  # Force to SPOT
        self._api_key = api_key
        self._transport = RESTTransport(base_url=BASE_URLS[MarketType.SPOT])
        self._runner = RestRunner(self._transport)

    async def fetch_health(self) -> dict[str, object]:
        """Ping Coinbase REST API to verify connectivity."""
        path = "/products"
        start = perf_counter()
        await self._transport.get(path, params={"limit": 1})
        latency_ms = (perf_counter() - start) * 1000.0
        return {
            "exchange": "coinbase",
            "market_type": self.market_type.value,
            "status": "ok",
            "latency_ms": latency_ms,
            "endpoint": path,
        }

    async def fetch(self, endpoint_id: str, params: dict[str, Any]) -> Any:
        """Fetch data from a Coinbase REST endpoint.

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
        timeframe: str | Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
        max_chunks: int | None = None,
    ) -> OHLCV:
        """Fetch OHLCV candles for a symbol.

        Coinbase returns up to 300 candles per request. If more are needed,
        requests are chunked automatically.

        Args:
            symbol: Trading symbol (e.g., "BTCUSD")
            timeframe: Timeframe for bars
            start_time: Optional start time
            end_time: Optional end time
            limit: Optional limit on number of bars
            max_chunks: Optional maximum number of chunks

        Returns:
            OHLCV object with bars
        """
        # Convert string timeframe to Timeframe if needed
        if isinstance(timeframe, str):
            tf = Timeframe.from_str(timeframe)
            if tf is None:
                raise ValueError(f"Invalid timeframe: {timeframe}")
            timeframe = tf

        if timeframe not in INTERVAL_MAP:
            raise ValueError(f"Invalid timeframe: {timeframe}")

        interval_str = INTERVAL_MAP[timeframe]

        # Simple path: delegate to fetch
        params = {
            "symbol": symbol,
            "interval": timeframe,
            "interval_str": interval_str,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
        }
        result: OHLCV = await self.fetch("ohlcv", params)
        return result

    async def get_symbols(
        self, quote_asset: str | None = None, use_cache: bool = True
    ) -> list[Symbol]:
        """Get trading symbols.

        Args:
            quote_asset: Optional filter by quote asset (e.g., "USD")
            use_cache: Whether to use cache (not implemented)

        Returns:
            List of Symbol objects
        """
        params = {"quote_asset": quote_asset}
        data = await self.fetch("exchange_info", params)
        return list(data) if use_cache else data

    async def get_exchange_info(self) -> dict:
        """Return raw exchange info payload.

        Returns:
            Raw exchange info response
        """
        params = {}
        data = await self.fetch("exchange_info", params)
        return data

    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        """Fetch order book.

        Args:
            symbol: Trading symbol
            limit: Number of levels (Coinbase uses levels: 1, 2, or 3)

        Returns:
            OrderBook object
        """
        params = {"symbol": symbol, "limit": limit}
        result: OrderBook = await self.fetch("order_book", params)
        return result

    async def get_recent_trades(self, symbol: str, limit: int = 500) -> list[Trade]:
        """Fetch recent trades.

        Args:
            symbol: Trading symbol
            limit: Number of trades (max 1000)

        Returns:
            List of Trade objects
        """
        params = {"symbol": symbol, "limit": limit}
        data = await self.fetch("recent_trades", params)
        return list(data)

    async def close(self) -> None:
        """Close underlying resources."""
        await self._transport.close()

