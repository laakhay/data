"""Unit tests for BinanceProvider."""

import pytest

from laakhay.data.core import TimeInterval
from laakhay.data.providers import BinanceProvider


def test_binance_provider_instantiation():
    """Test BinanceProvider can be instantiated."""
    provider = BinanceProvider()
    assert provider.name == "binance"
    assert provider.BASE_URL == "https://api.binance.com"


def test_binance_interval_mapping():
    """Test interval mapping to Binance format."""
    provider = BinanceProvider()
    
    assert provider.INTERVAL_MAP[TimeInterval.M1] == "1m"
    assert provider.INTERVAL_MAP[TimeInterval.H1] == "1h"
    assert provider.INTERVAL_MAP[TimeInterval.D1] == "1d"
    assert provider.INTERVAL_MAP[TimeInterval.W1] == "1w"


def test_binance_validate_interval_valid():
    """Test validate_interval with valid intervals."""
    provider = BinanceProvider()
    
    # Should not raise
    provider.validate_interval(TimeInterval.M1)
    provider.validate_interval(TimeInterval.H1)
    provider.validate_interval(TimeInterval.D1)


def test_binance_validate_symbol():
    """Test validate_symbol."""
    provider = BinanceProvider()
    
    # Should not raise
    provider.validate_symbol("BTCUSDT")
    provider.validate_symbol("ETHUSDT")
    
    # Should raise for empty
    with pytest.raises(ValueError, match="non-empty string"):
        provider.validate_symbol("")
