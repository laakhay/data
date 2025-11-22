"""Unit tests for core enums."""

from laakhay.data.core import MarketType, MarketVariant, Timeframe


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


# MarketVariant tests
def test_market_variant_values():
    """Test MarketVariant enum values."""
    assert MarketVariant.SPOT.value == "spot"
    assert MarketVariant.LINEAR_PERP.value == "linear_perp"
    assert MarketVariant.INVERSE_PERP.value == "inverse_perp"
    assert MarketVariant.LINEAR_DELIVERY.value == "linear_delivery"
    assert MarketVariant.INVERSE_DELIVERY.value == "inverse_delivery"
    assert MarketVariant.OPTIONS.value == "options"
    assert MarketVariant.EQUITY.value == "equity"


def test_market_variant_from_market_type_spot():
    """Test from_market_type for SPOT."""
    assert MarketVariant.from_market_type(MarketType.SPOT) == MarketVariant.SPOT


def test_market_variant_from_market_type_futures_default():
    """Test from_market_type for FUTURES defaults to LINEAR_PERP."""
    assert MarketVariant.from_market_type(MarketType.FUTURES) == MarketVariant.LINEAR_PERP


def test_market_variant_from_market_type_futures_with_default():
    """Test from_market_type for FUTURES with explicit default."""
    assert (
        MarketVariant.from_market_type(MarketType.FUTURES, MarketVariant.INVERSE_PERP)
        == MarketVariant.INVERSE_PERP
    )


def test_market_variant_from_market_type_options():
    """Test from_market_type for OPTIONS."""
    assert MarketVariant.from_market_type(MarketType.OPTIONS) == MarketVariant.OPTIONS


def test_market_variant_from_market_type_equity():
    """Test from_market_type for EQUITY."""
    assert MarketVariant.from_market_type(MarketType.EQUITY) == MarketVariant.EQUITY


def test_market_variant_from_market_type_fx():
    """Test from_market_type for FX maps to SPOT."""
    assert MarketVariant.from_market_type(MarketType.FX) == MarketVariant.SPOT


def test_market_variant_to_market_type_spot():
    """Test to_market_type for spot variants."""
    assert MarketVariant.SPOT.to_market_type() == MarketType.SPOT


def test_market_variant_to_market_type_futures():
    """Test to_market_type for futures variants."""
    assert MarketVariant.LINEAR_PERP.to_market_type() == MarketType.FUTURES
    assert MarketVariant.INVERSE_PERP.to_market_type() == MarketType.FUTURES
    assert MarketVariant.LINEAR_DELIVERY.to_market_type() == MarketType.FUTURES
    assert MarketVariant.INVERSE_DELIVERY.to_market_type() == MarketType.FUTURES


def test_market_variant_to_market_type_options():
    """Test to_market_type for OPTIONS."""
    assert MarketVariant.OPTIONS.to_market_type() == MarketType.OPTIONS


def test_market_variant_to_market_type_equity():
    """Test to_market_type for EQUITY."""
    assert MarketVariant.EQUITY.to_market_type() == MarketType.EQUITY


def test_market_variant_str():
    """Test string representation."""
    assert str(MarketVariant.SPOT) == "spot"
    assert str(MarketVariant.LINEAR_PERP) == "linear_perp"
