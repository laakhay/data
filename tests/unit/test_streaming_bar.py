"""Unit tests for StreamingBar model."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from laakhay.data.models import StreamingBar


def test_streaming_bar_creation():
    """Test StreamingBar creation."""
    streaming_bar = StreamingBar(
        symbol="BTCUSDT",
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
        is_closed=True,
    )
    
    assert streaming_bar.symbol == "BTCUSDT"
    assert streaming_bar.timestamp == datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert streaming_bar.close == Decimal("50500")


def test_streaming_bar_inheritance():
    """Test that StreamingBar inherits Bar properties."""
    streaming_bar = StreamingBar(
        symbol="BTCUSDT",
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
        is_closed=True,
    )
    
    # Test inherited properties
    assert streaming_bar.timestamp == datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert streaming_bar.open == Decimal("50000")
    assert streaming_bar.high == Decimal("51000")
    assert streaming_bar.low == Decimal("49000")
    assert streaming_bar.close == Decimal("50500")
    assert streaming_bar.volume == Decimal("100")
    assert streaming_bar.is_closed == True
    # Test symbol property
    assert streaming_bar.symbol == "BTCUSDT"


def test_streaming_bar_method_inheritance():
    """Test that StreamingBar inherits Bar methods."""
    streaming_bar = StreamingBar(
        symbol="BTCUSDT",
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
        is_closed=True,
    )
    
    # Test inherited methods
    assert streaming_bar.open_time_ms == 1704110400000
    assert streaming_bar.close_time_ms(60) == 1704110460000
    assert streaming_bar.hl2 == Decimal("50000")  # (high + low) / 2
    # Test hlc3 calculation: (51000 + 49000 + 50500) / 3 = 150500 / 3 ≈ 50166.67
    expected_hlc3 = (streaming_bar.high + streaming_bar.low + streaming_bar.close) / 3
    assert streaming_bar.hlc3 == expected_hlc3
    expected_ohlc4 = (streaming_bar.open + streaming_bar.high + streaming_bar.low + streaming_bar.close) / 4
    assert streaming_bar.ohlc4 == expected_ohlc4


def test_streaming_bar_immutable():
    """Test that StreamingBar is immutable."""
    streaming_bar = StreamingBar(
        symbol="BTCUSDT",
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
        is_closed=True,
    )
    
    with pytest.raises(Exception):  # Pydantic ValidationError or AttributeError
        streaming_bar.symbol = "ETHUSDT"
