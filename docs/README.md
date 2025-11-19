# Laakhay Data Library Documentation

Welcome to the comprehensive documentation for the Laakhay Data library.

## Documentation Structure

### 📐 [Architecture](./architecture/)
Deep dive into the library's architecture, design decisions, and system components.

**Core Architecture:**
- [Overview](./architecture/overview.md) - High-level architecture and component interactions
- [Design Decisions](./architecture/design-decisions.md) - Architecture Decision Records (ADRs)
- [Models](./architecture/models.md) - Data models architecture and design patterns

**System Layers:**
- [I/O Layer](./architecture/io-layer.md) - REST/WebSocket transport abstractions
- [Clients Layer](./architecture/clients.md) - High-level streaming feeds

**Core Components (Documented in Code):**
- `core/api.py` - DataAPI facade pattern
- `core/router.py` - DataRouter coordination
- `core/registry.py` - Provider registry and pooling
- `core/capabilities.py` - Capability discovery system
- `core/urm.py` - Universal Representation Mapping
- `core/relay.py` - Stream relay pattern
- `core/request.py` - Request object pattern
- `core/capability_service.py` - Capability validation service

### 📚 [Guides](./guides/)
Step-by-step guides for using the library.

- [Getting Started](./guides/getting-started.md) - Quick start guide
- [Basic Usage](./guides/basic-usage.md) - Basic usage examples
- [Error Handling](./guides/error-handling.md) - Error handling guide

### 📖 [API Reference](./api-reference/)
Complete API documentation.

- [DataAPI](./api-reference/data-api.md) - DataAPI reference
- [Models](./api-reference/models.md) - Data models reference
- [Exceptions](./api-reference/exceptions.md) - Exception reference

### 💡 [Examples](./examples/)
Real-world code examples.

- [Basic REST](./examples/basic-rest.md) - Basic REST examples
- [Basic Streaming](./examples/basic-streaming.md) - Basic streaming examples
- [Multi-Exchange](./examples/multi-exchange.md) - Multi-exchange examples
- [Feeds](./examples/feeds.md) - Feed examples
- [Relay](./examples/relay.md) - Stream relay examples

### 🔧 [Internals](./internals/)
Documentation for library developers and contributors.

- [Provider Development](./internals/provider-development.md) - Provider development guide
- [Testing](./internals/testing.md) - Testing guidelines

## Quick Links

- [Main README](../README.md) - Library overview and installation
- [API Documentation](./api.md) - API surface specification
- [Contributing Guide](../CONTRIBUTING.md) - How to contribute

