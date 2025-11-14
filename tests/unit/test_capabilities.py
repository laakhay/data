"""Unit tests for capability primitives and registry."""

from datetime import datetime

from laakhay.data.core import (
    CapabilityError,
    CapabilityKey,
    CapabilityStatus,
    DataFeature,
    FallbackOption,
    InstrumentSpec,
    InstrumentType,
    MarketType,
    TransportKind,
    describe_exchange,
    list_features,
    supports,
)


def test_data_feature_enum():
    """Test DataFeature enum values."""
    assert DataFeature.OHLCV == "ohlcv"
    assert DataFeature.TRADES == "trades"
    assert DataFeature.LIQUIDATIONS == "liquidations"
    assert str(DataFeature.ORDER_BOOK) == "order_book"


def test_transport_kind_enum():
    """Test TransportKind enum values."""
    assert TransportKind.REST == "rest"
    assert TransportKind.WS == "ws"
    assert str(TransportKind.REST) == "rest"


def test_instrument_type_enum():
    """Test InstrumentType enum values."""
    assert InstrumentType.SPOT == "spot"
    assert InstrumentType.PERPETUAL == "perpetual"
    assert InstrumentType.FUTURE == "future"
    assert str(InstrumentType.OPTION) == "option"


def test_instrument_spec():
    """Test InstrumentSpec dataclass."""
    spec = InstrumentSpec(
        base="BTC",
        quote="USDT",
        instrument_type=InstrumentType.SPOT,
    )
    assert spec.base == "BTC"
    assert spec.quote == "USDT"
    assert spec.instrument_type == InstrumentType.SPOT
    assert spec.expiry is None
    assert spec.strike is None

    # Test with expiry and strike
    expiry = datetime(2024, 6, 28)
    spec2 = InstrumentSpec(
        base="BTC",
        quote="USD",
        instrument_type=InstrumentType.OPTION,
        expiry=expiry,
        strike=35000.0,
    )
    assert spec2.expiry == expiry
    assert spec2.strike == 35000.0
    assert "BTC/USD" in str(spec2)


def test_capability_key():
    """Test CapabilityKey dataclass."""
    key = CapabilityKey(
        exchange="binance",
        market_type=MarketType.SPOT,
        instrument_type=InstrumentType.SPOT,
        feature=DataFeature.OHLCV,
        transport=TransportKind.REST,
    )
    assert key.exchange == "binance"
    assert key.market_type == MarketType.SPOT
    assert key.feature == DataFeature.OHLCV
    assert key.transport == TransportKind.REST
    assert key.stream_variant is None

    # Test with stream variant
    key2 = CapabilityKey(
        exchange="binance",
        market_type=MarketType.FUTURES,
        instrument_type=InstrumentType.PERPETUAL,
        feature=DataFeature.LIQUIDATIONS,
        transport=TransportKind.WS,
        stream_variant="global",
    )
    assert key2.stream_variant == "global"


def test_capability_status():
    """Test CapabilityStatus dataclass."""
    status = CapabilityStatus(
        supported=True,
        reason=None,
        source="static",
    )
    assert status.supported is True
    assert status.reason is None
    assert status.source == "static"
    assert status.constraints == {}
    assert status.recommendations == []
    assert status.stream_metadata == {}

    # Test with all fields
    fallback = FallbackOption(
        exchange="bybit",
        market_type=MarketType.FUTURES,
        instrument_type=InstrumentType.PERPETUAL,
        feature=DataFeature.LIQUIDATIONS,
        transport=TransportKind.WS,
        note="Try Bybit instead",
    )
    status2 = CapabilityStatus(
        supported=False,
        reason="Not supported on this exchange",
        constraints={"max_depth": 500},
        recommendations=[fallback],
        source="runtime",
        last_verified_at=datetime.now(),
        stream_metadata={"symbol_scope": "symbol"},
    )
    assert status2.supported is False
    assert len(status2.recommendations) == 1
    assert status2.stream_metadata["symbol_scope"] == "symbol"


