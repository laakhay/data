"""Unit tests for SeriesMeta model."""

import pytest

from laakhay.data.models import SeriesMeta


def test_series_meta_valid():
    """Test valid SeriesMeta creation."""
    meta = SeriesMeta(symbol="BTCUSDT", timeframe="1m")
    assert meta.symbol == "BTCUSDT"
    assert meta.timeframe == "1m"


def test_series_meta_frozen():
    """Test SeriesMeta is immutable."""
    meta = SeriesMeta(symbol="BTCUSDT", timeframe="1m")
    with pytest.raises(Exception):  # ValidationError or AttributeError
        meta.symbol = "ETHUSDT"


def test_series_meta_string_representation():
    """Test string representations."""
    meta = SeriesMeta(symbol="BTCUSDT", timeframe="1m")

    # Test __str__
    assert str(meta) == "BTCUSDT@1m"

    # Test __repr__
    repr_str = repr(meta)
    assert "BTCUSDT" in repr_str
    assert "1m" in repr_str


def test_series_meta_symbol_upper():
    """Test symbol_upper property."""
    meta = SeriesMeta(symbol="btcusdt", timeframe="1m")
    assert meta.symbol_upper == "BTCUSDT"


def test_series_meta_key():
    """Test key property for unique identification."""
    meta1 = SeriesMeta(symbol="BTCUSDT", timeframe="1m")
    meta2 = SeriesMeta(symbol="BTCUSDT", timeframe="5m")
    meta3 = SeriesMeta(symbol="ETHUSDT", timeframe="1m")

    key1 = meta1.key
    key2 = meta2.key
    key3 = meta3.key

    assert key1 == ("BTCUSDT", "1m")
    assert key2 == ("BTCUSDT", "5m")
    assert key3 == ("ETHUSDT", "1m")

    # Keys should be different
    assert key1 != key2
    assert key1 != key3
    assert key2 != key3


def test_series_meta_case_insensitive_key():
    """Test that key is case insensitive."""
    meta1 = SeriesMeta(symbol="BTCUSDT", timeframe="1m")
    meta2 = SeriesMeta(symbol="btcusdt", timeframe="1m")

    assert meta1.key == meta2.key
