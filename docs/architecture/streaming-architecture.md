# Streaming Architecture

## Components

- **`WSProvider` implementations**: manage WebSocket connections per exchange,
  handle subscriptions, heartbeats, and reconnection logic.
- **`DataAPI.stream_*` methods**: expose async iterators that yield typed models.
- **`StreamRelay`**: intermediates between raw streams and sinks, handling
  backpressure and multi-sink fan-out.
- **`clients/` feeds**: high-level abstractions (OHLCVFeed, LiquidationFeed,
  OpenInterestFeed) that add caching, subscription management, and history
  buffering on top of the raw provider streams.
- **`sinks/`**: pluggable destinations (in-memory, Redis Streams) for forwarding
  streaming data.

## Flow

```
WSProvider.stream_* → DataAPI.stream_* / Feed
    → StreamRelay (optional)
        → Sinks (Redis, in-memory, custom)
```

Feeds can warm up caches via REST before starting WS streaming, ensuring alert
systems have enough historical data before consuming live updates.

## Backpressure & Error Handling

- `StreamRelay` offers drop/block policies.
- Feeds detect stale connections and restart automatically.
- Users can subscribe to connection events to monitor health.

## Usage Examples

See [examples/feeds.md](../examples/feeds.md) and [examples/relay.md](../examples/relay.md) for
concrete code snippets.
