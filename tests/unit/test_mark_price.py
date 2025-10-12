"""Unit tests for MarkPrice model."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from laakhay.data.models.mark_price import MarkPrice


def test_mark_price_valid():
    """Test valid MarkPrice creation."""
    mp = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50000.00"),
        index_price=Decimal("49950.00"),
        estimated_settle_price=Decimal("49975.00"),
        last_funding_rate=Decimal("0.0001"),
        next_funding_time=datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc),
        timestamp=datetime(2024, 1, 1, 7, 0, tzinfo=timezone.utc),
    )

    assert mp.symbol == "BTCUSDT"
    assert mp.mark_price == Decimal("50000.00")
    assert mp.index_price == Decimal("49950.00")


def test_mark_price_without_optional_fields():
    """Test MarkPrice with only required fields."""
    mp = MarkPrice(
        symbol="ETHUSDT",
        mark_price=Decimal("3000.00"),
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
    )

    assert mp.symbol == "ETHUSDT"
    assert mp.mark_price == Decimal("3000.00")
    assert mp.index_price is None
    assert mp.estimated_settle_price is None
    assert mp.last_funding_rate is None
    assert mp.next_funding_time is None


def test_mark_index_spread():
    """Test mark/index spread calculation."""
    mp = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50100.00"),  # Premium
        index_price=Decimal("50000.00"),
        timestamp=datetime.now(timezone.utc),
    )

    assert mp.mark_index_spread == Decimal("100.00")
    assert mp.is_premium is True
    assert mp.is_discount is False


def test_mark_index_spread_discount():
    """Test mark price at discount to index."""
    mp = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("49900.00"),  # Discount
        index_price=Decimal("50000.00"),
        timestamp=datetime.now(timezone.utc),
    )

    assert mp.mark_index_spread == Decimal("-100.00")
    assert mp.is_premium is False
    assert mp.is_discount is True


def test_mark_index_spread_bps():
    """Test spread in basis points."""
    mp = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50050.00"),
        index_price=Decimal("50000.00"),
        timestamp=datetime.now(timezone.utc),
    )

    # Spread = 50, Index = 50000
    # BPS = (50 / 50000) * 10000 = 10 bps
    expected_bps = Decimal("10.00")
    assert abs(mp.mark_index_spread_bps - expected_bps) < Decimal("0.01")


def test_mark_index_spread_percentage():
    """Test spread as percentage."""
    mp = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50050.00"),
        index_price=Decimal("50000.00"),
        timestamp=datetime.now(timezone.utc),
    )

    # Spread = 50, Index = 50000
    # Percentage = (50 / 50000) * 100 = 0.1%
    expected_pct = Decimal("0.1")
    assert abs(mp.mark_index_spread_percentage - expected_pct) < Decimal("0.01")


def test_spread_severity():
    """Test spread severity categorization."""
    now = datetime.now(timezone.utc)

    # Normal spread < 10 bps (< 0.10%)
    mp_normal = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50005.00"),
        index_price=Decimal("50000.00"),
        timestamp=now,
    )
    assert mp_normal.spread_severity == "normal"

    # Moderate spread 10-30 bps
    mp_moderate = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50075.00"),
        index_price=Decimal("50000.00"),
        timestamp=now,
    )
    assert mp_moderate.spread_severity == "moderate"

    # High spread 30-100 bps
    mp_high = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50200.00"),
        index_price=Decimal("50000.00"),
        timestamp=now,
    )
    assert mp_high.spread_severity == "high"

    # Extreme spread > 100 bps (> 1%)
    mp_extreme = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50600.00"),
        index_price=Decimal("50000.00"),
        timestamp=now,
    )
    assert mp_extreme.spread_severity == "extreme"


def test_compare_to_last_price():
    """Test comparison with last traded price (dislocation detection)."""
    mp = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50000.00"),
        index_price=Decimal("49990.00"),
        timestamp=datetime.now(timezone.utc),
    )

    # Last price diverged significantly from mark
    last_price = Decimal("50200.00")
    comparison = mp.compare_to_last_price(last_price)

    assert comparison["last_price"] == last_price
    assert comparison["mark_price"] == Decimal("50000.00")
    assert comparison["spread"] == Decimal("-200.00")
    assert comparison["spread_bps"] is not None
    # 200 / 50200 * 10000 ≈ 39.8 bps > 30 bps threshold
    assert comparison["is_dislocation"] is True


def test_compare_to_exchange_spot():
    """Test comparison with exchange spot price (venue anomaly detection)."""
    mp = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50000.00"),
        index_price=Decimal("50000.00"),
        timestamp=datetime.now(timezone.utc),
    )

    # Exchange spot diverged from index
    exchange_spot = Decimal("49700.00")  # 300 difference
    comparison = mp.compare_to_exchange_spot(exchange_spot)

    assert comparison["exchange_spot_price"] == exchange_spot
    assert comparison["index_price"] == Decimal("50000.00")
    assert comparison["spread"] == Decimal("300.00")
    # 300 / 49700 * 10000 ≈ 60.4 bps > 50 bps threshold
    assert comparison["is_venue_anomaly"] is True


def test_seconds_to_funding():
    """Test seconds until next funding calculation."""
    now = datetime.now(timezone.utc)
    next_funding = now + timedelta(hours=1)

    mp = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50000.00"),
        next_funding_time=next_funding,
        timestamp=now,
    )

    seconds = mp.seconds_to_funding
    assert 3595 < seconds < 3605  # ~3600 seconds (1 hour)


def test_is_fresh():
    """Test freshness check."""
    # Fresh data
    recent_time = datetime.now(timezone.utc) - timedelta(seconds=5)
    mp_fresh = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50000.00"),
        timestamp=recent_time,
    )
    assert mp_fresh.is_fresh(max_age_seconds=10.0) is True

    # Stale data
    old_time = datetime.now(timezone.utc) - timedelta(seconds=15)
    mp_stale = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50000.00"),
        timestamp=old_time,
    )
    assert mp_stale.is_fresh(max_age_seconds=10.0) is False


def test_to_dict():
    """Test to_dict conversion."""
    mp = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50000.00"),
        index_price=Decimal("49990.00"),
        estimated_settle_price=Decimal("49995.00"),
        last_funding_rate=Decimal("0.0001"),
        next_funding_time=datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc),
        timestamp=datetime(2024, 1, 1, 7, 0, tzinfo=timezone.utc),
    )

    data = mp.to_dict()

    assert data["symbol"] == "BTCUSDT"
    assert data["mark_price"] == "50000.00"
    assert data["index_price"] == "49990.00"
    assert data["spread_severity"] in ["normal", "moderate", "high", "extreme"]
    assert isinstance(data["is_premium"], bool)
    assert data["timestamp"] == "2024-01-01T07:00:00+00:00"


def test_mark_price_frozen():
    """Test that MarkPrice is immutable."""
    mp = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50000.00"),
        timestamp=datetime.now(timezone.utc),
    )

    with pytest.raises(Exception):  # Pydantic frozen validation error
        mp.symbol = "ETHUSDT"

    with pytest.raises(Exception):
        mp.mark_price = Decimal("51000.00")


def test_mark_price_validation():
    """Test model validation."""
    # Valid
    mp = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50000.00"),
        timestamp=datetime.now(timezone.utc),
    )
    assert mp.symbol == "BTCUSDT"

    # Empty symbol should fail
    with pytest.raises(Exception):
        MarkPrice(
            symbol="",
            mark_price=Decimal("50000.00"),
            timestamp=datetime.now(timezone.utc),
        )

    # Negative mark price should fail
    with pytest.raises(Exception):
        MarkPrice(
            symbol="BTCUSDT",
            mark_price=Decimal("-50000.00"),
            timestamp=datetime.now(timezone.utc),
        )


def test_high_spread_detection():
    """Test high spread detection with 30 bps threshold."""
    mp = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50151.00"),  # > 30 bps spread
        index_price=Decimal("50000.00"),
        timestamp=datetime.now(timezone.utc),
    )

    # Threshold is > 30 bps
    assert mp.is_high_spread is True

    # Small spread
    mp_small = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50010.00"),  # 2 bps
        index_price=Decimal("50000.00"),
        timestamp=datetime.now(timezone.utc),
    )
    assert mp_small.is_high_spread is False


def test_get_age_seconds():
    """Test age calculation."""
    old_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    mp = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50000.00"),
        timestamp=old_time,
    )

    age = mp.get_age_seconds()
    assert 295 < age < 305  # ~300 seconds (5 minutes)


def test_timestamp_ms():
    """Test timestamp conversion to milliseconds."""
    timestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    mp = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50000.00"),
        timestamp=timestamp,
    )

    expected_ms = int(timestamp.timestamp() * 1000)
    assert mp.timestamp_ms == expected_ms


def test_edge_cases():
    """Test edge cases."""
    # No index price
    mp_no_index = MarkPrice(
        symbol="BTCUSDT",
        mark_price=Decimal("50000.00"),
        timestamp=datetime.now(timezone.utc),
    )

    assert mp_no_index.mark_index_spread is None
    assert mp_no_index.mark_index_spread_bps is None
    assert mp_no_index.is_premium is None
    assert mp_no_index.spread_severity == "unknown"

    # Zero index price (shouldn't happen but handle gracefully)
    comparison = mp_no_index.compare_to_exchange_spot(Decimal("50000.00"))
    assert "error" in comparison or comparison["index_price"] is None
