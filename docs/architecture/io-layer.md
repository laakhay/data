# I/O Layer Architecture

## Overview

The `io/` directory provides transport abstractions for REST (HTTP) and WebSocket connections. It decouples provider implementations from transport details, allowing for clean separation of concerns.

## Design Principles

### Transport Abstraction
- REST and WebSocket are separate abstractions
- Providers implement transport-specific interfaces
- Transport details (HTTP client, WebSocket client) are encapsulated

### Interface Segregation
- RESTProvider: Pure request/response interface
- WSProvider: Pure streaming interface
- No mixing of REST and WebSocket concepts

### Async-First
- All operations are async
- Non-blocking I/O throughout
- AsyncIterator pattern for streams

## REST Layer

### RESTProvider

Abstract base class for REST-based data providers.

**Required Methods:**
- `get_candles()`: Fetch OHLCV bars
- `get_symbols()`: List trading symbols
- `close()`: Cleanup resources

**Optional Methods:**
- `get_order_book()`: Fetch order book
- `get_recent_trades()`: Fetch recent trades
- `get_funding_rate()`: Fetch funding rates (futures)
- `get_open_interest()`: Fetch open interest (futures)

### RESTTransport

Generic HTTP transport wrapper around HTTPClient.

**Features:**
- GET/POST methods
- Response hooks (e.g., rate-limit detection)
- Base URL configuration

### HTTPClient

Low-level HTTP client implementation.

**Features:**
- Async HTTP requests
- Session management
- Response hooks
- Error handling

## WebSocket Layer

### WSProvider

Abstract base class for WebSocket/streaming providers.

**Required Methods:**
- `stream_ohlcv()`: Stream OHLCV for single symbol
- `stream_ohlcv_multi()`: Stream OHLCV for multiple symbols

**Features:**
- AsyncIterator pattern for streams
- Multi-symbol support
- Configurable options (only_closed, throttle, dedupe)
- Optional `max_streams_per_connection` hint

### WSClient

WebSocket client implementation.

**Features:**
- Connection management
- Reconnection logic
- Message parsing
- Heartbeat handling

### WSTransport

WebSocket transport abstraction.

**Features:**
- Connection lifecycle
- Message sending/receiving
- Error handling

## Provider Pattern

Exchange-specific providers implement both RESTProvider and WSProvider:

```python
class BinanceProvider:
    def __init__(self):
        self._rest = BinanceRESTProvider()
        self._ws = BinanceWSProvider()
    
    # Implements RESTProvider interface
    async def get_candles(...):
        return await self._rest.get_candles(...)
    
    # Implements WSProvider interface
    async def stream_ohlcv(...):
        async for bar in self._ws.stream_ohlcv(...):
            yield bar
```

## Adapter Pattern

Exchange-specific adapters convert between:
- Exchange API format ↔ Library models
- Exchange symbols ↔ Canonical format (via URM)
- Exchange timeframes ↔ Standardized Timeframe enum

## Runner Pattern

Runners manage transport lifecycle:
- Connection establishment
- Reconnection logic
- Heartbeat/ping-pong
- Error recovery
- Resource cleanup

## See Also

- [Provider System](./provider-system.md) - Exchange implementations
- [Core API](./overview.md) - High-level DataAPI
- [Models](./models.md) - Data models

