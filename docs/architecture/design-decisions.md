# Architecture Decision Records (ADRs)

This document records the major architectural decisions made in the Laakhay Data library, along with their context and consequences.

## ADR Format

Each ADR follows this structure:
- **Status**: Proposed | Accepted | Deprecated | Superseded
- **Context**: The issue motivating this decision
- **Decision**: The change that we're proposing or have agreed to implement
- **Consequences**: What becomes easier or more difficult because of this change

---

## ADR-001: Provider-Agnostic Architecture

**Status:** Accepted  
**Date:** 2025-11-19

### Context

Different cryptocurrency exchanges have different APIs, symbol formats, rate limits, and capabilities. We needed a way to provide a unified interface while supporting exchange-specific implementations.

### Decision

We implement a provider-agnostic architecture where:
1. All providers implement the same `BaseProvider` interface
2. Exchange-specific logic is encapsulated in provider implementations
3. A `ProviderRegistry` manages provider instances and feature routing
4. A `DataRouter` coordinates requests across providers

### Consequences

**Positive:**
- Code works across exchanges without modification
- Easy to add new exchanges
- Consistent API surface
- Simplified testing (can mock BaseProvider)

**Negative:**
- Some exchange-specific features may not be exposed
- Provider implementations must handle exchange quirks
- Initial setup complexity (registry, routing)

