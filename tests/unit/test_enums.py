"""Unit tests for Timeframe enum."""

from laakhay.data.core import Timeframe


def test_seconds_property():
    """Test seconds property."""
    assert Timeframe.M1.seconds == 60
    assert Timeframe.H1.seconds == 3600
    assert Timeframe.D1.seconds == 86400


def test_milliseconds_property():
    """Test milliseconds property."""
    assert Timeframe.M1.milliseconds == 60000
    assert Timeframe.H1.milliseconds == 3600000


def test_from_seconds_match():
    """Test from_seconds with valid value."""
    assert Timeframe.from_seconds(60) == Timeframe.M1
    assert Timeframe.from_seconds(3600) == Timeframe.H1


def test_from_seconds_no_match():
    """Test from_seconds with invalid value returns None."""
    assert Timeframe.from_seconds(90) is None
