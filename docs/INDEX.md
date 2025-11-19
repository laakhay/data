# Laakhay Data Library - Documentation Index

Complete index of all documentation for the Laakhay Data library.

## 🏗️ Architecture Documentation

### Core Architecture
- **[Overview](./architecture/overview.md)** - High-level architecture, component interactions, and request flows
- **[Design Decisions](./architecture/design-decisions.md)** - Architecture Decision Records (ADRs) covering major design choices
- **[Models](./architecture/models.md)** - Data models architecture, immutability patterns, and usage
- **[Provider System](./architecture/provider-system.md)** - Provider lifecycle and registration

### System Layers
- **[I/O Layer](./architecture/io-layer.md)** - REST/WebSocket transport abstractions and provider interfaces
- **[Clients Layer](./architecture/clients.md)** - High-level streaming feeds with caching and subscriptions
- **[Sinks](./architecture/sinks.md)** - Stream sink implementations for event forwarding

## 📝 Inline Code Documentation

All core modules include comprehensive inline architectural comments:

### Core Modules (`laakhay/data/core/`)
- **`api.py`** - DataAPI facade pattern, default parameter resolution
- **`router.py`** - DataRouter coordination, request flow
- **`registry.py`** - Provider registry, instance pooling
- **`capabilities.py`** - Hierarchical capability registry
- **`urm.py`** - Universal Representation Mapping (symbol normalization)
- **`relay.py`** - Stream relay pattern, backpressure handling
- **`request.py`** - Request object pattern, validation
- **`capability_service.py`** - Capability validation service
- **`base.py`** - Abstract base class for providers
- **`enums.py`** - Standardized types and enums
- **`exceptions.py`** - Exception hierarchy

### Models (`laakhay/data/models/`)
- **`__init__.py`** - Module overview and model categories
- **`ohlcv.py`** - OHLCV series model with architectural comments

### I/O Layer (`laakhay/data/io/`)
- **`rest/provider.py`** - REST provider interface
- **`ws/provider.py`** - WebSocket provider interface

### Clients Layer (`laakhay/data/clients/`)
- **`base_feed.py`** - Base feed architecture
- **`ohlcv_feed.py`** - OHLCV feed architecture

### Sinks (`laakhay/data/sinks/`)
- **`in_memory.py`** - In-memory sink implementation
- **`redis.py`** - Redis Streams sink implementation

## 🎯 Quick Navigation

### By Topic

**Understanding the Architecture:**
1. Start with [Architecture Overview](./architecture/overview.md)
2. Read [Design Decisions](./architecture/design-decisions.md) for rationale
3. Explore specific layers: [I/O](./architecture/io-layer.md), [Clients](./architecture/clients.md), [Models](./architecture/models.md)
4. Dive into [Provider System](./architecture/provider-system.md) for exchange-specific details

**Using the Library:**
- See inline documentation in `core/api.py` for DataAPI usage
- Check `clients/ohlcv_feed.py` for feed examples
- Review `sinks/` for event forwarding patterns

**Extending the Library:**
- Review `io/rest/provider.py` and `io/ws/provider.py` for provider interfaces
- Check `core/base.py` for base provider class
- See `core/registry.py` for provider registration

### By Component

**Routing & Coordination:**
- `core/api.py` - High-level facade
- `core/router.py` - Request routing
- `core/registry.py` - Provider management
- `core/request.py` - Request model

**Capabilities & Validation:**
- `core/capabilities.py` - Capability registry
- `core/capability_service.py` - Validation service

**Symbol Normalization:**
- `core/urm.py` - URM system

**Streaming:**
- `core/relay.py` - Stream relay
- `clients/base_feed.py` - Base feeds
- `clients/ohlcv_feed.py` - OHLCV feeds
- `sinks/` - Event sinks

**Data Models:**
- `models/` - All data models
- `core/enums.py` - Type definitions

## 🔗 External Resources

- [Main README](../README.md) - Library overview and installation
- [Pydantic Documentation](https://docs.pydantic.dev/) - Data model framework
