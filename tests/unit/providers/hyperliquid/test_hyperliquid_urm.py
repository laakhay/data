"""Unit tests for Hyperliquid URM mapper."""

import pytest

from laakhay.data.core import InstrumentSpec, InstrumentType, MarketType, SymbolResolutionError
from laakhay.data.providers.hyperliquid.urm import HyperliquidURM


def test_hyperliquid_urm_futures_to_spec():
    """Test converting Hyperliquid futures symbol to spec."""
    mapper = HyperliquidURM()

    spec = mapper.to_spec("BTC", market_type=MarketType.FUTURES)
    assert spec.base == "BTC"
    assert spec.quote == "USDT"  # Default for perpetuals
    assert spec.instrument_type == InstrumentType.PERPETUAL


def test_hyperliquid_urm_spot_to_spec():
    """Test converting Hyperliquid spot symbol to spec."""
    mapper = HyperliquidURM()

    spec = mapper.to_spec("BTC/USDC", market_type=MarketType.SPOT)
    assert spec.base == "BTC"
    assert spec.quote == "USDC"
    assert spec.instrument_type == InstrumentType.SPOT


def test_hyperliquid_urm_spec_to_futures_symbol():
    """Test converting spec to Hyperliquid futures symbol."""
    mapper = HyperliquidURM()

    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.PERPETUAL)
    symbol = mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)
    assert symbol == "BTC"  # Just the coin name


def test_hyperliquid_urm_spec_to_spot_symbol():
    """Test converting spec to Hyperliquid spot symbol."""
    mapper = HyperliquidURM()

    spec = InstrumentSpec(base="BTC", quote="USDC", instrument_type=InstrumentType.SPOT)
    symbol = mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
    assert symbol == "BTC/USDC"


def test_hyperliquid_urm_round_trip_futures():
    """Test round-trip conversion for futures."""
    mapper = HyperliquidURM()

    original = "BTC"
    spec = mapper.to_spec(original, market_type=MarketType.FUTURES)
    converted = mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)
    assert converted == original


def test_hyperliquid_urm_round_trip_spot():
    """Test round-trip conversion for spot."""
    mapper = HyperliquidURM()

    original = "BTC/USDC"
    spec = mapper.to_spec(original, market_type=MarketType.SPOT)
    converted = mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
    assert converted == original


def test_hyperliquid_urm_index_symbol_error():
    """Test error for index symbol format."""
    mapper = HyperliquidURM()

    with pytest.raises(SymbolResolutionError):
        mapper.to_spec("@107", market_type=MarketType.SPOT)  # Index format not supported


def test_hyperliquid_urm_invalid_futures_for_spot():
    """Test error when trying to convert futures spec to spot symbol."""
    mapper = HyperliquidURM()

    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.PERPETUAL)

    with pytest.raises(SymbolResolutionError):
        mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
