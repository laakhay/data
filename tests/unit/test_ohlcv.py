"""Unit tests for OHLCV model."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from laakhay.data.models import OHLCV, Bar, SeriesMeta


def test_ohlcv_empty():
    """Test empty OHLCV creation."""
    meta = SeriesMeta(symbol="BTCUSDT", timeframe="1m")
    ohlcv = OHLCV(meta=meta, bars=[])

    assert ohlcv.meta == meta
    assert len(ohlcv) == 0
    assert ohlcv.is_empty is True
    assert ohlcv.latest is None
    assert ohlcv.earliest is None


def test_ohlcv_with_bars():
    """Test OHLCV with bars."""
    meta = SeriesMeta(symbol="BTCUSDT", timeframe="1m")

    bar1 = Bar(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
    )

    bar2 = Bar(
        timestamp=datetime(2024, 1, 1, 12, 1, tzinfo=timezone.utc),
        open=Decimal("50500"),
        high=Decimal("52000"),
        low=Decimal("50000"),
        close=Decimal("51500"),
        volume=Decimal("150"),
    )

    ohlcv = OHLCV(meta=meta, bars=[bar1, bar2])

    assert len(ohlcv) == 2
    assert ohlcv.is_empty is False
    assert ohlcv.latest == bar2
    assert ohlcv.earliest == bar1


def test_ohlcv_access_methods():
    """Test OHLCV access methods."""
    meta = SeriesMeta(symbol="BTCUSDT", timeframe="1m")

    bar1 = Bar(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
    )

    bar2 = Bar(
        timestamp=datetime(2024, 1, 1, 12, 1, tzinfo=timezone.utc),
        open=Decimal("50500"),
        high=Decimal("52000"),
        low=Decimal("50000"),
        close=Decimal("51500"),
        volume=Decimal("150"),
    )

    ohlcv = OHLCV(meta=meta, bars=[bar1, bar2])

    # Test indexing
    assert ohlcv[0] == bar1
    assert ohlcv[1] == bar2

    # Test iteration
    bars_list = list(ohlcv)
    assert bars_list == [bar1, bar2]


def test_ohlcv_time_range():
    """Test time range properties."""
    meta = SeriesMeta(symbol="BTCUSDT", timeframe="1m")

    bar1 = Bar(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
    )

    bar2 = Bar(
        timestamp=datetime(2024, 1, 1, 12, 1, tzinfo=timezone.utc),
        open=Decimal("50500"),
        high=Decimal("52000"),
        low=Decimal("50000"),
        close=Decimal("51500"),
        volume=Decimal("150"),
    )

    ohlcv = OHLCV(meta=meta, bars=[bar1, bar2])

    assert ohlcv.start_time == bar1.timestamp
    assert ohlcv.end_time == bar2.timestamp


def test_ohlcv_price_statistics():
    """Test price statistics."""
    meta = SeriesMeta(symbol="BTCUSDT", timeframe="1m")

    bar1 = Bar(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
    )

    bar2 = Bar(
        timestamp=datetime(2024, 1, 1, 12, 1, tzinfo=timezone.utc),
        open=Decimal("50500"),
        high=Decimal("52000"),
        low=Decimal("50000"),
        close=Decimal("51500"),
        volume=Decimal("150"),
    )

    ohlcv = OHLCV(meta=meta, bars=[bar1, bar2])

    assert ohlcv.highest_price == Decimal("52000")
    assert ohlcv.lowest_price == Decimal("49000")
    assert ohlcv.total_volume == Decimal("250")


def test_ohlcv_filtering():
    """Test filtering methods."""
    meta = SeriesMeta(symbol="BTCUSDT", timeframe="1m")

    bar1 = Bar(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
        is_closed=True,
    )

    bar2 = Bar(
        timestamp=datetime(2024, 1, 1, 12, 1, tzinfo=timezone.utc),
        open=Decimal("50500"),
        high=Decimal("52000"),
        low=Decimal("50000"),
        close=Decimal("51500"),
        volume=Decimal("150"),
        is_closed=False,  # Open bar
    )

    ohlcv = OHLCV(meta=meta, bars=[bar1, bar2])

    # Test get_closed_bars
    closed_bars = ohlcv.get_closed_bars()
    assert len(closed_bars) == 1
    assert closed_bars.bars[0] == bar1

    # Test get_open_bars
    open_bars = ohlcv.get_open_bars()
    assert len(open_bars) == 1
    assert open_bars.bars[0] == bar2

    # Test get_last_n_bars
    last_1 = ohlcv.get_last_n_bars(1)
    assert len(last_1) == 1
    assert last_1.bars[0] == bar2


def test_ohlcv_validation():
    """Test OHLCV validation."""
    meta = SeriesMeta(symbol="BTCUSDT", timeframe="1m")

    bar1 = Bar(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
    )

    bar2 = Bar(
        timestamp=datetime(2024, 1, 1, 11, 59, tzinfo=timezone.utc),  # Earlier timestamp
        open=Decimal("50500"),
        high=Decimal("52000"),
        low=Decimal("50000"),
        close=Decimal("51500"),
        volume=Decimal("150"),
    )

    # Should raise validation error for unsorted bars
    with pytest.raises(Exception):  # ValidationError
        OHLCV(meta=meta, bars=[bar1, bar2])


def test_ohlcv_conversion():
    """Test OHLCV conversion methods."""
    meta = SeriesMeta(symbol="BTCUSDT", timeframe="1m")

    bar = Bar(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("100"),
    )

    ohlcv = OHLCV(meta=meta, bars=[bar])

    # Test to_dict
    data = ohlcv.to_dict()
    assert data["meta"]["symbol"] == "BTCUSDT"
    assert data["meta"]["timeframe"] == "1m"
    assert len(data["bars"]) == 1
    assert data["bars"][0]["open"] == "50000"

    # Test from_dict
    reconstructed = OHLCV.from_dict(data)
    assert reconstructed.meta.symbol == "BTCUSDT"
    assert reconstructed.meta.timeframe == "1m"
    assert len(reconstructed.bars) == 1
    assert reconstructed.bars[0].open == Decimal("50000")
