"""Custom exception hierarchy."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .capabilities import CapabilityKey, CapabilityStatus, FallbackOption
    from .enums import MarketType


class DataError(Exception):
    """Base exception for all library errors."""

    pass


class CapabilityError(DataError):
    """Capability is unsupported or unavailable.

    Raised when a requested feature/transport/instrument combination
    is not supported by the exchange. Includes recommendations for alternatives.
    """

    def __init__(
        self,
        message: str,
        key: CapabilityKey | None = None,
        status: CapabilityStatus | None = None,
        recommendations: list[FallbackOption] | None = None,
    ) -> None:
        super().__init__(message)
        self.key = key
        self.status = status
        self.recommendations = recommendations or []


class ProviderError(DataError):
    """Error from external data provider."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(ProviderError):
    """Provider rate limit exceeded."""

    def __init__(self, message: str, retry_after: int = 60) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class InvalidSymbolError(ProviderError):
    """Symbol does not exist or is not tradeable."""

    pass


class InvalidIntervalError(ProviderError):
    """Time interval not supported by provider."""

    pass


class ValidationError(DataError):
    """Data validation failure."""

    pass


class SymbolResolutionError(DataError):
    """Symbol cannot be resolved or converted.

    Raised when URM cannot resolve a symbol to/from exchange format.
    """

    def __init__(
        self,
        message: str,
        *,
        exchange: str | None = None,
        value: str | None = None,
        market_type: MarketType | None = None,
        known_aliases: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.exchange = exchange
        self.value = value
        self.market_type = market_type
        self.known_aliases = known_aliases or {}


class RelayError(DataError):
    """Error emitted by StreamRelay when a sink fails repeatedly."""

    def __init__(
        self,
        message: str,
        *,
        sink_name: str | None = None,
        consecutive_failures: int = 0,
    ) -> None:
        super().__init__(message)
        self.sink_name = sink_name
        self.consecutive_failures = consecutive_failures
