"""Unit tests for InMemorySink."""

from __future__ import annotations

import asyncio

import pytest

from laakhay.data.sinks.in_memory import InMemorySink


@pytest.mark.asyncio
async def test_in_memory_sink_publish_get():
    """Test publishing and getting events."""
    sink = InMemorySink()

    event1 = {"symbol": "BTCUSDT", "price": 50000}
    event2 = {"symbol": "ETHUSDT", "price": 3000}

    await sink.publish(event1)
    await sink.publish(event2)

    assert sink.qsize() == 2
    assert not sink.empty()

    # Get events
    e1 = await sink.get()
    assert e1 == event1

    e2 = await sink.get()
    assert e2 == event2

    assert sink.empty()


@pytest.mark.asyncio
async def test_in_memory_sink_get_nowait():
    """Test getting events without waiting."""
    sink = InMemorySink()

    event = {"symbol": "BTCUSDT", "price": 50000}
    await sink.publish(event)

    e = sink.get_nowait()
    assert e == event

    # Should raise QueueEmpty
    with pytest.raises(asyncio.QueueEmpty):
        sink.get_nowait()


@pytest.mark.asyncio
async def test_in_memory_sink_stream():
    """Test streaming events."""
    sink = InMemorySink()

    events = [
        {"symbol": "BTCUSDT", "price": 50000},
        {"symbol": "ETHUSDT", "price": 3000},
    ]

    # Publish events
    for event in events:
        await sink.publish(event)

    # Stream events
    received = []
    async for event in sink.stream():
        received.append(event)
        if len(received) >= len(events):
            break

    assert received == events


@pytest.mark.asyncio
async def test_in_memory_sink_maxsize():
    """Test sink with maxsize limit."""
    sink = InMemorySink(maxsize=2)

    await sink.publish({"event": 1})
    await sink.publish({"event": 2})

    # Third event should raise QueueFull if we try to put synchronously
    # But with async put, it will block
    task = asyncio.create_task(sink.publish({"event": 3}))

    # Wait a bit
    await asyncio.sleep(0.01)

    # Get one event to make space
    await sink.get()

    # Now the third event should go through
    await task

    assert sink.qsize() == 2


@pytest.mark.asyncio
async def test_in_memory_sink_close():
    """Test closing sink."""
    sink = InMemorySink()

    await sink.publish({"event": 1})
    await sink.close()

    # Should raise error if trying to publish after close
    with pytest.raises(RuntimeError, match="closed"):
        await sink.publish({"event": 2})


@pytest.mark.asyncio
async def test_in_memory_sink_get_timeout():
    """Test getting with timeout."""
    sink = InMemorySink()

    # Should timeout if no events
    with pytest.raises(asyncio.TimeoutError):
        await sink.get(timeout=0.1)

    # Should work if event is available
    await sink.publish({"event": 1})
    event = await sink.get(timeout=0.1)
    assert event == {"event": 1}

