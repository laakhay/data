"""Precise unit tests for DataRequest and DataRequestBuilder.

Tests focus on validation logic, edge cases, and builder pattern.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from laakhay.data.core.enums import (
    DataFeature,
    InstrumentType,
    MarketType,
    Timeframe,
    TransportKind,
)
from laakhay.data.core.request import DataRequest, DataRequestBuilder, request


class TestDataRequestValidation:
    """Test DataRequest validation logic."""

    def test_valid_request_with_symbol(self):
        """Test valid request with single symbol."""
        req = DataRequest(
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
            symbol="BTC/USDT",
            timeframe=Timeframe.H1,
        )
        assert req.symbol == "BTC/USDT"
        assert req.feature == DataFeature.OHLCV

    def test_valid_request_with_symbols(self):
        """Test valid request with multiple symbols."""
        req = DataRequest(
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
            symbols=["BTC/USDT", "ETH/USDT"],
            timeframe=Timeframe.H1,
        )
        assert req.symbols == ["BTC/USDT", "ETH/USDT"]

    def test_valid_request_liquidations_no_symbol(self):
        """Test liquidations feature doesn't require symbol."""
        req = DataRequest(
            feature=DataFeature.LIQUIDATIONS,
            transport=TransportKind.WS,
            exchange="binance",
            market_type=MarketType.FUTURES,
        )
        assert req.symbol is None
        assert req.symbols is None

    def test_valid_request_symbol_metadata_no_symbol(self):
        """Test symbol metadata feature doesn't require symbol."""
        req = DataRequest(
            feature=DataFeature.SYMBOL_METADATA,
            transport=TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
        )
        assert req.symbol is None
        assert req.symbols is None

    def test_invalid_request_no_symbol(self):
        """Test request without symbol raises error."""
        with pytest.raises(ValueError, match="Either 'symbol' or 'symbols' must be provided"):
            DataRequest(
                feature=DataFeature.OHLCV,
                transport=TransportKind.REST,
                exchange="binance",
                market_type=MarketType.SPOT,
                timeframe=Timeframe.H1,
            )

    def test_invalid_request_both_symbol_and_symbols(self):
        """Test request with both symbol and symbols raises error."""
        with pytest.raises(ValueError, match="Cannot specify both 'symbol' and 'symbols'"):
            DataRequest(
                feature=DataFeature.OHLCV,
                transport=TransportKind.REST,
                exchange="binance",
                market_type=MarketType.SPOT,
                symbol="BTC/USDT",
                symbols=["ETH/USDT"],
                timeframe=Timeframe.H1,
            )

    def test_invalid_ohlcv_rest_no_timeframe(self):
        """Test OHLCV REST request without timeframe raises error."""
        with pytest.raises(ValueError, match="timeframe is required for OHLCV REST requests"):
            DataRequest(
                feature=DataFeature.OHLCV,
                transport=TransportKind.REST,
                exchange="binance",
                market_type=MarketType.SPOT,
                symbol="BTC/USDT",
            )

    def test_valid_ohlcv_ws_no_timeframe(self):
        """Test OHLCV WS request doesn't require timeframe."""
        req = DataRequest(
            feature=DataFeature.OHLCV,
            transport=TransportKind.WS,
            exchange="binance",
            market_type=MarketType.SPOT,
            symbol="BTC/USDT",
        )
        assert req.timeframe is None

    def test_order_book_default_depth(self):
        """Test order book request gets default depth."""
        req = DataRequest(
            feature=DataFeature.ORDER_BOOK,
            transport=TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
            symbol="BTC/USDT",
        )
        assert req.depth == 100

    def test_order_book_custom_depth(self):
        """Test order book request with custom depth."""
        req = DataRequest(
            feature=DataFeature.ORDER_BOOK,
            transport=TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
            symbol="BTC/USDT",
            depth=50,
        )
        assert req.depth == 50


