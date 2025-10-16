"""Unit tests for Bar model."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from laakhay.data.models import Bar


def test_bar_valid():
    """Test valid bar creation."""
    bar = Bar(
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100.5"),
        is_closed=True,
    )
    assert bar.open == Decimal("50000")
    assert bar.high == Decimal("51000")
    assert bar.low == Decimal("49000")
    assert bar.close == Decimal("50500")
    assert bar.volume == Decimal("100.5")
    assert bar.is_closed is True


def test_bar_frozen():
    """Test bar is immutable."""
    bar = Bar(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
        is_closed=True,
    )
    with pytest.raises(Exception):  # ValidationError or AttributeError
        bar.open = Decimal("60000")


def test_bar_invalid_high_low():
    """Test validation: high must be >= low."""
    with pytest.raises(Exception):  # ValidationError
        Bar(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open=Decimal("50000"),
            high=Decimal("49000"),  # high < low
            low=Decimal("51000"),
            close=Decimal("50000"),
            volume=Decimal("100"),
        )


def test_bar_zero_volume():
    """Test volume can be zero."""
    bar = Bar(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("50000"),
        low=Decimal("50000"),
        close=Decimal("50000"),
        volume=Decimal("0"),
    )
    assert bar.volume == Decimal("0")


def test_bar_time_utilities():
    """Test time utility methods."""
    timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    bar = Bar(
        timestamp=timestamp,
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
    )
    
    # Test open_time_ms
    expected_ms = int(timestamp.timestamp() * 1000)
    assert bar.open_time_ms == expected_ms
    
    # Test close_time_ms
    close_ms = bar.close_time_ms(interval_seconds=60)
    assert close_ms == expected_ms + 60000


def test_bar_price_calculations():
    """Test price calculation properties."""
    bar = Bar(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
    )
    
    # Test hl2
    expected_hl2 = (Decimal("51000") + Decimal("49000")) / Decimal("2")
    assert bar.hl2 == expected_hl2
    
    # Test hlc3
    expected_hlc3 = (Decimal("51000") + Decimal("49000") + Decimal("50500")) / Decimal("3")
    assert bar.hlc3 == expected_hlc3
    
    # Test ohlc4
    expected_ohlc4 = (Decimal("50000") + Decimal("51000") + Decimal("49000") + Decimal("50500")) / Decimal("4")
    assert bar.ohlc4 == expected_ohlc4


def test_bar_candle_properties():
    """Test candle pattern properties."""
    # Bullish bar
    bullish_bar = Bar(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
    )
    assert bullish_bar.is_bullish is True
    assert bullish_bar.is_bearish is False
    
    # Bearish bar
    bearish_bar = Bar(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=Decimal("50500"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50000"),
        volume=Decimal("100"),
    )
    assert bearish_bar.is_bullish is False
    assert bearish_bar.is_bearish is True


def test_bar_shadow_calculations():
    """Test shadow size calculations."""
    bar = Bar(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
    )
    
    # Upper shadow = high - max(open, close)
    expected_upper = Decimal("51000") - Decimal("50500")  # max(50000, 50500)
    assert bar.upper_shadow == expected_upper
    
    # Lower shadow = min(open, close) - low
    expected_lower = Decimal("50000") - Decimal("49000")  # min(50000, 50500)
    assert bar.lower_shadow == expected_lower
    
    # Body size = |close - open|
    expected_body = abs(Decimal("50500") - Decimal("50000"))
    assert bar.body_size == expected_body