**Alternatives Considered:**
- Exchange-specific APIs (rejected: too much duplication)
- Adapter pattern only (rejected: doesn't handle capability differences)
- Single provider with exchange parameter (rejected: too complex)

---

## ADR-002: Universal Representation Mapping (URM)

**Status:** Accepted  
**Date:** 2025-11-19

### Context

Exchanges use different symbol formats:
- Binance: `BTCUSDT`
- Kraken Spot: `XBT/USD`
- Kraken Futures: `PI_XBTUSD`
- Coinbase: `BTC-USD`
- Hyperliquid: `BTC` (normalized internally)

Users shouldn't need to know exchange-specific formats.

### Decision

We implement a Universal Representation Mapping (URM) system:
1. Canonical format: `BASE/QUOTE` (e.g., `BTC/USDT`)
2. Exchange-specific mappers convert to/from canonical format
3. URM IDs supported: `urm://exchange:base/quote:instrument_type`
4. Caching for performance (5-minute TTL)

### Consequences

**Positive:**
- Users can use consistent symbol format
- Automatic conversion to exchange-native format
- Support for multiple input formats
- Cached for performance

**Negative:**
- Additional complexity in symbol resolution
- Cache invalidation considerations
- Some edge cases in symbol mapping

**Alternatives Considered:**
- Force users to use exchange-native formats (rejected: poor UX)
- Single global symbol format (rejected: loses exchange-specific info)
- No normalization (rejected: too error-prone)

---

## ADR-003: Capability System

**Status:** Accepted  
**Date:** 2025-11-19

### Context

Different exchanges support different features:
- Some support liquidations, others don't
- Some support futures, others only spot
- Some support certain timeframes, others don't
- Features may be REST-only or WebSocket-only

We need to validate requests and provide helpful error messages.

### Decision

We implement a hierarchical capability system:
1. Static capability registry: `Exchange → MarketType → InstrumentType → Feature → Transport → Status`
2. Runtime capability discovery (optional, for dynamic features)
3. Capability validation before request routing
4. Helpful error messages with alternative suggestions

### Consequences

**Positive:**
- Early error detection (before API calls)
- Helpful error messages
- Alternative suggestions
- Clear capability documentation

**Negative:**
- Maintenance overhead (keep capability registry updated)
- Static registry may become stale
- Additional validation step

**Alternatives Considered:**
- Try-and-fail approach (rejected: poor UX, wasted API calls)
- Runtime discovery only (rejected: too slow, unreliable)
- No validation (rejected: confusing errors)

---

## ADR-004: DataRouter Pattern

**Status:** Accepted  
**Date:** 2025-11-19

### Context

We need to coordinate:
- Capability validation
- Symbol resolution (URM)
- Provider lookup
- Feature handler invocation

This coordination logic could live in DataAPI, but that would make it too complex.

### Decision

We introduce a `DataRouter` that:
1. Validates capabilities
2. Resolves symbols via URM
3. Looks up providers and feature handlers
4. Invokes provider methods with normalized parameters

DataAPI delegates to DataRouter for actual routing.

### Consequences

**Positive:**
- Separation of concerns
- Testable routing logic
- Reusable across different entry points
- Clear request flow

**Negative:**
- Additional abstraction layer
- More components to understand

**Alternatives Considered:**
- Routing logic in DataAPI (rejected: too complex)
- Routing logic in providers (rejected: duplication)
- No routing layer (rejected: can't coordinate URM + capabilities)

---

## ADR-005: Async-First Design

**Status:** Accepted  
**Date:** 2025-11-19

### Context

Market data requires:
- High throughput (many symbols, frequent updates)
- Low latency (real-time streaming)
- Concurrent operations (multiple exchanges, multiple symbols)

Synchronous I/O would be a bottleneck.

### Decision

We design the library as async-first:
1. All I/O operations use `async/await`
2. Built on `asyncio`, `aiohttp`, and `websockets`
3. Async context managers for resource cleanup
4. Async iterators for streaming

### Consequences

**Positive:**
- High concurrency
- Non-blocking operations
- Efficient resource usage
- Modern Python patterns

**Negative:**
- Requires async code from users
- More complex error handling
- Debugging async code is harder

**Alternatives Considered:**
- Synchronous with threading (rejected: GIL limitations, complexity)
- Synchronous with callbacks (rejected: callback hell)
- Hybrid sync/async (rejected: confusion, maintenance burden)

---

## ADR-006: Pydantic Models

**Status:** Accepted  
**Date:** 2025-11-19

### Context

We need:
- Type safety
- Runtime validation
- Immutable data structures
- Clear data contracts

Python's built-in types don't provide enough structure.

### Decision

We use Pydantic v2 for all data models:
1. All models are Pydantic `BaseModel` subclasses
2. Models are frozen (immutable)
3. Comprehensive validation
4. Type hints throughout

### Consequences

**Positive:**
- Runtime validation catches errors early
- Type hints improve IDE support
- Immutability prevents accidental mutations
- Clear data contracts

**Negative:**
- Pydantic dependency
- Some performance overhead (minimal)
- Learning curve for Pydantic

**Alternatives Considered:**
- Dataclasses (rejected: no validation, mutable by default)
- TypedDict (rejected: no validation, no immutability)
- Custom validation (rejected: too much work)

---

## ADR-007: Stream Relay Pattern

**Status:** Accepted  
**Date:** 2025-11-19

### Context

Users need to:
- Forward streams to external systems (Redis, Kafka, databases)
- Handle backpressure
- Manage multiple sinks
- Monitor stream health

Direct provider streams don't support this.

### Decision

We implement a `StreamRelay` that:
1. Subscribes to streams via DataRouter
2. Forwards events to pluggable sinks (`StreamSink` protocol)
3. Handles backpressure (drop/block/buffer policies)
4. Provides metrics and observability

### Consequences

**Positive:**
- Pluggable sinks (Redis, Kafka, custom)
- Backpressure handling
- Metrics and monitoring
- Separation of concerns

**Negative:**
- Additional abstraction
- More components to understand
- Potential performance overhead

**Alternatives Considered:**
- Users handle forwarding themselves (rejected: too much boilerplate)
- Built-in Redis/Kafka support only (rejected: not flexible enough)
- No relay layer (rejected: missing important use case)

---

## ADR-008: Feature Handler Registration

**Status:** Accepted  
**Date:** 2025-11-19

### Context

We need to map `(DataFeature, TransportKind)` pairs to provider methods. This mapping could be:
- Hardcoded (not flexible)
- Convention-based (error-prone)
- Explicit registration (clear but verbose)

### Decision

We use decorator-based feature handler registration:
1. `@register_feature_handler(DataFeature, TransportKind)` decorator
2. `collect_feature_handlers()` scans provider class
3. Handlers stored in `ProviderRegistry`
4. DataRouter looks up handlers for routing

### Consequences

**Positive:**
- Explicit and clear
- Easy to see what methods handle what features
- Type-safe
- Self-documenting

**Negative:**
- Requires decorators on every handler method
- Slight boilerplate

**Alternatives Considered:**
- Convention-based naming (rejected: error-prone, unclear)
- Manual registration (rejected: too verbose, error-prone)
- Hardcoded mapping (rejected: not flexible)

---

## ADR-009: Provider Instance Pooling

**Status:** Accepted  
**Date:** 2025-11-19

### Context

Provider instances are expensive to create (HTTP sessions, WebSocket connections). Creating a new instance for every request would be inefficient.

### Decision

We implement provider instance pooling:
1. One provider instance per `(exchange, market_type)` combination
2. Instances cached in `ProviderRegistry`
3. Instances entered into async context automatically
4. Cleanup on registry shutdown

### Consequences

**Positive:**
- Efficient resource usage
- Connection reuse
- Lower latency (no instance creation overhead)

**Negative:**
- Shared state between requests (usually fine)
- Cleanup complexity
- Potential memory usage (one instance per combination)

**Alternatives Considered:**
- New instance per request (rejected: too slow, wasteful)
- Global singleton (rejected: can't support different market types)
- Manual instance management (rejected: too much boilerplate)

---

## Summary

These ADRs document the key architectural decisions that shape the Laakhay Data library. They provide context for why certain design choices were made and help future developers understand the system's architecture.

For more details on specific components, see:
- [Routing System](./routing-system.md)
- [Provider System](./provider-system.md)
- [URM System](./urm-system.md)
- [Capability System](./capability-system.md)
- [Streaming Architecture](./streaming-architecture.md)


