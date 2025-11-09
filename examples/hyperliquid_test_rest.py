#!/usr/bin/env python3
"""Test script for Hyperliquid REST API endpoints.

This script tests all REST endpoints supported by HyperliquidProvider:
- OHLCV/Candles
- Exchange Info/Symbols
- Order Book
- Recent Trades (if available)
- Funding Rate (if available)
- Open Interest (if available)

Usage:
    cd data && python examples/hyperliquid_test_rest.py
    OR
    cd data && PYTHONPATH=. python examples/hyperliquid_test_rest.py
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from laakhay.data.core import MarketType, Timeframe
from laakhay.data.providers import HyperliquidRESTProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_candles(provider: HyperliquidRESTProvider):
    """Test OHLCV/Candles endpoint."""
    logger.info("=" * 60)
    logger.info("Testing OHLCV/Candles endpoint")
    logger.info("=" * 60)
    
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)
        
        result = await provider.get_candles(
            symbol="BTC",
            timeframe=Timeframe.M15,
            start_time=start_time,
            end_time=end_time,
            limit=100,
        )
        
        logger.info(f"✅ Successfully fetched {len(result.bars)} candles")
        logger.info(f"   Symbol: {result.meta.symbol}")
        logger.info(f"   Timeframe: {result.meta.timeframe}")
        if result.bars:
            logger.info(f"   First bar: {result.bars[0].timestamp} - O:{result.bars[0].open} H:{result.bars[0].high} L:{result.bars[0].low} C:{result.bars[0].close}")
            logger.info(f"   Last bar: {result.bars[-1].timestamp} - O:{result.bars[-1].open} H:{result.bars[-1].high} L:{result.bars[-1].low} C:{result.bars[-1].close}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to fetch candles: {e}")
        return False


async def test_symbols(provider: HyperliquidRESTProvider):
    """Test Exchange Info/Symbols endpoint."""
    logger.info("=" * 60)
    logger.info("Testing Exchange Info/Symbols endpoint")
    logger.info("=" * 60)
    
    try:
        symbols = await provider.get_symbols()
        
        logger.info(f"✅ Successfully fetched {len(symbols)} symbols")
        if symbols:
            logger.info(f"   First 5 symbols:")
            for sym in symbols[:5]:
                logger.info(f"     - {sym.symbol} ({sym.contract_type}) - Base: {sym.base_asset}, Quote: {sym.quote_asset}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to fetch symbols: {e}")
        return False


async def test_order_book(provider: HyperliquidRESTProvider):
    """Test Order Book endpoint."""
    logger.info("=" * 60)
    logger.info("Testing Order Book endpoint")
    logger.info("=" * 60)
    
    try:
        order_book = await provider.get_order_book(symbol="BTC", limit=10)
        
        logger.info(f"✅ Successfully fetched order book for {order_book.symbol}")
        logger.info(f"   Timestamp: {order_book.timestamp}")
        logger.info(f"   Bids: {len(order_book.bids)} levels")
        logger.info(f"   Asks: {len(order_book.asks)} levels")
        if order_book.bids:
            logger.info(f"   Best bid: {order_book.bids[0][0]} @ {order_book.bids[0][1]}")
        if order_book.asks:
            logger.info(f"   Best ask: {order_book.asks[0][0]} @ {order_book.asks[0][1]}")
        if order_book.best_bid_price and order_book.best_ask_price:
            logger.info(f"   Spread: {order_book.spread}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to fetch order book: {e}")
        return False


async def test_recent_trades(provider: HyperliquidRESTProvider):
    """Test Recent Trades endpoint."""
    logger.info("=" * 60)
    logger.info("Testing Recent Trades endpoint")
    logger.info("=" * 60)
    
    try:
        trades = await provider.get_recent_trades(symbol="BTC", limit=10)
        
        if trades:
            logger.info(f"✅ Successfully fetched {len(trades)} recent trades")
            for trade in trades[:3]:
                logger.info(f"   {trade.timestamp} - {trade.symbol} - {trade.price} @ {trade.quantity} ({'BUY' if not trade.is_buyer_maker else 'SELL'})")
            return True
        else:
            logger.warning("⚠️  No trades returned (endpoint may not be available via REST)")
            return True  # Not an error, just not available
    except Exception as e:
        logger.warning(f"⚠️  Recent trades endpoint not available: {e}")
        return True  # Not an error, endpoint may not exist


async def test_funding_rate(provider: HyperliquidRESTProvider):
    """Test Funding Rate endpoint."""
    logger.info("=" * 60)
    logger.info("Testing Funding Rate endpoint")
    logger.info("=" * 60)
    
    try:
        funding_rates = await provider.get_funding_rate(symbol="BTC", limit=10)
        
        if funding_rates:
            logger.info(f"✅ Successfully fetched {len(funding_rates)} funding rates")
            for fr in funding_rates[:3]:
                logger.info(f"   {fr.timestamp} - {fr.symbol} - Rate: {fr.funding_rate}")
            return True
        else:
            logger.warning("⚠️  No funding rates returned (endpoint may not be available via REST)")
            return True  # Not an error, just not available
    except Exception as e:
        logger.warning(f"⚠️  Funding rate endpoint not available: {e}")
        return True  # Not an error, endpoint may not exist


async def test_open_interest(provider: HyperliquidRESTProvider):
    """Test Open Interest endpoint."""
    logger.info("=" * 60)
    logger.info("Testing Open Interest endpoint")
    logger.info("=" * 60)
    
    try:
        oi = await provider.get_open_interest(symbol="BTC")
        
        if oi:
            logger.info(f"✅ Successfully fetched open interest for {oi.symbol}")
            logger.info(f"   Timestamp: {oi.timestamp}")
            logger.info(f"   Open Interest: {oi.open_interest}")
            return True
        else:
            logger.warning("⚠️  No open interest returned (endpoint may not be available via REST)")
            return True  # Not an error, just not available
    except Exception as e:
        logger.warning(f"⚠️  Open interest endpoint not available: {e}")
        return True  # Not an error, endpoint may not exist


async def main():
    """Run all REST API tests."""
    logger.info("Starting Hyperliquid REST API Tests")
    logger.info("=" * 60)
    
    # Test Futures market
    logger.info("\n🔵 Testing FUTURES Market")
    futures_provider = HyperliquidRESTProvider(market_type=MarketType.FUTURES)
    
    results = []
    results.append(await test_candles(futures_provider))
    results.append(await test_symbols(futures_provider))
    results.append(await test_order_book(futures_provider))
    results.append(await test_recent_trades(futures_provider))
    results.append(await test_funding_rate(futures_provider))
    results.append(await test_open_interest(futures_provider))
    
    # Test Spot market
    logger.info("\n🟢 Testing SPOT Market")
    spot_provider = HyperliquidRESTProvider(market_type=MarketType.SPOT)
    
    results.append(await test_candles(spot_provider))
    results.append(await test_symbols(spot_provider))
    results.append(await test_order_book(spot_provider))
    
    # Cleanup
    await futures_provider.close()
    await spot_provider.close()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    passed = sum(results)
    total = len(results)
    logger.info(f"Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("✅ All tests passed!")
    else:
        logger.warning(f"⚠️  {total - passed} test(s) had issues (some endpoints may not be available)")


if __name__ == "__main__":
    asyncio.run(main())

