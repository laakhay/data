"""Redis Streams sink for forwarding market data to Redis.

This sink publishes events to Redis Streams, enabling persistence and
multi-consumer scenarios.
"""

from __future__ import annotations

import json
from typing import Any


class RedisStreamSink:
    """Redis Streams sink that publishes events to Redis.

    Requires redis-py library. Events are serialized as JSON and published
    to a Redis stream with configurable key and batching.
    """

    def __init__(
        self,
        stream_key: str,
        *,
        redis_client: Any | None = None,
        batch_size: int = 1,
        batch_timeout: float = 0.1,
    ) -> None:
        """Initialize Redis stream sink.

        Args:
            stream_key: Redis stream key (e.g., "market-data:trades")
            redis_client: Optional redis client (creates new if None)
            batch_size: Number of events to batch before publishing
            batch_timeout: Maximum time to wait before flushing batch (seconds)

        Raises:
            ImportError: If redis library is not installed
        """
        try:
            import redis.asyncio as redis
        except ImportError:
            raise ImportError(
                "Redis sink requires redis library. Install with: pip install redis"
            ) from None

        self.stream_key = stream_key
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self._redis: Any = redis_client or redis.Redis()
        self._batch: list[dict[str, Any]] = []
        self._closed = False

    async def publish(self, event: Any) -> None:
        """Publish event to Redis stream.

        Args:
            event: Data event to publish

        Raises:
            RuntimeError: If sink is closed
            Exception: If Redis operation fails
        """
        if self._closed:
            raise RuntimeError("Sink is closed")

        # Serialize event to dict
        if hasattr(event, "model_dump"):
            # Pydantic model
            event_dict = event.model_dump()
        elif hasattr(event, "dict"):
            # Pydantic v1
            event_dict = event.dict()
        elif isinstance(event, dict):
            event_dict = event
        else:
            # Fallback: convert to dict
            event_dict = {"data": str(event), "type": type(event).__name__}

        # Add to batch
        self._batch.append(event_dict)

        # Publish if batch is full
        if len(self._batch) >= self.batch_size:
            await self._flush_batch()

    async def _flush_batch(self) -> None:
        """Flush current batch to Redis."""
        if not self._batch:
            return

        # Create stream entries
        entries = {}
        for i, event_dict in enumerate(self._batch):
            # Use timestamp as score for ordering
            entry_id = f"{int(event_dict.get('timestamp', 0) * 1000)}-{i}"
            entries[entry_id] = json.dumps(event_dict)

        # Publish to Redis stream
        if entries:
            await self._redis.xadd(self.stream_key, entries)

        self._batch.clear()

    async def close(self) -> None:
        """Close sink and flush any remaining batch."""
        if not self._closed:
            await self._flush_batch()
            await self._redis.aclose()
            self._closed = True
