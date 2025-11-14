"""Unified Coinbase provider that wraps REST and WebSocket implementations."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

from ...core import (
    BaseProvider,
    DataFeature,
    InstrumentType,
    MarketType,
    Timeframe,
    TransportKind,
    register_feature_handler,
)
from ...core.capabilities import CapabilityStatus, supports
from ...models import OHLCV, OrderBook, StreamingBar, Symbol, Trade
from .rest.provider import CoinbaseRESTProvider
from .ws.provider import CoinbaseWSProvider


class CoinbaseProvider(BaseProvider):
    """High-level Coinbase provider exposing REST and streaming helpers.

    Coinbase Advanced Trade API only supports Spot markets.
    """

    def __init__(
        self,
        *,
        market_type: MarketType = MarketType.SPOT,
        api_key: str | None = None,
        api_secret: str | None = None,
        rest_provider: CoinbaseRESTProvider | None = None,
        ws_provider: CoinbaseWSProvider | None = None,
    ) -> None:
        # Coinbase Advanced Trade API only supports Spot markets
        if market_type != MarketType.SPOT:
            raise ValueError(
                "Coinbase Advanced Trade API only supports Spot markets. "
                f"Got market_type={market_type}"
            )

        super().__init__(name="coinbase")
        self.market_type = MarketType.SPOT  # Force to SPOT
        self._rest = rest_provider or CoinbaseRESTProvider(
            market_type=MarketType.SPOT, api_key=api_key, api_secret=api_secret
        )
        self._ws = ws_provider or CoinbaseWSProvider(market_type=MarketType.SPOT)
        self._owns_rest = rest_provider is None
        self._owns_ws = ws_provider is None
        self._closed = False

    def get_timeframes(self) -> list[str]:
        """Get list of supported timeframes."""
        from .constants import INTERVAL_MAP

        return list(INTERVAL_MAP.keys())

    # --- REST delegations -------------------------------------------------
    @register_feature_handler(DataFeature.OHLCV, TransportKind.REST)
    async def get_candles(
        self,
        symbol: str,
        timeframe: str | Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> OHLCV:
        """Fetch OHLCV candles."""
        return await self._rest.get_candles(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    @register_feature_handler(DataFeature.SYMBOL_METADATA, TransportKind.REST)
    async def get_symbols(  # type: ignore[override]
        self, quote_asset: str | None = None, use_cache: bool = True
    ) -> list[Symbol]:
        """List trading symbols."""
        return await self._rest.get_symbols(quote_asset=quote_asset, use_cache=use_cache)

    @register_feature_handler(DataFeature.ORDER_BOOK, TransportKind.REST)
    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        """Fetch current order book."""
        return await self._rest.get_order_book(symbol=symbol, limit=limit)

    async def get_exchange_info(self) -> dict:
        """Get raw exchange info."""
        return await self._rest.get_exchange_info()

    @register_feature_handler(DataFeature.TRADES, TransportKind.REST)
    async def get_recent_trades(self, symbol: str, limit: int = 500) -> list[Trade]:
        """Fetch recent trades."""
        return await self._rest.get_recent_trades(symbol=symbol, limit=limit)

    @register_feature_handler(DataFeature.FUNDING_RATE, TransportKind.REST)
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

    @register_feature_handler(DataFeature.OPEN_INTEREST, TransportKind.REST)
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
        """Stream OHLCV candles."""
        async for bar in self._ws.stream_ohlcv(
            symbol,
            timeframe,
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
        """Stream OHLCV candles for multiple symbols."""
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

    async def stream_trades_multi(self, symbols: list[str]) -> AsyncIterator[Trade]:
        """Stream trades for multiple symbols."""
        async for trade in self._ws.stream_trades_multi(symbols):
            yield trade

    @register_feature_handler(DataFeature.ORDER_BOOK, TransportKind.WS)
    async def stream_order_book(
        self, symbol: str, update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        """Stream order book updates.

        Note: Coinbase Exchange API requires authentication for level2 WebSocket.
        This method will raise NotImplementedError. Use REST API (get_order_book) for order book data instead.
        """
        # Raise immediately - async generators need to raise before yielding
        raise NotImplementedError(
            "Coinbase Exchange API requires authentication for level2 WebSocket. "
            "Use REST API (get_order_book) for order book data, or implement authentication for WebSocket."
        )
        yield  # type: ignore[unreachable]  # Never reached, but needed for async generator type

    @register_feature_handler(DataFeature.OPEN_INTEREST, TransportKind.WS)
    async def stream_open_interest(self, symbols: list[str], period: str = "5m") -> AsyncIterator:
        """Stream open interest - NOT SUPPORTED by Coinbase Advanced Trade API."""
        raise NotImplementedError(
            "Coinbase Advanced Trade API does not support open interest "
            "(Futures feature, not available on Spot markets)"
        )

    @register_feature_handler(DataFeature.FUNDING_RATE, TransportKind.WS)
    async def stream_funding_rate(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator:
        """Stream funding rates - NOT SUPPORTED by Coinbase Advanced Trade API."""
        raise NotImplementedError(
            "Coinbase Advanced Trade API does not support funding rates "
            "(Futures feature, not available on Spot markets)"
        )

    @register_feature_handler(DataFeature.MARK_PRICE, TransportKind.WS)
    async def stream_mark_price(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator:
        """Stream mark prices - NOT SUPPORTED by Coinbase Advanced Trade API."""
        raise NotImplementedError(
            "Coinbase Advanced Trade API does not support mark prices "
            "(Futures feature, not available on Spot markets)"
        )

    @register_feature_handler(DataFeature.LIQUIDATIONS, TransportKind.WS)
    async def stream_liquidations(self) -> AsyncIterator:
        """Stream liquidations - NOT SUPPORTED by Coinbase Advanced Trade API."""
        raise NotImplementedError(
            "Coinbase Advanced Trade API does not support liquidations "
            "(Futures feature, not available on Spot markets)"
        )

    # --- Capability discovery ----------------------------------------------
    async def describe_capabilities(
        self,
        feature: DataFeature,
        transport: TransportKind,
        *,
        market_type: MarketType,
        instrument_type: InstrumentType,
    ) -> CapabilityStatus:
        """Describe capabilities for Coinbase.

        Returns static capability status from the registry.
        Runtime discovery can be added later to probe actual API availability.
        """
        return supports(
            feature=feature,
            transport=transport,
            exchange="coinbase",
            market_type=market_type,
            instrument_type=instrument_type,
        )

    # --- Lifecycle --------------------------------------------------------
    async def close(self) -> None:
        """Close provider connections."""
        if self._closed:
            return
        self._closed = True
        if self._owns_rest:
            await self._rest.close()
        if self._owns_ws:
            await self._ws.close()
