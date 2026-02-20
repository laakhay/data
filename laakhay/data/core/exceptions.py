"""Custom exception hierarchy.

Architecture:
    This module defines a structured exception hierarchy for the library.
    All exceptions inherit from DataError, allowing catch-all error handling.
    Specific exceptions provide context (exchange, symbol, status codes, etc.)

Exception Hierarchy:
    DataError (base)
    ├── CapabilityError (unsupported capabilities with recommendations)
    ├── ProviderError (provider-specific errors)
    │   ├── RateLimitError (rate limiting)
    │   ├── InvalidSymbolError (invalid symbols)
    │   └── InvalidIntervalError (unsupported timeframes)
    ├── ValidationError (data validation failures)
    ├── SymbolResolutionError (URM symbol resolution failures)
    └── RelayError (stream relay sink failures)

Design Decisions:
    - Hierarchical structure: Allows catch-all or specific error handling
    - Rich context: Exceptions include relevant context (exchange, symbol, etc.)
    - Recommendations: CapabilityError includes alternative suggestions

See Also:
    - CapabilityService: Raises CapabilityError
    - URM: Raises SymbolResolutionError
    - StreamRelay: Raises RelayError
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from laakhay.core.exceptions import SymbolResolutionError, ValidationError

if TYPE_CHECKING:
    from .capabilities import CapabilityKey, CapabilityStatus, FallbackOption


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


# SymbolResolutionError and ValidationError are imported from laakhay.core and
# re-exported from this module for backward compatibility.


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


__all__ = [
    "DataError",
    "CapabilityError",
    "ProviderError",
    "RateLimitError",
    "InvalidSymbolError",
    "InvalidIntervalError",
    "ValidationError",
    "SymbolResolutionError",
    "RelayError",
]
