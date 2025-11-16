"""Unit tests for URM protocol and registry."""

import pytest

from laakhay.data.core import (
    InstrumentSpec,
    InstrumentType,
    MarketType,
    SymbolResolutionError,
    URMRegistry,
    parse_urm_id,
    spec_to_urm_id,
    validate_urm_id,
)


class MockMapper:
    """Mock mapper for testing."""

    def __init__(self, exchange_name: str) -> None:
        self.exchange_name = exchange_name
        self._symbols: dict[str, InstrumentSpec] = {}
        # Use tuple key instead of InstrumentSpec directly (since it's not hashable)
        self._specs: dict[tuple[str, str, str], str] = {}

    def add_mapping(self, symbol: str, spec: InstrumentSpec) -> None:
        """Add a symbol -> spec mapping."""
        self._symbols[symbol.upper()] = spec
        # Use tuple key for reverse lookup
        key = (spec.base, spec.quote, spec.instrument_type.value)
        self._specs[key] = symbol

    def to_spec(
        self,
        exchange_symbol: str,
        *,
        market_type: MarketType,
    ) -> InstrumentSpec:
        """Convert symbol to spec."""
        symbol_upper = exchange_symbol.upper()
        if symbol_upper not in self._symbols:
            raise SymbolResolutionError(
                f"Symbol '{exchange_symbol}' not found",
                exchange=self.exchange_name,
                value=exchange_symbol,
                market_type=market_type,
            )
        return self._symbols[symbol_upper]

    def to_exchange_symbol(
        self,
        spec: InstrumentSpec,
        *,
        market_type: MarketType,
    ) -> str:
        """Convert spec to symbol."""
        key = (spec.base, spec.quote, spec.instrument_type.value)
        if key not in self._specs:
            raise SymbolResolutionError(
                f"Spec '{spec}' not found",
                exchange=self.exchange_name,
            )
        return self._specs[key]


def test_urm_registry_register():
    """Test registering a mapper."""
    registry = URMRegistry()
    mapper = MockMapper("test")

    registry.register("test", mapper)
    assert "test" in registry._mappers


def test_urm_registry_unregister():
    """Test unregistering a mapper."""
    registry = URMRegistry()
    mapper = MockMapper("test")

    registry.register("test", mapper)
    registry.unregister("test")
    assert "test" not in registry._mappers


def test_urm_registry_urm_to_spec():
    """Test converting exchange symbol to spec."""
    registry = URMRegistry()
    mapper = MockMapper("binance")
    spec = InstrumentSpec(
        base="BTC",
        quote="USDT",
        instrument_type=InstrumentType.SPOT,
    )
    mapper.add_mapping("BTCUSDT", spec)

    registry.register("binance", mapper)

    result = registry.urm_to_spec("BTCUSDT", exchange="binance", market_type=MarketType.SPOT)
    assert result.base == "BTC"
    assert result.quote == "USDT"
    assert result.instrument_type == InstrumentType.SPOT


def test_urm_registry_urm_to_spec_cached():
    """Test that results are cached."""
    registry = URMRegistry()
    mapper = MockMapper("binance")
    spec = InstrumentSpec(
        base="BTC",
        quote="USDT",
        instrument_type=InstrumentType.SPOT,
    )
    mapper.add_mapping("BTCUSDT", spec)

    registry.register("binance", mapper)

    # First call
    result1 = registry.urm_to_spec("BTCUSDT", exchange="binance", market_type=MarketType.SPOT)
    # Second call should use cache
    result2 = registry.urm_to_spec("BTCUSDT", exchange="binance", market_type=MarketType.SPOT)

    assert result1 == result2
    assert ("binance", "BTCUSDT", MarketType.SPOT) in registry._cache


def test_urm_registry_urm_to_exchange_symbol():
    """Test converting spec to exchange symbol."""
    registry = URMRegistry()
    mapper = MockMapper("binance")
    spec = InstrumentSpec(
        base="BTC",
        quote="USDT",
        instrument_type=InstrumentType.SPOT,
    )
    mapper.add_mapping("BTCUSDT", spec)

    registry.register("binance", mapper)

    result = registry.urm_to_exchange_symbol(spec, exchange="binance", market_type=MarketType.SPOT)
    assert result == "BTCUSDT"


def test_urm_registry_unregistered_exchange():
    """Test error when exchange is not registered."""
    registry = URMRegistry()

    with pytest.raises(SymbolResolutionError) as exc_info:
        registry.urm_to_spec("BTCUSDT", exchange="nonexistent", market_type=MarketType.SPOT)

    assert "No mapper registered" in str(exc_info.value)
    assert exc_info.value.exchange == "nonexistent"


