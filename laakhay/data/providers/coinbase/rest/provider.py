"""Coinbase REST-only provider (shim for backward compatibility).

This module is a shim that wraps the connector-based REST provider.
The actual implementation has been moved to connectors/coinbase/rest/provider.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from laakhay.data.connectors.coinbase.rest.provider import CoinbaseRESTConnector

from ....core import MarketType, Timeframe
from ....models import OHLCV, OrderBook, Symbol, Trade
from ....runtime.rest import RESTProvider


class CoinbaseRESTProvider(RESTProvider):
    """REST-only provider for Coinbase Spot (shim)."""

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
        """Fetch OHLCV bars (delegates to connector)."""
        # Convert string timeframe to Timeframe if needed
        if isinstance(timeframe, str):
            tf = Timeframe.from_str(timeframe)
            if tf is None:
                raise ValueError(f"Invalid timeframe: {timeframe}")
            timeframe = tf

        # Simple path: delegate to connector
        return await self._connector.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            max_chunks=max_chunks,
        )

    async def get_symbols(
        self, quote_asset: str | None = None, use_cache: bool = True
    ) -> list[Symbol]:
        """Get trading symbols."""
        return await self._connector.get_symbols(quote_asset=quote_asset, use_cache=use_cache)

    async def get_exchange_info(self) -> dict:
        """Return raw exchange info payload."""
        return await self._connector.get_exchange_info()

    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        """Fetch order book."""
        return await self._connector.get_order_book(symbol=symbol, limit=limit)

    async def get_recent_trades(self, symbol: str, limit: int = 500) -> list[Trade]:
        """Fetch recent trades."""
        return await self._connector.get_recent_trades(symbol=symbol, limit=limit)

    async def close(self) -> None:
        """Close underlying resources."""
        await self._connector.close()
