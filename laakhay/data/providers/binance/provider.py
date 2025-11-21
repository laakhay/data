"""Unified Binance provider (shim for backward compatibility).

This module is a shim that wraps the connector-based provider. The actual
implementation has been moved to connectors/binance/provider.py.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

from laakhay.data.connectors.binance.provider import BinanceProvider as BinanceConnectorProvider
from laakhay.data.connectors.binance.rest.provider import BinanceRESTConnector
from laakhay.data.connectors.binance.ws.provider import BinanceWSConnector

from ...capability.registry import CapabilityStatus, supports
from ...core import (
    BaseProvider,
    DataFeature,
    InstrumentType,
    MarketType,
    Timeframe,
    TransportKind,
    register_feature_handler,
)
from ...models import (
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


class BinanceProvider(BaseProvider):
    """High-level Binance provider (shim wrapping connector-based provider)."""

    def __init__(
        self,
        *,
        market_type: MarketType = MarketType.SPOT,
        api_key: str | None = None,
        api_secret: str | None = None,
        rest_provider: BinanceRESTConnector | None = None,
        ws_provider: BinanceWSConnector | None = None,
    ) -> None:
        super().__init__(name="binance")
        self.market_type = market_type
        # Use connector-based provider
        self._connector = BinanceConnectorProvider(
            market_type=market_type,
            api_key=api_key,
            api_secret=api_secret,
            rest_connector=rest_provider,
            ws_connector=ws_provider,
        )
        # Expose _rest and _ws for backward compatibility with tests
        self._rest = self._connector._rest
        self._ws = self._connector._ws
        self._owns_rest = rest_provider is None
        self._owns_ws = ws_provider is None
        self._closed = False

    def get_timeframes(self) -> list[Timeframe]:
        """Get list of supported timeframes."""
        return self._connector.get_timeframes()

    @register_feature_handler(DataFeature.HEALTH, TransportKind.REST)
    async def fetch_health(self) -> dict[str, object]:
        """Fetch health information for Binance."""
        return await self._connector.fetch_health()

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
        # Convert string timeframe to Timeframe if needed
        if isinstance(timeframe, str):
            from ...core import Timeframe

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

    @register_feature_handler(DataFeature.SYMBOL_METADATA, TransportKind.REST)
    async def get_symbols(  # type: ignore[override]
        self, quote_asset: str | None = None, use_cache: bool = True
    ) -> list[Symbol]:
        return await self._connector.get_symbols(quote_asset=quote_asset, use_cache=use_cache)

    @register_feature_handler(DataFeature.ORDER_BOOK, TransportKind.REST)
    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        return await self._connector.get_order_book(symbol=symbol, limit=limit)

    async def get_exchange_info(self) -> dict:
        """Return raw exchange info payload."""
        # Delegate to REST connector's fetch method
        return await self._connector._rest.fetch("exchange_info", {})

    @register_feature_handler(DataFeature.TRADES, TransportKind.REST)
    async def get_recent_trades(self, symbol: str, limit: int = 500) -> list[Trade]:
        return await self._connector.get_recent_trades(symbol=symbol, limit=limit)

    @register_feature_handler(DataFeature.HISTORICAL_TRADES, TransportKind.REST)
    async def fetch_historical_trades(
        self, symbol: str, *, limit: int | None = None, from_id: int | None = None
    ) -> list[Trade]:
        return await self._connector.fetch_historical_trades(
            symbol=symbol, limit=limit, from_id=from_id
        )

    @register_feature_handler(DataFeature.FUNDING_RATE, TransportKind.REST)
    async def get_funding_rate(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[FundingRate]:
        return await self._connector.get_funding_rate(
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
        return await self._connector.get_open_interest(
            symbol=symbol,
            historical=historical,
            period=period,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

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
        async for bar in self._connector.stream_ohlcv(
            symbol=symbol,
            interval=timeframe,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_same_candle=dedupe_same_candle,
        ):
            yield bar

    async def stream_ohlcv_multi(
        self,
        symbols: list[str],
        timeframe: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        async for bar in self._connector._ws.stream_ohlcv_multi(
            symbols=symbols,
            interval=timeframe,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_same_candle=dedupe_same_candle,
        ):
            yield bar

    @register_feature_handler(DataFeature.TRADES, TransportKind.WS)
    async def stream_trades(self, symbol: str) -> AsyncIterator[Trade]:
        async for trade in self._connector.stream_trades(symbol=symbol):
            yield trade

    async def stream_trades_multi(self, symbols: list[str]) -> AsyncIterator[Trade]:
        async for trade in self._connector._ws.stream_trades_multi(symbols=symbols):
            yield trade

    @register_feature_handler(DataFeature.OPEN_INTEREST, TransportKind.WS)
    async def stream_open_interest(
        self, symbols: list[str], period: str = "5m"
    ) -> AsyncIterator[OpenInterest]:
        async for oi in self._connector.stream_open_interest(symbols=symbols, period=period):
            yield oi

    @register_feature_handler(DataFeature.FUNDING_RATE, TransportKind.WS)
    async def stream_funding_rate(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[FundingRate]:
        async for rate in self._connector.stream_funding_rate(
            symbols=symbols, update_speed=update_speed
        ):
            yield rate

    @register_feature_handler(DataFeature.MARK_PRICE, TransportKind.WS)
    async def stream_mark_price(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator[MarkPrice]:
        async for mark in self._connector.stream_mark_price(
            symbols=symbols, update_speed=update_speed
        ):
            yield mark

    @register_feature_handler(DataFeature.ORDER_BOOK, TransportKind.WS)
    async def stream_order_book(
        self, symbol: str, update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        async for ob in self._connector.stream_order_book(symbol=symbol, update_speed=update_speed):
            yield ob

    async def stream_order_book_multi(
        self, symbols: list[str], update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        async for ob in self._connector._ws.stream_order_book_multi(
            symbols=symbols, update_speed=update_speed
        ):
            yield ob

    @register_feature_handler(DataFeature.LIQUIDATIONS, TransportKind.WS)
    async def stream_liquidations(self) -> AsyncIterator[Liquidation]:
        async for liq in self._connector.stream_liquidations():
            yield liq

    # --- Capability discovery ----------------------------------------------
    async def describe_capabilities(
        self,
        feature: DataFeature,
        transport: TransportKind,
        *,
        market_type: MarketType,
        instrument_type: InstrumentType,
    ) -> CapabilityStatus:
        """Describe capabilities for Binance.

        Returns static capability status from the registry.
        Runtime discovery can be added later to probe actual API availability.
        """
        return supports(
            feature=feature,
            transport=transport,
            exchange="binance",
            market_type=market_type,
            instrument_type=instrument_type,
        )

    # --- Lifecycle --------------------------------------------------------
    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._connector.close()
