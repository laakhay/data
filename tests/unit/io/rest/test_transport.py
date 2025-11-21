"""Precise unit tests for RESTTransport.

Tests focus on HTTPClient delegation and response hooks.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from laakhay.data.runtime.rest import RESTTransport


class TestRESTTransport:
    """Test RESTTransport wrapper."""

    def test_init(self):
        """Test RESTTransport initialization."""
        transport = RESTTransport(base_url="https://api.example.com")
        assert transport._http.base_url == "https://api.example.com"

    def test_add_response_hook(self):
        """Test add_response_hook delegates to HTTPClient."""
        transport = RESTTransport(base_url="https://api.example.com")
        hook = MagicMock()

        transport.add_response_hook(hook)

        assert hook in transport._http._response_hooks

    @pytest.mark.asyncio
    async def test_get_delegates_to_http_client(self):
        """Test get() delegates to HTTPClient."""
        transport = RESTTransport(base_url="https://api.example.com")
        transport._http.get = AsyncMock(return_value={"data": "test"})

        result = await transport.get("/test", params={"key": "value"})

        assert result == {"data": "test"}
        transport._http.get.assert_called_once_with("/test", params={"key": "value"}, headers=None)

    @pytest.mark.asyncio
    async def test_post_delegates_to_http_client(self):
        """Test post() delegates to HTTPClient."""
        transport = RESTTransport(base_url="https://api.example.com")
        transport._http.post = AsyncMock(return_value={"data": "created"})

        result = await transport.post("/test", json_body={"key": "value"})

        assert result == {"data": "created"}
        transport._http.post.assert_called_once_with("/test", json={"key": "value"}, headers=None)

    @pytest.mark.asyncio
    async def test_close_delegates_to_http_client(self):
        """Test close() delegates to HTTPClient."""
        transport = RESTTransport(base_url="https://api.example.com")
        transport._http.close = AsyncMock()

        await transport.close()

        transport._http.close.assert_called_once()
