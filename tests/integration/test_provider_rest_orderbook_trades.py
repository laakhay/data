"""Integration tests for REST order book and trades across all providers."""

import os

import pytest

from laakhay.data.core import MarketType
from laakhay.data.providers import (
    BinanceProvider,
    BybitProvider,
    CoinbaseProvider,
    KrakenProvider,
    OKXProvider,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LAAKHAY_NETWORK_TESTS") != "1",
    reason="Requires network access to test REST order book and trades",
)


class TestRESTOrderBookIntegration:
    """Test REST order book endpoints across exchanges."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider_class,exchange,symbol,market_type",
        [
            (BinanceProvider, "binance", "BTCUSDT", MarketType.SPOT),
            (BinanceProvider, "binance", "BTCUSDT", MarketType.FUTURES),
            (BybitProvider, "bybit", "BTCUSDT", MarketType.SPOT),
            (BybitProvider, "bybit", "BTCUSDT", MarketType.FUTURES),
            (OKXProvider, "okx", "BTC-USDT", MarketType.SPOT),
            (KrakenProvider, "kraken", "XBT/USD", MarketType.SPOT),
            (CoinbaseProvider, "coinbase", "BTC-USD", MarketType.SPOT),
        ],
    )
    async def test_fetch_order_book_basic(self, provider_class, exchange, symbol, market_type):
        """Test basic order book fetching for each exchange."""
        async with provider_class(market_type=market_type) as provider:
            try:
                order_book = await provider.get_order_book(symbol=symbol, limit=10)

                assert order_book is not None
                assert order_book.symbol == symbol or symbol.upper()
                assert len(order_book.bids) > 0
                assert len(order_book.asks) > 0

                # Verify bid/ask structure
                for price, quantity in order_book.bids:
                    assert price > 0
                    assert quantity > 0

                for price, quantity in order_book.asks:
                    assert price > 0
                    assert quantity > 0

                # Bids should be sorted descending, asks ascending
                if len(order_book.bids) > 1:
                    assert order_book.bids[0][0] >= order_book.bids[1][0]
                if len(order_book.asks) > 1:
                    assert order_book.asks[0][0] <= order_book.asks[1][0]

                # Best bid should be less than best ask
                if order_book.bids and order_book.asks:
                    assert order_book.bids[0][0] < order_book.asks[0][0]

            except NotImplementedError:
                pytest.skip(f"Order book not implemented for {exchange}")


class TestRESTTradesIntegration:
    """Test REST recent trades endpoints across exchanges."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider_class,exchange,symbol,market_type",
        [
            (BinanceProvider, "binance", "BTCUSDT", MarketType.SPOT),
            (BinanceProvider, "binance", "BTCUSDT", MarketType.FUTURES),
            (BybitProvider, "bybit", "BTCUSDT", MarketType.SPOT),
            (BybitProvider, "bybit", "BTCUSDT", MarketType.FUTURES),
            (OKXProvider, "okx", "BTC-USDT", MarketType.SPOT),
            (KrakenProvider, "kraken", "XBT/USD", MarketType.SPOT),
            (CoinbaseProvider, "coinbase", "BTC-USD", MarketType.SPOT),
        ],
    )
    async def test_fetch_recent_trades_basic(self, provider_class, exchange, symbol, market_type):
        """Test basic recent trades fetching for each exchange."""
        async with provider_class(market_type=market_type) as provider:
            try:
                trades = await provider.get_recent_trades(symbol=symbol, limit=10)

                assert trades is not None
                assert len(trades) > 0
                assert len(trades) <= 10

                # Verify trade structure
                for trade in trades:
                    assert trade.symbol == symbol or symbol.upper()
                    assert trade.price > 0
                    assert trade.quantity > 0
                    assert trade.timestamp is not None
                    assert trade.trade_id is not None or trade.timestamp is not None

            except NotImplementedError:
                pytest.skip(f"Recent trades not implemented for {exchange}")