def test_fallback_option():
    """Test FallbackOption dataclass."""
    fallback = FallbackOption(
        exchange="bybit",
        market_type=MarketType.FUTURES,
        instrument_type=InstrumentType.PERPETUAL,
        feature=DataFeature.OHLCV,
        transport=TransportKind.REST,
        note="Alternative exchange",
    )
    assert fallback.exchange == "bybit"
    assert fallback.market_type == MarketType.FUTURES
    assert fallback.note == "Alternative exchange"


def test_capability_error():
    """Test CapabilityError exception."""
    key = CapabilityKey(
        exchange="coinbase",
        market_type=MarketType.SPOT,
        instrument_type=InstrumentType.SPOT,
        feature=DataFeature.LIQUIDATIONS,
        transport=TransportKind.WS,
    )
    status = CapabilityStatus(
        supported=False,
        reason="Liquidations are only available for futures/perpetual markets",
        source="static",
    )
    error = CapabilityError(
        "Capability not supported",
        key=key,
        status=status,
    )
    assert error.key == key
    assert error.status == status
    assert str(error) == "Capability not supported"


def test_supports_function():
    """Test supports() function."""
    # Test supported capability
    status = supports(
        feature=DataFeature.OHLCV,
        transport=TransportKind.REST,
        exchange="binance",
        market_type=MarketType.SPOT,
        instrument_type=InstrumentType.SPOT,
    )
    assert status.supported is True
    assert status.source == "static"

    # Test unsupported capability (liquidations on spot)
    status2 = supports(
        feature=DataFeature.LIQUIDATIONS,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        instrument_type=InstrumentType.SPOT,
    )
    assert status2.supported is False
    assert "futures" in status2.reason.lower() or "perpetual" in status2.reason.lower()

    # Test non-existent exchange
    status3 = supports(
        feature=DataFeature.OHLCV,
        transport=TransportKind.REST,
        exchange="nonexistent",
        market_type=MarketType.SPOT,
        instrument_type=InstrumentType.SPOT,
    )
    assert status3.supported is False
    assert "not found" in status3.reason.lower()


def test_describe_exchange():
    """Test describe_exchange() function."""
    capability = describe_exchange("binance")
    assert capability is not None
    assert capability["name"] == "binance"
    assert "spot" in capability["supported_market_types"]

    # Test non-existent exchange
    assert describe_exchange("nonexistent") is None


def test_list_features():
    """Test list_features() function."""
    features = list_features(
        exchange="binance",
        market_type=MarketType.SPOT,
        instrument_type=InstrumentType.SPOT,
    )
    assert len(features) > 0
    assert DataFeature.OHLCV in features
    assert DataFeature.TRADES in features

    # Check that each feature has transport capabilities
    ohlcv_caps = features[DataFeature.OHLCV]
    assert TransportKind.REST in ohlcv_caps
    assert TransportKind.WS in ohlcv_caps

    # Test non-existent exchange
    features2 = list_features(
        exchange="nonexistent",
        market_type=MarketType.SPOT,
        instrument_type=InstrumentType.SPOT,
    )
    assert len(features2) == 0


def test_supports_futures_features():
    """Test that futures-specific features work correctly."""
    # Test liquidations on futures/perpetual
    status = supports(
        feature=DataFeature.LIQUIDATIONS,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.FUTURES,
        instrument_type=InstrumentType.PERPETUAL,
    )
    assert status.supported is True

    # Test funding rates on perpetual
    status2 = supports(
        feature=DataFeature.FUNDING_RATE,
        transport=TransportKind.REST,
        exchange="bybit",
        market_type=MarketType.FUTURES,
        instrument_type=InstrumentType.PERPETUAL,
    )
    assert status2.supported is True

    # Test that spot doesn't support futures features
    status3 = supports(
        feature=DataFeature.FUNDING_RATE,
        transport=TransportKind.REST,
        exchange="binance",
        market_type=MarketType.SPOT,
        instrument_type=InstrumentType.SPOT,
    )
    assert status3.supported is False
