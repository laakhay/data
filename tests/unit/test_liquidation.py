"""Unit tests for Liquidation model."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from laakhay.data.models.liquidation import Liquidation


class TestLiquidation:
    """Test Liquidation model."""

    def test_liquidation_valid(self):
        """Test valid Liquidation creation."""
        liquidation = Liquidation(
            symbol="BTCUSDT",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            side="SELL",
            order_type="LIQUIDATION",
            time_in_force="IOC",
            original_quantity=Decimal("1.5"),
            price=Decimal("50000.00"),
            average_price=Decimal("49950.00"),
            order_status="FILLED",
            last_filled_quantity=Decimal("1.5"),
            accumulated_quantity=Decimal("1.5"),
        )

        assert liquidation.symbol == "BTCUSDT"
        assert liquidation.side == "SELL"
        assert liquidation.original_quantity == Decimal("1.5")
        assert liquidation.price == Decimal("50000.00")
        assert liquidation.is_long_liquidation is True
        assert liquidation.is_short_liquidation is False

    def test_liquidation_with_optional_fields(self):
        """Test Liquidation creation with optional fields."""
        liquidation = Liquidation(
            symbol="ETHUSDT",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            side="BUY",
            order_type="LIQUIDATION",
            time_in_force="GTC",
            original_quantity=Decimal("10.0"),
            price=Decimal("3000.00"),
            average_price=Decimal("2995.00"),
            order_status="FILLED",
            last_filled_quantity=Decimal("10.0"),
            accumulated_quantity=Decimal("10.0"),
            commission=Decimal("0.1"),
            commission_asset="USDT",
            trade_id=12345,
        )

        assert liquidation.commission == Decimal("0.1")
        assert liquidation.commission_asset == "USDT"
        assert liquidation.trade_id == 12345
        assert liquidation.is_short_liquidation is True
        assert liquidation.is_long_liquidation is False

    def test_liquidation_side_validation(self):
        """Test side field validation."""
        # Valid sides
        for side in ["BUY", "SELL", "buy", "sell"]:
            liquidation = Liquidation(
                symbol="BTCUSDT",
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                side=side,
                order_type="LIQUIDATION",
                time_in_force="IOC",
                original_quantity=Decimal("1.0"),
                price=Decimal("50000.00"),
                average_price=Decimal("50000.00"),
                order_status="FILLED",
                last_filled_quantity=Decimal("1.0"),
                accumulated_quantity=Decimal("1.0"),
            )
            assert liquidation.side == side.upper()

        # Invalid side
        with pytest.raises(ValueError, match="side must be 'BUY' or 'SELL'"):
            Liquidation(
                symbol="BTCUSDT",
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                side="INVALID",
                order_type="LIQUIDATION",
                time_in_force="IOC",
                original_quantity=Decimal("1.0"),
                price=Decimal("50000.00"),
                average_price=Decimal("50000.00"),
                order_status="FILLED",
                last_filled_quantity=Decimal("1.0"),
                accumulated_quantity=Decimal("1.0"),
            )

    def test_liquidation_price_validation(self):
        """Test price validation."""
        # Valid prices
        liquidation = Liquidation(
            symbol="BTCUSDT",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            side="SELL",
            order_type="LIQUIDATION",
            time_in_force="IOC",
            original_quantity=Decimal("1.0"),
            price=Decimal("0.01"),  # Very small price
            average_price=Decimal("0.01"),
            order_status="FILLED",
            last_filled_quantity=Decimal("1.0"),
            accumulated_quantity=Decimal("1.0"),
        )
        assert liquidation.price == Decimal("0.01")

        # Invalid prices (zero or negative)
        with pytest.raises(Exception):  # Pydantic validation error
            Liquidation(
                symbol="BTCUSDT",
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                side="SELL",
                order_type="LIQUIDATION",
                time_in_force="IOC",
                original_quantity=Decimal("1.0"),
                price=Decimal("0"),  # Zero price
                average_price=Decimal("50000.00"),
                order_status="FILLED",
                last_filled_quantity=Decimal("1.0"),
                accumulated_quantity=Decimal("1.0"),
            )

    def test_liquidation_quantity_validation(self):
        """Test quantity validation."""
        # Valid quantities
        liquidation = Liquidation(
            symbol="BTCUSDT",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            side="SELL",
            order_type="LIQUIDATION",
            time_in_force="IOC",
            original_quantity=Decimal("0.001"),  # Very small quantity
            price=Decimal("50000.00"),
            average_price=Decimal("50000.00"),
            order_status="FILLED",
            last_filled_quantity=Decimal("0"),  # Zero is allowed for last_filled
            accumulated_quantity=Decimal("0.001"),
        )
        assert liquidation.original_quantity == Decimal("0.001")

        # Invalid quantities (negative)
        with pytest.raises(Exception):  # Pydantic validation error
            Liquidation(
                symbol="BTCUSDT",
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                side="SELL",
                order_type="LIQUIDATION",
                time_in_force="IOC",
                original_quantity=Decimal("-1.0"),  # Negative quantity
                price=Decimal("50000.00"),
                average_price=Decimal("50000.00"),
                order_status="FILLED",
                last_filled_quantity=Decimal("1.0"),
                accumulated_quantity=Decimal("1.0"),
            )

    def test_liquidation_properties(self):
        """Test liquidation properties."""
        liquidation = Liquidation(
            symbol="BTCUSDT",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            side="SELL",
            order_type="LIQUIDATION",
            time_in_force="IOC",
            original_quantity=Decimal("2.1"),
            price=Decimal("50000.00"),
            average_price=Decimal("49950.00"),
            order_status="FILLED",
            last_filled_quantity=Decimal("2.1"),
            accumulated_quantity=Decimal("2.1"),
        )

        # Test timestamp_ms property
        expected_ms = int(datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
        assert liquidation.timestamp_ms == expected_ms

        # Test value_usdt property
        expected_value = Decimal("2.1") * Decimal("50000.00")  # 105,000
        assert liquidation.value_usdt == expected_value

        # Test liquidation type properties
        assert liquidation.is_long_liquidation is True
        assert liquidation.is_short_liquidation is False

        # Test large liquidation (value = $105k, should be large)
        assert liquidation.value_usdt == Decimal("105000")
        assert liquidation.is_large is True

    def test_liquidation_age_and_freshness(self):
        """Test age and freshness methods."""
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        recent_time = now - timedelta(minutes=1)  # 1 minute ago
        old_time = now - timedelta(minutes=10)  # 10 minutes ago

        # Recent liquidation
        recent_liquidation = Liquidation(
            symbol="BTCUSDT",
            timestamp=recent_time,
            side="SELL",
            order_type="LIQUIDATION",
            time_in_force="IOC",
            original_quantity=Decimal("1.0"),
            price=Decimal("50000.00"),
            average_price=Decimal("50000.00"),
            order_status="FILLED",
            last_filled_quantity=Decimal("1.0"),
            accumulated_quantity=Decimal("1.0"),
        )

        assert recent_liquidation.get_age_seconds() < 120  # Less than 2 minutes
        assert recent_liquidation.is_fresh(max_age_seconds=300) is True

        # Old liquidation
        old_liquidation = Liquidation(
            symbol="BTCUSDT",
            timestamp=old_time,
            side="SELL",
            order_type="LIQUIDATION",
            time_in_force="IOC",
            original_quantity=Decimal("1.0"),
            price=Decimal("50000.00"),
            average_price=Decimal("50000.00"),
            order_status="FILLED",
            last_filled_quantity=Decimal("1.0"),
            accumulated_quantity=Decimal("1.0"),
        )

        assert old_liquidation.get_age_seconds() > 300  # More than 5 minutes
        assert old_liquidation.is_fresh(max_age_seconds=300) is False

    def test_liquidation_to_dict(self):
        """Test to_dict method."""
        liquidation = Liquidation(
            symbol="BTCUSDT",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            side="SELL",
            order_type="LIQUIDATION",
            time_in_force="IOC",
            original_quantity=Decimal("1.5"),
            price=Decimal("50000.00"),
            average_price=Decimal("49950.00"),
            order_status="FILLED",
            last_filled_quantity=Decimal("1.5"),
            accumulated_quantity=Decimal("1.5"),
            commission=Decimal("0.075"),
            commission_asset="USDT",
            trade_id=12345,
        )

        data = liquidation.to_dict()

        assert data["symbol"] == "BTCUSDT"
        assert data["side"] == "SELL"
        assert data["original_quantity"] == "1.5"
        assert data["price"] == "50000.00"
        assert data["commission"] == "0.075"
        assert data["commission_asset"] == "USDT"
        assert data["trade_id"] == 12345
        assert data["timestamp"] == "2024-01-01T12:00:00+00:00"

    def test_liquidation_immutable(self):
        """Test that liquidation is immutable."""
        liquidation = Liquidation(
            symbol="BTCUSDT",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            side="SELL",
            order_type="LIQUIDATION",
            time_in_force="IOC",
            original_quantity=Decimal("1.0"),
            price=Decimal("50000.00"),
            average_price=Decimal("50000.00"),
            order_status="FILLED",
            last_filled_quantity=Decimal("1.0"),
            accumulated_quantity=Decimal("1.0"),
        )

        # Should raise ValidationError when trying to modify (Pydantic frozen)
        with pytest.raises(Exception):  # Pydantic frozen validation error
            liquidation.symbol = "ETHUSDT"

        with pytest.raises(Exception):  # Pydantic frozen validation error
            liquidation.price = Decimal("60000.00")

    def test_liquidation_edge_cases(self):
        """Test edge cases for liquidation."""
        # Very small liquidation
        small_liquidation = Liquidation(
            symbol="BTCUSDT",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            side="SELL",
            order_type="LIQUIDATION",
            time_in_force="IOC",
            original_quantity=Decimal("0.000001"),
            price=Decimal("50000.00"),
            average_price=Decimal("50000.00"),
            order_status="FILLED",
            last_filled_quantity=Decimal("0.000001"),
            accumulated_quantity=Decimal("0.000001"),
        )

        assert small_liquidation.value_usdt == Decimal("0.05")  # $0.05
        assert small_liquidation.is_large is False

        # Partial fill liquidation
        partial_liquidation = Liquidation(
            symbol="BTCUSDT",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            side="BUY",
            order_type="LIQUIDATION",
            time_in_force="IOC",
            original_quantity=Decimal("2.0"),
            price=Decimal("50000.00"),
            average_price=Decimal("49950.00"),
            order_status="PARTIALLY_FILLED",
            last_filled_quantity=Decimal("1.5"),
            accumulated_quantity=Decimal("1.5"),
        )

        assert partial_liquidation.last_filled_quantity < partial_liquidation.original_quantity
        assert partial_liquidation.accumulated_quantity == partial_liquidation.last_filled_quantity
