# Stream Relay Examples

## Basic Relay

```python
import asyncio
from laakhay.data.core import StreamRelay, DataRequest, DataFeature, TransportKind, MarketType
from laakhay.data.sinks import InMemorySink

async def basic_relay():
    relay = StreamRelay()
    sink = InMemorySink()
    relay.add_sink(sink)
    
    request = DataRequest(
        feature=DataFeature.TRADES,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
    )
    
    # Start relaying in background
    relay_task = asyncio.create_task(relay.relay(request))
    
    # Consume from sink
    async for event in sink.stream():
        print(f"Trade: {event.symbol} @ {event.price}")
        # Stop after 10 events
        if sink.qsize() >= 10:
            break
    
    # Stop relay
    await relay.stop()
    relay_task.cancel()

asyncio.run(basic_relay())
```

## Multiple Sinks

```python
from laakhay.data.sinks import InMemorySink, RedisStreamSink

async def multiple_sinks():
    relay = StreamRelay()
    
    # Add multiple sinks
    memory_sink = InMemorySink()
    redis_sink = RedisStreamSink("market-data:trades")
    
    relay.add_sink(memory_sink)
    relay.add_sink(redis_sink)
    
    request = DataRequest(
        feature=DataFeature.TRADES,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
    )
    
    relay_task = asyncio.create_task(relay.relay(request))
    
    # Consume from memory sink
    async for event in memory_sink.stream():
        print(f"Trade: {event.symbol} @ {event.price}")
        if memory_sink.qsize() >= 10:
            break
    
    await relay.stop()
    relay_task.cancel()

asyncio.run(multiple_sinks())
```

## Backpressure Policies

### Drop Policy (Low Latency)

```python
async def drop_policy():
    relay = StreamRelay(
        max_buffer_size=100,
        backpressure_policy="drop",  # Drop events when buffer full
    )
    sink = InMemorySink()
    relay.add_sink(sink)
    
    request = DataRequest(
        feature=DataFeature.TRADES,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
    )
    
    relay_task = asyncio.create_task(relay.relay(request))
    
    # Slow consumer
    await asyncio.sleep(5)
    
    metrics = relay.get_metrics()
    print(f"Published: {metrics.events_published}")
    print(f"Dropped: {metrics.events_dropped}")
    
    await relay.stop()
    relay_task.cancel()

asyncio.run(drop_policy())
```

### Block Policy (No Data Loss)

```python
async def block_policy():
    relay = StreamRelay(
        max_buffer_size=1000,
        backpressure_policy="block",  # Block until space available
    )
    sink = InMemorySink()
    relay.add_sink(sink)
    
    request = DataRequest(
        feature=DataFeature.TRADES,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
    )
    
    relay_task = asyncio.create_task(relay.relay(request))
    await asyncio.sleep(5)
    await relay.stop()
    relay_task.cancel()

asyncio.run(block_policy())
```

## Custom Sink

```python
class CustomSink:
    async def publish(self, event):
        # Custom processing
        print(f"Processing: {event.symbol} @ {event.price}")
        # Could send to database, message queue, etc.
    
    async def close(self):
        # Cleanup
        pass

async def custom_sink():
    relay = StreamRelay()
    custom = CustomSink()
    relay.add_sink(custom)
    
    request = DataRequest(
        feature=DataFeature.TRADES,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
    )
    
    relay_task = asyncio.create_task(relay.relay(request))
    await asyncio.sleep(5)
    await relay.stop()
    relay_task.cancel()

asyncio.run(custom_sink())
```

## Metrics

```python
async def with_metrics():
    relay = StreamRelay()
    sink = InMemorySink()
    relay.add_sink(sink)
    
    request = DataRequest(
        feature=DataFeature.TRADES,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
    )
    
    relay_task = asyncio.create_task(relay.relay(request))
    await asyncio.sleep(10)
    
    metrics = relay.get_metrics()
    print(f"Events published: {metrics.events_published}")
    print(f"Events dropped: {metrics.events_dropped}")
    print(f"Events failed: {metrics.events_failed}")
    print(f"Reconnection attempts: {metrics.reconnection_attempts}")
    print(f"Last event time: {metrics.last_event_time}")
    
    await relay.stop()
    relay_task.cancel()

asyncio.run(with_metrics())
```

## See Also

- [Stream Relay Architecture](../architecture/overview.md#stream-relay) - Architecture details
- [Sinks Architecture](../architecture/sinks.md) - Sink implementations
- [API Reference](../api-reference/data-api.md) - Complete API docs

