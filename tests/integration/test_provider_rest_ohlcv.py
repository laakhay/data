"""Integration tests for REST OHLCV across all providers."""

import os
from datetime import UTC, datetime, timedelta

import pytest

from laakhay.data.connectors.okx.provider import OKXProvider
from laakhay.data.core import MarketType, Timeframe
from laakhay.data.providers import (
    BinanceProvider,
    BybitProvider,
    CoinbaseProvider,
    HyperliquidProvider,
    KrakenProvider,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LAAKHAY_NETWORK_TESTS") != "1",
    reason="Requires network access to test REST OHLCV",
)


class TestRESTOHLCVIntegration:
    """Test REST OHLCV endpoints across all exchanges."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider_class,exchange,symbol,market_type",
        [
            (BinanceProvider, "binance", "BTCUSDT", MarketType.SPOT),
            (BinanceProvider, "binance", "BTCUSDT", MarketType.FUTURES),
            (BybitProvider, "bybit", "BTCUSDT", MarketType.SPOT),
            (BybitProvider, "bybit", "BTCUSDT", MarketType.FUTURES),
            (OKXProvider, "okx", "BTC-USDT", MarketType.SPOT),
            (OKXProvider, "okx", "BTC-USDT", MarketType.FUTURES),
            (KrakenProvider, "kraken", "XBT/USD", MarketType.SPOT),
            (KrakenProvider, "kraken", "PI_XBTUSD", MarketType.FUTURES),
            (CoinbaseProvider, "coinbase", "BTC-USD", MarketType.SPOT),
            (HyperliquidProvider, "hyperliquid", "BTC", MarketType.FUTURES),
        ],
    )
    async def test_fetch_ohlcv_basic(self, provider_class, exchange, symbol, market_type):
        """Test basic OHLCV fetching for each exchange."""
        async with provider_class(market_type=market_type) as provider:
            ohlcv = await provider.fetch_ohlcv(
                symbol=symbol,
                timeframe=Timeframe.M1,
                limit=10,
            )

            assert ohlcv is not None
            assert len(ohlcv.bars) > 0
            assert len(ohlcv.bars) <= 10
            assert ohlcv.meta.symbol == symbol.upper() or symbol
            assert ohlcv.meta.timeframe == Timeframe.M1.value

            # Verify bar structure
            for bar in ohlcv.bars:
                assert bar.open > 0
                assert bar.high >= bar.low
                assert bar.high >= bar.open
                assert bar.high >= bar.close
                assert bar.low <= bar.open
                assert bar.low <= bar.close
                assert bar.volume >= 0
                assert bar.timestamp.tzinfo == UTC

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider_class,exchange,symbol,market_type",
        [
            (BinanceProvider, "binance", "BTCUSDT", MarketType.SPOT),
            (BybitProvider, "bybit", "BTCUSDT", MarketType.SPOT),
            (OKXProvider, "okx", "BTC-USDT", MarketType.SPOT),
        ],
    )
    async def test_fetch_ohlcv_with_time_range(self, provider_class, exchange, symbol, market_type):
        """Test OHLCV fetching with time range."""
        async with provider_class(market_type=market_type) as provider:
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(hours=1)

            ohlcv = await provider.fetch_ohlcv(
                symbol=symbol,
                timeframe=Timeframe.M5,
                start_time=start_time,
                end_time=end_time,
                limit=100,
            )

            assert ohlcv is not None
            assert len(ohlcv.bars) > 0

            # Verify timestamps are within range
            for bar in ohlcv.bars:
                assert start_time <= bar.timestamp <= end_time

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider_class,exchange,symbol,market_type,timeframe",
        [
            (BinanceProvider, "binance", "BTCUSDT", MarketType.SPOT, Timeframe.M1),
            (BinanceProvider, "binance", "BTCUSDT", MarketType.SPOT, Timeframe.M5),
            (BinanceProvider, "binance", "BTCUSDT", MarketType.SPOT, Timeframe.H1),
            (BinanceProvider, "binance", "BTCUSDT", MarketType.SPOT, Timeframe.D1),
            (BybitProvider, "bybit", "BTCUSDT", MarketType.SPOT, Timeframe.M1),
            (BybitProvider, "bybit", "BTCUSDT", MarketType.SPOT, Timeframe.M5),
        ],
    )
    async def test_fetch_ohlcv_different_timeframes(
        self, provider_class, exchange, symbol, market_type, timeframe
    ):
        """Test OHLCV fetching with different timeframes."""
        async with provider_class(market_type=market_type) as provider:
            ohlcv = await provider.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=5,
            )

            assert ohlcv is not None
            assert len(ohlcv.bars) > 0
            assert ohlcv.meta.timeframe == timeframe.value

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider_class,exchange,symbol,market_type",
        [
            (BinanceProvider, "binance", "INVALID", MarketType.SPOT),
            (BybitProvider, "bybit", "INVALID", MarketType.SPOT),
        ],
    )
    async def test_fetch_ohlcv_invalid_symbol(self, provider_class, exchange, symbol, market_type):
        """Test OHLCV fetching with invalid symbol raises error."""
        async with provider_class(market_type=market_type) as provider:
            from aiohttp import ClientResponseError

            from laakhay.data.core.exceptions import ProviderError

            with pytest.raises((ProviderError, ValueError, ClientResponseError)):
                await provider.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=Timeframe.M1,
                    limit=10,
                )
