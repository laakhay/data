"""Unit tests for Kraken URM mapper."""

import pytest

from laakhay.data.connectors.kraken.urm import KrakenURM
from laakhay.data.core import InstrumentSpec, InstrumentType, MarketType, SymbolResolutionError


def test_kraken_urm_spot_to_spec():
    """Test converting Kraken spot symbol to spec."""
    mapper = KrakenURM()

    spec = mapper.to_spec("XBT/USD", market_type=MarketType.SPOT)
    assert spec.base == "BTC"  # XBT normalized to BTC
    assert spec.quote == "USD"
    assert spec.instrument_type == InstrumentType.SPOT

    spec = mapper.to_spec("ETH/USD", market_type=MarketType.SPOT)
    assert spec.base == "ETH"
    assert spec.quote == "USD"
    assert spec.instrument_type == InstrumentType.SPOT


def test_kraken_urm_futures_to_spec():
    """Test converting Kraken futures symbol to spec."""
    mapper = KrakenURM()

    spec = mapper.to_spec("PI_XBTUSD", market_type=MarketType.FUTURES)
    assert spec.base == "BTC"  # XBT normalized to BTC
    assert spec.quote == "USD"
    assert spec.instrument_type == InstrumentType.PERPETUAL

    spec = mapper.to_spec("PI_ETHUSD", market_type=MarketType.FUTURES)
    assert spec.base == "ETH"
    assert spec.quote == "USD"
    assert spec.instrument_type == InstrumentType.PERPETUAL


def test_kraken_urm_spec_to_spot_symbol():
    """Test converting spec to Kraken spot symbol."""
    mapper = KrakenURM()

    spec = InstrumentSpec(base="BTC", quote="USD", instrument_type=InstrumentType.SPOT)
    symbol = mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
    assert symbol == "XBT/USD"  # BTC denormalized to XBT

    spec = InstrumentSpec(base="ETH", quote="USD", instrument_type=InstrumentType.SPOT)
    symbol = mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
    assert symbol == "ETH/USD"


def test_kraken_urm_spec_to_futures_symbol():
    """Test converting spec to Kraken futures symbol."""
    mapper = KrakenURM()

    spec = InstrumentSpec(base="BTC", quote="USD", instrument_type=InstrumentType.PERPETUAL)
    symbol = mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)
    assert symbol == "PI_XBTUSD"  # BTC denormalized to XBT

    spec = InstrumentSpec(base="ETH", quote="USD", instrument_type=InstrumentType.PERPETUAL)
    symbol = mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)
    assert symbol == "PI_ETHUSD"


def test_kraken_urm_round_trip_spot():
    """Test round-trip conversion for spot."""
    mapper = KrakenURM()

    original = "XBT/USD"
    spec = mapper.to_spec(original, market_type=MarketType.SPOT)
    converted = mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
    assert converted == original


def test_kraken_urm_round_trip_futures():
    """Test round-trip conversion for futures."""
    mapper = KrakenURM()

    original = "PI_XBTUSD"
    spec = mapper.to_spec(original, market_type=MarketType.FUTURES)
    converted = mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)
    assert converted == original


def test_kraken_urm_invalid_spot_format():
    """Test error for invalid spot format."""
    mapper = KrakenURM()

    with pytest.raises(SymbolResolutionError):
        mapper.to_spec("XBTUSD", market_type=MarketType.SPOT)  # Missing separator


def test_kraken_urm_invalid_futures_format():
    """Test error for invalid futures format."""
    mapper = KrakenURM()

    with pytest.raises(SymbolResolutionError):
        mapper.to_spec("XBTUSD", market_type=MarketType.FUTURES)  # Missing PI_ prefix


def test_kraken_urm_invalid_futures_for_spot():
    """Test error when trying to convert futures spec to spot symbol."""
    mapper = KrakenURM()

    spec = InstrumentSpec(base="BTC", quote="USD", instrument_type=InstrumentType.PERPETUAL)

    with pytest.raises(SymbolResolutionError):
        mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)


def test_kraken_urm_invalid_spot_for_futures():
    """Test error when trying to convert spot spec to futures symbol."""
    mapper = KrakenURM()

    spec = InstrumentSpec(base="BTC", quote="USD", instrument_type=InstrumentType.SPOT)

    with pytest.raises(SymbolResolutionError):
        mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)


def test_kraken_urm_invalid_future_type():
    """Test error when trying to convert dated future (not supported)."""
    mapper = KrakenURM()

    from datetime import datetime

    spec = InstrumentSpec(
        base="BTC",
        quote="USD",
        instrument_type=InstrumentType.FUTURE,
        expiry=datetime(2024, 3, 29),
    )

    with pytest.raises(SymbolResolutionError):
        mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)
