#!/usr/bin/env python3
"""Test script for Hyperliquid WebSocket API streams.

This script tests all WebSocket streams supported by HyperliquidWSProvider:
- OHLCV/Candles
- Trades
- Order Book
- Open Interest
- Funding Rate
- Mark Price
- Liquidations (if available)

Usage:
    cd data && python examples/hyperliquid_test_websocket.py
    OR
    cd data && PYTHONPATH=. python examples/hyperliquid_test_websocket.py
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from laakhay.data.core import MarketType, Timeframe
from laakhay.data.providers import HyperliquidWSProvider

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_flag = False


def signal_handler(sig, frame):
    """Handle shutdown signal."""
    global shutdown_flag
    logger.info("Shutdown signal received, stopping streams...")
    shutdown_flag = True


async def test_ohlcv_stream(provider: HyperliquidWSProvider):
    """Test OHLCV stream."""
    logger.info("=" * 60)
    logger.info("Testing OHLCV Stream")
    logger.info("=" * 60)

    try:
        count = 0
        async for bar in provider.stream_ohlcv("BTC", Timeframe.M15):
            if shutdown_flag:
                break
            count += 1
            logger.info(
                f"✅ Received OHLCV bar #{count}: {bar.symbol} - {bar.timestamp} - O:{bar.open} H:{bar.high} L:{bar.low} C:{bar.close} V:{bar.volume}"
            )
            if count >= 3:
                logger.info("✅ OHLCV stream working correctly")
                break
        return True
    except Exception as e:
        logger.error(f"❌ Failed to stream OHLCV: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_trades_stream(provider: HyperliquidWSProvider):
    """Test Trades stream."""
    logger.info("=" * 60)
    logger.info("Testing Trades Stream")
    logger.info("=" * 60)

    try:
        count = 0
        async for trade in provider.stream_trades("BTC"):
            if shutdown_flag:
                break
            count += 1
            logger.info(
                f"✅ Received trade #{count}: {trade.symbol} - {trade.timestamp} - {trade.price} @ {trade.quantity} ({'BUY' if not trade.is_buyer_maker else 'SELL'})"
            )
            if count >= 5:
                logger.info("✅ Trades stream working correctly")
                break
        return True
    except Exception as e:
        logger.error(f"❌ Failed to stream trades: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_order_book_stream(provider: HyperliquidWSProvider):
    """Test Order Book stream."""
    logger.info("=" * 60)
    logger.info("Testing Order Book Stream")
    logger.info("=" * 60)

    try:
        count = 0
        async for ob in provider.stream_order_book("BTC"):
            if shutdown_flag:
                break
            count += 1
            logger.info(
                f"✅ Received order book update #{count}: {ob.symbol} - {ob.timestamp} - {len(ob.bids)} bids, {len(ob.asks)} asks"
            )
            if ob.best_bid_price and ob.best_ask_price:
                logger.info(
                    f"   Best bid: {ob.best_bid_price}, Best ask: {ob.best_ask_price}, Spread: {ob.spread}"
                )
            if count >= 3:
                logger.info("✅ Order book stream working correctly")
                break
        return True
    except Exception as e:
        logger.error(f"❌ Failed to stream order book: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_open_interest_stream(provider: HyperliquidWSProvider):
    """Test Open Interest stream."""
    logger.info("=" * 60)
    logger.info("Testing Open Interest Stream")
    logger.info("=" * 60)

    try:
        count = 0
        async for oi in provider.stream_open_interest("BTC"):
            if shutdown_flag:
                break
            count += 1
            logger.info(
                f"✅ Received open interest update #{count}: {oi.symbol} - {oi.timestamp} - OI: {oi.open_interest}"
            )
            if count >= 3:
                logger.info("✅ Open interest stream working correctly")
                break
        return True
    except Exception as e:
        logger.error(f"❌ Failed to stream open interest: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_funding_rate_stream(provider: HyperliquidWSProvider):
    """Test Funding Rate stream."""
    logger.info("=" * 60)
    logger.info("Testing Funding Rate Stream")
    logger.info("=" * 60)

    try:
        count = 0
        async for fr in provider.stream_funding_rate("BTC"):
            if shutdown_flag:
                break
            count += 1
            logger.info(
                f"✅ Received funding rate update #{count}: {fr.symbol} - {fr.timestamp} - Rate: {fr.funding_rate}"
            )
            if count >= 3:
                logger.info("✅ Funding rate stream working correctly")
                break
        return True
    except Exception as e:
        logger.error(f"❌ Failed to stream funding rate: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_mark_price_stream(provider: HyperliquidWSProvider):
    """Test Mark Price stream."""
    logger.info("=" * 60)
    logger.info("Testing Mark Price Stream")
    logger.info("=" * 60)

    try:
        count = 0
        async for mp in provider.stream_mark_price("BTC"):
            if shutdown_flag:
                break
            count += 1
            logger.info(
                f"✅ Received mark price update #{count}: {mp.symbol} - {mp.timestamp} - Mark Price: {mp.mark_price}"
            )
            if count >= 3:
                logger.info("✅ Mark price stream working correctly")
                break
        return True
    except Exception as e:
        logger.error(f"❌ Failed to stream mark price: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_liquidations_stream(provider: HyperliquidWSProvider):
    """Test Liquidations stream."""
    logger.info("=" * 60)
    logger.info("Testing Liquidations Stream")
    logger.info("=" * 60)

    try:
        count = 0
        async for liq in provider.stream_liquidations(["BTC"]):
            if shutdown_flag:
                break
            count += 1
            logger.info(
                f"✅ Received liquidation #{count}: {liq.symbol} - {liq.timestamp} - {liq.side} - {liq.quantity} @ {liq.price}"
            )
            if count >= 3:
                logger.info("✅ Liquidations stream working correctly")
                break

        # If no liquidations received, that's okay (they're rare)
        if count == 0:
            logger.warning(
                "⚠️  No liquidations received (this is normal - liquidations are rare events)"
            )
        return True
    except Exception as e:
        logger.warning(f"⚠️  Liquidations stream not available: {e}")
        return True  # Not an error, may require user address


async def run_single_test(provider: HyperliquidWSProvider, test_name: str, test_func):
    """Run a single test with timeout."""
    try:
        logger.info(f"\n🧪 Running {test_name}...")
        result = await asyncio.wait_for(test_func(provider), timeout=30.0)
        return result
    except TimeoutError:
        logger.warning(f"⚠️  {test_name} timed out after 30 seconds")
        return False
    except Exception as e:
        logger.error(f"❌ {test_name} failed: {e}")
        return False


async def main():
    """Run all WebSocket stream tests."""
    global shutdown_flag

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting Hyperliquid WebSocket API Tests")
    logger.info("=" * 60)
    logger.info("Press Ctrl+C to stop any test early")
    logger.info("=" * 60)

    # Test Futures market
    logger.info("\n🔵 Testing FUTURES Market")
    futures_provider = HyperliquidWSProvider(market_type=MarketType.FUTURES)

    results = []

    # Run tests sequentially to avoid connection issues
    results.append(await run_single_test(futures_provider, "OHLCV Stream", test_ohlcv_stream))
    await asyncio.sleep(2)  # Brief pause between tests

    results.append(await run_single_test(futures_provider, "Trades Stream", test_trades_stream))
    await asyncio.sleep(2)

    results.append(
        await run_single_test(futures_provider, "Order Book Stream", test_order_book_stream)
    )
    await asyncio.sleep(2)

    results.append(
        await run_single_test(futures_provider, "Open Interest Stream", test_open_interest_stream)
    )
    await asyncio.sleep(2)

    results.append(
        await run_single_test(futures_provider, "Funding Rate Stream", test_funding_rate_stream)
    )
    await asyncio.sleep(2)

    results.append(
        await run_single_test(futures_provider, "Mark Price Stream", test_mark_price_stream)
    )
    await asyncio.sleep(2)

    results.append(
        await run_single_test(futures_provider, "Liquidations Stream", test_liquidations_stream)
    )

    # Test Spot market (limited endpoints)
    logger.info("\n🟢 Testing SPOT Market")
    spot_provider = HyperliquidWSProvider(market_type=MarketType.SPOT)

    results.append(await run_single_test(spot_provider, "OHLCV Stream (Spot)", test_ohlcv_stream))
    await asyncio.sleep(2)

    results.append(await run_single_test(spot_provider, "Trades Stream (Spot)", test_trades_stream))
    await asyncio.sleep(2)

    results.append(
        await run_single_test(spot_provider, "Order Book Stream (Spot)", test_order_book_stream)
    )

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
        logger.warning(f"⚠️  {total - passed} test(s) failed or timed out")

    # Cleanup
    try:
        await futures_provider.close()
        await spot_provider.close()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        shutdown_flag = True
