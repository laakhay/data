# Routing System

## Purpose

The routing layer coordinates every request flowing through `DataAPI`. It is
responsible for validating capabilities, resolving symbols, locating provider
instances, and invoking the correct feature handlers.

## Components

- **`DataRequest`** (`core/request.py`): immutable object capturing feature,
  transport, exchange, market/instrument types, symbol, timeframe, and other
  parameters.
- **`CapabilityService`** (`capability/service.py`): validates that a
  request is supported before any network call is made.
- **`URMRegistry`** (`core/urm.py`): converts symbols to/from canonical
  representations.
- **`ProviderRegistry`** (`runtime/provider_registry.py`): manages provider instances and
  feature-handler mappings.
- **`DataRouter`** (`runtime/router.py`): orchestrates the end-to-end flow.

## Request Flow

```
DataAPI → DataRouter.route()
    → CapabilityService.validate_request()
    → URMRegistry.urm_to_exchange_symbol()
    → ProviderRegistry.get_provider()
    → ProviderRegistry.get_feature_handler()
    → Provider method invocation
```

Streaming requests follow the same steps but delegate to `route_stream()`.

## Error Handling

- `CapabilityError` for unsupported combinations.
- `SymbolResolutionError` when URM cannot resolve a symbol.
- `ProviderError` for provider/transport issues.

Understanding this layer helps when debugging routing issues or extending the
system with new features.
