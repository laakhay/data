"""Unit tests for Coinbase URM mapper."""

import pytest

from laakhay.data.connectors.coinbase.urm import CoinbaseURM
from laakhay.data.core import InstrumentSpec, InstrumentType, MarketType, SymbolResolutionError


def test_coinbase_urm_spot_to_spec():
    """Test converting Coinbase spot symbol to spec."""
    mapper = CoinbaseURM()

    spec = mapper.to_spec("BTC-USD", market_type=MarketType.SPOT)
    assert spec.base == "BTC"
    assert spec.quote == "USD"
    assert spec.instrument_type == InstrumentType.SPOT


def test_coinbase_urm_preserves_quote():
    """Test that quote asset is preserved."""
    mapper = CoinbaseURM()

    spec = mapper.to_spec("BTC-USD", market_type=MarketType.SPOT)
    assert spec.quote == "USD"


def test_coinbase_urm_spec_to_spot_symbol():
    """Test converting spec to Coinbase spot symbol."""
    mapper = CoinbaseURM()

    spec = InstrumentSpec(base="BTC", quote="USD", instrument_type=InstrumentType.SPOT)
    symbol = mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
    assert symbol == "BTC-USD"


def test_coinbase_urm_usdt_error():
    """Test that USDT spec raises error."""
    mapper = CoinbaseURM()

    # Spec with USDT should raise error since Coinbase doesn't support USDT
    spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.SPOT)
    with pytest.raises(SymbolResolutionError, match="only supports USD pairs"):
        mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)


def test_coinbase_urm_round_trip():
    """Test round-trip conversion for spot."""
    mapper = CoinbaseURM()

    original = "BTC-USD"
    spec = mapper.to_spec(original, market_type=MarketType.SPOT)
    converted = mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
    assert converted == original


def test_coinbase_urm_invalid_format():
    """Test error for invalid format."""
    mapper = CoinbaseURM()

    with pytest.raises(SymbolResolutionError):
        mapper.to_spec("BTCUSD", market_type=MarketType.SPOT)  # Missing hyphen


def test_coinbase_urm_futures_not_supported():
    """Test error when trying to use futures."""
    mapper = CoinbaseURM()

    with pytest.raises(SymbolResolutionError):
        mapper.to_spec("BTC-USD", market_type=MarketType.FUTURES)

    spec = InstrumentSpec(base="BTC", quote="USD", instrument_type=InstrumentType.SPOT)
    with pytest.raises(SymbolResolutionError):
        mapper.to_exchange_symbol(spec, market_type=MarketType.FUTURES)


def test_coinbase_urm_invalid_instrument_type():
    """Test error for non-spot instrument type."""
    mapper = CoinbaseURM()

    spec = InstrumentSpec(base="BTC", quote="USD", instrument_type=InstrumentType.PERPETUAL)

    with pytest.raises(SymbolResolutionError):
        mapper.to_exchange_symbol(spec, market_type=MarketType.SPOT)
