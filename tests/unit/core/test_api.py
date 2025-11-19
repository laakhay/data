"""Comprehensive unit tests for DataAPI.

This module tests the high-level DataAPI facade, which is the main user-facing
interface for laakhay-data. Tests focus on:
- Parameter resolution (defaults, overrides)
- Method delegation to DataRouter
- Error handling and propagation
- Context manager behavior
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from laakhay.data.core.api import DataAPI
from laakhay.data.core.enums import (
    DataFeature,
    InstrumentType,
    MarketType,
    Timeframe,
    TransportKind,
)
from laakhay.data.core.exceptions import (
    CapabilityError,
    InvalidSymbolError,
    ProviderError,
    RateLimitError,
    SymbolResolutionError,
)
from laakhay.data.core.request import DataRequest
from laakhay.data.core.router import DataRouter


@pytest.fixture
def mock_router():
    """Create a mock DataRouter."""
    router = MagicMock(spec=DataRouter)
    router.route = AsyncMock()
    router.route_stream = MagicMock(return_value=AsyncMock())
    return router


@pytest.fixture
def mock_ohlcv():
    """Create a mock OHLCV response."""
    from laakhay.data.models.bar import Bar
    from laakhay.data.models.ohlcv import OHLCV
    from laakhay.data.models.series_meta import SeriesMeta

    bars = [
        Bar(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=100.0,
        )
    ]
    meta = SeriesMeta(
        symbol="BTC/USDT",
        timeframe=Timeframe.H1,
        exchange="binance",
        market_type=MarketType.SPOT,
        count=1,
    )
    return OHLCV(bars=bars, meta=meta)


@pytest.fixture
def mock_order_book():
    """Create a mock OrderBook response."""
    from decimal import Decimal

    from laakhay.data.models.order_book import OrderBook

    return OrderBook(
        symbol="BTC/USDT",
        last_update_id=123456,
        timestamp=datetime.now(),
        bids=[(Decimal("50000.0"), Decimal("1.0")), (Decimal("49999.0"), Decimal("2.0"))],
        asks=[(Decimal("50001.0"), Decimal("1.0")), (Decimal("50002.0"), Decimal("2.0"))],
    )


@pytest.fixture
def mock_trade():
    """Create a mock Trade response."""
    from decimal import Decimal

    from laakhay.data.models.trade import Trade

    return Trade(
        symbol="BTC/USDT",
        trade_id=12345,
        timestamp=datetime.now(),
        price=Decimal("50000.0"),
        quantity=Decimal("0.1"),
        is_buyer_maker=False,  # Buyer is taker (buy market order)
    )


class TestDataAPIInitialization:
    """Test DataAPI initialization and configuration."""

    def test_init_with_defaults(self):
        """Test DataAPI initialization with default parameters."""
        api = DataAPI()
        assert api._default_exchange is None
        assert api._default_market_type is None
        assert api._default_instrument_type == InstrumentType.SPOT
        assert api._router is not None
        assert not api._closed

    def test_init_with_default_exchange(self):
        """Test DataAPI initialization with default exchange."""
        api = DataAPI(default_exchange="binance")
        assert api._default_exchange == "binance"
        assert api._default_market_type is None

    def test_init_with_default_market_type(self):
        """Test DataAPI initialization with default market type."""
        api = DataAPI(default_market_type=MarketType.SPOT)
        assert api._default_market_type == MarketType.SPOT

    def test_init_with_custom_router(self, mock_router):
        """Test DataAPI initialization with custom router."""
        api = DataAPI(router=mock_router)
        assert api._router is mock_router

    @pytest.mark.asyncio
    async def test_context_manager_enter_exit(self, mock_router):
        """Test DataAPI as async context manager."""
        api = DataAPI(router=mock_router)
        async with api:
            assert not api._closed
        # Note: __aexit__ doesn't do anything currently, but test structure is ready


class TestDataAPIParameterResolution:
    """Test parameter resolution (defaults, overrides)."""

    @pytest.mark.asyncio
    async def test_resolve_exchange_with_default(self, mock_router, mock_ohlcv):
        """Test exchange resolution uses default when not provided."""
        mock_router.route.return_value = mock_ohlcv

        api = DataAPI(default_exchange="binance", router=mock_router)
        async with api:
            await api.fetch_ohlcv(
                symbol="BTC/USDT",
                timeframe=Timeframe.H1,
                market_type=MarketType.SPOT,
                # exchange not provided, should use default
            )

        call_args = mock_router.route.call_args[0][0]
        assert call_args.exchange == "binance"

    @pytest.mark.asyncio
    async def test_resolve_exchange_with_override(self, mock_router, mock_ohlcv):
        """Test exchange resolution uses provided value over default."""
        mock_router.route.return_value = mock_ohlcv

        api = DataAPI(default_exchange="binance", router=mock_router)
        async with api:
            await api.fetch_ohlcv(
                symbol="BTC/USDT",
                timeframe=Timeframe.H1,
                exchange="bybit",  # Override default
                market_type=MarketType.SPOT,
            )

        call_args = mock_router.route.call_args[0][0]
        assert call_args.exchange == "bybit"

    @pytest.mark.asyncio
    async def test_resolve_exchange_no_default_raises(self, mock_router):
        """Test that missing exchange raises ValueError when no default."""
        api = DataAPI(router=mock_router)
        async with api:
            with pytest.raises(ValueError, match="exchange must be provided"):
                await api.fetch_ohlcv(
                    symbol="BTC/USDT",
                    timeframe=Timeframe.H1,
                    # No exchange, no default
                )

    @pytest.mark.asyncio
    async def test_resolve_market_type_with_default(self, mock_router, mock_ohlcv):
        """Test market type resolution uses default when not provided."""
        mock_router.route.return_value = mock_ohlcv

        api = DataAPI(default_market_type=MarketType.SPOT, router=mock_router)
        async with api:
            await api.fetch_ohlcv(
                symbol="BTC/USDT",
                timeframe=Timeframe.H1,
                exchange="binance",
                # market_type not provided, should use default
            )

        call_args = mock_router.route.call_args[0][0]
        assert call_args.market_type == MarketType.SPOT

    @pytest.mark.asyncio
    async def test_resolve_market_type_with_override(self, mock_router, mock_ohlcv):
        """Test market type resolution uses provided value over default."""
        mock_router.route.return_value = mock_ohlcv

        api = DataAPI(default_market_type=MarketType.SPOT, router=mock_router)
        async with api:
            await api.fetch_ohlcv(
                symbol="BTC/USDT",
                timeframe=Timeframe.H1,
                exchange="binance",
                market_type=MarketType.FUTURES,  # Override default
            )

        call_args = mock_router.route.call_args[0][0]
        assert call_args.market_type == MarketType.FUTURES

    @pytest.mark.asyncio
    async def test_resolve_instrument_type_with_default(self, mock_router, mock_ohlcv):
        """Test instrument type resolution uses default when not provided."""
        mock_router.route.return_value = mock_ohlcv

        api = DataAPI(default_instrument_type=InstrumentType.SPOT, router=mock_router)
        async with api:
            await api.fetch_ohlcv(
                symbol="BTC/USDT",
                timeframe=Timeframe.H1,
                exchange="binance",
                market_type=MarketType.SPOT,
                # instrument_type not provided, should use default
            )

        call_args = mock_router.route.call_args[0][0]
        assert call_args.instrument_type == InstrumentType.SPOT

    @pytest.mark.asyncio
    async def test_resolve_instrument_type_with_override(self, mock_router, mock_ohlcv):
        """Test instrument type resolution uses provided value over default."""
        mock_router.route.return_value = mock_ohlcv

        api = DataAPI(default_instrument_type=InstrumentType.SPOT, router=mock_router)
        async with api:
            await api.fetch_ohlcv(
                symbol="BTC/USDT",
                timeframe=Timeframe.H1,
                exchange="binance",
                market_type=MarketType.FUTURES,
                instrument_type=InstrumentType.PERPETUAL,  # Override default
            )

        call_args = mock_router.route.call_args[0][0]
        assert call_args.instrument_type == InstrumentType.PERPETUAL


class TestDataAPIFetchHealth:
    """Test DataAPI.fetch_health method."""

    @pytest.mark.asyncio
    async def test_fetch_health_success(self, mock_router):
        """Test health fetch builds correct request."""
        mock_router.route.return_value = {"status": "ok"}

        api = DataAPI(router=mock_router)
        async with api:
            result = await api.fetch_health(
                exchange="binance",
                market_type=MarketType.SPOT,
            )

        assert result == {"status": "ok"}
        mock_router.route.assert_called_once()
        call_args = mock_router.route.call_args[0][0]
        assert isinstance(call_args, DataRequest)
        assert call_args.feature == DataFeature.HEALTH
        assert call_args.transport == TransportKind.REST
        assert call_args.exchange == "binance"
        assert call_args.market_type == MarketType.SPOT


class TestDataAPIFetchOHLCV:
    """Test DataAPI.fetch_ohlcv method."""

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_success(self, mock_router, mock_ohlcv):
        """Test successful OHLCV fetch."""
        mock_router.route.return_value = mock_ohlcv

        api = DataAPI(router=mock_router)
        async with api:
            result = await api.fetch_ohlcv(
                symbol="BTC/USDT",
                timeframe=Timeframe.H1,
                exchange="binance",
                market_type=MarketType.SPOT,
                limit=100,
            )

        assert result == mock_ohlcv
        mock_router.route.assert_called_once()
        call_args = mock_router.route.call_args[0][0]
        assert isinstance(call_args, DataRequest)
        assert call_args.feature == DataFeature.OHLCV
        assert call_args.transport == TransportKind.REST
        assert call_args.symbol == "BTC/USDT"
        assert call_args.timeframe == Timeframe.H1
        assert call_args.limit == 100

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_with_time_range(self, mock_router, mock_ohlcv):
        """Test OHLCV fetch with time range."""
        mock_router.route.return_value = mock_ohlcv

        start_time = datetime.now() - timedelta(days=7)
        end_time = datetime.now()

        api = DataAPI(router=mock_router)
        async with api:
            await api.fetch_ohlcv(
                symbol="BTC/USDT",
                timeframe=Timeframe.H1,
                exchange="binance",
                market_type=MarketType.SPOT,
                start_time=start_time,
                end_time=end_time,
            )

        call_args = mock_router.route.call_args[0][0]
        assert call_args.start_time == start_time
        assert call_args.end_time == end_time

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_with_pagination(self, mock_router, mock_ohlcv):
        """Test OHLCV fetch with pagination limits."""
        mock_router.route.return_value = mock_ohlcv

        api = DataAPI(router=mock_router)
        async with api:
            await api.fetch_ohlcv(
                symbol="BTC/USDT",
                timeframe=Timeframe.H1,
                exchange="binance",
                market_type=MarketType.SPOT,
                limit=1000,
                max_chunks=5,
            )

        call_args = mock_router.route.call_args[0][0]
        assert call_args.limit == 1000
        assert call_args.max_chunks == 5

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_capability_error(self, mock_router):
        """Test OHLCV fetch raises CapabilityError when unsupported."""
        mock_router.route.side_effect = CapabilityError(
            "OHLCV REST not supported",
            key=MagicMock(),
            status=MagicMock(),
        )

        api = DataAPI(router=mock_router)
        async with api:
            with pytest.raises(CapabilityError):
                await api.fetch_ohlcv(
                    symbol="BTC/USDT",
                    timeframe=Timeframe.H1,
                    exchange="coinbase",
                    market_type=MarketType.FUTURES,  # Coinbase doesn't support futures
                )

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_symbol_resolution_error(self, mock_router):
        """Test OHLCV fetch raises SymbolResolutionError for invalid symbol."""
        mock_router.route.side_effect = SymbolResolutionError(
            "Symbol not found",
            exchange="binance",
            value="INVALID/USDT",
            market_type=MarketType.SPOT,
        )

        api = DataAPI(router=mock_router)
        async with api:
            with pytest.raises(SymbolResolutionError):
                await api.fetch_ohlcv(
                    symbol="INVALID/USDT",
                    timeframe=Timeframe.H1,
                    exchange="binance",
                    market_type=MarketType.SPOT,
                )

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_all_timeframes(self, mock_router, mock_ohlcv):
        """Test OHLCV fetch works with all supported timeframes."""
        mock_router.route.return_value = mock_ohlcv

        api = DataAPI(router=mock_router)
        async with api:
            for timeframe in Timeframe:
                await api.fetch_ohlcv(
                    symbol="BTC/USDT",
                    timeframe=timeframe,
                    exchange="binance",
                    market_type=MarketType.SPOT,
                )

        # Should be called once per timeframe
        assert mock_router.route.call_count == len(Timeframe)


class TestDataAPIFetchOrderBook:
    """Test DataAPI.fetch_order_book method."""

    @pytest.mark.asyncio
    async def test_fetch_order_book_success(self, mock_router, mock_order_book):
        """Test successful order book fetch."""
        mock_router.route.return_value = mock_order_book

        api = DataAPI(router=mock_router)
        async with api:
            result = await api.fetch_order_book(
                symbol="BTC/USDT",
                exchange="binance",
                market_type=MarketType.SPOT,
                depth=20,
            )

        assert result == mock_order_book
        call_args = mock_router.route.call_args[0][0]
        assert call_args.feature == DataFeature.ORDER_BOOK
        assert call_args.transport == TransportKind.REST
        assert call_args.depth == 20

    @pytest.mark.asyncio
    async def test_fetch_order_book_default_depth(self, mock_router, mock_order_book):
        """Test order book fetch uses default depth."""
        mock_router.route.return_value = mock_order_book

        api = DataAPI(router=mock_router)
        async with api:
            await api.fetch_order_book(
                symbol="BTC/USDT",
                exchange="binance",
                market_type=MarketType.SPOT,
                # depth not provided, should use default 100
            )

        call_args = mock_router.route.call_args[0][0]
        assert call_args.depth == 100

    @pytest.mark.asyncio
    async def test_fetch_order_book_custom_depth(self, mock_router, mock_order_book):
        """Test order book fetch with custom depth."""
        mock_router.route.return_value = mock_order_book

        api = DataAPI(router=mock_router)
        async with api:
            await api.fetch_order_book(
                symbol="BTC/USDT",
                exchange="binance",
                market_type=MarketType.SPOT,
                depth=500,
            )

        call_args = mock_router.route.call_args[0][0]
        assert call_args.depth == 500


class TestDataAPIFetchTrades:
    """Test DataAPI.fetch_recent_trades method."""

    @pytest.mark.asyncio
    async def test_fetch_recent_trades_success(self, mock_router, mock_trade):
        """Test successful recent trades fetch."""
        mock_router.route.return_value = [mock_trade]

        api = DataAPI(router=mock_router)
        async with api:
            result = await api.fetch_recent_trades(
                symbol="BTC/USDT",
                exchange="binance",
                market_type=MarketType.SPOT,
                limit=10,
            )

        assert result == [mock_trade]
        call_args = mock_router.route.call_args[0][0]
        assert call_args.feature == DataFeature.TRADES
        assert call_args.transport == TransportKind.REST
        assert call_args.limit == 10

    @pytest.mark.asyncio
    async def test_fetch_recent_trades_default_limit(self, mock_router, mock_trade):
        """Test recent trades fetch uses default limit."""
        mock_router.route.return_value = [mock_trade]

        api = DataAPI(router=mock_router)
        async with api:
            await api.fetch_recent_trades(
                symbol="BTC/USDT",
                exchange="binance",
                market_type=MarketType.SPOT,
                # limit not provided, should use default 500
            )

        call_args = mock_router.route.call_args[0][0]
        assert call_args.limit == 500


class TestDataAPIFetchHistoricalTrades:
    """Test DataAPI.fetch_historical_trades method."""

    @pytest.mark.asyncio
    async def test_fetch_historical_trades(self, mock_router, mock_trade):
        mock_router.route.return_value = [mock_trade]

        api = DataAPI(router=mock_router)
        async with api:
            result = await api.fetch_historical_trades(
                symbol="BTC/USDT",
                exchange="binance",
                market_type=MarketType.SPOT,
                limit=100,
                from_id=1234,
            )

        assert result == [mock_trade]
        call_args = mock_router.route.call_args[0][0]
        assert call_args.feature == DataFeature.HISTORICAL_TRADES
        assert call_args.limit == 100
        assert call_args.from_id == 1234

    @pytest.mark.asyncio
    async def test_fetch_historical_trades_without_optional_args(self, mock_router, mock_trade):
        mock_router.route.return_value = [mock_trade]

        api = DataAPI(router=mock_router)
        async with api:
            await api.fetch_historical_trades(
                symbol="BTC/USDT",
                exchange="binance",
                market_type=MarketType.SPOT,
            )

        call_args = mock_router.route.call_args[0][0]
        assert call_args.limit is None
        assert call_args.from_id is None


class TestDataAPIFetchSymbols:
    """Test DataAPI.fetch_symbols method."""

    @pytest.mark.asyncio
    async def test_fetch_symbols_success(self, mock_router):
        """Test successful symbols fetch."""
        from laakhay.data.models.symbol import Symbol

        mock_symbols = [
            Symbol(
                symbol="BTCUSDT",
                base_asset="BTC",
                quote_asset="USDT",
            )
        ]
        mock_router.route.return_value = mock_symbols

        api = DataAPI(router=mock_router)
        async with api:
            result = await api.fetch_symbols(
                exchange="binance",
                market_type=MarketType.SPOT,
            )

        assert result == mock_symbols
        call_args = mock_router.route.call_args[0][0]
        assert call_args.feature == DataFeature.SYMBOL_METADATA
        assert call_args.transport == TransportKind.REST

    @pytest.mark.asyncio
    async def test_fetch_symbols_with_quote_filter(self, mock_router):
        """Test symbols fetch with quote asset filter."""
        from laakhay.data.models.symbol import Symbol

        mock_symbols = [
            Symbol(
                symbol="BTCUSDT",
                base_asset="BTC",
                quote_asset="USDT",
            )
        ]
        mock_router.route.return_value = mock_symbols

        api = DataAPI(router=mock_router)
        async with api:
            await api.fetch_symbols(
                exchange="binance",
                market_type=MarketType.SPOT,
                quote_asset="USDT",
            )

        call_args = mock_router.route.call_args[0][0]
        assert call_args.extra_params["quote_asset"] == "USDT"


class TestDataAPIStreaming:
    """Test DataAPI streaming methods."""

    @pytest.mark.asyncio
    async def test_stream_ohlcv(self, mock_router, mock_ohlcv):
        """Test OHLCV streaming."""

        async def mock_stream():
            yield mock_ohlcv.bars[0]

        mock_router.route_stream.return_value = mock_stream()

        api = DataAPI(router=mock_router)
        async with api:
            count = 0
            async for _bar in api.stream_ohlcv(
                symbol="BTC/USDT",
                timeframe=Timeframe.M1,
                exchange="binance",
                market_type=MarketType.SPOT,
            ):
                count += 1
                if count >= 1:
                    break

        assert count == 1
        mock_router.route_stream.assert_called_once()
        call_args = mock_router.route_stream.call_args[0][0]
        assert call_args.feature == DataFeature.OHLCV
        assert call_args.transport == TransportKind.WS

    @pytest.mark.asyncio
    async def test_stream_trades(self, mock_router, mock_trade):
        """Test trades streaming."""

        async def mock_stream():
            yield mock_trade

        mock_router.route_stream.return_value = mock_stream()

        api = DataAPI(router=mock_router)
        async with api:
            count = 0
            async for _trade in api.stream_trades(
                symbol="BTC/USDT",
                exchange="binance",
                market_type=MarketType.SPOT,
            ):
                count += 1
                if count >= 1:
                    break

        assert count == 1
        call_args = mock_router.route_stream.call_args[0][0]
        assert call_args.feature == DataFeature.TRADES
        assert call_args.transport == TransportKind.WS


class TestDataAPIFuturesMethods:
    """Test DataAPI futures-specific methods."""

    @pytest.mark.asyncio
    async def test_fetch_open_interest_success(self, mock_router):
        """Test successful open interest fetch."""
        from decimal import Decimal

        from laakhay.data.models.open_interest import OpenInterest

        mock_oi = [
            OpenInterest(
                symbol="BTC/USDT",
                exchange="binance",
                market_type=MarketType.FUTURES,
                timestamp=datetime.now(),
                open_interest=Decimal("1000.5"),
            )
        ]
        mock_router.route.return_value = mock_oi

        api = DataAPI(router=mock_router)
        async with api:
            result = await api.fetch_open_interest(
                symbol="BTC/USDT",
                exchange="binance",
                market_type=MarketType.FUTURES,
                historical=False,
            )

        assert result == mock_oi
        call_args = mock_router.route.call_args[0][0]
        assert call_args.feature == DataFeature.OPEN_INTEREST
        assert call_args.transport == TransportKind.REST
        assert call_args.historical is False

    @pytest.mark.asyncio
    async def test_fetch_open_interest_historical(self, mock_router):
        """Test historical open interest fetch."""
        from decimal import Decimal

        from laakhay.data.models.open_interest import OpenInterest

        mock_oi = [
            OpenInterest(
                symbol="BTC/USDT",
                exchange="binance",
                market_type=MarketType.FUTURES,
                timestamp=datetime.now(),
                open_interest=Decimal("1000.5"),
            )
        ]
        mock_router.route.return_value = mock_oi

        start_time = datetime.now() - timedelta(days=7)
        end_time = datetime.now()

        api = DataAPI(router=mock_router)
        async with api:
            await api.fetch_open_interest(
                symbol="BTC/USDT",
                exchange="binance",
                market_type=MarketType.FUTURES,
                historical=True,
                start_time=start_time,
                end_time=end_time,
                period="1h",
                limit=100,
            )

        call_args = mock_router.route.call_args[0][0]
        assert call_args.historical is True
        assert call_args.start_time == start_time
        assert call_args.end_time == end_time
        assert call_args.period == "1h"
        assert call_args.limit == 100

    @pytest.mark.asyncio
    async def test_fetch_funding_rates_success(self, mock_router):
        """Test successful funding rates fetch."""
        from datetime import UTC
        from decimal import Decimal

        from laakhay.data.models.funding_rate import FundingRate

        mock_rates = [
            FundingRate(
                symbol="BTC/USDT",
                funding_time=datetime.now(UTC),
                funding_rate=Decimal("0.0001"),
            )
        ]
        mock_router.route.return_value = mock_rates

        api = DataAPI(router=mock_router)
        async with api:
            result = await api.fetch_funding_rates(
                symbol="BTC/USDT",
                exchange="binance",
                market_type=MarketType.FUTURES,
                limit=50,
            )

        assert result == mock_rates
        call_args = mock_router.route.call_args[0][0]
        assert call_args.feature == DataFeature.FUNDING_RATE
        assert call_args.transport == TransportKind.REST
        assert call_args.limit == 50

    @pytest.mark.asyncio
    async def test_fetch_funding_rates_historical(self, mock_router):
        """Test historical funding rates fetch."""
        from datetime import UTC
        from decimal import Decimal

        from laakhay.data.models.funding_rate import FundingRate

        mock_rates = [
            FundingRate(
                symbol="BTC/USDT",
                funding_time=datetime.now(UTC),
                funding_rate=Decimal("0.0001"),
            )
        ]
        mock_router.route.return_value = mock_rates

        start_time = datetime.now() - timedelta(days=30)
        end_time = datetime.now()

        api = DataAPI(router=mock_router)
        async with api:
            await api.fetch_funding_rates(
                symbol="BTC/USDT",
                exchange="binance",
                market_type=MarketType.FUTURES,
                start_time=start_time,
                end_time=end_time,
                limit=200,
            )

        call_args = mock_router.route.call_args[0][0]
        assert call_args.start_time == start_time
        assert call_args.end_time == end_time
        assert call_args.limit == 200


class TestDataAPIErrorHandling:
    """Test error handling and propagation."""

    @pytest.mark.asyncio
    async def test_provider_error_propagation(self, mock_router):
        """Test that ProviderError is propagated correctly."""
        mock_router.route.side_effect = ProviderError("Provider error")

        api = DataAPI(router=mock_router)
        async with api:
            with pytest.raises(ProviderError, match="Provider error"):
                await api.fetch_ohlcv(
                    symbol="BTC/USDT",
                    timeframe=Timeframe.H1,
                    exchange="binance",
                    market_type=MarketType.SPOT,
                )

    @pytest.mark.asyncio
    async def test_rate_limit_error_propagation(self, mock_router):
        """Test that RateLimitError is propagated correctly."""
        mock_router.route.side_effect = RateLimitError(
            "Rate limit exceeded",
            retry_after=60,
        )

        api = DataAPI(router=mock_router)
        async with api:
            with pytest.raises(RateLimitError) as exc_info:
                await api.fetch_ohlcv(
                    symbol="BTC/USDT",
                    timeframe=Timeframe.H1,
                    exchange="binance",
                    market_type=MarketType.SPOT,
                )
            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_invalid_symbol_error_propagation(self, mock_router):
        """Test that InvalidSymbolError is propagated correctly."""
        mock_router.route.side_effect = InvalidSymbolError("Invalid symbol")

        api = DataAPI(router=mock_router)
        async with api:
            with pytest.raises(InvalidSymbolError):
                await api.fetch_ohlcv(
                    symbol="INVALID/USDT",
                    timeframe=Timeframe.H1,
                    exchange="binance",
                    market_type=MarketType.SPOT,
                )


class TestDataAPIStreamingMethods:
    """Test additional streaming methods."""

    @pytest.mark.asyncio
    async def test_stream_ohlcv_multi(self, mock_router, mock_ohlcv):
        """Test multi-symbol OHLCV streaming."""
        from unittest.mock import AsyncMock, MagicMock

        # Mock provider registry and provider
        async def mock_stream(*args, **kwargs):
            yield mock_ohlcv.bars[0]

        mock_provider = AsyncMock()
        mock_provider.stream_ohlcv_multi = mock_stream  # Direct function, not AsyncMock

        mock_registry = MagicMock()
        mock_registry.is_registered.return_value = True
        mock_registry.get_provider = AsyncMock(return_value=mock_provider)
        mock_router._provider_registry = mock_registry
        mock_router._capability_service = MagicMock()

        api = DataAPI(router=mock_router)
        async with api:
            count = 0
            async for _bar in api.stream_ohlcv_multi(
                symbols=["BTC/USDT", "ETH/USDT"],
                timeframe=Timeframe.M1,
                exchange="binance",
                market_type=MarketType.SPOT,
            ):
                count += 1
                if count >= 1:
                    break

        assert count == 1
        mock_registry.get_provider.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_trades_multi(self, mock_router, mock_trade):
        """Test multi-symbol trades streaming."""
        from unittest.mock import AsyncMock, MagicMock

        async def mock_stream(*args, **kwargs):
            yield mock_trade

        mock_provider = AsyncMock()
        mock_provider.stream_trades_multi = mock_stream  # Direct function, not AsyncMock

        mock_registry = MagicMock()
        mock_registry.is_registered.return_value = True
        mock_registry.get_provider = AsyncMock(return_value=mock_provider)
        mock_router._provider_registry = mock_registry
        mock_router._capability_service = MagicMock()

        api = DataAPI(router=mock_router)
        async with api:
            count = 0
            async for _trade in api.stream_trades_multi(
                symbols=["BTC/USDT", "ETH/USDT"],
                exchange="binance",
                market_type=MarketType.SPOT,
            ):
                count += 1
                if count >= 1:
                    break

        assert count == 1

    @pytest.mark.asyncio
    async def test_stream_order_book(self, mock_router, mock_order_book):
        """Test order book streaming."""

        async def mock_stream():
            yield mock_order_book

        mock_router.route_stream.return_value = mock_stream()

        api = DataAPI(router=mock_router)
        async with api:
            count = 0
            async for _ob in api.stream_order_book(
                symbol="BTC/USDT",
                exchange="binance",
                market_type=MarketType.SPOT,
                depth=20,
            ):
                count += 1
                if count >= 1:
                    break

        assert count == 1
        call_args = mock_router.route_stream.call_args[0][0]
        assert call_args.feature == DataFeature.ORDER_BOOK
        assert call_args.transport == TransportKind.WS
        assert call_args.depth == 20

    @pytest.mark.asyncio
    async def test_stream_liquidations(self, mock_router):
        """Test liquidations streaming."""
        from datetime import UTC
        from decimal import Decimal

        from laakhay.data.models.liquidation import Liquidation

        mock_liq = Liquidation(
            symbol="BTC/USDT",
            timestamp=datetime.now(UTC),
            side="SELL",
            order_type="LIQUIDATION",
            time_in_force="IOC",
            original_quantity=Decimal("1.0"),
            price=Decimal("50000.0"),
            average_price=Decimal("50000.0"),
            order_status="FILLED",
            last_filled_quantity=Decimal("1.0"),
            accumulated_quantity=Decimal("1.0"),
        )

        async def mock_stream():
            yield mock_liq

        mock_router.route_stream.return_value = mock_stream()

        api = DataAPI(router=mock_router)
        async with api:
            count = 0
            async for _liq in api.stream_liquidations(
                exchange="binance",
                market_type=MarketType.FUTURES,
            ):
                count += 1
                if count >= 1:
                    break

        assert count == 1
        call_args = mock_router.route_stream.call_args[0][0]
        assert call_args.feature == DataFeature.LIQUIDATIONS
        assert call_args.transport == TransportKind.WS

    @pytest.mark.asyncio
    async def test_stream_open_interest(self, mock_router):
        """Test open interest streaming."""
        from decimal import Decimal

        from laakhay.data.models.open_interest import OpenInterest

        mock_oi = OpenInterest(
            symbol="BTC/USDT",
            exchange="binance",
            market_type=MarketType.FUTURES,
            timestamp=datetime.now(),
            open_interest=Decimal("1000.5"),
        )

        async def mock_stream():
            yield mock_oi

        mock_router.route_stream.return_value = mock_stream()

        api = DataAPI(router=mock_router)
        async with api:
            count = 0
            async for _oi in api.stream_open_interest(
                symbols=["BTC/USDT"],
                exchange="binance",
                market_type=MarketType.FUTURES,
                period="5m",
            ):
                count += 1
                if count >= 1:
                    break

        assert count == 1
        call_args = mock_router.route_stream.call_args[0][0]
        assert call_args.feature == DataFeature.OPEN_INTEREST
        assert call_args.transport == TransportKind.WS

    @pytest.mark.asyncio
    async def test_stream_funding_rates(self, mock_router):
        """Test funding rates streaming."""
        from datetime import UTC
        from decimal import Decimal

        from laakhay.data.models.funding_rate import FundingRate

        mock_rate = FundingRate(
            symbol="BTC/USDT",
            funding_time=datetime.now(UTC),
            funding_rate=Decimal("0.0001"),
        )

        async def mock_stream():
            yield mock_rate

        mock_router.route_stream.return_value = mock_stream()

        api = DataAPI(router=mock_router)
        async with api:
            count = 0
            async for _rate in api.stream_funding_rates(
                symbols=["BTC/USDT"],
                exchange="binance",
                market_type=MarketType.FUTURES,
            ):
                count += 1
                if count >= 1:
                    break

        assert count == 1
        call_args = mock_router.route_stream.call_args[0][0]
        assert call_args.feature == DataFeature.FUNDING_RATE
        assert call_args.transport == TransportKind.WS

    @pytest.mark.asyncio
    async def test_stream_mark_price(self, mock_router):
        """Test mark price streaming."""
        from decimal import Decimal

        from laakhay.data.models.mark_price import MarkPrice

        mock_mark = MarkPrice(
            symbol="BTC/USDT",
            exchange="binance",
            market_type=MarketType.FUTURES,
            timestamp=datetime.now(),
            mark_price=Decimal("50000.0"),
        )

        async def mock_stream():
            yield mock_mark

        mock_router.route_stream.return_value = mock_stream()

        api = DataAPI(router=mock_router)
        async with api:
            count = 0
            async for _mark in api.stream_mark_price(
                symbols=["BTC/USDT"],
                exchange="binance",
                market_type=MarketType.FUTURES,
            ):
                count += 1
                if count >= 1:
                    break

        assert count == 1
        call_args = mock_router.route_stream.call_args[0][0]
        assert call_args.feature == DataFeature.MARK_PRICE
        assert call_args.transport == TransportKind.WS
