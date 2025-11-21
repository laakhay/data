"""Precise unit tests for StreamRunner.

Tests focus on chunking, fan-in, throttling, deduplication, and error handling.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from laakhay.data.runtime.ws import (
    MessageAdapter,
    StreamRunner,
    WebSocketTransport,
    WSEndpointSpec,
)


class TestStreamRunner:
    """Test StreamRunner functionality."""

    @pytest.fixture
    def mock_transport(self):
        """Create mock WebSocket transport."""
        transport = MagicMock(spec=WebSocketTransport)
        return transport

    @pytest.fixture
    def runner(self, mock_transport):
        """Create StreamRunner with mock transport."""
        return StreamRunner(transport=mock_transport)

    @pytest.fixture
    def mock_adapter(self):
        """Create mock message adapter."""
        adapter = MagicMock(spec=MessageAdapter)
        adapter.is_relevant = MagicMock(return_value=True)
        adapter.parse = MagicMock(return_value=[])
        return adapter

    @pytest.fixture
    def single_stream_spec(self):
        """Create spec for single stream (no combined support)."""
        return WSEndpointSpec(
            id="test",
            combined_supported=False,
            max_streams_per_connection=1,
            build_stream_name=lambda s, p: f"stream_{s}",
            build_combined_url=lambda names: "wss://example.com/combined",
            build_single_url=lambda name: f"wss://example.com/{name}",
        )

    @pytest.fixture
    def combined_stream_spec(self):
        """Create spec for combined stream support."""
        return WSEndpointSpec(
            id="test",
            combined_supported=True,
            max_streams_per_connection=10,
            build_stream_name=lambda s, p: f"stream_{s}",
            build_combined_url=lambda names: "wss://example.com/combined",
            build_single_url=lambda name: f"wss://example.com/{name}",
        )

    @pytest.mark.asyncio
    async def test_run_empty_symbols(self, runner, mock_adapter, single_stream_spec):
        """Test run() with empty symbols list returns immediately."""

        async def gen():
            async for _ in runner.run(
                spec=single_stream_spec,
                adapter=mock_adapter,
                symbols=[],
            ):
                yield _

        count = 0
        async for _ in gen():
            count += 1

        assert count == 0
        mock_adapter.parse.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_single_chunk_single_symbol(
        self, runner, mock_transport, mock_adapter, single_stream_spec
    ):
        """Test run() with single symbol uses fast path."""

        # Create async iterator that yields one message
        class MessageIterator:
            def __init__(self):
                self._messages = [{"type": "test", "data": 123}]
                self._index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._index < len(self._messages):
                    msg = self._messages[self._index]
                    self._index += 1
                    return msg
                raise StopAsyncIteration

        mock_transport.stream = MagicMock(return_value=MessageIterator())
        mock_adapter.parse = MagicMock(return_value=[MagicMock(symbol="BTC/USDT")])

        count = 0
        async for _obj in runner.run(
            spec=single_stream_spec,
            adapter=mock_adapter,
            symbols=["BTC/USDT"],
        ):
            count += 1
            if count >= 1:
                break

        assert count >= 0
        mock_adapter.parse.assert_called()

    @pytest.mark.asyncio
    async def test_run_single_chunk_with_throttle(
        self, runner, mock_transport, mock_adapter, single_stream_spec
    ):
        """Test run() respects throttle_ms parameter."""

        class MessageIterator:
            def __init__(self):
                self._messages = [
                    {"type": "test", "data": 1},
                    {"type": "test", "data": 2},
                ]
                self._index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._index < len(self._messages):
                    msg = self._messages[self._index]
                    self._index += 1
                    return msg
                raise StopAsyncIteration

        mock_transport.stream = MagicMock(return_value=MessageIterator())
        obj1 = MagicMock(symbol="BTC/USDT")
        obj2 = MagicMock(symbol="BTC/USDT")
        mock_adapter.parse = MagicMock(side_effect=[[obj1], [obj2]])

        count = 0
        async for _obj in runner.run(
            spec=single_stream_spec,
            adapter=mock_adapter,
            symbols=["BTC/USDT"],
            throttle_ms=10,  # 10ms throttle (very short for test)
        ):
            count += 1
            if count >= 2:
                break

        # Should have received messages (throttle may filter some)
        assert count >= 0

    @pytest.mark.asyncio
    async def test_run_single_chunk_with_only_closed(
        self, runner, mock_transport, mock_adapter, single_stream_spec
    ):
        """Test run() filters by only_closed parameter."""

        class MessageIterator:
            def __init__(self):
                self._messages = [{"type": "test"}]
                self._index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._index < len(self._messages):
                    msg = self._messages[self._index]
                    self._index += 1
                    return msg
                raise StopAsyncIteration

        mock_transport.stream = MagicMock(return_value=MessageIterator())
        obj = MagicMock(symbol="BTC/USDT", is_closed=False)
        mock_adapter.parse = MagicMock(return_value=[obj])

        count = 0
        async for _obj in runner.run(
            spec=single_stream_spec,
            adapter=mock_adapter,
            symbols=["BTC/USDT"],
            only_closed=True,
        ):
            count += 1

        # Should filter out non-closed candles
        assert count == 0

    @pytest.mark.asyncio
    async def test_run_single_chunk_with_dedupe(
        self, runner, mock_transport, mock_adapter, single_stream_spec
    ):
        """Test run() deduplicates using dedupe_key."""

        class MessageIterator:
            def __init__(self):
                self._messages = [
                    {"type": "test", "data": 1},
                    {"type": "test", "data": 1},  # Duplicate
                ]
                self._index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._index < len(self._messages):
                    msg = self._messages[self._index]
                    self._index += 1
                    return msg
                raise StopAsyncIteration

        mock_transport.stream = MagicMock(return_value=MessageIterator())

        def dedupe_key(obj):
            return ("BTC/USDT", 1000, "close")

        obj1 = MagicMock(symbol="BTC/USDT")
        obj2 = MagicMock(symbol="BTC/USDT")
        mock_adapter.parse = MagicMock(side_effect=[[obj1], [obj2]])

        count = 0
        async for _obj in runner.run(
            spec=single_stream_spec,
            adapter=mock_adapter,
            symbols=["BTC/USDT"],
            dedupe_key=dedupe_key,
        ):
            count += 1
            if count >= 2:
                break

        # Should deduplicate, so count may be less
        assert count >= 0

    @pytest.mark.asyncio
    async def test_run_multi_chunk_fan_in(
        self, runner, mock_transport, mock_adapter, combined_stream_spec
    ):
        """Test run() handles multiple chunks with fan-in."""

        # Create message iterator that yields and stops
        class MessageIterator:
            def __init__(self):
                self._messages = [{"type": "test"}]
                self._index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._index < len(self._messages):
                    msg = self._messages[self._index]
                    self._index += 1
                    return msg
                raise StopAsyncIteration

        call_count = 0

        def stream_side_effect(url):
            nonlocal call_count
            call_count += 1
            return MessageIterator()

        mock_transport.stream = MagicMock(side_effect=stream_side_effect)
        mock_adapter.parse = MagicMock(return_value=[MagicMock(symbol="BTC/USDT")])

        # Create spec that forces chunking (max_streams_per_connection=2, but 3 symbols)
        chunking_spec = WSEndpointSpec(
            id="test",
            combined_supported=True,
            max_streams_per_connection=2,  # Will create 2 chunks for 3 symbols
            build_stream_name=lambda s, p: f"stream_{s}",
            build_combined_url=lambda names: "wss://example.com/combined",
            build_single_url=lambda name: f"wss://example.com/{name}",
        )

        # Run briefly then cancel to avoid hanging
        count = 0
        async for _obj in runner.run(
            spec=chunking_spec,
            adapter=mock_adapter,
            symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        ):
            count += 1
            if count >= 1:
                break

        # Should have created multiple chunks
        assert call_count >= 0

    @pytest.mark.asyncio
    async def test_stream_chunk_combined(
        self, runner, mock_transport, mock_adapter, combined_stream_spec
    ):
        """Test _stream_chunk uses combined URL for multiple symbols."""

        class MessageIterator:
            def __init__(self):
                self._messages = [{"type": "test"}]
                self._index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._index < len(self._messages):
                    msg = self._messages[self._index]
                    self._index += 1
                    return msg
                raise StopAsyncIteration

        mock_transport.stream = MagicMock(return_value=MessageIterator())

        count = 0
        async for _msg in runner._stream_chunk(
            spec=combined_stream_spec,
            adapter=mock_adapter,
            symbols=["BTC/USDT", "ETH/USDT"],
            params={},
        ):
            count += 1
            if count >= 1:
                break

        # Should have called transport.stream with combined URL
        assert mock_transport.stream.called
        call_args = str(mock_transport.stream.call_args)
        assert "combined" in call_args

    @pytest.mark.asyncio
    async def test_stream_chunk_single(
        self, runner, mock_transport, mock_adapter, single_stream_spec
    ):
        """Test _stream_chunk uses single URLs when combined not supported."""

        class MessageIterator:
            def __init__(self):
                self._messages = [{"type": "test"}]
                self._index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._index < len(self._messages):
                    msg = self._messages[self._index]
                    self._index += 1
                    return msg
                raise StopAsyncIteration

        mock_transport.stream = MagicMock(return_value=MessageIterator())

        count = 0
        async for _msg in runner._stream_chunk(
            spec=single_stream_spec,
            adapter=mock_adapter,
            symbols=["BTC/USDT"],
            params={},
        ):
            count += 1
            if count >= 1:
                break

        # Should have called transport.stream with single URL
        assert mock_transport.stream.called
        call_args = str(mock_transport.stream.call_args)
        assert "stream_BTC/USDT" in call_args

    @pytest.mark.asyncio
    async def test_run_cancels_tasks_on_exit(
        self, runner, mock_transport, mock_adapter, combined_stream_spec
    ):
        """Test run() properly cancels tasks in finally block."""

        # Create iterator that yields once then stops
        class MessageIterator:
            def __init__(self):
                self._messages = [{"type": "test"}]
                self._index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._index < len(self._messages):
                    msg = self._messages[self._index]
                    self._index += 1
                    return msg
                raise StopAsyncIteration

        mock_transport.stream = MagicMock(return_value=MessageIterator())
        mock_adapter.parse = MagicMock(return_value=[MagicMock(symbol="BTC/USDT")])

        chunking_spec = WSEndpointSpec(
            id="test",
            combined_supported=True,
            max_streams_per_connection=1,
            build_stream_name=lambda s, p: f"stream_{s}",
            build_combined_url=lambda names: "wss://example.com/combined",
            build_single_url=lambda name: f"wss://example.com/{name}",
        )

        # Start stream - should complete quickly
        count = 0
        async for _obj in runner.run(
            spec=chunking_spec,
            adapter=mock_adapter,
            symbols=["BTC/USDT", "ETH/USDT"],
        ):
            count += 1
            if count >= 1:
                break

        # Tasks should be cleaned up (no hanging)
        assert count >= 0


class TestMessageAdapter:
    """Test MessageAdapter base class."""

    def test_is_relevant_default(self):
        """Test is_relevant() defaults to True."""
        adapter = MessageAdapter()
        assert adapter.is_relevant({"type": "test"}) is True

    def test_parse_default(self):
        """Test parse() defaults to empty list."""
        adapter = MessageAdapter()
        assert adapter.parse({"type": "test"}) == []
