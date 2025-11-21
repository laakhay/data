# API Surface Summary

This page summarizes the public surface area of the `laakhay-data` package and
links to the detailed references for each layer.

## High-Level Facade

- **`laakhay.data.api.DataAPI`** – Primary entry point for most users. Handles
  capability validation, URM normalization, provider routing, and exposes
  `fetch_*` / `stream_*` methods. See
  [DataAPI reference](./api-reference/data-api.md).

## Capability & Symbol Utilities

- **Capability helpers** in `laakhay.data.capability`:
  - `supports(...)`, `is_exchange_supported(...)`, `get_exchange_capability(...)`.
  - Use these to tailor UX or pre-flight validation. See
    [Capability reference](./api-reference/capabilities.md).
- **URM utilities** in `laakhay.data.core.urm`:
  - `get_urm_registry()`, `UniversalRepresentationMapper` protocol.
  - Convert between exchange-native symbols and canonical specs. See
    [URM guide](./guides/urm.md).

## Providers

- Each exchange exports a provider class (e.g., `BinanceProvider`). Direct
  provider usage remains supported for advanced workflows (custom transports,
  experimental endpoints). See [Provider system](./architecture/provider-system.md).

## Clients & Sinks

- **Streaming feeds** under `laakhay.data.clients` provide batteries-included
  streaming with caching/subscriptions. See [Clients layer](./architecture/clients.md)
  and [Feed examples](./examples/feeds.md).
- **Sinks** under `laakhay.data.sinks` forward events to in-memory queues or
  Redis Streams. See [Sinks architecture](./architecture/sinks.md).

## Data Models & Exceptions

- Typed Pydantic models live in `laakhay.data.models`. Reference:
  [Models](./api-reference/models.md).
- Unified exception hierarchy (CapabilityError, ProviderError, etc.). Reference:
  [Exceptions](./api-reference/exceptions.md).

## Developer-Facing Modules

- **Provider registry & router**: `laakhay.data.runtime.provider_registry`,
  `laakhay.data.runtime.router`.
- **Testing helpers** documented in [Internals → Testing](./internals/testing.md).
- **Provider development** guide: [Internals → Provider Development](./internals/provider-development.md).

Use this page as the launching point when exploring the package structure or
reading code alongside the docs.