class TestDataRequestBuilder:
    """Test DataRequestBuilder fluent API."""

    def test_builder_minimal_request(self):
        """Test building minimal valid request."""
        req = (
            DataRequestBuilder()
            .feature(DataFeature.OHLCV)
            .transport(TransportKind.REST)
            .exchange("binance")
            .market_type(MarketType.SPOT)
            .symbol("BTC/USDT")
            .timeframe(Timeframe.H1)
            .build()
        )
        assert req.feature == DataFeature.OHLCV
        assert req.symbol == "BTC/USDT"

    def test_builder_all_parameters(self):
        """Test builder with all parameters."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 2)
        req = (
            DataRequestBuilder()
            .feature(DataFeature.OHLCV)
            .transport(TransportKind.REST)
            .exchange("binance")
            .market_type(MarketType.SPOT)
            .instrument_type(InstrumentType.SPOT)
            .symbol("BTC/USDT")
            .timeframe(Timeframe.H1)
            .start_time(start)
            .end_time(end)
            .limit(100)
            .max_chunks(5)
            .build()
        )
        assert req.start_time == start
        assert req.end_time == end
        assert req.limit == 100
        assert req.max_chunks == 5

    def test_builder_multiple_symbols(self):
        """Test builder with multiple symbols."""
        req = (
            DataRequestBuilder()
            .feature(DataFeature.OHLCV)
            .transport(TransportKind.REST)
            .exchange("binance")
            .market_type(MarketType.SPOT)
            .symbols(["BTC/USDT", "ETH/USDT"])
            .timeframe(Timeframe.H1)
            .build()
        )
        assert req.symbols == ["BTC/USDT", "ETH/USDT"]
        assert req.symbol is None

    def test_builder_symbol_overwrites_symbols(self):
        """Test setting symbol clears symbols."""
        builder = (
            DataRequestBuilder()
            .feature(DataFeature.OHLCV)
            .transport(TransportKind.REST)
            .exchange("binance")
            .market_type(MarketType.SPOT)
            .symbols(["BTC/USDT", "ETH/USDT"])
        )
        assert builder._symbols == ["BTC/USDT", "ETH/USDT"]
        builder.symbol("BTC/USDT")
        assert builder._symbol == "BTC/USDT"
        assert builder._symbols is None

    def test_builder_symbols_overwrites_symbol(self):
        """Test setting symbols clears symbol."""
        builder = (
            DataRequestBuilder()
            .feature(DataFeature.OHLCV)
            .transport(TransportKind.REST)
            .exchange("binance")
            .market_type(MarketType.SPOT)
            .symbol("BTC/USDT")
        )
        assert builder._symbol == "BTC/USDT"
        builder.symbols(["ETH/USDT"])
        assert builder._symbols == ["ETH/USDT"]
        assert builder._symbol is None

    def test_builder_streaming_options(self):
        """Test builder with streaming options."""
        req = (
            DataRequestBuilder()
            .feature(DataFeature.OHLCV)
            .transport(TransportKind.WS)
            .exchange("binance")
            .market_type(MarketType.SPOT)
            .symbol("BTC/USDT")
            .timeframe(Timeframe.M1)
            .only_closed(True)
            .throttle_ms(100)
            .dedupe_same_candle(True)
            .build()
        )
        assert req.only_closed is True
        assert req.throttle_ms == 100
        assert req.dedupe_same_candle is True

    def test_builder_futures_features(self):
        """Test builder with futures-specific features."""
        req = (
            DataRequestBuilder()
            .feature(DataFeature.OPEN_INTEREST)
            .transport(TransportKind.REST)
            .exchange("binance")
            .market_type(MarketType.FUTURES)
            .instrument_type(InstrumentType.PERPETUAL)
            .symbol("BTC/USDT")
            .period("5m")
            .historical(True)
            .build()
        )
        assert req.period == "5m"
        assert req.historical is True

    def test_builder_extra_params(self):
        """Test builder with extra parameters."""
        req = (
            DataRequestBuilder()
            .feature(DataFeature.SYMBOL_METADATA)
            .transport(TransportKind.REST)
            .exchange("binance")
            .market_type(MarketType.SPOT)
            .extra_param("quote_asset", "USDT")
            .extra_param("use_cache", True)
            .build()
        )
        assert req.extra_params["quote_asset"] == "USDT"
        assert req.extra_params["use_cache"] is True

    def test_builder_missing_feature(self):
        """Test builder raises error when feature is missing."""
        with pytest.raises(ValueError, match="feature is required"):
            (
                DataRequestBuilder()
                .transport(TransportKind.REST)
                .exchange("binance")
                .market_type(MarketType.SPOT)
                .symbol("BTC/USDT")
                .build()
            )

    def test_builder_missing_transport(self):
        """Test builder raises error when transport is missing."""
        with pytest.raises(ValueError, match="transport is required"):
            (
                DataRequestBuilder()
                .feature(DataFeature.OHLCV)
                .exchange("binance")
                .market_type(MarketType.SPOT)
                .symbol("BTC/USDT")
                .timeframe(Timeframe.H1)
                .build()
            )

    def test_builder_missing_exchange(self):
        """Test builder raises error when exchange is missing."""
        with pytest.raises(ValueError, match="exchange is required"):
            (
                DataRequestBuilder()
                .feature(DataFeature.OHLCV)
                .transport(TransportKind.REST)
                .market_type(MarketType.SPOT)
                .symbol("BTC/USDT")
                .timeframe(Timeframe.H1)
                .build()
            )

    def test_builder_missing_market_type(self):
        """Test builder raises error when market_type is missing."""
        with pytest.raises(ValueError, match="market_type is required"):
            (
                DataRequestBuilder()
                .feature(DataFeature.OHLCV)
                .transport(TransportKind.REST)
                .exchange("binance")
                .symbol("BTC/USDT")
                .timeframe(Timeframe.H1)
                .build()
            )


class TestRequestFactory:
    """Test request() factory function."""

    def test_factory_minimal(self):
        """Test factory function with minimal parameters."""
        req = request(
            DataFeature.OHLCV,
            TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
            symbol="BTC/USDT",
            timeframe=Timeframe.H1,
        )
        assert req.feature == DataFeature.OHLCV
        assert req.symbol == "BTC/USDT"

    def test_factory_with_kwargs(self):
        """Test factory function with kwargs."""
        req = request(
            DataFeature.OHLCV,
            TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
            symbol="BTC/USDT",
            timeframe=Timeframe.H1,
            limit=100,
            start_time=datetime(2024, 1, 1),
        )
        assert req.limit == 100
        assert req.start_time == datetime(2024, 1, 1)

    def test_factory_with_extra_params(self):
        """Test factory function with extra params via kwargs."""
        req = request(
            DataFeature.SYMBOL_METADATA,
            TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
            quote_asset="USDT",
            use_cache=False,
        )
        assert req.extra_params["quote_asset"] == "USDT"
        assert req.extra_params["use_cache"] is False

    def test_factory_multiple_symbols(self):
        """Test factory function with multiple symbols."""
        req = request(
            DataFeature.OHLCV,
            TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
            symbols=["BTC/USDT", "ETH/USDT"],
            timeframe=Timeframe.H1,
        )
        assert req.symbols == ["BTC/USDT", "ETH/USDT"]

