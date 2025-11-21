"""Precise unit tests for HTTPClient.

Tests focus on session management, throttling, response hooks, and rate limiting.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from laakhay.data.runtime.rest import HTTPClient


class TestHTTPClientSessionManagement:
    """Test HTTPClient session management."""

    def test_init(self):
        """Test HTTPClient initialization."""
        client = HTTPClient(timeout=10.0)
        assert client.timeout.total == 10.0
        assert client._session is None
        assert client._response_hooks == []
        assert client._throttle_until is None

    def test_init_with_base_url(self):
        """Test HTTPClient with base_url."""
        client = HTTPClient(base_url="https://api.example.com", timeout=30.0)
        assert client.base_url == "https://api.example.com"

    @pytest.mark.asyncio
    async def test_session_property_creates_session(self):
        """Test session property creates session when needed."""
        client = HTTPClient()
        assert client._session is None

        session = client.session
        assert isinstance(session, aiohttp.ClientSession)
        assert client._session is session

    @pytest.mark.asyncio
    async def test_session_property_recreates_closed_session(self):
        """Test session property recreates closed session."""
        client = HTTPClient()
        session1 = client.session
        await session1.close()

        session2 = client.session
        assert session1 is not session2
        assert not session2.closed

    @pytest.mark.asyncio
    async def test_close_closes_session(self):
        """Test close() closes session."""
        client = HTTPClient()
        session = client.session
        assert not session.closed

        await client.close()
        assert session.closed

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        """Test close() can be called multiple times."""
        client = HTTPClient()
        await client.close()
        await client.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test HTTPClient as async context manager."""
        async with HTTPClient() as client:
            assert client.session is not None

        # Session should be closed after context exit
        assert client._session is None or client._session.closed


class TestHTTPClientThrottling:
    """Test HTTPClient throttling functionality."""

    def test_set_throttle(self):
        """Test set_throttle sets throttle window."""
        client = HTTPClient()
        client.set_throttle(5.0)

        assert client._throttle_until is not None
        assert client._throttle_until > 0

    def test_set_throttle_zero_does_nothing(self):
        """Test set_throttle with 0 does nothing."""
        client = HTTPClient()
        client.set_throttle(5.0)
        original_throttle = client._throttle_until

        client.set_throttle(0.0)
        # Should not change existing throttle
        assert client._throttle_until == original_throttle

    def test_set_throttle_extends_existing(self):
        """Test set_throttle extends existing throttle if later."""
        client = HTTPClient()
        client.set_throttle(5.0)
        first_end = client._throttle_until

        # Set a longer throttle - should extend
        client.set_throttle(10.0)
        assert client._throttle_until > first_end

    @pytest.mark.asyncio
    async def test_get_respects_throttle(self):
        """Test get() waits for throttle before request."""
        import time

        client = HTTPClient()
        client.set_throttle(0.05)  # 50ms throttle

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.closed = False  # Important: session property checks this
        # get() should return the response directly (not a coroutine) for async context manager
        mock_session.get = MagicMock(return_value=mock_response)
        client._session = mock_session

        # Use time.time() to match implementation timing precision
        start = time.time()
        await client.get("https://api.example.com/test")
        elapsed = time.time() - start

        # Allow small tolerance for timing variance (0.04s = 40ms, close enough to 50ms)
        assert elapsed >= 0.04, f"Expected at least 0.04s, got {elapsed:.6f}s"
        assert client._throttle_until is None  # Cleared after use


class TestHTTPClientResponseHooks:
    """Test HTTPClient response hooks."""

    def test_add_response_hook(self):
        """Test add_response_hook registers hook."""
        client = HTTPClient()
        hook = MagicMock()

        client.add_response_hook(hook)
        assert len(client._response_hooks) == 1
        assert hook in client._response_hooks

    @pytest.mark.asyncio
    async def test_response_hook_called(self):
        """Test response hooks are called for each response."""
        client = HTTPClient()
        hook = MagicMock(return_value=None)
        client.add_response_hook(hook)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.get = MagicMock(return_value=mock_response)
        client._session = mock_session

        await client.get("https://api.example.com/test")

        hook.assert_called_once_with(mock_response)

    @pytest.mark.asyncio
    async def test_response_hook_returns_delay(self):
        """Test response hook can return delay for throttling."""
        client = HTTPClient()

        def hook(response):
            return 2.0  # Request 2 second delay

        client.add_response_hook(hook)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.get = MagicMock(return_value=mock_response)
        client._session = mock_session

        await client.get("https://api.example.com/test")

        # Should have set throttle
        assert client._throttle_until is not None

    @pytest.mark.asyncio
    async def test_response_hook_async(self):
        """Test async response hook works."""
        client = HTTPClient()

        async def async_hook(response):
            await asyncio.sleep(0.01)
            return 1.0

        client.add_response_hook(async_hook)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.get = MagicMock(return_value=mock_response)
        client._session = mock_session

        await client.get("https://api.example.com/test")

        assert client._throttle_until is not None

    @pytest.mark.asyncio
    async def test_response_hook_exception_handled(self):
        """Test response hook exceptions don't break requests."""
        client = HTTPClient()

        def failing_hook(response):
            raise Exception("Hook error")

        client.add_response_hook(failing_hook)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.get = MagicMock(return_value=mock_response)
        client._session = mock_session

        # Should not raise
        result = await client.get("https://api.example.com/test")
        assert result == {"data": "test"}


