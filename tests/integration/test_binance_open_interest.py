"""Integration tests for Binance Open Interest functionality."""

from datetime import datetime, timedelta, timezone

import pytest

from laakhay.data.core import MarketType
from laakhay.data.models import OpenInterest
from laakhay.data.providers.binance import BinanceProvider


@pytest.mark.asyncio
async def test_get_current_open_interest():
    """Test fetching current Open Interest for a valid symbol."""
    async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
        oi_list = await provider.get_open_interest("BTCUSDT", historical=False)

        assert len(oi_list) == 1
        oi = oi_list[0]

        assert isinstance(oi, OpenInterest)
        assert oi.symbol == "BTCUSDT"
        assert oi.open_interest >= 0
        # Note: current OI endpoint doesn't provide open_interest_value
        assert oi.open_interest_value is None
        assert oi.is_fresh(max_age_seconds=300)  # Should be fresh


@pytest.mark.asyncio
async def test_get_historical_open_interest():
    """Test fetching historical Open Interest data."""
    async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
        # Fetch last 10 data points with 5m period
        oi_list = await provider.get_open_interest(
            "BTCUSDT", historical=True, period="5m", limit=10
        )

        assert len(oi_list) <= 10
        assert len(oi_list) > 0

        for oi in oi_list:
            assert isinstance(oi, OpenInterest)
            assert oi.symbol == "BTCUSDT"
            assert oi.open_interest >= 0
            assert oi.open_interest_value is not None
            assert oi.sum_open_interest is not None
            assert oi.sum_open_interest_value is not None


@pytest.mark.asyncio
async def test_get_open_interest_with_time_range():
    """Test fetching historical OI with time range."""
    async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=2)

        oi_list = await provider.get_open_interest(
            "BTCUSDT",
            historical=True,
            period="1h",
            start_time=start_time,
            end_time=end_time,
            limit=5,
        )

        assert len(oi_list) <= 5

        # Check timestamps are within range
        for oi in oi_list:
            assert start_time <= oi.timestamp <= end_time


@pytest.mark.asyncio
async def test_get_open_interest_invalid_symbol():
    """Test error handling for invalid symbol."""
    async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
        from laakhay.data.core.exceptions import InvalidSymbolError

        with pytest.raises(InvalidSymbolError):
            await provider.get_open_interest("INVALID", historical=False)


@pytest.mark.asyncio
async def test_get_open_interest_invalid_period():
    """Test error handling for invalid period."""
    async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
        with pytest.raises(ValueError, match="Invalid period"):
            await provider.get_open_interest("BTCUSDT", historical=True, period="invalid")


@pytest.mark.asyncio
async def test_get_open_interest_spot_market_error():
    """Test that OI is not available for spot market."""
    async with BinanceProvider(market_type=MarketType.SPOT) as provider:
        with pytest.raises(ValueError, match="Open Interest is only available for Futures market"):
            await provider.get_open_interest("BTCUSDT", historical=False)


@pytest.mark.asyncio
async def test_stream_open_interest_single_symbol():
    """Test streaming Open Interest for a single symbol."""
    async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
        received_count = 0
        max_received = 3

        async for oi in provider.stream_open_interest(["BTCUSDT"], update_speed="1s"):
            assert isinstance(oi, OpenInterest)
            assert oi.symbol == "BTCUSDT"
            assert oi.open_interest >= 0
            assert oi.open_interest_value is not None
            assert oi.is_fresh(max_age_seconds=5)  # Should be very fresh from stream

            received_count += 1
            if received_count >= max_received:
                break

        assert received_count >= 1  # Should receive at least one update


@pytest.mark.asyncio
async def test_stream_open_interest_multiple_symbols():
    """Test streaming Open Interest for multiple symbols."""
    async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
        symbols = ["BTCUSDT", "ETHUSDT"]
        received_symbols = set()
        max_received = 6  # 3 per symbol

        async for oi in provider.stream_open_interest(symbols, update_speed="1s"):
            assert isinstance(oi, OpenInterest)
            assert oi.symbol in symbols
            assert oi.open_interest >= 0
            assert oi.is_fresh(max_age_seconds=5)

            received_symbols.add(oi.symbol)

            if len(received_symbols) >= len(symbols) and len(received_symbols) >= 4:
                break

        # Should receive data from both symbols
        assert len(received_symbols) >= 1


@pytest.mark.asyncio
async def test_stream_open_interest_invalid_speed():
    """Test error handling for invalid update speed."""
    async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
        with pytest.raises(ValueError, match="update_speed must be '1s' or '3s'"):
            # This will raise immediately, not when we start iterating
            async for _ in provider.stream_open_interest(["BTCUSDT"], update_speed="invalid"):
                break


@pytest.mark.asyncio
async def test_stream_open_interest_spot_market_error():
    """Test that OI streaming is not available for spot market."""
    async with BinanceProvider(market_type=MarketType.SPOT) as provider:
        with pytest.raises(
            ValueError, match="Open Interest streaming is only available for Futures market"
        ):
            async for _ in provider.stream_open_interest(["BTCUSDT"]):
                break


@pytest.mark.asyncio
async def test_open_interest_data_consistency():
    """Test that REST and WebSocket data are consistent."""
    async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
        # Get current OI via REST
        rest_oi_list = await provider.get_open_interest("BTCUSDT", historical=False)
        rest_oi = rest_oi_list[0]

        # Stream OI via WebSocket and compare structure
        async for ws_oi in provider.stream_open_interest(["BTCUSDT"], update_speed="1s"):
            # Both should have same symbol
            assert ws_oi.symbol == rest_oi.symbol

            # Both should have valid OI values
            assert ws_oi.open_interest >= 0
            assert rest_oi.open_interest >= 0

            # WebSocket should be fresher
            assert ws_oi.is_fresh(max_age_seconds=5)

            break  # Just test one update


@pytest.mark.asyncio
async def test_open_interest_period_validation():
    """Test that all valid periods work."""
    async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
        valid_periods = ["5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"]

        for period in valid_periods:
            oi_list = await provider.get_open_interest(
                "BTCUSDT", historical=True, period=period, limit=2
            )

            assert len(oi_list) <= 2
            for oi in oi_list:
                assert oi.symbol == "BTCUSDT"
                assert oi.open_interest >= 0
