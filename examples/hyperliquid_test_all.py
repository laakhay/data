#!/usr/bin/env python3
"""Comprehensive test script for all Hyperliquid APIs.

This script runs both REST and WebSocket tests in sequence.

Usage:
    cd data && python examples/hyperliquid_test_all.py
    OR
    cd data && PYTHONPATH=. python examples/hyperliquid_test_all.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import test modules
from examples.hyperliquid_test_rest import main as test_rest
from examples.hyperliquid_test_websocket import main as test_websocket

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main():
    """Run all tests."""
    logger.info("=" * 80)
    logger.info("HYPERLIQUID API COMPREHENSIVE TEST SUITE")
    logger.info("=" * 80)
    
    # Test REST APIs
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 1: REST API TESTS")
    logger.info("=" * 80)
    try:
        await test_rest()
    except Exception as e:
        logger.error(f"REST tests failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Brief pause
    await asyncio.sleep(3)
    
    # Test WebSocket APIs
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2: WEBSOCKET API TESTS")
    logger.info("=" * 80)
    try:
        await test_websocket()
    except Exception as e:
        logger.error(f"WebSocket tests failed: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("\n" + "=" * 80)
    logger.info("ALL TESTS COMPLETED")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)

