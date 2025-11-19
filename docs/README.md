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
- [Advanced Usage](./guides/advanced-usage.md) - Advanced patterns
- [Error Handling](./guides/error-handling.md) - Error handling guide
- [Performance](./guides/performance.md) - Performance optimization
- [Extending](./guides/extending.md) - How to add new providers

### 📖 [API Reference](./api-reference/)
Complete API documentation.

- [DataAPI](./api-reference/data-api.md) - DataAPI reference
- [Providers](./api-reference/providers.md) - Provider reference
- [Models](./api-reference/models.md) - Data models reference
- [Exceptions](./api-reference/exceptions.md) - Exception reference
- [Capabilities](./api-reference/capabilities.md) - Capability API reference

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
- [Transport Layer](./internals/transport-layer.md) - Transport layer details
- [Testing](./internals/testing.md) - Testing guidelines
- [Contributing](./internals/contributing.md) - Contribution guidelines

## Quick Links

- [Main README](../README.md) - Library overview and installation
- [API Documentation](./api.md) - API surface specification
- [Contributing Guide](../CONTRIBUTING.md) - How to contribute

## Documentation Status

**Completed:**
- • Core architecture documentation (13 core files)
- • Architecture overview and ADRs
- • Models layer documentation
- • I/O layer documentation
- • Clients layer documentation
- • Inline architectural comments throughout core modules

**In Progress:**
- 🔄 Usage guides and examples (planned)
- 🔄 API reference documentation (planned)
- 🔄 Provider-specific documentation (planned)

See [DOCUMENTATION_PLAN.md](../DOCUMENTATION_PLAN.md) for the full implementation plan.

---

**Last Updated:** 2025-11-19

