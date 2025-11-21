"""Integration tests for REST symbol metadata across all providers."""

import os

import pytest

from laakhay.data.connectors.okx.provider import OKXProvider
from laakhay.data.core import MarketType
from laakhay.data.providers import (
    BinanceProvider,
    BybitProvider,
    CoinbaseProvider,
    HyperliquidProvider,
    KrakenProvider,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LAAKHAY_NETWORK_TESTS") != "1",
    reason="Requires network access to test REST symbols",
)


class TestRESTSymbolsIntegration:
    """Test REST symbol metadata endpoints across all exchanges."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider_class,exchange,market_type",
        [
            (BinanceProvider, "binance", MarketType.SPOT),
            (BinanceProvider, "binance", MarketType.FUTURES),
            (BybitProvider, "bybit", MarketType.SPOT),
            (BybitProvider, "bybit", MarketType.FUTURES),
            (OKXProvider, "okx", MarketType.SPOT),
            (OKXProvider, "okx", MarketType.FUTURES),
            (KrakenProvider, "kraken", MarketType.SPOT),
            (KrakenProvider, "kraken", MarketType.FUTURES),
            (CoinbaseProvider, "coinbase", MarketType.SPOT),
            (HyperliquidProvider, "hyperliquid", MarketType.FUTURES),
        ],
    )
    async def test_fetch_symbols_all(self, provider_class, exchange, market_type):
        """Test fetching all symbols for each exchange."""
        async with provider_class(market_type=market_type) as provider:
            symbols = await provider.get_symbols()

            assert symbols is not None
            assert len(symbols) > 0

            # Verify symbol structure
            for symbol in symbols[:10]:  # Check first 10
                assert symbol.symbol is not None
                assert len(symbol.symbol) > 0
                assert symbol.base_asset is not None
                assert symbol.quote_asset is not None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider_class,exchange,market_type,quote_asset",
        [
            (BinanceProvider, "binance", MarketType.SPOT, "USDT"),
            (BinanceProvider, "binance", MarketType.FUTURES, "USDT"),
            (BybitProvider, "bybit", MarketType.SPOT, "USDT"),
            (BybitProvider, "bybit", MarketType.FUTURES, "USDT"),
            (OKXProvider, "okx", MarketType.SPOT, "USDT"),
            (KrakenProvider, "kraken", MarketType.SPOT, "USD"),
        ],
    )
    async def test_fetch_symbols_filtered_by_quote(
        self, provider_class, exchange, market_type, quote_asset
    ):
        """Test fetching symbols filtered by quote asset."""
        async with provider_class(market_type=market_type) as provider:
            symbols = await provider.get_symbols(quote_asset=quote_asset)

            assert symbols is not None
            assert len(symbols) > 0

            # Verify all symbols have the correct quote asset
            for symbol in symbols:
                assert symbol.quote_asset == quote_asset

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider_class,exchange,market_type,expected_symbol",
        [
            (BinanceProvider, "binance", MarketType.SPOT, "BTCUSDT"),
            (BinanceProvider, "binance", MarketType.FUTURES, "BTCUSDT"),
            (BybitProvider, "bybit", MarketType.SPOT, "BTCUSDT"),
            (BybitProvider, "bybit", MarketType.FUTURES, "BTCUSDT"),
            (OKXProvider, "okx", MarketType.SPOT, "BTC-USDT"),
            (KrakenProvider, "kraken", MarketType.SPOT, "XBT/USD"),
            (CoinbaseProvider, "coinbase", MarketType.SPOT, "BTC-USD"),
        ],
    )
    async def test_fetch_symbols_contains_major_pairs(
        self, provider_class, exchange, market_type, expected_symbol
    ):
        """Test that major trading pairs are present in symbol list."""
        async with provider_class(market_type=market_type) as provider:
            symbols = await provider.get_symbols()

            symbol_names = [s.symbol for s in symbols]
            assert expected_symbol in symbol_names or expected_symbol.upper() in symbol_names