def test_urm_registry_round_trip():
    """Test round-trip conversion."""
    registry = URMRegistry()
    mapper = MockMapper("binance")
    spec = InstrumentSpec(
        base="BTC",
        quote="USDT",
        instrument_type=InstrumentType.SPOT,
    )
    mapper.add_mapping("BTCUSDT", spec)

    registry.register("binance", mapper)

    # Exchange symbol -> spec -> exchange symbol
    spec_result = registry.urm_to_spec("BTCUSDT", exchange="binance", market_type=MarketType.SPOT)
    symbol_result = registry.urm_to_exchange_symbol(
        spec_result, exchange="binance", market_type=MarketType.SPOT
    )

    assert symbol_result == "BTCUSDT"


def test_urm_registry_clear_cache():
    """Test clearing cache."""
    registry = URMRegistry()
    mapper = MockMapper("binance")
    spec = InstrumentSpec(
        base="BTC",
        quote="USDT",
        instrument_type=InstrumentType.SPOT,
    )
    mapper.add_mapping("BTCUSDT", spec)

    registry.register("binance", mapper)
    registry.urm_to_spec("BTCUSDT", exchange="binance", market_type=MarketType.SPOT)

    assert len(registry._cache) > 0

    registry.clear_cache("binance")
    assert len(registry._cache) == 0


def test_urm_registry_clear_all_cache():
    """Test clearing all caches."""
    registry = URMRegistry()
    mapper1 = MockMapper("binance")
    mapper2 = MockMapper("kraken")

    spec1 = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.SPOT)
    spec2 = InstrumentSpec(base="BTC", quote="USD", instrument_type=InstrumentType.SPOT)

    mapper1.add_mapping("BTCUSDT", spec1)
    mapper2.add_mapping("XBT/USD", spec2)

    registry.register("binance", mapper1)
    registry.register("kraken", mapper2)

    registry.urm_to_spec("BTCUSDT", exchange="binance", market_type=MarketType.SPOT)
    registry.urm_to_spec("XBT/USD", exchange="kraken", market_type=MarketType.SPOT)

    assert len(registry._cache) == 2

    registry.clear_cache()
    assert len(registry._cache) == 0


def test_urm_registry_unregister_clears_cache():
    """Test that unregistering clears cache."""
    registry = URMRegistry()
    mapper = MockMapper("binance")
    spec = InstrumentSpec(
        base="BTC",
        quote="USDT",
        instrument_type=InstrumentType.SPOT,
    )
    mapper.add_mapping("BTCUSDT", spec)

    registry.register("binance", mapper)
    registry.urm_to_spec("BTCUSDT", exchange="binance", market_type=MarketType.SPOT)

    assert len(registry._cache) > 0

    registry.unregister("binance")
    assert len(registry._cache) == 0


def test_get_urm_registry_singleton():
    """Test that get_urm_registry returns singleton."""
    from laakhay.data.core.urm import get_urm_registry

    registry1 = get_urm_registry()
    registry2 = get_urm_registry()

    assert registry1 is registry2


def test_parse_urm_id():
    """Test parsing URM IDs."""
    # Spot
    spec = parse_urm_id("urm://binance:btc/usdt:spot")
    assert spec.base == "BTC"
    assert spec.quote == "USDT"
    assert spec.instrument_type == InstrumentType.SPOT
    assert spec.metadata.get("exchange") == "binance"

    # Perpetual with wildcard
    spec = parse_urm_id("urm://*:btc/usdt:perpetual")
    assert spec.base == "BTC"
    assert spec.quote == "USDT"
    assert spec.instrument_type == InstrumentType.PERPETUAL

    # Future with expiry
    spec = parse_urm_id("urm://okx:btc/usdt:future:20240329")
    assert spec.base == "BTC"
    assert spec.quote == "USDT"
    assert spec.instrument_type == InstrumentType.FUTURE
    assert spec.expiry is not None
    assert spec.expiry.year == 2024
    assert spec.expiry.month == 3
    assert spec.expiry.day == 29


def test_parse_urm_id_invalid_format():
    """Test parsing invalid URM IDs."""
    with pytest.raises(SymbolResolutionError):
        parse_urm_id("invalid-format")

    with pytest.raises(SymbolResolutionError):
        parse_urm_id("urm://binance:btc/usdt")  # Missing instrument_type

    with pytest.raises(SymbolResolutionError):
        parse_urm_id("urm://binance:btc/usdt:invalid")  # Invalid instrument type


