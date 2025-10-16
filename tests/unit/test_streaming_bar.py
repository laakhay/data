"""Unit tests for StreamingBar model."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from laakhay.data.models import Bar, StreamingBar


def test_streaming_bar_creation():
    """Test StreamingBar creation."""
    bar = Bar(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
    )
    
    streaming_bar = StreamingBar(symbol="BTCUSDT", bar=bar)
    
    assert streaming_bar.symbol == "BTCUSDT"
    assert streaming_bar.bar == bar


def test_streaming_bar_delegation():
    """Test that StreamingBar delegates properties to bar."""
    bar = Bar(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
        is_closed=True,
    )
    
    streaming_bar = StreamingBar(symbol="BTCUSDT", bar=bar)
    
    # Test direct property access
    assert streaming_bar.timestamp == bar.timestamp
    assert streaming_bar.open == bar.open
    assert streaming_bar.high == bar.high
    assert streaming_bar.low == bar.low
    assert streaming_bar.close == bar.close
    assert streaming_bar.volume == bar.volume
    assert streaming_bar.is_closed == bar.is_closed


def test_streaming_bar_method_delegation():
    """Test that StreamingBar delegates methods to bar."""
    bar = Bar(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
    )
    
    streaming_bar = StreamingBar(symbol="BTCUSDT", bar=bar)
    
    # Test method delegation
    assert streaming_bar.open_time_ms == bar.open_time_ms
    assert streaming_bar.close_time_ms(60) == bar.close_time_ms(60)
    assert streaming_bar.hl2 == bar.hl2
    assert streaming_bar.hlc3 == bar.hlc3
    assert streaming_bar.ohlc4 == bar.ohlc4


def test_streaming_bar_immutable():
    """Test that StreamingBar is immutable."""
    bar = Bar(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
    )
    
    streaming_bar = StreamingBar(symbol="BTCUSDT", bar=bar)
    
    with pytest.raises(Exception):  # dataclasses.frozen or AttributeError
        streaming_bar.symbol = "ETHUSDT"
