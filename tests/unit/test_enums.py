"""Unit tests for TimeInterval enum."""

from laakhay.data.core import TimeInterval


def test_seconds_property():
    """Test seconds property."""
    assert TimeInterval.M1.seconds == 60
    assert TimeInterval.H1.seconds == 3600
    assert TimeInterval.D1.seconds == 86400


def test_milliseconds_property():
    """Test milliseconds property."""
    assert TimeInterval.M1.milliseconds == 60000
    assert TimeInterval.H1.milliseconds == 3600000


def test_from_seconds_match():
    """Test from_seconds with valid value."""
    assert TimeInterval.from_seconds(60) == TimeInterval.M1
    assert TimeInterval.from_seconds(3600) == TimeInterval.H1


def test_from_seconds_no_match():
    """Test from_seconds with invalid value returns None."""
    assert TimeInterval.from_seconds(90) is None
