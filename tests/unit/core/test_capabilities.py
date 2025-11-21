"""Precise unit tests for capability system.

Tests focus on actual behavior, edge cases, and business logic.
Trivial enum/dataclass tests removed - focus on meaningful functionality.
"""

from datetime import datetime

import pytest

from laakhay.data.capability.registry import rebuild_registry_from_discovery
from laakhay.data.core import (
    CapabilityError,
    CapabilityStatus,
    DataFeature,
    FallbackOption,
    InstrumentSpec,
    InstrumentType,
    MarketType,
    TransportKind,
    describe_exchange,
    get_all_capabilities,
    get_all_exchanges,
    get_all_supported_market_types,
    get_exchange_capability,
    get_supported_data_types,
    get_supported_market_types,
    get_supported_timeframes,
    is_exchange_supported,
    list_features,
    supports,
    supports_data_type,
    supports_market_type,
)
from laakhay.data.registration import register_all


@pytest.fixture(autouse=True)
def setup_capability_registry():
    """Register providers and rebuild capability registry for each test."""
    from laakhay.data.runtime.provider_registry import get_provider_registry

    registry = get_provider_registry()
    # Clear any existing registrations to ensure clean state
    # Note: This is safe because we're in a test environment
    if registry.list_exchanges():
        # Clear registrations by creating a fresh registry instance
        # We can't easily clear the singleton, so we'll just ensure providers are registered
        pass
    # Register all providers if not already registered
    if not registry.list_exchanges():
        register_all(registry)
    rebuild_registry_from_discovery()


def test_instrument_spec_with_optional_fields():
    """Test InstrumentSpec with optional fields (expiry, strike)."""
    expiry = datetime(2024, 6, 28)
    spec = InstrumentSpec(
        base="BTC",
        quote="USD",
        instrument_type=InstrumentType.OPTION,
        expiry=expiry,
        strike=35000.0,
    )
    assert spec.expiry == expiry
    assert spec.strike == 35000.0
    assert "BTC/USD" in str(spec)


def test_supports_function():
    """Test supports() function with various scenarios."""
    # Test supported capability
    status = supports(
        feature=DataFeature.OHLCV,
        transport=TransportKind.REST,
        exchange="binance",
        market_type=MarketType.SPOT,
        instrument_type=InstrumentType.SPOT,
    )
    assert status.supported is True

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


def test_describe_exchange():
    """Test describe_exchange() function."""
    capability = describe_exchange("binance")
    assert capability is not None
    assert capability["name"] == "binance"
    assert "spot" in capability["supported_market_types"]

    # Test non-existent exchange
    assert describe_exchange("nonexistent") is None

    # Test case-insensitive
    capability2 = describe_exchange("BINANCE")
    assert capability2 is not None


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


def test_get_all_exchanges():
    """Test get_all_exchanges() returns all supported exchanges."""
    exchanges = get_all_exchanges()
    assert len(exchanges) > 0
    assert "binance" in exchanges
    assert "bybit" in exchanges
    assert isinstance(exchanges, list)


def test_get_exchange_capability():
    """Test get_exchange_capability() with various inputs."""
    # Test existing exchange
    capability = get_exchange_capability("binance")
    assert capability is not None
    assert capability["name"] == "binance"

    # Test non-existent exchange
    assert get_exchange_capability("nonexistent") is None

    # Test case-insensitive
    capability2 = get_exchange_capability("BINANCE")
    assert capability2 is not None


def test_get_all_capabilities():
    """Test get_all_capabilities() returns all exchange capabilities."""
    all_caps = get_all_capabilities()
    assert len(all_caps) > 0
    assert "binance" in all_caps
    assert isinstance(all_caps, dict)
    # Should be a copy, not the original
    all_caps["test"] = "value"
    all_caps2 = get_all_capabilities()
    assert "test" not in all_caps2


