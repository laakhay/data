"""Unit tests for API request builder.

This module tests the APIRequestBuilder and api_request factory function,
ensuring they work correctly with defaults and provide a fluent API.
"""

from datetime import UTC, datetime

import pytest

from laakhay.data.api.request_builder import (
    APIRequestBuilder,
    DataRequest,
    DataRequestBuilder,
    api_request,
)
from laakhay.data.core.enums import (
    DataFeature,
    InstrumentType,
    MarketType,
    Timeframe,
    TransportKind,
)


class TestAPIRequestBuilder:
    """Test APIRequestBuilder with defaults."""

    def test_builder_with_defaults(self):
        """Test builder with DataAPI-style defaults."""
        builder = APIRequestBuilder.with_defaults(
            default_exchange="binance",
            default_market_type=MarketType.SPOT,
            default_instrument_type=InstrumentType.SPOT,
        )
        request = (
            builder.feature(DataFeature.OHLCV)
            .transport(TransportKind.REST)
            .symbol("BTC/USDT")
            .timeframe(Timeframe.H1)
            .limit(100)
            .build()
        )
        assert request.exchange == "binance"
        assert request.market_type == MarketType.SPOT
        assert request.instrument_type == InstrumentType.SPOT
        assert request.symbol == "BTC/USDT"

    def test_builder_overrides_defaults(self):
        """Test that explicit values override defaults."""
        builder = APIRequestBuilder.with_defaults(
            default_exchange="binance",
            default_market_type=MarketType.SPOT,
        )
        request = (
            builder.feature(DataFeature.OHLCV)
            .transport(TransportKind.REST)
            .exchange("bybit")
            .market_type(MarketType.FUTURES)
            .symbol("BTC/USDT")
            .timeframe(Timeframe.H1)
            .build()
        )
        assert request.exchange == "bybit"
        assert request.market_type == MarketType.FUTURES

    def test_builder_exchange_none_uses_default(self):
        """Test that exchange(None) uses default."""
        builder = APIRequestBuilder.with_defaults(default_exchange="binance")
        request = (
            builder.feature(DataFeature.OHLCV)
            .transport(TransportKind.REST)
            .exchange(None)
            .market_type(MarketType.SPOT)
            .symbol("BTC/USDT")
            .timeframe(Timeframe.H1)
            .build()
        )
        assert request.exchange == "binance"

    def test_builder_missing_required_without_defaults(self):
        """Test that missing required fields raise errors even with defaults."""
        builder = APIRequestBuilder.with_defaults(default_exchange="binance")
        with pytest.raises(ValueError, match="market_type is required"):
            (
                builder.feature(DataFeature.OHLCV)
                .transport(TransportKind.REST)
                .symbol("BTC/USDT")
                .timeframe(Timeframe.H1)
                .build()
            )

    def test_builder_standalone_without_defaults(self):
        """Test builder works standalone without defaults."""
        builder = APIRequestBuilder()
        request = (
            builder.feature(DataFeature.OHLCV)
            .transport(TransportKind.REST)
            .exchange("binance")
            .market_type(MarketType.SPOT)
            .symbol("BTC/USDT")
            .timeframe(Timeframe.H1)
            .build()
        )
        assert request.exchange == "binance"
        assert request.market_type == MarketType.SPOT

    def test_builder_inherits_base_functionality(self):
        """Test that APIRequestBuilder inherits all base builder methods."""
        builder = APIRequestBuilder()
        request = (
            builder.feature(DataFeature.OHLCV)
            .transport(TransportKind.REST)
            .exchange("binance")
            .market_type(MarketType.SPOT)
            .symbol("BTC/USDT")
            .timeframe(Timeframe.H1)
            .start_time(datetime(2024, 1, 1, tzinfo=UTC))
            .end_time(datetime(2024, 1, 2, tzinfo=UTC))
            .limit(100)
            .max_chunks(5)
            .build()
        )
        assert request.limit == 100
        assert request.max_chunks == 5


