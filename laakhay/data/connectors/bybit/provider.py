"""Unified Bybit connector provider.

This provider combines REST and WebSocket connectors for use by DataRouter
or direct research use. It registers all feature handlers for capability
discovery.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

from laakhay.data.connectors.bybit.config import INTERVAL_MAP
from laakhay.data.connectors.bybit.rest.provider import BybitRESTConnector
from laakhay.data.connectors.bybit.ws.provider import BybitWSConnector
from laakhay.data.core import (
    DataFeature,
    MarketType,
    MarketVariant,
    Timeframe,
    TransportKind,
    register_feature_handler,
)
from laakhay.data.models import (
    OHLCV,
    FundingRate,
    Liquidation,
    MarkPrice,
    OpenInterest,
    OrderBook,
    StreamingBar,
    Symbol,
    Trade,
)


class BybitProvider:
    """Unified Bybit provider combining REST and WebSocket connectors.

    This provider can be used directly by researchers or wrapped by the
    DataRouter. It registers all feature handlers for capability discovery.
    """

    def __init__(
        self,
        *,
        market_type: MarketType = MarketType.SPOT,
        market_variant: MarketVariant | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        rest_connector: BybitRESTConnector | None = None,
        ws_connector: BybitWSConnector | None = None,
    ) -> None:
        """Initialize unified Bybit provider.

        Args:
            market_type: Market type (spot or futures)
            market_variant: Optional market variant. If not provided, derived from
                          market_type with smart defaults:
                          - SPOT → SPOT
                          - FUTURES → LINEAR_PERP (can be overridden)
                          - OPTIONS → OPTIONS
            api_key: Optional API key for authenticated endpoints
            api_secret: Optional API secret (not currently used)
            rest_connector: Optional REST connector instance
            ws_connector: Optional WebSocket connector instance
        """
        self.name = "bybit"
        self.market_type = market_type
        # Derive market_variant from market_type if not provided (backward compatibility)
        if market_variant is None:
            self.market_variant = MarketVariant.from_market_type(market_type)
        else:
            self.market_variant = market_variant

        self._rest = rest_connector or BybitRESTConnector(
            market_type=market_type,
            market_variant=self.market_variant,
            api_key=api_key,
            api_secret=api_secret,
        )
        self._ws = ws_connector or BybitWSConnector(
            market_type=market_type, market_variant=self.market_variant
        )
        self._owns_rest = rest_connector is None
        self._owns_ws = ws_connector is None
        self._closed = False

    def get_timeframes(self) -> list[Timeframe]:
        """Get list of supported timeframes.

        Returns:
            List of Timeframe objects
        """
        return list(INTERVAL_MAP.keys())

    @register_feature_handler(DataFeature.HEALTH, TransportKind.REST)
    async def fetch_health(self) -> dict[str, object]:
        """Fetch health status."""
        return await self._rest.fetch_health()

    @register_feature_handler(DataFeature.OHLCV, TransportKind.REST)
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> OHLCV:
        """Fetch OHLCV bars."""
        return await self._rest.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    @register_feature_handler(DataFeature.SYMBOL_METADATA, TransportKind.REST)
    async def get_symbols(
        self, quote_asset: str | None = None, use_cache: bool = True
    ) -> list[Symbol]:
        """Get trading symbols."""
        return await self._rest.get_symbols(quote_asset=quote_asset, use_cache=use_cache)

    @register_feature_handler(DataFeature.ORDER_BOOK, TransportKind.REST)
    async def get_order_book(self, symbol: str, limit: int = 50) -> OrderBook:
        """Fetch order book."""
        return await self._rest.get_order_book(symbol=symbol, limit=limit)

    @register_feature_handler(DataFeature.TRADES, TransportKind.REST)
    async def get_recent_trades(self, symbol: str, limit: int = 50) -> list[Trade]:
        """Fetch recent trades."""
        return await self._rest.get_recent_trades(symbol=symbol, limit=limit)

    @register_feature_handler(DataFeature.FUNDING_RATE, TransportKind.REST)
    async def get_funding_rate(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[FundingRate]:
        """Fetch funding rates."""
        return await self._rest.get_funding_rate(
            symbol=symbol, start_time=start_time, end_time=end_time, limit=limit
        )

    @register_feature_handler(DataFeature.OPEN_INTEREST, TransportKind.REST)
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
        return await self._rest.get_open_interest(
            symbol=symbol,
            historical=historical,
            period=period,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    @register_feature_handler(DataFeature.OHLCV, TransportKind.WS)
    async def stream_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        """Stream OHLCV bars."""
        async for bar in self._ws.stream_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_same_candle=dedupe_same_candle,
        ):
            yield bar

    @register_feature_handler(DataFeature.TRADES, TransportKind.WS)
    async def stream_trades(self, symbol: str) -> AsyncIterator[Trade]:
        """Stream trades."""
        async for trade in self._ws.stream_trades(symbol=symbol):
            yield trade

    @register_feature_handler(DataFeature.OPEN_INTEREST, TransportKind.WS)
    async def stream_open_interest(
        self, symbols: list[str], period: str = "5m"
    ) -> AsyncIterator[OpenInterest]:
        """Stream open interest updates."""
        async for oi in self._ws.stream_open_interest(symbols=symbols, period=period):
            yield oi

    @register_feature_handler(DataFeature.FUNDING_RATE, TransportKind.WS)
    async def stream_funding_rate(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[FundingRate]:
        """Stream funding rate updates."""
        async for fr in self._ws.stream_funding_rate(symbols=symbols, update_speed=update_speed):
            yield fr

    @register_feature_handler(DataFeature.MARK_PRICE, TransportKind.WS)
    async def stream_mark_price(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[MarkPrice]:
        """Stream mark price updates."""
        async for mp in self._ws.stream_mark_price(symbols=symbols, update_speed=update_speed):
            yield mp

    @register_feature_handler(DataFeature.ORDER_BOOK, TransportKind.WS)
    async def stream_order_book(
        self, symbol: str, update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        """Stream order book updates."""
        async for ob in self._ws.stream_order_book(symbol=symbol, update_speed=update_speed):
            yield ob

    @register_feature_handler(DataFeature.LIQUIDATIONS, TransportKind.WS)
    async def stream_liquidations(self) -> AsyncIterator[Liquidation]:
        """Stream liquidation events."""
        async for liq in self._ws.stream_liquidations():
            yield liq

    async def close(self) -> None:
        """Close underlying resources."""
        if self._closed:
            return
        self._closed = True
        if self._owns_rest:
            await self._rest.close()
        if self._owns_ws:
            await self._ws.close()

    async def __aenter__(self) -> BybitProvider:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
