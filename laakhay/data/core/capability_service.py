"""Capability service for validating data requests.

This module provides a service layer that wraps capability checks and
ensures consistent error handling with recommendations.
"""

from __future__ import annotations

from .capabilities import CapabilityKey, CapabilityStatus, supports
from .enums import DataFeature, InstrumentType, MarketType, TransportKind
from .exceptions import CapabilityError
from .request import DataRequest


class CapabilityService:
    """Service for validating capabilities and raising structured errors.

    This service wraps the capability store and provides consistent
    error handling with recommendations for unsupported capabilities.
    """

    @staticmethod
    def validate_request(request: DataRequest) -> CapabilityStatus:
        """Validate a DataRequest and return capability status.

        Args:
            request: DataRequest to validate

        Returns:
            CapabilityStatus indicating support status

        Raises:
            CapabilityError: If capability is unsupported, with recommendations
        """
        key = CapabilityKey(
            exchange=request.exchange,
            market_type=request.market_type,
            instrument_type=request.instrument_type,
            feature=request.feature,
            transport=request.transport,
            stream_variant=None,  # Could be extracted from request if needed
        )

        status = supports(
            feature=request.feature,
            transport=request.transport,
            exchange=request.exchange,
            market_type=request.market_type,
            instrument_type=request.instrument_type,
        )

        if not status.supported:
            raise CapabilityError(
                message=(
                    f"Capability not supported: {request.feature.value} "
                    f"({request.transport.value}) on {request.exchange} "
                    f"{request.market_type.value}/{request.instrument_type.value}. "
                    f"{status.reason or 'No reason provided'}"
                ),
                key=key,
                status=status,
                recommendations=status.recommendations,
            )

        return status

    @staticmethod
    def check_capability(
        feature: DataFeature,
        transport: TransportKind,
        *,
        exchange: str,
        market_type: MarketType,
        instrument_type: InstrumentType = InstrumentType.SPOT,
    ) -> CapabilityStatus:
        """Check if a capability is supported without raising an error.

        Args:
            feature: Data feature to check
            transport: Transport kind
            exchange: Exchange name
            market_type: Market type
            instrument_type: Instrument type

        Returns:
            CapabilityStatus indicating support status
        """
        return supports(
            feature=feature,
            transport=transport,
            exchange=exchange,
            market_type=market_type,
            instrument_type=instrument_type,
        )

    @staticmethod
    def get_capability_key(request: DataRequest) -> CapabilityKey:
        """Extract CapabilityKey from a DataRequest.

        Args:
            request: DataRequest to extract key from

        Returns:
            CapabilityKey for the request
        """
        return CapabilityKey(
            exchange=request.exchange,
            market_type=request.market_type,
            instrument_type=request.instrument_type,
            feature=request.feature,
            transport=request.transport,
            stream_variant=None,
        )
