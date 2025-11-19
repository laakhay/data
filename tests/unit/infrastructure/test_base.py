"""Unit tests for BaseProvider ABC."""

import pytest

from laakhay.data import OHLCV, BaseProvider


def test_cannot_instantiate():
    """Test BaseProvider cannot be instantiated."""
    with pytest.raises(TypeError):
        BaseProvider("test")


def test_validate_symbol_valid():
    """Test validate_symbol with valid input."""
    # We need a concrete subclass to test instance methods
    from datetime import datetime

    from laakhay.data import Timeframe

    class TestProvider(BaseProvider):
        async def fetch_ohlcv(
            self,
            symbol: str,
            interval: Timeframe,
            start_time: datetime | None = None,
            end_time: datetime | None = None,
            limit: int | None = None,
        ) -> OHLCV:
            from laakhay.data.models import SeriesMeta

            return OHLCV(meta=SeriesMeta(symbol="TEST", timeframe=interval.value), bars=[])

        async def get_symbols(self) -> list[dict]:
            return [{"symbol": "TEST", "status": "TRADING"}]

        async def close(self) -> None:
            pass

    provider = TestProvider("test")
    provider.validate_symbol("BTCUSDT")  # Should not raise


def test_validate_symbol_invalid():
    """Test validate_symbol with invalid input."""
    from datetime import datetime

    from laakhay.data import Timeframe

    class TestProvider(BaseProvider):
        async def fetch_ohlcv(
            self,
            symbol: str,
            interval: Timeframe,
            start_time: datetime | None = None,
            end_time: datetime | None = None,
            limit: int | None = None,
        ) -> OHLCV:
            from laakhay.data.models import SeriesMeta

            return OHLCV(meta=SeriesMeta(symbol="TEST", timeframe=interval.value), bars=[])

        async def get_symbols(self) -> list[dict]:
            return [{"symbol": "TEST", "status": "TRADING"}]

        async def close(self) -> None:
            pass

    provider = TestProvider("test")

    with pytest.raises(ValueError, match="non-empty string"):
        provider.validate_symbol("")

    with pytest.raises(ValueError, match="non-empty string"):
        provider.validate_symbol(None)
