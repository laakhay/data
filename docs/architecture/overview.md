# Architecture Overview

## High-Level Architecture

The Laakhay Data library follows a **layered, provider-agnostic architecture** designed to provide unified access to cryptocurrency market data across multiple exchanges.

### Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  DataAPI, High-Level Feeds, Stream Relay                    │
│  - User-facing API                                          │
│  - Simplified interface                                     │
│  - Default configuration                                    │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Routing Layer                             │
│  DataRouter, CapabilityService, URM Registry                │
│  - Request routing                                          │
│  - Symbol normalization                                     │
│  - Capability validation                                    │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Provider Layer                            │
│  BaseProvider, RESTProvider, WSProvider                      │
│  - Exchange-specific implementations                        │
│  - Feature handlers                                         │
│  - Transport abstraction                                    │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Transport Layer                            │
│  HTTP Transport, WebSocket Transport, Adapters               │
│  - Network communication                                    │
│  - Message parsing                                          │
│  - Reconnection logic                                       │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Exchange APIs                             │
│  Binance, Bybit, OKX, Hyperliquid, Kraken, Coinbase        │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. DataAPI (Application Layer)

**Purpose:** High-level facade providing unified interface for data access.

**Responsibilities:**
- Default configuration management
- Request parameter resolution
- Delegation to DataRouter
- Resource lifecycle management

**Key Features:**
- Context manager support for cleanup
- Default exchange/market type configuration
- Convenient `fetch_*` and `stream_*` methods

### 2. DataRouter (Routing Layer)

**Purpose:** Central coordinator for request routing.

**Responsibilities:**
- Capability validation
- Symbol resolution via URM
- Provider lookup
- Feature handler invocation

**Request Flow:**
```
DataRequest → Capability Validation → URM Resolution → Provider Lookup → Method Invocation → Result
```

### 3. ProviderRegistry (Provider Layer)

**Purpose:** Manages provider lifecycles and feature routing.

**Responsibilities:**
- Provider instance pooling
- Feature handler mapping
- URM mapper registration
- Async context lifecycle

**Key Features:**
- Singleton pattern for global access
- Lazy provider instantiation
- Instance reuse across requests
- Automatic cleanup on shutdown

### 4. URM System (Routing Layer)

**Purpose:** Universal Representation Mapping for symbol normalization.

**Responsibilities:**
- Exchange-native to canonical symbol conversion
- Canonical to exchange-native symbol conversion
- Symbol resolution caching
- Error handling with helpful messages

**Key Features:**
- Exchange-specific mappers
- 5-minute cache TTL
- Support for URM IDs and normalized formats

### 5. Capability System (Routing Layer)

**Purpose:** Runtime and static feature discovery.

**Responsibilities:**
- Capability validation
- Constraint checking
- Alternative recommendations
- Error message generation

**Key Features:**
- Hierarchical capability registry
- Static and runtime discovery
- Stream metadata
- Fallback suggestions

## Data Flow

### REST Request Flow

```
User Code
  ↓
DataAPI.fetch_ohlcv()
  ↓
DataRouter.route()
  ↓
  ├─→ CapabilityService.validate_request()
  ├─→ URMRegistry.urm_to_exchange_symbol()
  ├─→ ProviderRegistry.get_provider()
  └─→ Provider.get_candles()
      ↓
  RESTProvider.get_candles()
      ↓
  HTTPTransport.request()
      ↓
  ResponseAdapter.normalize()
      ↓
  Return OHLCV model
```

### WebSocket Stream Flow

```
User Code
  ↓
DataAPI.stream_trades()
  ↓
DataRouter.route_stream()
  ↓
  ├─→ CapabilityService.validate_request()
  ├─→ URMRegistry.urm_to_exchange_symbol()
  ├─→ ProviderRegistry.get_provider()
  └─→ Provider.stream_trades()
      ↓
  WSProvider.stream_trades()
      ↓
  WebSocketTransport.connect()
      ↓
  MessageAdapter.parse()
      ↓
  Yield Trade models
```

