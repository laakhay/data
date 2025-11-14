"""Unit tests for Binance URM mapper."""

from datetime import datetime

import pytest

from laakhay.data.core import InstrumentSpec, InstrumentType, MarketType, SymbolResolutionError
from laakhay.data.providers.binance.urm import BinanceURM


def test_binance_urm_spot_to_spec():
    """Test converting Binance spot symbol to spec."""
    mapper = BinanceURM()

    spec = mapper.to_spec("BTCUSDT", market_type=MarketType.SPOT)
    assert spec.base == "BTC"
    assert spec.quote == "USDT"
    assert spec.instrument_type == InstrumentType.SPOT

    spec = mapper.to_spec("ETHUSDT", market_type=MarketType.SPOT)
    assert spec.base == "ETH"
    assert spec.quote == "USDT"
    assert spec.instrument_type == InstrumentType.SPOT


def test_binance_urm_futures_perpetual_to_spec():
    """Test converting Binance perpetual futures symbol to spec."""
    mapper = BinanceURM()

    spec = mapper.to_spec("BTCUSDT", market_type=MarketType.FUTURES)
    assert spec.base == "BTC"
    assert spec.quote == "USDT"
    assert spec.instrument_type == InstrumentType.PERPETUAL


def test_binance_urm_futures_dated_to_spec():
    """Test converting Binance dated futures symbol to spec."""
    mapper = BinanceURM()

    spec = mapper.to_spec("BTCUSDT_240329", market_type=MarketType.FUTURES)
    assert spec.base == "BTC"
    assert spec.quote == "USDT"
    assert spec.instrument_type == InstrumentType.FUTURE
    assert spec.expiry is not None
    assert spec.expiry.year == 2024
    assert spec.expiry.month == 3
    assert spec.expiry.day == 29

    # Test with 2-digit year format (actual Binance format)
    spec = mapper.to_spec("BTCUSDT_240329", market_type=MarketType.FUTURES)
    assert spec.expiry.year == 2024


def test_binance_urm_spec_to_spot_symbol():
    """Test converting spec to Binance spot symbol."""
    mapper = BinanceURM()

    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.SPOT)
    symbol = mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
    assert symbol == "BTCUSDT"


def test_binance_urm_spec_to_perpetual_symbol():
    """Test converting spec to Binance perpetual futures symbol."""
    mapper = BinanceURM()

    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.PERPETUAL)
    symbol = mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)
    assert symbol == "BTCUSDT"


def test_binance_urm_spec_to_dated_future_symbol():
    """Test converting spec to Binance dated future symbol."""
    mapper = BinanceURM()

    expiry = datetime(2024, 3, 29)
    spec = InstrumentSpec(
        base="BTC", quote="USDT", instrument_type=InstrumentType.FUTURE, expiry=expiry
    )
    symbol = mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)
    assert symbol == "BTCUSDT_240329"


def test_binance_urm_round_trip_spot():
    """Test round-trip conversion for spot."""
    mapper = BinanceURM()

    original = "BTCUSDT"
    spec = mapper.to_spec(original, market_type=MarketType.SPOT)
    converted = mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
    assert converted == original


def test_binance_urm_round_trip_perpetual():
    """Test round-trip conversion for perpetual."""
    mapper = BinanceURM()

    original = "BTCUSDT"
    spec = mapper.to_spec(original, market_type=MarketType.FUTURES)
    converted = mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)
    assert converted == original


def test_binance_urm_round_trip_dated_future():
    """Test round-trip conversion for dated future."""
    mapper = BinanceURM()

    original = "BTCUSDT_240329"
    spec = mapper.to_spec(original, market_type=MarketType.FUTURES)
    converted = mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)
    assert converted == original


def test_binance_urm_invalid_futures_for_spot():
    """Test error when trying to convert futures spec to spot symbol."""
    mapper = BinanceURM()

    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.PERPETUAL)

    with pytest.raises(SymbolResolutionError):
        mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)


def test_binance_urm_invalid_spot_for_futures():
    """Test error when trying to convert spot spec to futures symbol."""
    mapper = BinanceURM()

    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.SPOT)

    with pytest.raises(SymbolResolutionError):
        mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)
