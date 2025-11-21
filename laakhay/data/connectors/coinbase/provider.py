"""Unified Coinbase connector provider.

This provider combines REST and WebSocket connectors for use by DataRouter
or direct research use. It registers all feature handlers for capability
discovery.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

from laakhay.data.capability.registry import CapabilityStatus, supports
from laakhay.data.connectors.coinbase.config import INTERVAL_MAP
from laakhay.data.connectors.coinbase.rest.provider import CoinbaseRESTConnector
from laakhay.data.connectors.coinbase.ws.provider import CoinbaseWSConnector
from laakhay.data.core import (
    BaseProvider,
    DataFeature,
    InstrumentType,
    MarketType,
    Timeframe,
    TransportKind,
    register_feature_handler,
)
from laakhay.data.models import OHLCV, OrderBook, StreamingBar, Symbol, Trade


class CoinbaseProvider(BaseProvider):
    """Unified Coinbase provider combining REST and WebSocket connectors.

    This provider can be used directly by researchers or wrapped by the
    DataRouter. It registers all feature handlers for capability discovery.

    Coinbase Advanced Trade API only supports Spot markets.
    """

    def __init__(
        self,
        *,
        market_type: MarketType = MarketType.SPOT,
        api_key: str | None = None,
        api_secret: str | None = None,
        rest_connector: CoinbaseRESTConnector | None = None,
        ws_connector: CoinbaseWSConnector | None = None,
    ) -> None:
        """Initialize unified Coinbase provider.

        Args:
            market_type: Market type (only SPOT supported for Coinbase)
            api_key: Optional API key (not currently used)
            api_secret: Optional API secret (not currently used)
            rest_connector: Optional REST connector instance
            ws_connector: Optional WebSocket connector instance
        """
        # Coinbase Advanced Trade API only supports Spot markets
        if market_type != MarketType.SPOT:
            raise ValueError(
                "Coinbase Advanced Trade API only supports Spot markets. "
                f"Got market_type={market_type}"
            )

        super().__init__(name="coinbase")
        self.market_type = MarketType.SPOT  # Force to SPOT
        self._rest = rest_connector or CoinbaseRESTConnector(
            market_type=MarketType.SPOT, api_key=api_key, api_secret=api_secret
        )
        self._ws = ws_connector or CoinbaseWSConnector(market_type=MarketType.SPOT)
        self._owns_rest = rest_connector is None
        self._owns_ws = ws_connector is None
        self._closed = False

    def get_timeframes(self) -> list[str]:
        """Get list of supported timeframes.

        Returns:
            List of timeframe strings
        """
        return list(INTERVAL_MAP.keys())

    @register_feature_handler(DataFeature.HEALTH, TransportKind.REST)
    async def fetch_health(self) -> dict[str, object]:
        """Fetch health status."""
        return await self._rest.fetch_health()

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
    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        """Fetch order book."""
        return await self._rest.get_order_book(symbol=symbol, limit=limit)

    @register_feature_handler(DataFeature.TRADES, TransportKind.REST)
    async def get_recent_trades(self, symbol: str, limit: int = 500) -> list[Trade]:
        """Fetch recent trades."""
        return await self._rest.get_recent_trades(symbol=symbol, limit=limit)

    async def get_exchange_info(self) -> dict:
        """Return raw exchange info payload."""
        return await self._rest.get_exchange_info()

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
        """Stream OHLCV bars."""
        async for bar in self._ws.stream_ohlcv(
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
        """Stream OHLCV bars for multiple symbols."""
        async for bar in self._ws.stream_ohlcv_multi(
            symbols,
            timeframe,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_same_candle=dedupe_same_candle,
        ):
            yield bar

    @register_feature_handler(DataFeature.TRADES, TransportKind.WS)
    async def stream_trades(self, symbol: str) -> AsyncIterator[Trade]:
        """Stream trades."""
        async for trade in self._ws.stream_trades(symbol):
            yield trade

    @register_feature_handler(DataFeature.TRADES, TransportKind.WS)
    async def stream_trades_multi(self, symbols: list[str]) -> AsyncIterator[Trade]:
        """Stream trades for multiple symbols."""
        async for trade in self._ws.stream_trades_multi(symbols):
            yield trade

    @register_feature_handler(DataFeature.ORDER_BOOK, TransportKind.WS)
    async def stream_order_book(
        self, symbol: str, update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        """Stream order book updates."""
        async for book in self._ws.stream_order_book(symbol, update_speed=update_speed):
            yield book

    @register_feature_handler(DataFeature.ORDER_BOOK, TransportKind.WS)
    async def stream_order_book_multi(
        self, symbols: list[str], update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        """Stream order book updates for multiple symbols."""
        async for book in self._ws.stream_order_book_multi(symbols, update_speed=update_speed):
            yield book

    async def describe_capabilities(
        self,
        feature: DataFeature,
        transport: TransportKind,
        *,
        market_type: MarketType,
        instrument_type: InstrumentType,
    ) -> CapabilityStatus:
        """Describe capabilities for a feature/transport combination."""
        return supports(
            feature=feature,
            transport=transport,
            exchange="coinbase",
            market_type=market_type,
            instrument_type=instrument_type,
        )

    async def close(self) -> None:
        """Close underlying resources."""
        if self._closed:
            return
        self._closed = True
        if self._owns_rest:
            await self._rest.close()
        if self._owns_ws:
            await self._ws.close()

