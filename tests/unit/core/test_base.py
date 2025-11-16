"""Precise unit tests for BaseProvider.

Tests focus on validation methods, context manager, and capability description.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from laakhay.data.core.base import BaseProvider
from laakhay.data.core.enums import (
    DataFeature,
    InstrumentType,
    MarketType,
    Timeframe,
    TransportKind,
)
from laakhay.data.models.bar import Bar
from laakhay.data.models.ohlcv import OHLCV
from laakhay.data.models.series_meta import SeriesMeta


class ConcreteProvider(BaseProvider):
    """Concrete implementation for testing."""

    def __init__(self, name: str = "test"):
        super().__init__(name)

    async def get_candles(
        self,
        symbol: str,
        interval: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> OHLCV:
        """Implement get_candles."""
        bars = [
            Bar(
                symbol=symbol,
                timestamp=datetime.now(),
                open=50000.0,
                high=51000.0,
                low=49000.0,
                close=50500.0,
                volume=100.0,
            )
        ]
        meta = SeriesMeta(
            symbol=symbol,
            timeframe=interval,
            exchange=self.name,
            market_type=MarketType.SPOT,
            count=1,
        )
        return OHLCV(bars=bars, meta=meta)

    async def get_symbols(self) -> list[dict]:
        """Implement get_symbols."""
        return [{"symbol": "BTCUSDT"}]

    async def close(self) -> None:
        """Implement close."""
        self._closed = True


class TestBaseProvider:
    """Test BaseProvider base class."""

    def test_init(self):
        """Test BaseProvider initialization."""
        provider = ConcreteProvider("test_provider")
        assert provider.name == "test_provider"
        assert provider._session is None

    def test_validate_symbol_valid(self):
        """Test symbol validation with valid symbol."""
        provider = ConcreteProvider()
        provider.validate_symbol("BTC/USDT")  # Should not raise

    def test_validate_symbol_empty_string(self):
        """Test symbol validation raises error for empty string."""
        provider = ConcreteProvider()
        with pytest.raises(ValueError, match="Symbol must be a non-empty string"):
            provider.validate_symbol("")

    def test_validate_symbol_none(self):
        """Test symbol validation raises error for None."""
        provider = ConcreteProvider()
        with pytest.raises(ValueError, match="Symbol must be a non-empty string"):
            provider.validate_symbol(None)  # type: ignore

    def test_validate_symbol_non_string(self):
        """Test symbol validation raises error for non-string."""
        provider = ConcreteProvider()
        with pytest.raises(ValueError, match="Symbol must be a non-empty string"):
            provider.validate_symbol(123)  # type: ignore

    def test_validate_interval_no_override(self):
        """Test validate_interval does nothing by default."""
        provider = ConcreteProvider()
        provider.validate_interval(Timeframe.H1)  # Should not raise

    @pytest.mark.asyncio
    async def test_describe_capabilities_default(self):
        """Test default describe_capabilities implementation."""
        provider = ConcreteProvider()

        status = await provider.describe_capabilities(
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
            market_type=MarketType.SPOT,
            instrument_type=InstrumentType.SPOT,
        )

        assert status.supported is False
        assert "Runtime capability discovery not implemented" in status.reason
        assert status.source == "static"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test BaseProvider as async context manager."""
        provider = ConcreteProvider()
        async with provider as p:
            assert p is provider

        # After context exit, close should be called
        assert provider._closed is True

    @pytest.mark.asyncio
    async def test_context_manager_exception_handling(self):
        """Test context manager handles exceptions."""
        provider = ConcreteProvider()

        # Make close raise an exception
        provider.close = AsyncMock(side_effect=Exception("Close error"))

        try:
            async with provider:
                pass
        except Exception:
            pass  # Exception should be handled

        # Verify close was called
        provider.close.assert_called_once()
