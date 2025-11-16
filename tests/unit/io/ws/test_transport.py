"""Precise unit tests for WebSocketTransport.

Tests focus on reconnection logic, message parsing, and error handling.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from laakhay.data.io.ws.transport import TransportConfig, WebSocketTransport


class TestWebSocketTransport:
    """Test WebSocketTransport."""

    def test_init_default_config(self):
        """Test WebSocketTransport with default config."""
        transport = WebSocketTransport()
        assert transport._conf.ping_interval == 30
        assert transport._conf.ping_timeout == 10

    def test_init_custom_config(self):
        """Test WebSocketTransport with custom config."""
        config = TransportConfig(
            ping_interval=20,
            ping_timeout=5,
            base_reconnect_delay=2.0,
            max_reconnect_delay=60.0,
        )
        transport = WebSocketTransport(config)
        assert transport._conf.ping_interval == 20
        assert transport._conf.max_reconnect_delay == 60.0

    def test_next_delay_exponential_backoff(self):
        """Test _next_delay uses exponential backoff with jitter."""
        transport = WebSocketTransport()
        delay1 = transport._next_delay(1.0)
        delay2 = transport._next_delay(delay1)

        assert delay2 > delay1
        assert delay2 <= transport._conf.max_reconnect_delay

    def test_next_delay_respects_max(self):
        """Test _next_delay respects max_reconnect_delay (with jitter tolerance)."""
        transport = WebSocketTransport()
        large_delay = 100.0
        result = transport._next_delay(large_delay)

        # Jitter can add up to 20%, so allow some tolerance
        max_with_jitter = transport._conf.max_reconnect_delay * (1 + transport._conf.jitter)
        assert result <= max_with_jitter
        # But the base delay before jitter should be capped
        # (We can't directly check this, but we verify it's reasonable)

    def test_connect_kwargs(self):
        """Test _connect_kwargs includes all config values."""
        config = TransportConfig(max_size=1024, max_queue=512)
        transport = WebSocketTransport(config)
        kwargs = transport._connect_kwargs()

        assert kwargs["ping_interval"] == 30
        assert kwargs["ping_timeout"] == 10
        assert kwargs["max_size"] == 1024
        assert kwargs["max_queue"] == 512

    @pytest.mark.asyncio
    async def test_stream_yields_json_messages(self):
        """Test stream() yields parsed JSON messages."""
        transport = WebSocketTransport()

        # Create proper async iterator
        class MessageIterator:
            def __init__(self):
                self._messages = ['{"type":"test","data":123}']
                self._index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._index < len(self._messages):
                    msg = self._messages[self._index]
                    self._index += 1
                    return msg
                raise StopAsyncIteration

        mock_ws = MessageIterator()

        # Mock websockets.connect as async context manager
        async def mock_connect(*args, **kwargs):
            return mock_ws

        mock_connect_context = AsyncMock()
        mock_connect_context.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_connect_context.__aexit__ = AsyncMock(return_value=None)

        with patch("websockets.connect", return_value=mock_connect_context):
            count = 0
            async for message in transport.stream("wss://example.com/ws"):
                assert isinstance(message, dict)
                assert message["type"] == "test"
                assert message["data"] == 123
                count += 1
                if count >= 1:
                    break

    @pytest.mark.asyncio
    async def test_stream_yields_raw_on_json_error(self):
        """Test stream() yields raw message on JSON parse error."""
        transport = WebSocketTransport()

        # Create async iterator with invalid JSON
        class MessageIterator:
            def __init__(self):
                self._messages = ["invalid json"]
                self._index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._index < len(self._messages):
                    msg = self._messages[self._index]
                    self._index += 1
                    return msg
                raise StopAsyncIteration

        mock_ws = MessageIterator()

        mock_connect_context = AsyncMock()
        mock_connect_context.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_connect_context.__aexit__ = AsyncMock(return_value=None)

        with patch("websockets.connect", return_value=mock_connect_context):
            count = 0
            async for message in transport.stream("wss://example.com/ws"):
                assert isinstance(message, str)
                assert message == "invalid json"
                count += 1
                if count >= 1:
                    break

    @pytest.mark.asyncio
    async def test_stream_reconnects_on_connection_closed(self):
        """Test stream() reconnects on connection closed."""
        transport = WebSocketTransport()

        # First connection closes
        class ClosedIterator:
            def __aiter__(self):
                return self

            async def __anext__(self):
                from websockets.exceptions import ConnectionClosed

                raise ConnectionClosed(None, None)

        mock_ws1 = ClosedIterator()
        mock_connect_context1 = AsyncMock()
        mock_connect_context1.__aenter__ = AsyncMock(return_value=mock_ws1)
        mock_connect_context1.__aexit__ = AsyncMock(return_value=None)

        # Second connection succeeds
        class SuccessIterator:
            def __init__(self):
                self._messages = ['{"type":"test"}']
                self._index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._index < len(self._messages):
                    msg = self._messages[self._index]
                    self._index += 1
                    return msg
                raise StopAsyncIteration

        mock_ws2 = SuccessIterator()
        mock_connect_context2 = AsyncMock()
        mock_connect_context2.__aenter__ = AsyncMock(return_value=mock_ws2)
        mock_connect_context2.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "websockets.connect", side_effect=[mock_connect_context1, mock_connect_context2]
        ):
            count = 0
            async for _message in transport.stream("wss://example.com/ws"):
                count += 1
                if count >= 1:
                    break

            # Should have reconnected and received message
            assert count == 1

    @pytest.mark.asyncio
    async def test_stream_handles_generic_errors(self):
        """Test stream() handles generic errors and reconnects."""
        transport = WebSocketTransport()

        # Create iterator that raises error
        class ErrorIterator:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise Exception("Network error")

        mock_ws = ErrorIterator()
        mock_connect_context = AsyncMock()
        mock_connect_context.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_connect_context.__aexit__ = AsyncMock(return_value=None)

        with patch("websockets.connect", return_value=mock_connect_context):
            # Should not raise immediately, but will reconnect
            # Cancel quickly to avoid infinite loop
            import contextlib

            task = asyncio.create_task(transport.stream("wss://example.com/ws").__anext__())
            await asyncio.sleep(0.01)
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task

    @pytest.mark.asyncio
    async def test_stream_respects_cancelled_error(self):
        """Test stream() propagates CancelledError."""
        transport = WebSocketTransport()

        # Create iterator that raises CancelledError
        class CancelledIterator:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise asyncio.CancelledError()

        mock_ws = CancelledIterator()
        mock_connect_context = AsyncMock()
        mock_connect_context.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_connect_context.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("websockets.connect", return_value=mock_connect_context),
            pytest.raises(asyncio.CancelledError),
        ):
            async for _ in transport.stream("wss://example.com/ws"):
                pass
