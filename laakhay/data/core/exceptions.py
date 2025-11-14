"""Custom exception hierarchy."""


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
        key: "CapabilityKey | None" = None,  # type: ignore[name-defined]
        status: "CapabilityStatus | None" = None,  # type: ignore[name-defined]
        recommendations: list["FallbackOption"] | None = None,  # type: ignore[name-defined]
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
