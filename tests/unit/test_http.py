"""Unit tests for HTTP client."""

from laakhay.data.io import HTTPClient


def test_http_client_instantiation():
    """Test HTTPClient can be instantiated."""
    client = HTTPClient(timeout=10.0)
    assert client.timeout.total == 10.0
    assert client._session is None


def test_http_client_default_timeout():
    """Test HTTPClient has default timeout."""
    client = HTTPClient()
    assert client.timeout.total == 30.0
    assert client._session is None
