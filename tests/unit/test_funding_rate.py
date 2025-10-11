"""Unit tests for FundingRate model."""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from laakhay.data.models.funding_rate import FundingRate


def test_funding_rate_valid():
    """Test valid FundingRate creation."""
    fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        funding_rate=Decimal("0.0001"),
        mark_price=Decimal("50000.00"),
    )
    
    assert fr.symbol == "BTCUSDT"
    assert fr.funding_rate == Decimal("0.0001")
    assert fr.mark_price == Decimal("50000.00")


def test_funding_rate_without_mark_price():
    """Test FundingRate creation without mark price."""
    fr = FundingRate(
        symbol="ETHUSDT",
        funding_time=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        funding_rate=Decimal("0.00015"),
    )
    
    assert fr.symbol == "ETHUSDT"
    assert fr.funding_rate == Decimal("0.00015")
    assert fr.mark_price is None


def test_funding_rate_percentage_conversion():
    """Test funding rate to percentage conversion."""
    fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        funding_rate=Decimal("0.0001"),  # 0.01%
    )
    
    assert fr.funding_rate_percentage == Decimal("0.01")


def test_annual_rate_calculation():
    """Test annual rate calculation (3 funding per day × 365 days)."""
    fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        funding_rate=Decimal("0.0001"),  # 0.01% per funding
    )
    
    # 0.01% × 1095 = 10.95% annualized
    expected_annual = Decimal("0.01") * Decimal("1095")
    assert fr.annual_rate_percentage == expected_annual


def test_positive_negative_funding():
    """Test positive and negative funding rate detection."""
    # Positive funding (longs pay shorts)
    positive_fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        funding_rate=Decimal("0.0001"),
    )
    
    assert positive_fr.is_positive is True
    assert positive_fr.is_negative is False
    
    # Negative funding (shorts pay longs)
    negative_fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        funding_rate=Decimal("-0.0001"),
    )
    
    assert negative_fr.is_positive is False
    assert negative_fr.is_negative is True
    
    # Zero funding
    zero_fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        funding_rate=Decimal("0"),
    )
    
    assert zero_fr.is_positive is False
    assert zero_fr.is_negative is False


def test_high_funding_rate_detection():
    """Test high funding rate detection (>0.01%)."""
    # High funding rate
    high_fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        funding_rate=Decimal("0.0002"),  # 0.02%
    )
    
    assert high_fr.is_high is True
    
    # Normal funding rate
    normal_fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        funding_rate=Decimal("0.00005"),  # 0.005%
    )
    
    assert normal_fr.is_high is False
    
    # High negative funding rate
    high_negative_fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        funding_rate=Decimal("-0.00015"),  # -0.015%
    )
    
    assert high_negative_fr.is_high is True


def test_funding_time_ms():
    """Test funding_time_ms property."""
    funding_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=funding_time,
        funding_rate=Decimal("0.0001"),
    )
    
    expected_ms = int(funding_time.timestamp() * 1000)
    assert fr.funding_time_ms == expected_ms


def test_get_age_seconds():
    """Test age calculation."""
    # Recent funding
    recent_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    recent_fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=recent_time,
        funding_rate=Decimal("0.0001"),
    )
    
    age = recent_fr.get_age_seconds()
    assert 55 < age < 65  # ~60 seconds, with some tolerance
    
    # Old funding
    old_time = datetime.now(timezone.utc) - timedelta(hours=1)
    old_fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=old_time,
        funding_rate=Decimal("0.0001"),
    )
    
    age = old_fr.get_age_seconds()
    assert 3595 < age < 3605  # ~3600 seconds


def test_is_fresh():
    """Test freshness check."""
    # Fresh funding
    fresh_time = datetime.now(timezone.utc) - timedelta(seconds=30)
    fresh_fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=fresh_time,
        funding_rate=Decimal("0.0001"),
    )
    
    assert fresh_fr.is_fresh(max_age_seconds=300) is True
    
    # Stale funding
    stale_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    stale_fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=stale_time,
        funding_rate=Decimal("0.0001"),
    )
    
    assert stale_fr.is_fresh(max_age_seconds=300) is False


def test_to_dict():
    """Test to_dict conversion."""
    fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        funding_rate=Decimal("0.0001"),
        mark_price=Decimal("50000.00"),
    )
    
    data = fr.to_dict()
    
    assert data["symbol"] == "BTCUSDT"
    assert data["funding_time"] == "2024-01-01T00:00:00+00:00"
    assert data["funding_rate"] == "0.0001"
    assert Decimal(data["funding_rate_percentage"]) == Decimal("0.01")
    assert data["mark_price"] == "50000.00"
    assert data["is_positive"] is True
    assert data["is_high"] is False


def test_funding_rate_frozen():
    """Test that FundingRate is immutable."""
    fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        funding_rate=Decimal("0.0001"),
    )
    
    # Should raise exception when trying to modify
    with pytest.raises(Exception):  # Pydantic frozen validation error
        fr.symbol = "ETHUSDT"
    
    with pytest.raises(Exception):
        fr.funding_rate = Decimal("0.0002")


def test_funding_rate_edge_cases():
    """Test edge cases."""
    # Very small funding rate
    small_fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        funding_rate=Decimal("0.00000001"),
    )
    
    assert small_fr.funding_rate_percentage == Decimal("0.000001")
    assert small_fr.is_high is False
    
    # Very large funding rate (extreme market conditions)
    large_fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        funding_rate=Decimal("0.01"),  # 1%
    )
    
    assert large_fr.funding_rate_percentage == Decimal("1")
    assert large_fr.is_high is True
    assert large_fr.annual_rate_percentage == Decimal("1095")  # 1095% annualized!


def test_funding_rate_validation():
    """Test model validation."""
    # Valid funding rate
    fr = FundingRate(
        symbol="BTCUSDT",
        funding_time=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        funding_rate=Decimal("0.0001"),
    )
    assert fr.symbol == "BTCUSDT"
    
    # Empty symbol should fail
    with pytest.raises(Exception):  # Pydantic validation error
        FundingRate(
            symbol="",
            funding_time=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            funding_rate=Decimal("0.0001"),
        )

