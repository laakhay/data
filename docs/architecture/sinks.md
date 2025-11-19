# Sinks Layer Architecture

## Overview

The `sinks/` directory provides implementations of the `StreamSink` protocol for forwarding market data events to various backends. Sinks are used by `StreamRelay` to decouple data streams from downstream consumers.

## StreamSink Protocol

All sinks implement the `StreamSink` protocol:

```python
class StreamSink(Protocol):
    async def publish(self, event: Any) -> None:
        """Publish a data event to the sink."""
    
    async def close(self) -> None:
        """Close the sink and clean up resources."""
```

## Sink Implementations

### InMemorySink

In-memory sink for testing and development.

**Features:**
- Async queue-based storage
- Bounded queue (optional maxsize)
- Stream interface (async iteration)
- Simple get/put operations

**Use Cases:**
- Unit testing
- Development and debugging
- Simple applications without persistence needs

**Example:**
```python
sink = InMemorySink(maxsize=1000)

# Publish events
await sink.publish(trade_event)

# Consume events
async for event in sink.stream():
    process(event)
```

### RedisStreamSink

Redis Streams sink for persistent storage.

**Features:**
- Redis Streams backend
- Automatic batching (configurable)
- Pydantic model serialization
- Multi-consumer support
- Persistence across restarts

**Use Cases:**
- Production event storage
- Multi-consumer scenarios
- Event replay
- Integration with other systems

**Example:**
```python
sink = RedisStreamSink(
    stream_key="market-data:trades",
    batch_size=10,
    batch_timeout=0.1
)

# Publish events (batched automatically)
await sink.publish(trade_event)
```

## Integration with StreamRelay

Sinks are used by `StreamRelay` to forward streams:

```python
relay = StreamRelay(router)

# Add sinks
relay.add_sink(InMemorySink())
relay.add_sink(RedisStreamSink("market-data:ohlcv"))

# Relay stream to all sinks
await relay.relay(request)
```

## Design Patterns

### Protocol-Based Design

Sinks use the Protocol pattern for flexibility:
- No inheritance required
- Easy to implement custom sinks
- Type-safe with Protocol

### Batching Pattern

Some sinks (e.g., RedisStreamSink) implement batching:
- Reduces I/O operations
- Configurable batch size and timeout
- Automatic flushing

### Serialization Strategy

Sinks handle different event types:
- Pydantic models: Automatic serialization
- Dicts: Direct use
- Other types: Fallback serialization

## Creating Custom Sinks

To create a custom sink, implement the `StreamSink` protocol:

```python
class CustomSink:
    async def publish(self, event: Any) -> None:
        # Custom publishing logic
        pass
    
    async def close(self) -> None:
        # Cleanup resources
        pass
```

## See Also

- [Stream Relay](./overview.md#stream-relay) - Uses sinks for forwarding
- [I/O Layer](./io-layer.md) - Transport abstractions
- [Models](./models.md) - Event data models

