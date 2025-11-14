"""Unit tests for Trade model."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from laakhay.data.models.trade import Trade


def test_trade_valid():
    """Test valid Trade creation."""
    trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("0.1"),
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        is_buyer_maker=False,
    )

    assert trade.symbol == "BTCUSDT"
    assert trade.trade_id == 12345
    assert trade.price == Decimal("50000")
    assert trade.quantity == Decimal("0.1")


def test_trade_value():
    """Test trade value calculation."""
    trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("0.1"),
        timestamp=datetime.now(UTC),
        is_buyer_maker=False,
    )

    # Value = price * quantity
    assert trade.value == Decimal("5000")


def test_trade_with_quote_quantity():
    """Test trade with explicit quote_quantity."""
    trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("0.1"),
        quote_quantity=Decimal("5001"),  # Slightly different due to rounding
        timestamp=datetime.now(UTC),
        is_buyer_maker=False,
    )

    # Should use quote_quantity when provided
    assert trade.value == Decimal("5001")


def test_trade_side():
    """Test trade side (buy/sell from taker perspective)."""
    # Buy trade (taker was buying, not buyer maker)
    buy_trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("0.1"),
        timestamp=datetime.now(UTC),
        is_buyer_maker=False,  # Buyer NOT maker = buy market order
    )

    assert buy_trade.side == "buy"
    assert buy_trade.is_buy is True
    assert buy_trade.is_sell is False

    # Sell trade (taker was selling, buyer is maker)
    sell_trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("0.1"),
        timestamp=datetime.now(UTC),
        is_buyer_maker=True,  # Buyer IS maker = sell market order
    )

    assert sell_trade.side == "sell"
    assert sell_trade.is_buy is False
    assert sell_trade.is_sell is True


def test_trade_size_classification():
    """Test trade size categorization."""
    # Small trade < $1k
    small_trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("0.01"),  # $500
        timestamp=datetime.now(UTC),
        is_buyer_maker=False,
    )
    assert small_trade.size_category == "small"
    assert small_trade.is_large is False
    assert small_trade.is_whale is False

    # Medium trade $1k - $10k
    medium_trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("0.1"),  # $5k
        timestamp=datetime.now(UTC),
        is_buyer_maker=False,
    )
    assert medium_trade.size_category == "medium"

    # Large trade $10k - $100k
    large_trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("1.1"),  # $55k (> $50k threshold)
        timestamp=datetime.now(UTC),
        is_buyer_maker=False,
    )
    assert large_trade.size_category == "large"
    assert large_trade.is_large is True

    # Whale trade > $100k
    whale_trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("100"),  # $5M
        timestamp=datetime.now(UTC),
        is_buyer_maker=False,
    )
    assert whale_trade.size_category == "whale"
    assert whale_trade.is_whale is True


def test_trade_freshness():
    """Test trade freshness check."""
    # Fresh trade
    fresh_trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("0.1"),
        timestamp=datetime.now(UTC),
        is_buyer_maker=False,
    )
    assert fresh_trade.is_fresh(max_age_seconds=60) is True

    # Stale trade
    stale_time = datetime.now(UTC) - timedelta(minutes=5)
    stale_trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("0.1"),
        timestamp=stale_time,
        is_buyer_maker=False,
    )
    assert stale_trade.is_fresh(max_age_seconds=60) is False


def test_trade_get_age_seconds():
    """Test age calculation."""
    old_time = datetime.now(UTC) - timedelta(seconds=30)
    trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("0.1"),
        timestamp=old_time,
        is_buyer_maker=False,
    )

    age = trade.get_age_seconds()
    assert 29 < age < 31  # ~30 seconds


def test_trade_to_dict():
    """Test to_dict conversion."""
    trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("0.1"),
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        is_buyer_maker=False,
        is_best_match=True,
    )

    data = trade.to_dict()

    assert data["symbol"] == "BTCUSDT"
    assert data["trade_id"] == 12345
    assert data["price"] == "50000"
    assert data["quantity"] == "0.1"
    assert Decimal(data["value"]) == Decimal("5000")
    assert data["side"] == "buy"
    assert data["is_buyer_maker"] is False
    assert data["size_category"] == "medium"


def test_trade_timestamp_ms():
    """Test timestamp milliseconds conversion."""
    timestamp = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("0.1"),
        timestamp=timestamp,
        is_buyer_maker=False,
    )

    expected_ms = int(timestamp.timestamp() * 1000)
    assert trade.timestamp_ms == expected_ms


def test_trade_frozen():
    """Test that Trade is immutable."""
    trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("0.1"),
        timestamp=datetime.now(UTC),
        is_buyer_maker=False,
    )

    with pytest.raises(Exception):  # Pydantic frozen validation error
        trade.symbol = "ETHUSDT"

    with pytest.raises(Exception):
        trade.price = Decimal("51000")


def test_trade_validation():
    """Test model validation."""
    # Valid trade
    trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("0.1"),
        timestamp=datetime.now(UTC),
        is_buyer_maker=False,
    )
    assert trade.symbol == "BTCUSDT"

    # Empty symbol should fail
    with pytest.raises(Exception):
        Trade(
            symbol="",
            trade_id=12345,
            price=Decimal("50000"),
            quantity=Decimal("0.1"),
            timestamp=datetime.now(UTC),
            is_buyer_maker=False,
        )

    # Zero/negative price should fail
    with pytest.raises(Exception):
        Trade(
            symbol="BTCUSDT",
            trade_id=12345,
            price=Decimal("0"),
            quantity=Decimal("0.1"),
            timestamp=datetime.now(UTC),
            is_buyer_maker=False,
        )

    # Zero/negative quantity should fail
    with pytest.raises(Exception):
        Trade(
            symbol="BTCUSDT",
            trade_id=12345,
            price=Decimal("50000"),
            quantity=Decimal("0"),
            timestamp=datetime.now(UTC),
            is_buyer_maker=False,
        )


def test_trade_optional_fields():
    """Test trade with optional fields."""
    # Minimal trade
    minimal_trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("0.1"),
        timestamp=datetime.now(UTC),
        is_buyer_maker=False,
    )
    assert minimal_trade.is_best_match is None
    assert minimal_trade.quote_quantity is None

    # Trade with all fields
    full_trade = Trade(
        symbol="BTCUSDT",
        trade_id=12345,
        price=Decimal("50000"),
        quantity=Decimal("0.1"),
        quote_quantity=Decimal("5000"),
        timestamp=datetime.now(UTC),
        is_buyer_maker=False,
        is_best_match=True,
    )
    assert full_trade.is_best_match is True
    assert full_trade.quote_quantity == Decimal("5000")
