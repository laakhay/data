"""Unit tests for OKX URM mapper."""

import pytest

from laakhay.data.connectors.okx.urm import OKXURM
from laakhay.data.core import InstrumentSpec, InstrumentType, MarketType, SymbolResolutionError


def test_okx_urm_spot_to_spec():
    """Test converting OKX spot symbol to spec."""
    mapper = OKXURM()

    spec = mapper.to_spec("BTC-USDT", market_type=MarketType.SPOT)
    assert spec.base == "BTC"
    assert spec.quote == "USDT"
    assert spec.instrument_type == InstrumentType.SPOT


def test_okx_urm_futures_to_spec():
    """Test converting OKX futures symbol to spec."""
    mapper = OKXURM()

    spec = mapper.to_spec("BTC-USDT-SWAP", market_type=MarketType.FUTURES)
    assert spec.base == "BTC"
    assert spec.quote == "USDT"
    assert spec.instrument_type == InstrumentType.PERPETUAL


def test_okx_urm_spec_to_spot_symbol():
    """Test converting spec to OKX spot symbol."""
    mapper = OKXURM()

    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.SPOT)
    symbol = mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
    assert symbol == "BTC-USDT"


def test_okx_urm_spec_to_futures_symbol():
    """Test converting spec to OKX futures symbol."""
    mapper = OKXURM()

    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.PERPETUAL)
    symbol = mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)
    assert symbol == "BTC-USDT-SWAP"


def test_okx_urm_round_trip_spot():
    """Test round-trip conversion for spot."""
    mapper = OKXURM()

    original = "BTC-USDT"
    spec = mapper.to_spec(original, market_type=MarketType.SPOT)
    converted = mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
    assert converted == original


def test_okx_urm_round_trip_futures():
    """Test round-trip conversion for futures."""
    mapper = OKXURM()

    original = "BTC-USDT-SWAP"
    spec = mapper.to_spec(original, market_type=MarketType.FUTURES)
    converted = mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)
    assert converted == original


def test_okx_urm_invalid_format():
    """Test error for invalid format."""
    mapper = OKXURM()

    with pytest.raises(SymbolResolutionError):
        mapper.to_spec("BTCUSDT", market_type=MarketType.SPOT)  # Missing hyphen


def test_okx_urm_invalid_futures_for_spot():
    """Test error when trying to convert futures spec to spot symbol."""
    mapper = OKXURM()

    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.PERPETUAL)

    with pytest.raises(SymbolResolutionError):
        mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
