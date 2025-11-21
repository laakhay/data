"""Unit tests for Bybit URM mapper."""

import pytest

from laakhay.data.core import InstrumentSpec, InstrumentType, MarketType, SymbolResolutionError
from laakhay.data.connectors.bybit.urm import BybitURM


def test_bybit_urm_spot_to_spec():
    """Test converting Bybit spot symbol to spec."""
    mapper = BybitURM()

    spec = mapper.to_spec("BTCUSDT", market_type=MarketType.SPOT)
    assert spec.base == "BTC"
    assert spec.quote == "USDT"
    assert spec.instrument_type == InstrumentType.SPOT


def test_bybit_urm_futures_to_spec():
    """Test converting Bybit futures symbol to spec."""
    mapper = BybitURM()

    spec = mapper.to_spec("BTCUSDT", market_type=MarketType.FUTURES)
    assert spec.base == "BTC"
    assert spec.quote == "USDT"
    assert spec.instrument_type == InstrumentType.PERPETUAL


def test_bybit_urm_spec_to_spot_symbol():
    """Test converting spec to Bybit spot symbol."""
    mapper = BybitURM()

    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.SPOT)
    symbol = mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
    assert symbol == "BTCUSDT"


def test_bybit_urm_spec_to_futures_symbol():
    """Test converting spec to Bybit futures symbol."""
    mapper = BybitURM()

    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.PERPETUAL)
    symbol = mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)
    assert symbol == "BTCUSDT"


def test_bybit_urm_round_trip_spot():
    """Test round-trip conversion for spot."""
    mapper = BybitURM()

    original = "BTCUSDT"
    spec = mapper.to_spec(original, market_type=MarketType.SPOT)
    converted = mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
    assert converted == original


def test_bybit_urm_round_trip_futures():
    """Test round-trip conversion for futures."""
    mapper = BybitURM()

    original = "BTCUSDT"
    spec = mapper.to_spec(original, market_type=MarketType.FUTURES)
    converted = mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)
    assert converted == original


def test_bybit_urm_invalid_futures_for_spot():
    """Test error when trying to convert futures spec to spot symbol."""
    mapper = BybitURM()

    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.PERPETUAL)

    with pytest.raises(SymbolResolutionError):
        mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
