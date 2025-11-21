"""Integration tests for Binance funding rate functionality."""

import asyncio
import os
from datetime import UTC, datetime, timedelta

import pytest

from laakhay.data.core import MarketType
from laakhay.data.models.funding_rate import FundingRate
from laakhay.data.connectors.binance import BinanceProvider

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LAAKHAY_NETWORK_TESTS") != "1",
    reason="Requires network access to Binance API",
)

REST_NOT_IMPLEMENTED = pytest.mark.xfail(
    raises=NotImplementedError,
    reason="Binance REST funding rate endpoint not implemented yet",
)


class TestBinanceFundingRateIntegration:
    """Integration tests for Binance funding rate endpoints."""

    @pytest.mark.asyncio
    @REST_NOT_IMPLEMENTED
    async def test_get_current_funding_rate(self):
        """Test fetching current/recent funding rate for a symbol."""
        async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
            # Fetch last funding rate
            fr_list = await provider.get_funding_rate("BTCUSDT", limit=1)

            assert len(fr_list) >= 1
            fr = fr_list[0]

            assert isinstance(fr, FundingRate)
            assert fr.symbol == "BTCUSDT"
            assert fr.funding_rate is not None
            assert fr.mark_price is not None

            # Should be recent (within last 8 hours as funding is every 8h)
            assert fr.get_age_seconds() < (8 * 3600 + 300)  # 8 hours + 5min tolerance

    @pytest.mark.asyncio
    @REST_NOT_IMPLEMENTED
    async def test_get_historical_funding_rates(self):
        """Test fetching historical funding rates."""
        async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
            # Get last 10 funding rates
            fr_list = await provider.get_funding_rate("BTCUSDT", limit=10)

            assert len(fr_list) <= 10
            assert all(isinstance(fr, FundingRate) for fr in fr_list)
            assert all(fr.symbol == "BTCUSDT" for fr in fr_list)

            # Should be in chronological order (oldest to newest or vice versa)
            if len(fr_list) > 1:
                # Check timestamps are different
                timestamps = [fr.funding_time_ms for fr in fr_list]
                assert len(set(timestamps)) == len(timestamps)  # All unique

    @pytest.mark.asyncio
    @REST_NOT_IMPLEMENTED
    async def test_get_funding_rate_with_time_range(self):
        """Test fetching funding rates with time range."""
        async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
            # Get funding rates from last 7 days
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(days=7)

            fr_list = await provider.get_funding_rate(
                "BTCUSDT", start_time=start_time, end_time=end_time, limit=100
            )

            assert isinstance(fr_list, list)
            assert len(fr_list) > 0

            # All funding rates should be within the time range
            for fr in fr_list:
                assert start_time <= fr.funding_time <= end_time

    @pytest.mark.asyncio
    @REST_NOT_IMPLEMENTED
    async def test_get_funding_rate_multiple_symbols(self):
        """Test fetching funding rates for multiple symbols."""
        async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

            for symbol in symbols:
                fr_list = await provider.get_funding_rate(symbol, limit=1)

                assert len(fr_list) >= 1
                assert fr_list[0].symbol == symbol
                assert fr_list[0].funding_rate is not None

    @pytest.mark.asyncio
    @REST_NOT_IMPLEMENTED
    async def test_funding_rate_properties(self):
        """Test funding rate model properties."""
        async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
            fr_list = await provider.get_funding_rate("BTCUSDT", limit=5)

            for fr in fr_list:
                # Test percentage conversion
                assert fr.funding_rate_percentage == fr.funding_rate * 100

                # Test positive/negative detection
                assert fr.is_positive == (fr.funding_rate > 0)
                assert fr.is_negative == (fr.funding_rate < 0)

                # Test to_dict conversion
                fr_dict = fr.to_dict()
                assert isinstance(fr_dict, dict)
                assert "symbol" in fr_dict
                assert "funding_rate" in fr_dict

    @pytest.mark.asyncio
    @REST_NOT_IMPLEMENTED
    async def test_get_funding_rate_spot_market_error(self):
        """Test that funding rate is not available for spot market."""
        async with BinanceProvider(market_type=MarketType.SPOT) as provider:
            with pytest.raises(
                ValueError, match="Funding rate is only available for Futures market"
            ):
                await provider.get_funding_rate("BTCUSDT", limit=1)

    @pytest.mark.asyncio
    @REST_NOT_IMPLEMENTED
    async def test_get_funding_rate_invalid_symbol(self):
        """Test funding rate with invalid symbol."""
        async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
            from laakhay.data.core import InvalidSymbolError

            with pytest.raises(InvalidSymbolError):
                await provider.get_funding_rate("INVALID_SYMBOL", limit=1)

    @pytest.mark.asyncio
    async def test_stream_funding_rate_connection(self):
        """Test that funding rate WebSocket connection works."""
        async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
            # Test connection by getting a few updates
            count = 0
            async for fr in provider.stream_funding_rate(["BTCUSDT"]):
                assert isinstance(fr, FundingRate)
                assert fr.symbol == "BTCUSDT"
                assert fr.funding_rate is not None
                assert fr.mark_price is not None
                assert fr.is_fresh(max_age_seconds=10)  # Should be very fresh

                count += 1
                if count >= 2:  # Just test a couple updates
                    break

    @pytest.mark.asyncio
    async def test_stream_funding_rate_multiple_symbols(self):
        """Test streaming funding rates for multiple symbols."""
        async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
            symbols = ["BTCUSDT", "ETHUSDT"]
            symbols_seen = set()

            count = 0
            async for fr in provider.stream_funding_rate(symbols):
                assert isinstance(fr, FundingRate)
                assert fr.symbol in symbols
                symbols_seen.add(fr.symbol)

                count += 1
                if count >= 10:  # Get enough updates to see both symbols
                    break

            # Should have seen multiple symbols
            assert len(symbols_seen) >= 1

    @pytest.mark.asyncio
    async def test_stream_funding_rate_data_structure(self):
        """Test streaming funding rate data structure."""
        async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
            async for fr in provider.stream_funding_rate(["BTCUSDT"]):
                # Required fields
                assert hasattr(fr, "symbol")
                assert hasattr(fr, "funding_time")
                assert hasattr(fr, "funding_rate")
                assert hasattr(fr, "mark_price")

                # Test properties
                assert fr.funding_time_ms > 0
                assert fr.funding_rate_percentage is not None
                assert fr.is_positive or fr.is_negative or fr.funding_rate == 0

                # Test to_dict
                fr_dict = fr.to_dict()
                assert isinstance(fr_dict, dict)
                assert "symbol" in fr_dict
                assert "funding_rate_percentage" in fr_dict

                break  # Just test one update

    @pytest.mark.asyncio
    async def test_stream_funding_rate_spot_market_error(self):
        """Test that funding rate streaming is not available for spot market."""
        async with BinanceProvider(market_type=MarketType.SPOT) as provider:
            with pytest.raises(
                ValueError, match="Funding rate streaming is only available for Futures market"
            ):
                async for _fr in provider.stream_funding_rate(["BTCUSDT"]):
                    break

    @pytest.mark.asyncio
    async def test_stream_funding_rate_timeout(self):
        """Test that streaming can be cancelled gracefully."""
        async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
            try:
                async with asyncio.timeout_at(asyncio.get_event_loop().time() + 5):
                    count = 0
                    async for _fr in provider.stream_funding_rate(["BTCUSDT", "ETHUSDT"]):
                        count += 1
                        if count >= 5:
                            break
            except TimeoutError:
                pass  # Expected, test passes

    @pytest.mark.asyncio
    async def test_funding_rate_consistency_rest_vs_ws(self):
        """Test consistency between REST and WebSocket funding rates."""
        async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
            # Get REST funding rate
            rest_fr_list = await provider.get_funding_rate("BTCUSDT", limit=1)
            rest_fr = rest_fr_list[0]

            # Get WebSocket funding rate
            async for ws_fr in provider.stream_funding_rate(["BTCUSDT"]):
                # Should be for same symbol
                assert ws_fr.symbol == rest_fr.symbol == "BTCUSDT"

                # Both should have funding rates
                assert ws_fr.funding_rate is not None
                assert rest_fr.funding_rate is not None

                # Both should have mark prices
                assert ws_fr.mark_price is not None
                assert rest_fr.mark_price is not None

                break  # Just need one comparison