def test_spec_to_urm_id():
    """Test converting spec to URM ID."""
    # Spot
    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.SPOT)
    urm_id = spec_to_urm_id(spec, exchange="binance")
    assert urm_id == "urm://binance:btc/usdt:spot"

    # Perpetual without exchange
    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.PERPETUAL)
    urm_id = spec_to_urm_id(spec)
    assert urm_id == "urm://*:btc/usdt:perpetual"

    # Future with expiry
    from datetime import datetime

    spec = InstrumentSpec(
        base="BTC",
        quote="USDT",
        instrument_type=InstrumentType.FUTURE,
        expiry=datetime(2024, 3, 29),
    )
    urm_id = spec_to_urm_id(spec, exchange="okx")
    assert urm_id == "urm://okx:btc/usdt:future:20240329"


def test_validate_urm_id():
    """Test URM ID validation."""
    assert validate_urm_id("urm://binance:btc/usdt:spot") is True
    assert validate_urm_id("urm://*:btc/usdt:perpetual") is True
    assert validate_urm_id("invalid") is False
    assert validate_urm_id("urm://binance:btc/usdt") is False


def test_urm_registry_mapper_exception_handling():
    """Test that mapper exceptions are wrapped in SymbolResolutionError."""
    registry = URMRegistry()
    mapper = MockMapper("binance")

    # Make mapper raise an exception
    def failing_to_spec(exchange_symbol, *, market_type):
        raise ValueError("Mapper error")

    mapper.to_spec = failing_to_spec
    registry.register("binance", mapper)

    with pytest.raises(SymbolResolutionError) as exc_info:
        registry.urm_to_spec("INVALID", exchange="binance", market_type=MarketType.SPOT)

    assert "Failed to resolve symbol" in str(exc_info.value)
    assert exc_info.value.exchange == "binance"


def test_urm_registry_exchange_symbol_exception_handling():
    """Test that mapper exceptions in to_exchange_symbol are wrapped."""
    registry = URMRegistry()
    mapper = MockMapper("binance")
    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.SPOT)

    # Make mapper raise an exception
    def failing_to_exchange_symbol(spec, *, market_type):
        raise ValueError("Conversion error")

    mapper.to_exchange_symbol = failing_to_exchange_symbol
    registry.register("binance", mapper)

    with pytest.raises(SymbolResolutionError) as exc_info:
        registry.urm_to_exchange_symbol(spec, exchange="binance", market_type=MarketType.SPOT)

    assert "Failed to convert spec" in str(exc_info.value)
    assert exc_info.value.exchange == "binance"


def test_urm_registry_urm_to_exchange_symbol_unregistered():
    """Test error when exchange not registered for urm_to_exchange_symbol."""
    registry = URMRegistry()
    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.SPOT)

    with pytest.raises(SymbolResolutionError, match="No mapper registered"):
        registry.urm_to_exchange_symbol(spec, exchange="nonexistent", market_type=MarketType.SPOT)


def test_urm_registry_cache_invalid_missing_timestamp():
    """Test cache validation when timestamp is missing."""
    registry = URMRegistry()
    cache_key = ("binance", "BTCUSDT", MarketType.SPOT)

    # Cache entry without timestamp
    registry._cache[cache_key] = InstrumentSpec(
        base="BTC", quote="USDT", instrument_type=InstrumentType.SPOT
    )

    # Should return False (cache invalid)
    assert registry._is_cache_valid(cache_key) is False


def test_parse_urm_id_invalid_exchange():
    """Test parsing URM ID with invalid exchange name."""
    with pytest.raises(SymbolResolutionError, match="Invalid exchange"):
        parse_urm_id("urm://invalid-exchange!:btc/usdt:spot")


def test_parse_urm_id_option_basic():
    """Test parsing URM ID with option instrument type."""
    spec = parse_urm_id("urm://deribit:btc/usd:option")
    assert spec.base == "BTC"
    assert spec.quote == "USD"
    assert spec.instrument_type == InstrumentType.OPTION


def test_spec_to_urm_id_with_option():
    """Test converting spec with option to URM ID."""
    from datetime import datetime

    spec = InstrumentSpec(
        base="BTC",
        quote="USD",
        instrument_type=InstrumentType.OPTION,
        strike=35000.0,
        expiry=datetime(2024, 6, 28),
        metadata={"option_type": "C"},
    )
    urm_id = spec_to_urm_id(spec, exchange="deribit")
    assert "C:35000" in urm_id
    assert "20240628" in urm_id
