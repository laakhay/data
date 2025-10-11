"""Unit tests for Candle model."""

from datetime import datetime
from decimal import Decimal

import pytest

from laakhay.data.models import Candle


def test_candle_valid():
    """Test valid candle creation."""
    candle = Candle(
        symbol="BTCUSDT",
        timestamp=datetime(2024, 1, 1, 0, 0),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100.5"),
    )
    assert candle.symbol == "BTCUSDT"
    assert candle.open == Decimal("50000")
    assert candle.high == Decimal("51000")


def test_candle_frozen():
    """Test candle is immutable."""
    candle = Candle(
        symbol="BTCUSDT",
        timestamp=datetime(2024, 1, 1),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
    )
    with pytest.raises(Exception):  # ValidationError or AttributeError
        candle.symbol = "ETHUSDT"


def test_candle_invalid_high_low():
    """Test validation: high must be >= low."""
    with pytest.raises(Exception):  # ValidationError
        Candle(
            symbol="BTCUSDT",
            timestamp=datetime(2024, 1, 1),
            open=Decimal("50000"),
            high=Decimal("49000"),  # high < low
            low=Decimal("51000"),
            close=Decimal("50000"),
            volume=Decimal("100"),
        )


def test_candle_zero_volume():
    """Test volume can be zero."""
    candle = Candle(
        symbol="BTCUSDT",
        timestamp=datetime(2024, 1, 1),
        open=Decimal("50000"),
        high=Decimal("50000"),
        low=Decimal("50000"),
        close=Decimal("50000"),
        volume=Decimal("0"),
    )
    assert candle.volume == Decimal("0")