def test_get_supported_market_types():
    """Test get_supported_market_types() for various exchanges."""
    # Test exchange with both spot and futures
    market_types = get_supported_market_types("binance")
    assert market_types is not None
    assert "spot" in market_types
    assert "futures" in market_types

    # Test exchange with only spot
    market_types2 = get_supported_market_types("coinbase")
    assert market_types2 is not None
    assert "spot" in market_types2

    # Test non-existent exchange
    assert get_supported_market_types("nonexistent") is None


def test_get_supported_timeframes():
    """Test get_supported_timeframes() function."""
    # Test without exchange (returns all)
    timeframes = get_supported_timeframes()
    assert len(timeframes) > 0
    assert "1m" in timeframes
    assert "1h" in timeframes

    # Test with exchange (currently same for all)
    timeframes2 = get_supported_timeframes("binance")
    assert len(timeframes2) > 0


def test_get_supported_data_types():
    """Test get_supported_data_types() function."""
    data_types = get_supported_data_types("binance")
    assert data_types is not None
    assert "ohlcv" in data_types
    assert "trades" in data_types
    assert data_types["ohlcv"]["rest"] is True
    assert data_types["ohlcv"]["ws"] is True

    # Test non-existent exchange
    assert get_supported_data_types("nonexistent") is None


def test_get_all_supported_market_types():
    """Test get_all_supported_market_types() returns unique market types."""
    market_types = get_all_supported_market_types()
    assert len(market_types) > 0
    assert "spot" in market_types
    assert "futures" in market_types
    assert isinstance(market_types, list)
    # Should be sorted
    assert market_types == sorted(market_types)


def test_is_exchange_supported():
    """Test is_exchange_supported() function."""
    assert is_exchange_supported("binance") is True
    assert is_exchange_supported("bybit") is True
    assert is_exchange_supported("nonexistent") is False
    # Test case-insensitive
    assert is_exchange_supported("BINANCE") is True


def test_supports_market_type():
    """Test supports_market_type() function."""
    assert supports_market_type("binance", "spot") is True
    assert supports_market_type("binance", "futures") is True
    assert supports_market_type("coinbase", "spot") is True
    assert supports_market_type("coinbase", "futures") is False
    assert supports_market_type("nonexistent", "spot") is False


def test_supports_data_type():
    """Test supports_data_type() function."""
    assert supports_data_type("binance", "ohlcv", "rest") is True
    assert supports_data_type("binance", "ohlcv", "ws") is True
    assert supports_data_type("binance", "nonexistent", "rest") is False
    assert supports_data_type("nonexistent", "ohlcv", "rest") is False

    # Test case-insensitive exchange
    assert supports_data_type("BINANCE", "ohlcv", "rest") is True


def test_capability_status_with_recommendations():
    """Test CapabilityStatus with recommendations (meaningful behavior)."""
    fallback = FallbackOption(
        exchange="bybit",
        market_type=MarketType.FUTURES,
        instrument_type=InstrumentType.PERPETUAL,
        feature=DataFeature.LIQUIDATIONS,
        transport=TransportKind.WS,
        note="Try Bybit instead",
    )
    status = CapabilityStatus(
        supported=False,
        reason="Not supported on this exchange",
        constraints={"max_depth": 500},
        recommendations=[fallback],
        last_verified_at=datetime.now(),
        stream_metadata={"symbol_scope": "symbol"},
    )
    assert status.supported is False
    assert len(status.recommendations) == 1
    assert status.recommendations[0].exchange == "bybit"
    assert status.stream_metadata["symbol_scope"] == "symbol"


def test_capability_error_with_context():
    """Test CapabilityError with full context (meaningful behavior)."""
    from laakhay.data.core import CapabilityKey

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
    )
    error = CapabilityError(
        "Capability not supported",
        key=key,
        status=status,
        recommendations=[
            FallbackOption(
                exchange="binance",
                market_type=MarketType.FUTURES,
                instrument_type=InstrumentType.PERPETUAL,
                feature=DataFeature.LIQUIDATIONS,
                transport=TransportKind.WS,
                note="Use Binance futures",
            )
        ],
    )
    assert error.key == key
    assert error.status == status
    assert len(error.recommendations) == 1
    assert str(error) == "Capability not supported"
