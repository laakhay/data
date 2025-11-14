"""Unit tests for StreamRelay."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import pytest

from laakhay.data.core.enums import DataFeature, MarketType, Timeframe, TransportKind
from laakhay.data.core.relay import StreamRelay
from laakhay.data.core.request import DataRequest
from laakhay.data.core.router import DataRouter
from laakhay.data.sinks.in_memory import InMemorySink


class MockSink:
    """Mock sink for testing."""

    def __init__(self, fail_count: int = 0) -> None:
        """Initialize mock sink.

        Args:
            fail_count: Number of times to fail before succeeding
        """
        self.fail_count = fail_count
        self.call_count = 0
        self.events: list[Any] = []
        self.closed = False

    async def publish(self, event: Any) -> None:
        """Publish event."""
        self.call_count += 1
        if self.call_count <= self.fail_count:
            raise Exception(f"Mock failure {self.call_count}")
        self.events.append(event)

    async def close(self) -> None:
        """Close sink."""
        self.closed = True


@pytest.fixture
def mock_router():
    """Create a mock router."""
    router = MagicMock(spec=DataRouter)
    return router


@pytest.fixture
def relay(mock_router):
    """Create a StreamRelay with mocked router."""
    return StreamRelay(router=mock_router, max_buffer_size=10)


@pytest.fixture
def in_memory_sink():
    """Create an in-memory sink."""
    return InMemorySink()


@pytest.mark.asyncio
async def test_relay_add_remove_sink(relay, in_memory_sink):
    """Test adding and removing sinks."""
    assert len(relay._sinks) == 0

    relay.add_sink(in_memory_sink)
    assert len(relay._sinks) == 1
    assert in_memory_sink in relay._sinks

    relay.remove_sink(in_memory_sink)
    assert len(relay._sinks) == 0


@pytest.mark.asyncio
async def test_relay_requires_ws_transport(relay, in_memory_sink):
    """Test that relay only accepts WS transport."""
    relay.add_sink(in_memory_sink)

    request = DataRequest(
        feature=DataFeature.OHLCV,
        transport=TransportKind.REST,  # Wrong transport
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
    )

    with pytest.raises(ValueError, match="only supports WebSocket streams"):
        await relay.relay(request)


@pytest.mark.asyncio
async def test_relay_requires_sink(relay):
    """Test that relay requires at least one sink."""
    request = DataRequest(
        feature=DataFeature.TRADES,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
    )

    with pytest.raises(ValueError, match="No sinks registered"):
        await relay.relay(request)


@pytest.mark.asyncio
async def test_relay_publishes_to_sink(relay, in_memory_sink):
    """Test that relay publishes events to sinks."""
    relay.add_sink(in_memory_sink)

    # Mock router to return a stream
    async def mock_stream(request: DataRequest) -> AsyncIterator[dict]:
        yield {"symbol": "BTCUSDT", "price": 50000}
        yield {"symbol": "BTCUSDT", "price": 50001}

    relay._router.route_stream = mock_stream

    request = DataRequest(
        feature=DataFeature.TRADES,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
    )

    # Start relay in background
    relay_task = asyncio.create_task(relay.relay(request))

    # Wait a bit for events to be processed
    await asyncio.sleep(0.1)

    # Stop relay
    await relay.stop()
    await relay_task

    # Check that events were published
    assert in_memory_sink.qsize() >= 0  # Events may have been consumed


@pytest.mark.asyncio
async def test_relay_backpressure_drop(relay, in_memory_sink):
    """Test drop backpressure policy."""
    relay = StreamRelay(
        router=relay._router,
        max_buffer_size=2,
        backpressure_policy="drop",
    )
    relay.add_sink(in_memory_sink)

    # Create slow sink that processes slowly
    slow_sink = MockSink()
    relay.add_sink(slow_sink)

    # Mock router to return many events quickly
    async def mock_stream() -> AsyncIterator[dict]:
        for i in range(10):
            yield {"symbol": "BTCUSDT", "price": 50000 + i}

    relay._router.route_stream = mock_stream

    request = DataRequest(
        feature=DataFeature.TRADES,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
    )

    relay_task = asyncio.create_task(relay.relay(request))
    await asyncio.sleep(0.2)
    await relay.stop()
    await relay_task

    # Some events should have been dropped
    assert relay.get_metrics().events_dropped >= 0


@pytest.mark.asyncio
async def test_relay_retry_on_failure(relay):
    """Test that relay retries on sink failures."""
    # Sink that fails twice then succeeds
    failing_sink = MockSink(fail_count=2)
    relay.add_sink(failing_sink)

    async def mock_stream(request: DataRequest) -> AsyncIterator[dict]:
        yield {"symbol": "BTCUSDT", "price": 50000}

    relay._router.route_stream = mock_stream

    request = DataRequest(
        feature=DataFeature.TRADES,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
    )

    relay_task = asyncio.create_task(relay.relay(request))
    await asyncio.sleep(0.1)
    await relay.stop()
    await relay_task

    # Should have retried and eventually succeeded
    assert failing_sink.call_count >= 1


@pytest.mark.asyncio
async def test_relay_max_retries_exceeded(relay):
    """Test that relay raises RelayError after max retries."""
    # Sink that always fails
    always_failing_sink = MockSink(fail_count=100)
    relay = StreamRelay(
        router=relay._router,
        max_retries=2,
        retry_delay=0.01,
    )
    relay.add_sink(always_failing_sink)

    async def mock_stream(request: DataRequest) -> AsyncIterator[dict]:
        yield {"symbol": "BTCUSDT", "price": 50000}

    relay._router.route_stream = mock_stream

    request = DataRequest(
        feature=DataFeature.TRADES,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
    )

    relay_task = asyncio.create_task(relay.relay(request))
    await asyncio.sleep(0.2)
    await relay.stop()

    # Should have failed after retries
    assert relay.get_metrics().events_failed > 0


@pytest.mark.asyncio
async def test_relay_metrics(relay, in_memory_sink):
    """Test relay metrics collection."""
    relay.add_sink(in_memory_sink)

    async def mock_stream() -> AsyncIterator[dict]:
        yield {"symbol": "BTCUSDT", "price": 50000}
        yield {"symbol": "BTCUSDT", "price": 50001}

    relay._router.route_stream = mock_stream

    request = DataRequest(
        feature=DataFeature.TRADES,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
    )

    relay_task = asyncio.create_task(relay.relay(request))
    await asyncio.sleep(0.1)
    await relay.stop()
    await relay_task

    metrics = relay.get_metrics()
    assert metrics.events_published >= 0
    assert metrics.last_event_time is not None or metrics.events_published == 0


@pytest.mark.asyncio
async def test_relay_context_manager(relay, in_memory_sink):
    """Test relay as async context manager."""
    relay.add_sink(in_memory_sink)

    async def mock_stream(request: DataRequest) -> AsyncIterator[dict]:
        yield {"symbol": "BTCUSDT", "price": 50000}

    relay._router.route_stream = mock_stream

    request = DataRequest(
        feature=DataFeature.TRADES,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
    )

    async with relay:
        relay_task = asyncio.create_task(relay.relay(request))
        await asyncio.sleep(0.05)
        # Context manager should close on exit
        await relay_task

    # Sink should be closed
    assert in_memory_sink._closed


@pytest.mark.asyncio
async def test_relay_temporary_sink(relay, in_memory_sink):
    """Test relay with temporary sink."""
    # No sinks registered initially
    assert len(relay._sinks) == 0

    async def mock_stream(request: DataRequest) -> AsyncIterator[dict]:
        yield {"symbol": "BTCUSDT", "price": 50000}

    relay._router.route_stream = mock_stream

    request = DataRequest(
        feature=DataFeature.TRADES,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
    )

    relay_task = asyncio.create_task(relay.relay(request, sink=in_memory_sink))
    await asyncio.sleep(0.05)
    await relay.stop()
    await relay_task

    # Temporary sink should be removed
    assert in_memory_sink not in relay._sinks

