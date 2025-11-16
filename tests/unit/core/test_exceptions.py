"""Precise unit tests for exception hierarchy.

Tests focus on meaningful behavior, not just field access.
"""

from laakhay.data.core import (
    DataError,
    ProviderError,
    RateLimitError,
    SymbolResolutionError,
)


def test_rate_limit_error_with_retry_after():
    """Test RateLimitError with retry_after (meaningful behavior)."""
    error = RateLimitError("rate limit", retry_after=120)
    assert error.status_code == 429
    assert error.retry_after == 120
    assert isinstance(error, ProviderError)
    assert isinstance(error, DataError)


def test_provider_error_with_status_code():
    """Test ProviderError with status_code (meaningful behavior)."""
    error = ProviderError("error", status_code=400)
    assert str(error) == "error"
    assert error.status_code == 400
    assert isinstance(error, DataError)


def test_symbol_resolution_error_with_context():
    """Test SymbolResolutionError with exchange context."""
    error = SymbolResolutionError(
        "Symbol not found",
        exchange="binance",
        value="INVALID",
        market_type="spot",
    )
    assert error.exchange == "binance"
    assert error.value == "INVALID"
    assert isinstance(error, DataError)
