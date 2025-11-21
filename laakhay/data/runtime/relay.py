"""Stream relay for forwarding market data to pluggable sinks.

The StreamRelay subscribes to data streams via the DataRouter and forwards
events to pluggable sinks (in-memory queues, Redis, Kafka, etc.).

Architecture:
    This module implements the Stream Relay pattern to decouple data streams
    from downstream consumers. Key responsibilities:
    - Subscribe to streams via DataRouter
    - Buffer events to handle sink backpressure
    - Forward events to multiple sinks (fan-out)
    - Handle sink failures with retry logic
    - Provide metrics for observability

Design Decisions:
    - Protocol-based sinks: Flexible, any implementation works
    - Buffering: Decouples stream rate from sink processing rate
    - Backpressure policies: Configurable (drop/block/buffer)
    - Retry logic: Exponential backoff for sink failures
    - Metrics: Track published, dropped, failed events

Backpressure Policies:
    - "drop": Drop events when buffer full (low latency, may lose data)
    - "block": Block until space available (no data loss, may slow stream)
    - "buffer": Try to buffer, drop if full (hybrid approach)

See Also:
    - ADR-007: Architecture Decision Record for stream relay
    - StreamSink: Protocol for sink implementations
    - DataRouter: Provides streams to relay
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from ..core.enums import TransportKind
from ..core.exceptions import RelayError
from ..core.request import DataRequest
from .router import DataRouter

logger = logging.getLogger(__name__)


class StreamSink(Protocol):
    """Protocol for stream sinks that receive market data events.

    Sinks can be in-memory queues, Redis Streams, Kafka, or any custom backend.

    Architecture:
        Protocol-based design allows any class implementing publish() and close()
        to be used as a sink. This provides flexibility for different backends
        without requiring inheritance or complex abstractions.

    Design Decision:
        Protocol chosen for simplicity and flexibility. Sinks can be simple
        (InMemorySink) or complex (RedisStreamSink) without shared base class.
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
        # Architecture: Router injection for testability
        self._router = router or DataRouter()
        # Architecture: Multiple sinks supported (fan-out pattern)
        # Events are published to all registered sinks
        self._sinks: list[StreamSink] = []
        self._max_buffer_size = max_buffer_size
        self._backpressure_policy = backpressure_policy
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        # Architecture: Metrics for observability
        # Track published, dropped, failed events for monitoring
        self._metrics = RelayMetrics()
        self._running = False
        # Architecture: Background tasks for async operations
        # Publish loop runs in separate task to avoid blocking stream
        self._tasks: list[asyncio.Task[None]] = []
        # Architecture: Event buffer decouples stream from sinks
        # Bounded queue prevents unbounded memory growth
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

        # Architecture: Producer-consumer pattern
        # Background task consumes buffer and publishes to sinks
        # Main loop subscribes to stream and buffers events
        task = asyncio.create_task(self._publish_loop())
        self._tasks.append(task)

        # Architecture: Subscribe to stream via DataRouter
        # Router handles capability validation, URM resolution, provider lookup
        try:
            async for event in self._router.route_stream(request):
                if not self._running:
                    break

                # Architecture: Apply backpressure policy
                # Different policies handle buffer full condition differently
                if self._backpressure_policy == "drop":
                    # Performance: Drop events when buffer full (low latency)
                    # Use case: Real-time systems where latest data is more important
                    if self._event_buffer.full():
                        self._metrics.events_dropped += 1
                        logger.warning("Event buffer full, dropping event")
                        continue
                    self._event_buffer.put_nowait(event)
                elif self._backpressure_policy == "block":
                    # Architecture: Block until space available (no data loss)
                    # Use case: Systems where data integrity is critical
                    await self._event_buffer.put(event)
                else:  # buffer
                    # Architecture: Try to buffer, drop if full (hybrid)
                    # Use case: Balance between latency and data loss
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
        """Background loop that consumes buffer and publishes to sinks.

        Architecture:
            This loop runs in a separate task, decoupling stream consumption
            from sink publishing. This allows sinks to be slow without blocking
            the stream. Timeout allows checking _running flag periodically.
        """
        while self._running:
            try:
                # Architecture: Get event with timeout
                # Timeout allows checking _running flag to exit gracefully
                try:
                    event = await asyncio.wait_for(self._event_buffer.get(), timeout=1.0)
                except TimeoutError:
                    continue

                # Architecture: Fan-out to all sinks
                # Each sink receives the same event (broadcast pattern)
                # Sinks are independent - one failure doesn't affect others
                for sink in self._sinks:
                    try:
                        await self._publish_with_retry(sink, event)
                        self._metrics.events_published += 1
                    except Exception as e:
                        # Architecture: Sink failures are logged but don't stop relay
                        # Failed events are tracked in metrics for monitoring
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

        # Architecture: Retry with exponential backoff
        # Exponential backoff: delay * (attempt + 1) reduces retry pressure
        # Max retries prevents infinite retry loops
        for attempt in range(self._max_retries + 1):
            try:
                await sink.publish(event)
                return  # Success
            except Exception as e:
                consecutive_failures += 1
                if attempt < self._max_retries:
                    # Architecture: Exponential backoff
                    # Delay increases with each attempt: 1s, 2s, 3s, ...
                    logger.warning(
                        f"Sink {sink.__class__.__name__} failed (attempt {attempt + 1}/{self._max_retries + 1}): {e}"
                    )
                    await asyncio.sleep(self._retry_delay * (attempt + 1))
                else:
                    # Architecture: Raise RelayError after max retries
                    # This allows caller to handle persistent sink failures
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
