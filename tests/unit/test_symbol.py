"""Unit tests for Symbol model."""

import pytest

from laakhay.data.models import Symbol


def test_symbol_valid():
    """Test valid symbol creation."""
    symbol = Symbol(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
    )
    assert symbol.symbol == "BTCUSDT"
    assert symbol.base_asset == "BTC"
    assert symbol.quote_asset == "USDT"


def test_symbol_frozen():
    """Test symbol is immutable."""
    symbol = Symbol(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
    )
    with pytest.raises(Exception):  # ValidationError or AttributeError
        symbol.symbol = "ETHUSDT"


def test_symbol_strip_whitespace():
    """Test whitespace is stripped."""
    symbol = Symbol(
        symbol=" BTCUSDT ",
        base_asset=" BTC ",
        quote_asset=" USDT ",
    )
    assert symbol.symbol == "BTCUSDT"
    assert symbol.base_asset == "BTC"
    assert symbol.quote_asset == "USDT"
