"""Unit tests for OpenInterest model."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from laakhay.data.models import OpenInterest


def test_open_interest_valid():
    """Test valid OpenInterest creation."""
    oi = OpenInterest(
        symbol="BTCUSDT",
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        open_interest=Decimal("12345.67"),
        open_interest_value=Decimal("500000000.50"),
    )
    assert oi.symbol == "BTCUSDT"
    assert oi.open_interest == Decimal("12345.67")
    assert oi.open_interest_value == Decimal("500000000.50")


def test_open_interest_frozen():
    """Test OpenInterest is immutable."""
    oi = OpenInterest(
        symbol="BTCUSDT",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open_interest=Decimal("1000"),
    )
    with pytest.raises(Exception):  # ValidationError or AttributeError
        oi.symbol = "ETHUSDT"


def test_open_interest_negative_values():
    """Test validation: values must be non-negative."""
    with pytest.raises(Exception):  # ValidationError
        OpenInterest(
            symbol="BTCUSDT",
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open_interest=Decimal("-1000"),  # negative OI
        )


def test_open_interest_zero_values():
    """Test zero values are allowed."""
    oi = OpenInterest(
        symbol="BTCUSDT",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open_interest=Decimal("0"),
        open_interest_value=Decimal("0"),
    )
    assert oi.open_interest == Decimal("0")
    assert oi.open_interest_value == Decimal("0")


def test_open_interest_optional_fields():
    """Test optional fields can be None."""
    oi = OpenInterest(
        symbol="BTCUSDT",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open_interest=Decimal("1000"),
        open_interest_value=None,
        sum_open_interest=None,
        sum_open_interest_value=None,
    )
    assert oi.open_interest_value is None
    assert oi.sum_open_interest is None
    assert oi.sum_open_interest_value is None


def test_open_interest_timestamp_ms():
    """Test timestamp_ms property."""
    timestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    oi = OpenInterest(
        symbol="BTCUSDT",
        timestamp=timestamp,
        open_interest=Decimal("1000"),
    )
    # 2024-01-01 00:00:00 UTC = 1704067200000 ms
    assert oi.timestamp_ms == 1704067200000


def test_open_interest_get_age_seconds():
    """Test get_age_seconds calculation."""
    now = datetime.now(timezone.utc)
    past_time = now - timedelta(minutes=5)  # 5 minutes ago

    oi = OpenInterest(
        symbol="BTCUSDT",
        timestamp=past_time,
        open_interest=Decimal("1000"),
    )

    age = oi.get_age_seconds()
    # Should be approximately 300 seconds (5 minutes)
    assert 290 <= age <= 310


def test_open_interest_is_fresh():
    """Test is_fresh method."""
    now = datetime.now(timezone.utc)
    recent_time = now - timedelta(seconds=30)  # 30 seconds ago
    old_time = now - timedelta(minutes=5)  # 5 minutes ago

    # Fresh OI (30 seconds old)
    fresh_oi = OpenInterest(
        symbol="BTCUSDT",
        timestamp=recent_time,
        open_interest=Decimal("1000"),
    )
    assert fresh_oi.is_fresh(max_age_seconds=120.0) is True

    # Stale OI (5 minutes old)
    stale_oi = OpenInterest(
        symbol="BTCUSDT",
        timestamp=old_time,
        open_interest=Decimal("1000"),
    )
    assert stale_oi.is_fresh(max_age_seconds=120.0) is False


def test_open_interest_to_dict():
    """Test to_dict serialization."""
    timestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    oi = OpenInterest(
        symbol="BTCUSDT",
        timestamp=timestamp,
        open_interest=Decimal("12345.67"),
        open_interest_value=Decimal("500000000.50"),
        sum_open_interest=Decimal("12345.67"),
        sum_open_interest_value=Decimal("500000000.50"),
    )

    result = oi.to_dict()
    expected = {
        "symbol": "BTCUSDT",
        "timestamp": "2024-01-01T00:00:00+00:00",
        "open_interest": "12345.67",
        "open_interest_value": "500000000.50",
        "sum_open_interest": "12345.67",
        "sum_open_interest_value": "500000000.50",
    }
    assert result == expected


def test_open_interest_to_dict_with_none():
    """Test to_dict with None values."""
    timestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    oi = OpenInterest(
        symbol="BTCUSDT",
        timestamp=timestamp,
        open_interest=Decimal("1000"),
        open_interest_value=None,
        sum_open_interest=None,
        sum_open_interest_value=None,
    )

    result = oi.to_dict()
    expected = {
        "symbol": "BTCUSDT",
        "timestamp": "2024-01-01T00:00:00+00:00",
        "open_interest": "1000",
        "open_interest_value": None,
        "sum_open_interest": None,
        "sum_open_interest_value": None,
    }
    assert result == expected
