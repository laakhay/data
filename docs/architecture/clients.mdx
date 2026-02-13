# Clients Layer Architecture

## Overview

The `clients/` directory provides high-level streaming feeds built on top of the I/O layer. These feeds add features like caching, subscriptions, history tracking, and event handling.

## Design Principles

### High-Level Abstractions
- Feeds provide convenient interfaces for common use cases
- Hide complexity of provider management
- Add value through caching, subscriptions, history

### Subscription Pattern
- Callbacks for feed updates
- Filtering by symbol/key
- Multiple subscribers per feed

### Lifecycle Management
- Start/stop/restart streams
- Proper cleanup of resources
- Background task management

## Base Feed

### BaseStreamFeed

Generic base class for streaming feeds.

**Features:**
- Type-safe with TypeVar
- Key-based caching (latest value per key)
- Subscription management
- Staleness detection
- Lifecycle management

**Key Methods:**
- `start()`: Start streaming
- `stop()`: Stop streaming
- `subscribe()`: Subscribe to updates
- `unsubscribe()`: Remove subscription
- `get_latest()`: Get cached latest value

### SymbolStreamFeed

Specialization of BaseStreamFeed for symbol-keyed streams.

**Features:**
- Symbol-based keying
- Symbol filtering in subscriptions
- Symbol-specific caching

## High-Level Feeds

### OHLCVFeed

Real-time OHLCV streaming feed.

**Features:**
- Multi-symbol streaming with automatic chunking
- Bar history tracking (configurable depth)
- REST warm-up (fetch historical before streaming)
- Deduplication and throttling
- Connection event handling
- Event subscriptions (bar updates, connection events)

**Usage:**
```python
feed = OHLCVFeed(ws_provider, rest_provider=rest_provider)

# Subscribe to bar updates
sub_id = feed.subscribe_bar(
    callback=handle_bar,
    symbols={"BTC/USDT", "ETH/USDT"},
    interval=Timeframe.M1
)

# Start streaming
await feed.start(
    symbols=["BTC/USDT", "ETH/USDT"],
    interval=Timeframe.M1,
    warm_up=100  # Fetch 100 bars from REST first
)
```

### LiquidationFeed

Liquidation event feed.

**Features:**
- Real-time liquidation events
- Symbol filtering
- Large liquidation detection

### OpenInterestFeed

Open interest feed.

**Features:**
- Real-time open interest updates
- Historical tracking
- Symbol filtering

## Feed Architecture

### Caching Strategy

Feeds maintain caches of latest values:
- Key-based: One value per key (e.g., symbol)
- Staleness detection: Track last update time
- Automatic expiration: Remove stale entries

### Subscription Management

- Multiple subscribers per feed
- Filtering: Subscribe to specific symbols/keys
- Callback execution: Async or sync callbacks
- Unsubscribe: Clean removal of subscriptions

### Lifecycle

1. **Initialization**: Create feed with providers
2. **Start**: Begin streaming with parameters
3. **Running**: Stream data, update cache, notify subscribers
4. **Stop**: Cancel tasks, cleanup resources

### Background Tasks

Feeds run background tasks for:
- Stream consumption
- Cache updates
- Subscriber notifications
- Staleness checks

## Integration with Providers

Feeds wrap providers and add:
- Caching layer
- Subscription system
- History tracking
- Event handling
- Connection management

## See Also

- [I/O Layer](./io-layer.md) - Transport abstractions
- [Provider System](./provider-system.md) - Exchange implementations
- [Models](./models.md) - Data models
