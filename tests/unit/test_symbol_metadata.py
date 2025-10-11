"""Unit tests for Symbol metadata helpers and provider caching."""

from decimal import Decimal

from laakhay.data.models import Symbol


def test_round_price_and_quantity_with_constraints():
    s = Symbol(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        tick_size=Decimal("0.10"),
        step_size=Decimal("0.001"),
        min_notional=Decimal("5"),
    )

    assert s.round_price(Decimal("42123.19")) == Decimal("42123.10")
    assert s.round_quantity(Decimal("0.123456")) == Decimal("0.123")

    # Valid order respects tick/step and min_notional
    assert s.is_valid_order(Decimal("42123.10"), Decimal("0.001"))

    # Invalid due to price not aligned
    assert not s.is_valid_order(Decimal("42123.11"), Decimal("0.001"))

    # Invalid due to qty not aligned
    assert not s.is_valid_order(Decimal("42123.10"), Decimal("0.0012"))

    # Invalid due to min notional
    assert not s.is_valid_order(Decimal("1.0"), Decimal("0.001"))


def test_round_helpers_without_constraints_return_identity():
    s = Symbol(symbol="ETHUSDT", base_asset="ETH", quote_asset="USDT")
    from decimal import Decimal
    assert s.round_price(Decimal("123.456")) == Decimal("123.456")
    assert s.round_quantity(Decimal("0.789")) == Decimal("0.789")
