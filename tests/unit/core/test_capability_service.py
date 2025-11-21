"""Precise unit tests for CapabilityService.

Tests focus on validation, error handling, and capability checking.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from laakhay.data.capability.service import CapabilityService
from laakhay.data.core.enums import (
    DataFeature,
    InstrumentType,
    MarketType,
    Timeframe,
    TransportKind,
)
from laakhay.data.core.exceptions import CapabilityError
from laakhay.data.core.request import DataRequest


class TestCapabilityServiceValidateRequest:
    """Test CapabilityService.validate_request method."""

    @patch("laakhay.data.capability.service.supports")
    def test_validate_request_supported(self, mock_supports):
        """Test validation passes for supported capability."""
        from laakhay.data.capability.registry import CapabilityStatus

        # Mock supported status
        mock_status = CapabilityStatus(supported=True, reason=None)
        mock_supports.return_value = mock_status

        request = DataRequest(
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
            symbol="BTC/USDT",
            timeframe=Timeframe.H1,
        )

        result = CapabilityService.validate_request(request)

        assert result == mock_status
        mock_supports.assert_called_once_with(
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
            instrument_type=InstrumentType.SPOT,
        )

    @patch("laakhay.data.capability.service.supports")
    def test_validate_request_unsupported_raises_error(self, mock_supports):
        """Test validation raises CapabilityError for unsupported capability."""
        from laakhay.data.capability.registry import CapabilityStatus

        # Mock unsupported status
        mock_status = CapabilityStatus(
            supported=False,
            reason="Feature not available on this exchange",
        )
        mock_supports.return_value = mock_status

        request = DataRequest(
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.REST,
            exchange="coinbase",
            market_type=MarketType.SPOT,  # Coinbase doesn't have futures
            symbol="BTC/USDT",
        )

        with pytest.raises(CapabilityError) as exc_info:
            CapabilityService.validate_request(request)

        assert "Capability not supported" in str(exc_info.value)
        assert "funding_rates" in str(exc_info.value)
        assert "coinbase" in str(exc_info.value)
        assert exc_info.value.status == mock_status

    @patch("laakhay.data.capability.service.supports")
    def test_validate_request_with_recommendations(self, mock_supports):
        """Test validation includes recommendations in error."""
        from laakhay.data.capability.registry import CapabilityStatus, FallbackOption

        # Mock unsupported status with recommendations
        recommendation = FallbackOption(
            exchange="binance",
            market_type=MarketType.FUTURES,
            instrument_type=InstrumentType.PERPETUAL,
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.REST,
            note="Use Binance futures for funding rates",
        )
        mock_status = CapabilityStatus(
            supported=False,
            reason="Not available on spot market",
            recommendations=[recommendation],
        )
        mock_supports.return_value = mock_status

        request = DataRequest(
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.REST,
            exchange="coinbase",
            market_type=MarketType.SPOT,
            symbol="BTC/USDT",
        )

        with pytest.raises(CapabilityError) as exc_info:
            CapabilityService.validate_request(request)

        assert len(exc_info.value.recommendations) == 1
        assert exc_info.value.recommendations[0] == recommendation


class TestCapabilityServiceCheckCapability:
    """Test CapabilityService.check_capability method."""

    @patch("laakhay.data.capability.service.supports")
    def test_check_capability_supported(self, mock_supports):
        """Test check_capability returns supported status."""
        from laakhay.data.capability.registry import CapabilityStatus

        mock_status = CapabilityStatus(supported=True, reason=None)
        mock_supports.return_value = mock_status

        result = CapabilityService.check_capability(
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
            instrument_type=InstrumentType.SPOT,
        )

        assert result == mock_status
        assert result.supported is True
        mock_supports.assert_called_once_with(
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
            instrument_type=InstrumentType.SPOT,
        )

    @patch("laakhay.data.capability.service.supports")
    def test_check_capability_unsupported_no_error(self, mock_supports):
        """Test check_capability returns unsupported status without raising."""
        from laakhay.data.capability.registry import CapabilityStatus

        mock_status = CapabilityStatus(
            supported=False,
            reason="Not supported",
        )
        mock_supports.return_value = mock_status

        result = CapabilityService.check_capability(
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.REST,
            exchange="coinbase",
            market_type=MarketType.SPOT,
        )

        assert result == mock_status
        assert result.supported is False
        # Should not raise an error

    @patch("laakhay.data.capability.service.supports")
    def test_check_capability_default_instrument_type(self, mock_supports):
        """Test check_capability uses SPOT as default instrument type."""
        from laakhay.data.capability.registry import CapabilityStatus

        mock_status = CapabilityStatus(supported=True)
        mock_supports.return_value = mock_status

        CapabilityService.check_capability(
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
            # instrument_type not provided
        )

        mock_supports.assert_called_once_with(
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
            instrument_type=InstrumentType.SPOT,  # Default
        )


class TestCapabilityServiceGetCapabilityKey:
    """Test CapabilityService.get_capability_key method."""

    def test_get_capability_key_extracts_all_fields(self):
        """Test get_capability_key extracts all fields from request."""
        request = DataRequest(
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
            exchange="binance",
            market_type=MarketType.SPOT,
            instrument_type=InstrumentType.SPOT,
            symbol="BTC/USDT",
            timeframe=Timeframe.H1,
        )

        key = CapabilityService.get_capability_key(request)

        assert key.exchange == "binance"
        assert key.market_type == MarketType.SPOT
        assert key.instrument_type == InstrumentType.SPOT
        assert key.feature == DataFeature.OHLCV
        assert key.transport == TransportKind.REST
        assert key.stream_variant is None

    def test_get_capability_key_futures_request(self):
        """Test get_capability_key with futures request."""
        request = DataRequest(
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.REST,
            exchange="binance",
            market_type=MarketType.FUTURES,
            instrument_type=InstrumentType.PERPETUAL,
            symbol="BTC/USDT",
        )

        key = CapabilityService.get_capability_key(request)

        assert key.market_type == MarketType.FUTURES
        assert key.instrument_type == InstrumentType.PERPETUAL
        assert key.feature == DataFeature.FUNDING_RATE
