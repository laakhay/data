"""In-memory sink for testing and development.

This sink stores events in an async queue that can be consumed by tests or
simple applications.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any


class InMemorySink:
    """In-memory sink that stores events in an async queue.

    Useful for testing and simple applications that don't need persistent storage.
    """

    def __init__(self, maxsize: int = 1000) -> None:
        """Initialize in-memory sink.

        Args:
            maxsize: Maximum queue size (0 = unlimited)
        """
        self._queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=maxsize)
        self._closed = False

    async def publish(self, event: Any) -> None:
        """Publish event to the queue.

        Args:
            event: Data event to publish

        Raises:
            asyncio.QueueFull: If queue is full (only if maxsize > 0)
        """
        if self._closed:
            raise RuntimeError("Sink is closed")

        await self._queue.put(event)

    async def get(self, timeout: float | None = None) -> Any:
        """Get next event from the queue.

        Args:
            timeout: Optional timeout in seconds

        Returns:
            Next event from queue

        Raises:
            asyncio.TimeoutError: If timeout is reached
        """
        if timeout is None:
            return await self._queue.get()
        return await asyncio.wait_for(self._queue.get(), timeout=timeout)

    def get_nowait(self) -> Any:
        """Get next event without waiting.

        Returns:
            Next event if available

        Raises:
            asyncio.QueueEmpty: If queue is empty
        """
        return self._queue.get_nowait()

    async def stream(self) -> AsyncIterator[Any]:
        """Stream events from the queue.

        Yields:
            Events as they arrive
        """
        while not self._closed or not self._queue.empty():
            try:
                event = await self._queue.get()
                yield event
                self._queue.task_done()
            except asyncio.CancelledError:
                break

    def qsize(self) -> int:
        """Get current queue size.

        Returns:
            Number of events in queue
        """
        return self._queue.qsize()

    def empty(self) -> bool:
        """Check if queue is empty.

        Returns:
            True if queue is empty
        """
        return self._queue.empty()

    async def close(self) -> None:
        """Close the sink."""
        self._closed = True