class TestHTTPClientRateLimiting:
    """Test HTTPClient rate limiting handling."""

    @pytest.mark.asyncio
    async def test_get_handles_429_with_retry_after(self):
        """Test get() handles 429 with Retry-After header."""
        client = HTTPClient()

        # First response: 429 with Retry-After
        mock_response1 = AsyncMock()
        mock_response1.status = 429
        mock_response1.headers = {"Retry-After": "0.01"}
        mock_response1.__aenter__ = AsyncMock(return_value=mock_response1)
        mock_response1.__aexit__ = AsyncMock(return_value=None)

        # Second response: success
        mock_response2 = AsyncMock()
        mock_response2.status = 200
        mock_response2.json = AsyncMock(return_value={"data": "test"})
        mock_response2.raise_for_status = MagicMock()
        mock_response2.__aenter__ = AsyncMock(return_value=mock_response2)
        mock_response2.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.get = MagicMock(side_effect=[mock_response1, mock_response2])
        client._session = mock_session

        result = await client.get("https://api.example.com/test")

        assert result == {"data": "test"}
        assert mock_session.get.call_count == 2

    @pytest.mark.asyncio
    async def test_get_handles_429_without_retry_after(self):
        """Test get() handles 429 without Retry-After uses fallback."""
        client = HTTPClient()

        mock_response1 = AsyncMock()
        mock_response1.status = 429
        mock_response1.headers = {}
        mock_response1.__aenter__ = AsyncMock(return_value=mock_response1)
        mock_response1.__aexit__ = AsyncMock(return_value=None)

        mock_response2 = AsyncMock()
        mock_response2.status = 200
        mock_response2.json = AsyncMock(return_value={"data": "test"})
        mock_response2.raise_for_status = MagicMock()
        mock_response2.__aenter__ = AsyncMock(return_value=mock_response2)
        mock_response2.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.get = MagicMock(side_effect=[mock_response1, mock_response2])
        client._session = mock_session

        result = await client.get("https://api.example.com/test")

        assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_post_handles_rate_limiting(self):
        """Test post() handles rate limiting."""
        client = HTTPClient()

        mock_response1 = AsyncMock()
        mock_response1.status = 418
        mock_response1.headers = {"Retry-After": "0.01"}
        mock_response1.__aenter__ = AsyncMock(return_value=mock_response1)
        mock_response1.__aexit__ = AsyncMock(return_value=None)

        mock_response2 = AsyncMock()
        mock_response2.status = 200
        mock_response2.json = AsyncMock(return_value={"data": "test"})
        mock_response2.raise_for_status = MagicMock()
        mock_response2.__aenter__ = AsyncMock(return_value=mock_response2)
        mock_response2.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.post = MagicMock(side_effect=[mock_response1, mock_response2])
        client._session = mock_session

        result = await client.post("https://api.example.com/test", json={"key": "value"})

        assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_get_with_base_url(self):
        """Test get() combines base_url with relative path."""
        client = HTTPClient(base_url="https://api.example.com")

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.closed = False
        # get() should return the response directly for async context manager
        mock_session.get = MagicMock(return_value=mock_response)
        client._session = mock_session

        await client.get("/test")

        # Check that base_url was combined
        call_args = mock_session.get.call_args
        assert "https://api.example.com/test" in str(call_args)

    @pytest.mark.asyncio
    async def test_get_with_absolute_url(self):
        """Test get() doesn't combine base_url with absolute URL."""
        client = HTTPClient(base_url="https://api.example.com")

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.closed = False
        # get() should return the response directly for async context manager
        mock_session.get = MagicMock(return_value=mock_response)
        client._session = mock_session

        await client.get("https://other.com/test")

        call_args = mock_session.get.call_args
        assert "https://other.com/test" in str(call_args)
        assert "api.example.com" not in str(call_args)