class TestAPIRequestBuilderFactoryMethods:
    """Test factory methods for common request patterns."""

    def test_for_ohlcv(self):
        """Test for_ohlcv factory method."""
        builder = APIRequestBuilder.for_ohlcv(
            "BTC/USDT",
            Timeframe.H1,
            exchange="binance",
            market_type=MarketType.SPOT,
        )
        request = builder.limit(100).build()
        assert request.feature == DataFeature.OHLCV
        assert request.transport == TransportKind.REST
        assert request.symbol == "BTC/USDT"
        assert request.timeframe == Timeframe.H1
        assert request.exchange == "binance"
        assert request.market_type == MarketType.SPOT

    def test_for_ohlcv_with_defaults(self):
        """Test for_ohlcv with some defaults missing."""
        builder = APIRequestBuilder.for_ohlcv(
            "BTC/USDT",
            Timeframe.H1,
        )
        # Should still need exchange and market_type
        with pytest.raises(ValueError):
            builder.build()

    def test_for_order_book(self):
        """Test for_order_book factory method."""
        builder = APIRequestBuilder.for_order_book(
            "BTC/USDT",
            exchange="binance",
            market_type=MarketType.SPOT,
        )
        request = builder.depth(100).build()
        assert request.feature == DataFeature.ORDER_BOOK
        assert request.symbol == "BTC/USDT"
        assert request.depth == 100

    def test_for_trades(self):
        """Test for_trades factory method."""
        builder = APIRequestBuilder.for_trades(
            "BTC/USDT",
            exchange="binance",
            market_type=MarketType.SPOT,
        )
        request = builder.limit(100).build()
        assert request.feature == DataFeature.TRADES
        assert request.symbol == "BTC/USDT"
        assert request.limit == 100

    def test_for_stream_single_symbol(self):
        """Test for_stream with single symbol."""
        builder = APIRequestBuilder.for_stream(
            DataFeature.OHLCV,
            "BTC/USDT",
            exchange="binance",
            market_type=MarketType.SPOT,
            timeframe=Timeframe.M1,
        )
        request = builder.only_closed(True).build()
        assert request.feature == DataFeature.OHLCV
        assert request.transport == TransportKind.WS
        assert request.symbol == "BTC/USDT"
        assert request.timeframe == Timeframe.M1
        assert request.only_closed is True

    def test_for_stream_multiple_symbols(self):
        """Test for_stream with multiple symbols."""
        builder = APIRequestBuilder.for_stream(
            DataFeature.TRADES,
            ["BTC/USDT", "ETH/USDT"],
            exchange="binance",
            market_type=MarketType.SPOT,
        )
        request = builder.build()
        assert request.feature == DataFeature.TRADES
        assert request.transport == TransportKind.WS
        assert request.symbols == ["BTC/USDT", "ETH/USDT"]


class TestAPIRequestFactory:
    """Test api_request factory function."""

    def test_api_request_minimal(self):
        """Test api_request with minimal parameters."""
        req = api_request(
            DataFeature.OHLCV,
            TransportKind.REST,
            symbol="BTC/USDT",
            timeframe=Timeframe.H1,
            exchange="binance",
            market_type=MarketType.SPOT,
        )
        assert req.feature == DataFeature.OHLCV
        assert req.symbol == "BTC/USDT"

    def test_api_request_with_defaults(self):
        """Test api_request with default resolution."""
        req = api_request(
            DataFeature.OHLCV,
            TransportKind.REST,
            symbol="BTC/USDT",
            timeframe=Timeframe.H1,
            default_exchange="binance",
            default_market_type=MarketType.SPOT,
        )
        assert req.exchange == "binance"
        assert req.market_type == MarketType.SPOT

    def test_api_request_overrides_defaults(self):
        """Test that explicit params override defaults."""
        req = api_request(
            DataFeature.OHLCV,
            TransportKind.REST,
            symbol="BTC/USDT",
            timeframe=Timeframe.H1,
            exchange="bybit",
            market_type=MarketType.FUTURES,
            default_exchange="binance",
            default_market_type=MarketType.SPOT,
        )
        assert req.exchange == "bybit"
        assert req.market_type == MarketType.FUTURES

    def test_api_request_extra_params(self):
        """Test api_request with extra parameters via kwargs."""
        req = api_request(
            DataFeature.SYMBOL_METADATA,
            TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
            quote_asset="USDT",
            use_cache=True,
        )
        assert req.extra_params["quote_asset"] == "USDT"
        assert req.extra_params["use_cache"] is True

    def test_api_request_missing_exchange(self):
        """Test api_request raises error when exchange is missing."""
        with pytest.raises(ValueError, match="exchange must be provided"):
            api_request(
                DataFeature.OHLCV,
                TransportKind.REST,
                symbol="BTC/USDT",
                timeframe=Timeframe.H1,
                # No exchange or default_exchange
            )

    def test_api_request_missing_market_type(self):
        """Test api_request raises error when market_type is missing."""
        with pytest.raises(ValueError, match="market_type must be provided"):
            api_request(
                DataFeature.OHLCV,
                TransportKind.REST,
                symbol="BTC/USDT",
                timeframe=Timeframe.H1,
                exchange="binance",
                # No market_type or default_market_type
            )


class TestAPIRequestBuilderCompatibility:
    """Test compatibility between APIRequestBuilder and DataRequestBuilder."""

    def test_api_builder_is_instance_of_base(self):
        """Test that APIRequestBuilder is a subclass."""
        builder = APIRequestBuilder()
        assert isinstance(builder, DataRequestBuilder)

    def test_api_builder_returns_same_type(self):
        """Test that method chaining returns APIRequestBuilder."""
        builder = APIRequestBuilder()
        result = builder.feature(DataFeature.OHLCV)
        assert isinstance(result, APIRequestBuilder)
        assert isinstance(result, DataRequestBuilder)

    def test_build_returns_data_request(self):
        """Test that build() returns DataRequest."""
        builder = APIRequestBuilder()
        request = (
            builder.feature(DataFeature.OHLCV)
            .transport(TransportKind.REST)
            .exchange("binance")
            .market_type(MarketType.SPOT)
            .symbol("BTC/USDT")
            .timeframe(Timeframe.H1)
            .build()
        )
        assert isinstance(request, DataRequest)