## Design Principles

### 1. Provider-Agnostic Interface

All providers implement the same `BaseProvider` interface, allowing code to work across exchanges without modification.

**Benefits:**
- Easy exchange switching
- Consistent API surface
- Simplified testing

### 2. Transport Abstraction

REST and WebSocket are abstracted through `RESTProvider` and `WSProvider` interfaces.

**Benefits:**
- Unified interface for different transports
- Easy to add new transports
- Consistent error handling

### 3. Symbol Normalization

URM system handles exchange-specific symbol formats automatically.

**Benefits:**
- No manual symbol conversion
- Support for multiple symbol formats
- Consistent symbol handling

### 4. Capability Validation

Requests are validated before execution with helpful error messages.

**Benefits:**
- Early error detection
- Helpful error messages
- Alternative suggestions

### 5. Type Safety

Pydantic models ensure data integrity at every layer.

**Benefits:**
- Runtime validation
- Type hints
- Immutable models

### 6. Async-First Design

All I/O operations are async to maximize throughput.

**Benefits:**
- High concurrency
- Non-blocking operations
- Efficient resource usage

## Component Interactions

### Provider Registration

```
Provider Class
  ↓
@register_feature_handler decorators
  ↓
collect_feature_handlers()
  ↓
ProviderRegistry.register()
  ↓
Feature handlers mapped to (DataFeature, TransportKind)
```

### Request Routing

```
DataRequest
  ↓
DataRouter.route()
  ↓
  ├─→ CapabilityService → CapabilityStatus
  ├─→ URMRegistry → Exchange Symbol
  ├─→ ProviderRegistry → Provider Instance
  └─→ Feature Handler → Method Invocation
```

### Stream Relay

```
DataRequest (WS)
  ↓
StreamRelay.relay()
  ↓
DataRouter.route_stream()
  ↓
Provider.stream_*()
  ↓
StreamRelay._publish_loop()
  ↓
Sink.publish()
```

## Error Propagation

```
Exchange API Error
  ↓
Transport Layer (HTTP/WS)
  ↓
Provider Layer
  ↓
Router Layer (if applicable)
  ↓
Application Layer
  ↓
User Code
```

**Exception Hierarchy:**
- `DataError` (base)
  - `CapabilityError`
  - `ProviderError`
    - `RateLimitError`
    - `InvalidSymbolError`
    - `InvalidIntervalError`
  - `ValidationError`
  - `SymbolResolutionError`
  - `RelayError`

## Performance Characteristics

### Connection Management
- Provider pooling: One instance per (exchange, market_type)
- HTTP session reuse
- WebSocket multiplexing when supported

### Caching
- URM cache: 5-minute TTL
- Symbol metadata: Cached per exchange/market_type
- Feed cache: Latest values cached

### Concurrency
- Async/await throughout
- Non-blocking I/O
- Proper task management

## Extension Points

### Adding a New Exchange

1. Implement `RESTProvider` and `WSProvider`
2. Create URM mapper
3. Register provider with `ProviderRegistry`
4. Add capability metadata
5. Write tests

### Adding a New Feature

1. Define `DataFeature` enum value
2. Implement in providers
3. Register feature handlers
4. Add capability metadata
5. Update DataAPI if needed

### Adding a New Sink

1. Implement `StreamSink` protocol
2. Register with `StreamRelay`
3. Handle errors appropriately

## Related Documentation

- [Design Decisions](./design-decisions.md) - Architecture Decision Records
- [Routing System](./routing-system.md) - DataRouter details
- [Provider System](./provider-system.md) - Provider architecture
- [URM System](./urm-system.md) - Symbol normalization
- [Capability System](./capability-system.md) - Capability discovery
- [Streaming Architecture](./streaming-architecture.md) - Streaming & feeds


