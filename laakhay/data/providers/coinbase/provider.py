"""Coinbase providers (REST-only, WS-only, and unified facade).

This module provides shims that delegate to the connector implementations.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

from laakhay.data.connectors.coinbase.provider import (
    CoinbaseProvider as ConnectorCoinbaseProvider,
)
from laakhay.data.connectors.coinbase.rest.provider import CoinbaseRESTConnector
from laakhay.data.connectors.coinbase.ws.provider import CoinbaseWSConnector

from ...capability.registry import CapabilityStatus
from ..coinbase.rest.provider import CoinbaseRESTProvider
from ..coinbase.ws.provider import CoinbaseWSProvider
from ...core import (
    BaseProvider,
    DataFeature,
    InstrumentType,
    MarketType,
    Timeframe,
    TransportKind,
    register_feature_handler,
)
from ...models import OHLCV, OrderBook, StreamingBar, Symbol, Trade


class CoinbaseProvider(BaseProvider):
    """High-level Coinbase provider exposing REST and streaming helpers.

    This is a shim that delegates to the connector implementation.
    """

    def __init__(
        self,
        *,
        market_type: MarketType = MarketType.SPOT,
        api_key: str | None = None,
        api_secret: str | None = None,
        rest_provider: CoinbaseRESTConnector | None = None,
        ws_provider: CoinbaseWSConnector | None = None,
    ) -> None:
        super().__init__(name="coinbase")
        self.market_type = market_type
        self._connector_provider = ConnectorCoinbaseProvider(
            market_type=market_type,
            api_key=api_key,
            api_secret=api_secret,
            rest_connector=rest_provider,
            ws_connector=ws_provider,
        )
        # Expose _rest and _ws as shims for backward compatibility with tests
        # Wrap connectors in shims so tests can check isinstance
        self._rest = CoinbaseRESTProvider(
            market_type=market_type,
            api_key=api_key,
            api_secret=api_secret,
        )
        # Use the connector's transport for the shim
        self._rest._connector = self._connector_provider._rest
        self._rest._transport = self._connector_provider._rest._transport
        self._ws = CoinbaseWSProvider(market_type=market_type)
        # Use the connector for the shim
        self._ws._connector = self._connector_provider._ws

    def get_timeframes(self) -> list[str]:
        return self._connector_provider.get_timeframes()

    @register_feature_handler(DataFeature.HEALTH, TransportKind.REST)
    async def fetch_health(self) -> dict[str, object]:
        return await self._connector_provider.fetch_health()

    # --- REST delegations -------------------------------------------------
    @register_feature_handler(DataFeature.OHLCV, TransportKind.REST)
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str | Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> OHLCV:
        return await self._connector_provider.fetch_ohlcv(
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
        return await self._connector_provider.get_symbols(
            quote_asset=quote_asset, use_cache=use_cache
        )

    @register_feature_handler(DataFeature.ORDER_BOOK, TransportKind.REST)
    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        return await self._connector_provider.get_order_book(symbol=symbol, limit=limit)

    async def get_exchange_info(self) -> dict:
        return await self._connector_provider.get_exchange_info()

    @register_feature_handler(DataFeature.TRADES, TransportKind.REST)
    async def get_recent_trades(self, symbol: str, limit: int = 500) -> list[Trade]:
        return await self._connector_provider.get_recent_trades(symbol=symbol, limit=limit)

    # --- Streaming delegations -------------------------------------------
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
        async for bar in self._connector_provider.stream_ohlcv(
            symbol,
            timeframe,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_same_candle=dedupe_same_candle,
        ):
            yield bar

    @register_feature_handler(DataFeature.OHLCV, TransportKind.WS)
    async def stream_ohlcv_multi(
        self,
        symbols: list[str],
        timeframe: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        async for bar in self._connector_provider.stream_ohlcv_multi(
            symbols,
            timeframe,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_same_candle=dedupe_same_candle,
        ):
            yield bar

    @register_feature_handler(DataFeature.TRADES, TransportKind.WS)
    async def stream_trades(self, symbol: str) -> AsyncIterator[Trade]:
        async for trade in self._connector_provider.stream_trades(symbol):
            yield trade

    @register_feature_handler(DataFeature.TRADES, TransportKind.WS)
    async def stream_trades_multi(self, symbols: list[str]) -> AsyncIterator[Trade]:
        async for trade in self._connector_provider.stream_trades_multi(symbols):
            yield trade

    @register_feature_handler(DataFeature.ORDER_BOOK, TransportKind.WS)
    async def stream_order_book(
        self, symbol: str, update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        async for book in self._connector_provider.stream_order_book(
            symbol, update_speed=update_speed
        ):
            yield book

    @register_feature_handler(DataFeature.ORDER_BOOK, TransportKind.WS)
    async def stream_order_book_multi(
        self, symbols: list[str], update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        async for book in self._connector_provider.stream_order_book_multi(
            symbols, update_speed=update_speed
        ):
            yield book

    async def describe_capabilities(
        self,
        feature: DataFeature,
        transport: TransportKind,
        *,
        market_type: MarketType,
        instrument_type: InstrumentType,
    ) -> CapabilityStatus:
        return await self._connector_provider.describe_capabilities(
            feature=feature,
            transport=transport,
            market_type=market_type,
            instrument_type=instrument_type,
        )

    async def close(self) -> None:
        await self._connector_provider.close()
