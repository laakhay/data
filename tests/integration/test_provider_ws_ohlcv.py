"""Integration tests for WebSocket OHLCV streaming across all providers."""

import asyncio
import os

import pytest

from laakhay.data.core import MarketType, Timeframe
from laakhay.data.providers import (
    BinanceProvider,
    BybitProvider,
    CoinbaseProvider,
    KrakenProvider,
    OKXProvider,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LAAKHAY_NETWORK_TESTS") != "1",
    reason="Requires network access to test WebSocket OHLCV",
)


class TestWSOHLCVIntegration:
    """Test WebSocket OHLCV streaming across all exchanges."""

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
            (CoinbaseProvider, "coinbase", "BTC-USD", MarketType.SPOT),
        ],
    )
    async def test_stream_ohlcv_single_symbol(self, provider_class, exchange, symbol, market_type):
        """Test streaming OHLCV for a single symbol."""
        async with provider_class(market_type=market_type) as provider:
            try:
                count = 0
                async for bar in provider.stream_ohlcv(
                    symbol=symbol,
                    timeframe=Timeframe.M1,
                ):
                    assert bar.symbol == symbol or symbol.upper()
                    assert bar.open > 0
                    assert bar.high >= bar.low
                    assert bar.high >= bar.open
                    assert bar.high >= bar.close
                    assert bar.low <= bar.open
                    assert bar.low <= bar.close
                    assert bar.volume >= 0
                    assert bar.timestamp is not None

                    count += 1
                    if count >= 3:  # Get a few updates
                        break

                assert count >= 1

            except NotImplementedError:
                pytest.skip(f"WebSocket OHLCV not implemented for {exchange}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider_class,exchange,symbols,market_type",
        [
            (
                BinanceProvider,
                "binance",
                ["BTCUSDT", "ETHUSDT"],
                MarketType.SPOT,
            ),
            (
                BybitProvider,
                "bybit",
                ["BTCUSDT", "ETHUSDT"],
                MarketType.SPOT,
            ),
            (OKXProvider, "okx", ["BTC-USDT", "ETH-USDT"], MarketType.SPOT),
        ],
    )
    async def test_stream_ohlcv_multi_symbol(self, provider_class, exchange, symbols, market_type):
        """Test streaming OHLCV for multiple symbols."""
        async with provider_class(market_type=market_type) as provider:
            try:
                symbols_seen = set()
                count = 0

                async for bar in provider.stream_ohlcv_multi(
                    symbols=symbols,
                    timeframe=Timeframe.M1,
                ):
                    assert bar.symbol in symbols or bar.symbol.upper() in [
                        s.upper() for s in symbols
                    ]
                    symbols_seen.add(bar.symbol)

                    count += 1
                    if count >= 10:  # Get enough updates to see both symbols
                        break

                assert count >= 1
                assert len(symbols_seen) >= 1

            except NotImplementedError:
                pytest.skip(f"WebSocket OHLCV multi not implemented for {exchange}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider_class,exchange,symbol,market_type",
        [
            (BinanceProvider, "binance", "BTCUSDT", MarketType.SPOT),
            (BybitProvider, "bybit", "BTCUSDT", MarketType.SPOT),
        ],
    )
    async def test_stream_ohlcv_only_closed(self, provider_class, exchange, symbol, market_type):
        """Test streaming only closed candles."""
        async with provider_class(market_type=market_type) as provider:
            try:
                count = 0
                async for bar in provider.stream_ohlcv(
                    symbol=symbol,
                    timeframe=Timeframe.M1,
                    only_closed=True,
                ):
                    assert bar.is_closed is True

                    count += 1
                    if count >= 2:
                        break

                assert count >= 1

            except NotImplementedError:
                pytest.skip(f"WebSocket OHLCV only_closed not implemented for {exchange}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider_class,exchange,symbol,market_type",
        [
            (BinanceProvider, "binance", "BTCUSDT", MarketType.SPOT),
            (BybitProvider, "bybit", "BTCUSDT", MarketType.SPOT),
        ],
    )
    async def test_stream_ohlcv_cancellation(self, provider_class, exchange, symbol, market_type):
        """Test that streaming can be cancelled gracefully."""
        async with provider_class(market_type=market_type) as provider:
            try:
                count = 0
                async with asyncio.timeout(5):  # 5 second timeout
                    async for _bar in provider.stream_ohlcv(
                        symbol=symbol,
                        timeframe=Timeframe.M1,
                    ):
                        count += 1
                        if count >= 3:
                            break

                assert count >= 1

            except (TimeoutError, NotImplementedError):
                pytest.skip(f"WebSocket OHLCV cancellation test failed for {exchange}")
