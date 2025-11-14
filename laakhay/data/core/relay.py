"""Stream relay for forwarding market data to pluggable sinks.

The StreamRelay subscribes to data streams via the DataRouter and forwards
events to pluggable sinks (in-memory queues, Redis, Kafka, etc.).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .enums import TransportKind
from .exceptions import RelayError
from .request import DataRequest
from .router import DataRouter

logger = logging.getLogger(__name__)


class StreamSink(Protocol):
    """Protocol for stream sinks that receive market data events.

    Sinks can be in-memory queues, Redis Streams, Kafka, or any custom backend.
    """

    async def publish(self, event: Any) -> None:
        """Publish a data event to the sink.

        Args:
            event: Data event to publish (Trade, OHLCV, OrderBook, etc.)

        Raises:
            Exception: If publishing fails (relay will handle retries/backpressure)
        """
        ...

    async def close(self) -> None:
        """Close the sink and clean up resources.

        Called when the relay is shutting down.
        """
        ...


@dataclass
class RelayMetrics:
    """Metrics for stream relay performance."""

    events_published: int = 0
    events_dropped: int = 0
    events_failed: int = 0
    reconnection_attempts: int = 0
    last_event_time: datetime | None = None
    sink_lag_seconds: float = 0.0


class StreamRelay:
    """Relay that subscribes to streams and forwards events to sinks.

    The relay:
    1. Subscribes to streams via DataRouter
    2. Handles reconnections automatically
    3. Forwards events to registered sinks
    4. Manages backpressure (buffer/drop/block policies)
    5. Emits metrics for observability
    """

    def __init__(
        self,
        router: DataRouter | None = None,
        *,
        max_buffer_size: int = 1000,
        backpressure_policy: str = "drop",  # "drop", "block", "buffer"
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize stream relay.

        Args:
            router: DataRouter instance (defaults to new instance)
            max_buffer_size: Maximum events to buffer before applying backpressure
            backpressure_policy: How to handle backpressure ("drop", "block", "buffer")
            max_retries: Maximum retry attempts for sink failures
            retry_delay: Delay between retries (seconds)
        """
        self._router = router or DataRouter()
        self._sinks: list[StreamSink] = []
        self._max_buffer_size = max_buffer_size
        self._backpressure_policy = backpressure_policy
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        self._metrics = RelayMetrics()
        self._running = False
        self._tasks: list[asyncio.Task[None]] = []
        self._event_buffer: asyncio.Queue[Any] = asyncio.Queue(maxsize=max_buffer_size)

    def add_sink(self, sink: StreamSink) -> None:
        """Register a sink to receive events.

        Args:
            sink: StreamSink implementation
        """
        self._sinks.append(sink)
        logger.info(f"Added sink: {sink.__class__.__name__}")

    def remove_sink(self, sink: StreamSink) -> None:
        """Remove a sink from the relay.

        Args:
            sink: Sink to remove
        """
        if sink in self._sinks:
            self._sinks.remove(sink)
            logger.info(f"Removed sink: {sink.__class__.__name__}")

    async def relay(
        self,
        request: DataRequest,
        *,
        sink: StreamSink | None = None,
    ) -> None:
        """Start relaying a stream to sinks.

        Args:
            request: DataRequest for the stream (must have transport=WS)
            sink: Optional sink to add temporarily for this relay

        Raises:
            ValueError: If request transport is not WS
            RelayError: If sink fails repeatedly
        """
        if request.transport != TransportKind.WS:
            raise ValueError("StreamRelay only supports WebSocket streams")

        if sink:
            self.add_sink(sink)

        if not self._sinks:
            raise ValueError("No sinks registered. Call add_sink() first.")

        self._running = True

        # Start background task to consume buffer and publish to sinks
        task = asyncio.create_task(self._publish_loop())
        self._tasks.append(task)

        # Subscribe to stream and buffer events
        try:
            async for event in self._router.route_stream(request):
                if not self._running:
                    break

                # Apply backpressure policy
                if self._backpressure_policy == "drop":
                    if self._event_buffer.full():
                        self._metrics.events_dropped += 1
                        logger.warning("Event buffer full, dropping event")
                        continue
                    self._event_buffer.put_nowait(event)
                elif self._backpressure_policy == "block":
                    # Block until space available
                    await self._event_buffer.put(event)
                else:  # buffer
                    try:
                        self._event_buffer.put_nowait(event)
                    except asyncio.QueueFull:
                        self._metrics.events_dropped += 1
                        logger.warning("Event buffer full, dropping event")

                self._metrics.last_event_time = datetime.now()

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            self._metrics.reconnection_attempts += 1
            raise
        finally:
            if sink:
                self.remove_sink(sink)

    async def _publish_loop(self) -> None:
        """Background loop that consumes buffer and publishes to sinks."""
        while self._running:
            try:
                # Get event from buffer (with timeout to allow checking _running)
                try:
                    event = await asyncio.wait_for(self._event_buffer.get(), timeout=1.0)
                except TimeoutError:
                    continue

                # Publish to all sinks
                for sink in self._sinks:
                    try:
                        await self._publish_with_retry(sink, event)
                        self._metrics.events_published += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to publish to sink {sink.__class__.__name__}: {e}",
                            exc_info=True,
                        )
                        self._metrics.events_failed += 1

            except Exception as e:
                logger.error(f"Publish loop error: {e}", exc_info=True)

    async def _publish_with_retry(
        self,
        sink: StreamSink,
        event: Any,
    ) -> None:
        """Publish event to sink with retry logic.

        Args:
            sink: Sink to publish to
            event: Event to publish

        Raises:
            RelayError: If sink fails after max retries
        """
        consecutive_failures = 0

        for attempt in range(self._max_retries + 1):
            try:
                await sink.publish(event)
                return  # Success
            except Exception as e:
                consecutive_failures += 1
                if attempt < self._max_retries:
                    logger.warning(
                        f"Sink {sink.__class__.__name__} failed (attempt {attempt + 1}/{self._max_retries + 1}): {e}"
                    )
                    await asyncio.sleep(self._retry_delay * (attempt + 1))
                else:
                    raise RelayError(
                        f"Sink {sink.__class__.__name__} failed after {self._max_retries + 1} attempts",
                        sink_name=sink.__class__.__name__,
                        consecutive_failures=consecutive_failures,
                    ) from e

    def get_metrics(self) -> RelayMetrics:
        """Get current relay metrics.

        Returns:
            RelayMetrics with current performance data
        """
        return self._metrics

    async def stop(self) -> None:
        """Stop the relay and close all sinks."""
        self._running = False

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        # Close all sinks
        for sink in self._sinks:
            try:
                await sink.close()
            except Exception as e:
                logger.error(f"Error closing sink {sink.__class__.__name__}: {e}")

        logger.info("StreamRelay stopped")

    async def __aenter__(self) -> StreamRelay:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.stop()
