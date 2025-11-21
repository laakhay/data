"""Integration tests for Binance liquidation functionality."""

import asyncio
import os
from datetime import UTC, datetime

import pytest

from laakhay.data.core import MarketType
from laakhay.data.models.liquidation import Liquidation
from laakhay.data.connectors.binance import BinanceProvider

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LAAKHAY_NETWORK_TESTS") != "1",
    reason="Requires network access to Binance API",
)


class TestBinanceLiquidationIntegration:
    """Integration tests for Binance liquidation WebSocket streaming."""

    @pytest.mark.asyncio
    async def test_stream_liquidations_connection(self):
        """Test that liquidation WebSocket connection works."""
        async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
            # Test connection by trying to get one liquidation
            count = 0
            async for liquidation in provider.stream_liquidations():
                assert isinstance(liquidation, Liquidation)
                assert liquidation.symbol
                assert liquidation.side in ["BUY", "SELL"]
                assert liquidation.price > 0
                assert liquidation.original_quantity > 0
                assert liquidation.is_fresh(max_age_seconds=3600)  # Should be fresh within 1 hour

                count += 1
                if count >= 1:  # Just test one liquidation
                    break

    @pytest.mark.asyncio
    async def test_stream_liquidations_data_structure(self):
        """Test that liquidation data has expected structure."""
        async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
            count = 0
            async for liquidation in provider.stream_liquidations():
                # Required fields
                assert hasattr(liquidation, "symbol")
                assert hasattr(liquidation, "timestamp")
                assert hasattr(liquidation, "side")
                assert hasattr(liquidation, "order_type")
                assert hasattr(liquidation, "price")
                assert hasattr(liquidation, "original_quantity")
                assert hasattr(liquidation, "order_status")

                # Test properties
                assert liquidation.timestamp_ms > 0
                assert liquidation.value_usdt >= 0
                assert liquidation.is_long_liquidation or liquidation.is_short_liquidation

                # Test to_dict conversion
                liquidation_dict = liquidation.to_dict()
                assert isinstance(liquidation_dict, dict)
                assert "symbol" in liquidation_dict
                assert "timestamp" in liquidation_dict
                assert "side" in liquidation_dict

                count += 1
                if count >= 1:  # Just test one liquidation
                    break

    @pytest.mark.asyncio
    async def test_stream_liquidations_spot_market_error(self):
        """Test that liquidations are not available for spot market."""
        async with BinanceProvider(market_type=MarketType.SPOT) as provider:
            with pytest.raises(
                ValueError, match="Liquidation streaming is only available for Futures market"
            ):
                # This should raise an error immediately
                async for _liquidation in provider.stream_liquidations():
                    break

    @pytest.mark.asyncio
    async def test_stream_liquidations_timeout(self):
        """Test that streaming can be cancelled gracefully."""
        async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
            try:
                # Set a timeout to test cancellation
                async with asyncio.timeout_at(asyncio.get_event_loop().time() + 5):
                    count = 0
                    async for _liquidation in provider.stream_liquidations():
                        count += 1
                        if count >= 3:  # Get a few liquidations
                            break

            except TimeoutError:
                # Timeout is expected, test passes
                pass

    @pytest.mark.asyncio
    async def test_stream_liquidations_large_detection(self):
        """Test detection of large liquidations."""
        async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
            count = 0
            async for liquidation in provider.stream_liquidations():
                # Test large liquidation detection
                if liquidation.is_large:
                    assert liquidation.value_usdt > 100000

                # Test liquidation type detection
                if liquidation.side == "SELL":
                    assert liquidation.is_long_liquidation is True
                    assert liquidation.is_short_liquidation is False
                elif liquidation.side == "BUY":
                    assert liquidation.is_long_liquidation is False
                    assert liquidation.is_short_liquidation is True

                count += 1
                if count >= 5:  # Test a few liquidations
                    break

    @pytest.mark.asyncio
    async def test_stream_liquidations_timestamp_accuracy(self):
        """Test that liquidation timestamps are reasonable."""
        async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
            count = 0
            async for liquidation in provider.stream_liquidations():
                now = datetime.now(UTC)

                # Timestamps should not be in the future
                assert liquidation.timestamp <= now

                # Should be very fresh (within last few minutes for streaming)
                age_seconds = liquidation.get_age_seconds()
                assert age_seconds >= 0
                assert age_seconds < 300  # Less than 5 minutes for streaming data

                # Test freshness
                assert liquidation.is_fresh(max_age_seconds=300) is True

                count += 1
                if count >= 3:  # Test a few liquidations
                    break
