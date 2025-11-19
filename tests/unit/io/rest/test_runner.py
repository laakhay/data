"""Precise unit tests for RestRunner.

Tests focus on endpoint execution, parameter building, and error handling.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from laakhay.data.io.rest.runner import ResponseAdapter, RestEndpointSpec, RestRunner
from laakhay.data.io.rest.transport import RESTTransport


class TestRestRunner:
    """Test RestRunner endpoint execution."""

    @pytest.fixture
    def mock_transport(self):
        """Create mock REST transport."""
        transport = MagicMock(spec=RESTTransport)
        transport.get = AsyncMock(return_value={"data": "test"})
        transport.post = AsyncMock(return_value={"data": "created"})
        return transport

    @pytest.fixture
    def runner(self, mock_transport):
        """Create RestRunner with mock transport."""
        return RestRunner(mock_transport)

    @pytest.fixture
    def mock_adapter(self):
        """Create mock response adapter."""
        adapter = MagicMock(spec=ResponseAdapter)
        adapter.parse = MagicMock(return_value={"parsed": "data"})
        return adapter

    @pytest.mark.asyncio
    async def test_run_get_endpoint(self, runner, mock_transport, mock_adapter):
        """Test running GET endpoint."""
        spec = RestEndpointSpec(
            id="test",
            method="GET",
            build_path=lambda p: f"/test/{p['id']}",
            build_query=lambda p: {"param": p.get("param")},
        )

        result = await runner.run(
            spec=spec, adapter=mock_adapter, params={"id": "123", "param": "value"}
        )

        assert result == {"parsed": "data"}
        mock_transport.get.assert_called_once_with(
            "/test/123", params={"param": "value"}, headers=None
        )
        mock_adapter.parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_post_endpoint(self, runner, mock_transport, mock_adapter):
        """Test running POST endpoint."""
        spec = RestEndpointSpec(
            id="test",
            method="POST",
            build_path=lambda p: "/test",
            build_body=lambda p: {"data": p["data"]},
        )

        result = await runner.run(spec=spec, adapter=mock_adapter, params={"data": "value"})

        assert result == {"parsed": "data"}
        mock_transport.post.assert_called_once_with(
            "/test", json_body={"data": "value"}, headers=None
        )
        mock_adapter.parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_without_query_builder(self, runner, mock_transport, mock_adapter):
        """Test endpoint without query builder."""
        spec = RestEndpointSpec(
            id="test",
            method="GET",
            build_path=lambda p: "/test",
            build_query=None,
        )

        await runner.run(spec=spec, adapter=mock_adapter, params={})

        mock_transport.get.assert_called_once_with("/test", params=None, headers=None)

    @pytest.mark.asyncio
    async def test_run_without_body_builder(self, runner, mock_transport, mock_adapter):
        """Test endpoint without body builder."""
        spec = RestEndpointSpec(
            id="test",
            method="POST",
            build_path=lambda p: "/test",
            build_body=None,
        )

        await runner.run(spec=spec, adapter=mock_adapter, params={})

        mock_transport.post.assert_called_once_with("/test", json_body=None, headers=None)

    @pytest.mark.asyncio
    async def test_adapter_receives_params(self, runner, mock_transport, mock_adapter):
        """Test adapter receives both response and params."""
        spec = RestEndpointSpec(
            id="test",
            method="GET",
            build_path=lambda p: "/test",
        )

        await runner.run(spec=spec, adapter=mock_adapter, params={"key": "value"})

        # Adapter should be called with response and params
        call_args = mock_adapter.parse.call_args
        assert call_args[0][0] == {"data": "test"}  # Response
        assert call_args[0][1] == {"key": "value"}  # Params
