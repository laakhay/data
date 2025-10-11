"""Unit tests for exception hierarchy."""

from laakhay.data.core import (
    DataError,
    InvalidIntervalError,
    InvalidSymbolError,
    ProviderError,
    RateLimitError,
    ValidationError,
)


def test_data_error():
    """Test DataError base exception."""
    error = DataError("test")
    assert str(error) == "test"


def test_provider_error():
    """Test ProviderError."""
    error = ProviderError("error", status_code=400)
    assert str(error) == "error"
    assert error.status_code == 400
    assert isinstance(error, DataError)


def test_rate_limit_error():
    """Test RateLimitError."""
    error = RateLimitError("rate limit", retry_after=120)
    assert error.status_code == 429
    assert error.retry_after == 120
    assert isinstance(error, ProviderError)


def test_invalid_symbol_error():
    """Test InvalidSymbolError."""
    error = InvalidSymbolError("invalid")
    assert isinstance(error, ProviderError)


def test_invalid_interval_error():
    """Test InvalidIntervalError."""
    error = InvalidIntervalError("invalid")
    assert isinstance(error, ProviderError)


def test_validation_error():
    """Test ValidationError."""
    error = ValidationError("invalid")
    assert isinstance(error, DataError)
