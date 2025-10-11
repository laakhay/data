"""Unit tests for OrderBook model."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from laakhay.data.models.order_book import OrderBook


def test_orderbook_valid():
    """Test valid OrderBook creation."""
    ob = OrderBook(
        symbol="BTCUSDT",
        last_update_id=123456,
        bids=[(Decimal("50000"), Decimal("1.5")), (Decimal("49900"), Decimal("2.0"))],
        asks=[(Decimal("50100"), Decimal("1.0")), (Decimal("50200"), Decimal("1.5"))],
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
    )
    
    assert ob.symbol == "BTCUSDT"
    assert len(ob.bids) == 2
    assert len(ob.asks) == 2


def test_orderbook_best_prices():
    """Test best bid/ask prices."""
    ob = OrderBook(
        symbol="BTCUSDT",
        last_update_id=123456,
        bids=[(Decimal("50000"), Decimal("1")), (Decimal("49900"), Decimal("2"))],
        asks=[(Decimal("50100"), Decimal("1")), (Decimal("50200"), Decimal("2"))],
        timestamp=datetime.now(timezone.utc),
    )
    
    assert ob.best_bid_price == Decimal("50000")
    assert ob.best_ask_price == Decimal("50100")
    assert ob.best_bid_qty == Decimal("1")
    assert ob.best_ask_qty == Decimal("1")


def test_orderbook_spread():
    """Test spread calculations."""
    ob = OrderBook(
        symbol="BTCUSDT",
        last_update_id=123456,
        bids=[(Decimal("50000"), Decimal("1"))],
        asks=[(Decimal("50100"), Decimal("1"))],
        timestamp=datetime.now(timezone.utc),
    )
    
    assert ob.spread == Decimal("100")
    assert ob.mid_price == Decimal("50050")
    
    # Spread in bps: (100 / 50050) * 10000 ≈ 19.98
    assert 19 < ob.spread_bps < 21
    
    # Spread percentage: (100 / 50050) * 100 ≈ 0.1998
    assert Decimal("0.19") < ob.spread_percentage < Decimal("0.21")


def test_orderbook_tight_wide_spread():
    """Test tight/wide spread detection."""
    # Tight spread < 10 bps
    tight_ob = OrderBook(
        symbol="BTCUSDT",
        last_update_id=123456,
        bids=[(Decimal("50000"), Decimal("1"))],
        asks=[(Decimal("50001"), Decimal("1"))],  # 1 dollar spread
        timestamp=datetime.now(timezone.utc),
    )
    assert tight_ob.is_tight_spread is True
    assert tight_ob.is_wide_spread is False
    
    # Wide spread > 50 bps
    wide_ob = OrderBook(
        symbol="BTCUSDT",
        last_update_id=123456,
        bids=[(Decimal("50000"), Decimal("1"))],
        asks=[(Decimal("50300"), Decimal("1"))],  # 300 dollar spread
        timestamp=datetime.now(timezone.utc),
    )
    assert wide_ob.is_tight_spread is False
    assert wide_ob.is_wide_spread is True


def test_orderbook_volume():
    """Test volume calculations."""
    ob = OrderBook(
        symbol="BTCUSDT",
        last_update_id=123456,
        bids=[(Decimal("50000"), Decimal("1")), (Decimal("49900"), Decimal("2"))],
        asks=[(Decimal("50100"), Decimal("1")), (Decimal("50200"), Decimal("1.5"))],
        timestamp=datetime.now(timezone.utc),
    )
    
    assert ob.total_bid_volume == Decimal("3")  # 1 + 2
    assert ob.total_ask_volume == Decimal("2.5")  # 1 + 1.5


def test_orderbook_value():
    """Test value calculations."""
    ob = OrderBook(
        symbol="BTCUSDT",
        last_update_id=123456,
        bids=[(Decimal("50000"), Decimal("1")), (Decimal("49900"), Decimal("2"))],
        asks=[(Decimal("50100"), Decimal("1")), (Decimal("50200"), Decimal("1.5"))],
        timestamp=datetime.now(timezone.utc),
    )
    
    # Bid value: 50000*1 + 49900*2 = 149800
    assert ob.total_bid_value == Decimal("149800")
    
    # Ask value: 50100*1 + 50200*1.5 = 125400
    assert ob.total_ask_value == Decimal("125400")


def test_orderbook_imbalance():
    """Test order book imbalance calculation."""
    # Balanced book
    balanced_ob = OrderBook(
        symbol="BTCUSDT",
        last_update_id=123456,
        bids=[(Decimal("50000"), Decimal("5"))],
        asks=[(Decimal("50100"), Decimal("5"))],
        timestamp=datetime.now(timezone.utc),
    )
    assert balanced_ob.imbalance == Decimal("0")
    assert balanced_ob.market_pressure == "neutral"
    
    # Bid-heavy (bullish)
    bid_heavy_ob = OrderBook(
        symbol="BTCUSDT",
        last_update_id=123456,
        bids=[(Decimal("50000"), Decimal("8"))],
        asks=[(Decimal("50100"), Decimal("2"))],
        timestamp=datetime.now(timezone.utc),
    )
    assert bid_heavy_ob.imbalance > Decimal("0")
    assert bid_heavy_ob.is_bid_heavy is True
    assert bid_heavy_ob.market_pressure == "bullish"
    
    # Ask-heavy (bearish)
    ask_heavy_ob = OrderBook(
        symbol="BTCUSDT",
        last_update_id=123456,
        bids=[(Decimal("50000"), Decimal("2"))],
        asks=[(Decimal("50100"), Decimal("8"))],
        timestamp=datetime.now(timezone.utc),
    )
    assert ask_heavy_ob.imbalance < Decimal("0")
    assert ask_heavy_ob.is_ask_heavy is True
    assert ask_heavy_ob.market_pressure == "bearish"


def test_orderbook_depth_percentage():
    """Test depth within percentage range."""
    ob = OrderBook(
        symbol="BTCUSDT",
        last_update_id=123456,
        bids=[
            (Decimal("50000"), Decimal("1")),
            (Decimal("49900"), Decimal("2")),  # 0.2% away
            (Decimal("49500"), Decimal("5")),  # 1% away
        ],
        asks=[
            (Decimal("50100"), Decimal("1")),
            (Decimal("50200"), Decimal("2")),  # 0.2% away
            (Decimal("50600"), Decimal("5")),  # 1% away
        ],
        timestamp=datetime.now(timezone.utc),
    )
    
    # Within 0.5% of mid price
    depth = ob.get_depth_percentage(Decimal("0.5"))
    assert depth["bid_volume"] == Decimal("3")  # 50000 and 49900 levels
    assert depth["ask_volume"] == Decimal("3")  # 50100 and 50200 levels


def test_orderbook_is_fresh():
    """Test freshness check."""
    # Fresh orderbook
    fresh_ob = OrderBook(
        symbol="BTCUSDT",
        last_update_id=123456,
        bids=[(Decimal("50000"), Decimal("1"))],
        asks=[(Decimal("50100"), Decimal("1"))],
        timestamp=datetime.now(timezone.utc),
    )
    assert fresh_ob.is_fresh(max_age_seconds=10) is True
    
    # Stale orderbook
    from datetime import timedelta
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=30)
    stale_ob = OrderBook(
        symbol="BTCUSDT",
        last_update_id=123456,
        bids=[(Decimal("50000"), Decimal("1"))],
        asks=[(Decimal("50100"), Decimal("1"))],
        timestamp=stale_time,
    )
    assert stale_ob.is_fresh(max_age_seconds=10) is False


def test_orderbook_to_dict():
    """Test to_dict conversion."""
    ob = OrderBook(
        symbol="BTCUSDT",
        last_update_id=123456,
        bids=[(Decimal("50000"), Decimal("1"))],
        asks=[(Decimal("50100"), Decimal("1"))],
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
    )
    
    data = ob.to_dict(include_levels=False)
    assert data["symbol"] == "BTCUSDT"
    assert data["spread"] == "100"
    assert data["bid_levels"] == 1
    assert data["ask_levels"] == 1
    
    # With levels
    data_with_levels = ob.to_dict(include_levels=True)
    assert "bids" in data_with_levels
    assert "asks" in data_with_levels
    assert len(data_with_levels["bids"]) == 1


def test_orderbook_frozen():
    """Test that OrderBook is immutable."""
    ob = OrderBook(
        symbol="BTCUSDT",
        last_update_id=123456,
        bids=[(Decimal("50000"), Decimal("1"))],
        asks=[(Decimal("50100"), Decimal("1"))],
        timestamp=datetime.now(timezone.utc),
    )
    
    with pytest.raises(Exception):  # Pydantic frozen validation error
        ob.symbol = "ETHUSDT"


def test_orderbook_validation():
    """Test model validation."""
    # Empty symbol should fail
    with pytest.raises(Exception):
        OrderBook(
            symbol="",
            last_update_id=123456,
            bids=[(Decimal("50000"), Decimal("1"))],
            asks=[(Decimal("50100"), Decimal("1"))],
            timestamp=datetime.now(timezone.utc),
        )
    
    # Empty bids/asks should fail
    with pytest.raises(Exception):
        OrderBook(
            symbol="BTCUSDT",
            last_update_id=123456,
            bids=[],
            asks=[(Decimal("50100"), Decimal("1"))],
            timestamp=datetime.now(timezone.utc),
        )
    
    # Invalid price (non-positive) should fail
    with pytest.raises(Exception):
        OrderBook(
            symbol="BTCUSDT",
            last_update_id=123456,
            bids=[(Decimal("-50000"), Decimal("1"))],
            asks=[(Decimal("50100"), Decimal("1"))],
            timestamp=datetime.now(timezone.utc),
        )


def test_orderbook_depth_score():
    """Test depth score categorization."""
    # Create small depth (thin market)
    thin_ob = OrderBook(
        symbol="BTCUSDT",
        last_update_id=123456,
        bids=[(Decimal("50000"), Decimal("0.001"))],  # $50 worth
        asks=[(Decimal("50100"), Decimal("0.001"))],
        timestamp=datetime.now(timezone.utc),
    )
    assert thin_ob.depth_score in ["thin", "moderate", "deep"]

