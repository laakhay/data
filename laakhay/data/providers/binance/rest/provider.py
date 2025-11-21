"""Binance REST-only provider (shim for backward compatibility).

This module is a shim that wraps the connector-based REST provider.
The actual implementation has been moved to connectors/binance/rest/provider.py.
"""

from __future__ import annotations

from datetime import datetime

from ....core import MarketType, Timeframe
from ....models import FundingRate, OHLCV, OpenInterest, OrderBook, Symbol, Trade
from ....runtime.rest import RESTProvider
from ...connectors.binance.rest.provider import BinanceRESTConnector


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
        """Fetch OHLCV bars (delegates to connector)."""
        # Convert string timeframe to Timeframe if needed
        if isinstance(timeframe, str):
            tf = Timeframe.from_str(timeframe)
            if tf is None:
                raise ValueError(f"Invalid timeframe: {timeframe}")
            timeframe = tf
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
