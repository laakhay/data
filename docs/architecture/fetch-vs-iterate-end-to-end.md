# Fetch vs Iterate API: End-to-End Architecture

This document explains the full request path for both `fetch_*` and `iterate_*` APIs in `laakhay-data`, including all key objects/services and where chunking, routing, symbol resolution, and provider dispatch happen.

## 1. Main Building Blocks

### API Layer
- `DataAPI`
  - User-facing facade (`fetch_ohlcv`, `iterate_ohlcv`, `stream_*`, etc.).
  - Resolves defaults via `APIRequestBuilder`.
  - File: `data/laakhay/data/api/data_api.py`

- `APIRequestBuilder`
  - Fluent request builder used by `DataAPI`.
  - Applies defaults and constructs immutable `DataRequest`.
  - File: `data/laakhay/data/api/request_builder.py`

### Request Model
- `DataRequest`
  - Immutable request object with feature/transport/exchange/market/symbol/timeframe/limits/etc.
  - Validated in `__post_init__`.
  - File: `data/laakhay/data/core/request.py`

### Runtime Orchestration
- `DataRouter`
  - Central orchestration for REST and WS routing.
  - Steps: capability check -> symbol resolution -> provider lookup -> feature handler dispatch -> invocation.
  - File: `data/laakhay/data/runtime/router.py`

- `CapabilityService`
  - Validates whether requested feature/transport is supported for exchange + market + instrument.
  - File: `data/laakhay/data/capability/service.py`

- `ProviderRegistry`
  - Registers provider classes.
  - Pools provider instances by `(exchange, market_type, market_variant)`.
  - Stores feature handler mapping from decorators.
  - Stores URM mappers for symbol normalization.
  - File: `data/laakhay/data/runtime/provider_registry.py`

- `registration.py`
  - Registers all exchange providers + URM mappers into the global registry.
  - File: `data/laakhay/data/registration.py`

### Exchange Provider Stack
- Unified provider (example: `BinanceProvider`)
  - Exposes feature methods and delegates to REST/WS connectors.
  - Decorators register handler metadata for router dispatch.
  - File: `data/laakhay/data/connectors/binance/provider.py`

- REST connector (example: `BinanceRESTConnector`)
  - Implements HTTP-facing logic.
  - Knows endpoint specs and adapter parsing.
  - File: `data/laakhay/data/connectors/binance/rest/provider.py`

- Endpoint spec + adapter (example: Binance OHLCV)
  - Defines path/query schema + chunk metadata + weight metadata.
  - Parses raw exchange payload into domain model (`OHLCV`, `Bar`).
  - File: `data/laakhay/data/connectors/binance/rest/endpoints/common/ohlcv.py`

- `RestRunner` + `RESTTransport`
  - Executes HTTP from `RestEndpointSpec`.
  - File: `data/laakhay/data/runtime/rest/runner.py`

### Chunking Runtime
- `ChunkPolicy`, `ChunkHint`, `WeightPolicy`, `ChunkPlan`, `ChunkResult`
  - Metadata and plan/result models.
  - File: `data/laakhay/data/runtime/chunking/definitions.py`

- `ChunkPlanner`
  - Splits request into chunk plans using timeframe/time windows/limits.
  - File: `data/laakhay/data/runtime/chunking/planners.py`

- `ChunkExecutor`
  - Fetches chunk plans (now with bounded parallelism), dedupes, buffers, and yields.
  - Supports:
    - `max_concurrency`
    - exchange budget-aware cap (via weight policy + budget)
    - yield-size-aware cap (`yield_points`)
    - coalesced yields
  - File: `data/laakhay/data/runtime/chunking/executors.py`

## 2. `fetch_ohlcv` Path (REST, non-generator return)

1. Caller invokes `DataAPI.fetch_ohlcv(...)`.
2. `DataAPI` builds a `DataRequest`.
3. `DataRouter.route(request)` runs:
   - capability validation (`CapabilityService`)
   - URM symbol normalization (via registry mapper)
   - provider acquisition from pooled `ProviderRegistry`
   - feature handler lookup for `(DataFeature.OHLCV, TransportKind.REST)`
   - method invocation on provider
4. Provider delegates to exchange REST connector (`BinanceRESTConnector.fetch_ohlcv`).
5. Connector:
   - reads endpoint spec for chunk policy/hints
   - executes single request when small
   - executes chunked fetch path when needed
6. HTTP is executed through `RestRunner` + adapter parsing to domain models.
7. Returns a single `OHLCV`.

## 3. `iterate_ohlcv` Path (REST async generator)

1. Caller invokes `DataAPI.iterate_ohlcv(...)`.
2. `DataAPI` builds request similarly to fetch path.
3. Current design note:
   - `iterate_ohlcv` currently bypasses `DataRouter.route()` (because `route()` expects awaited result, not REST async generator).
   - It still uses router internals for:
     - provider lookup (`_provider_registry.get_provider(...)`)
     - symbol normalization (`_resolve_symbols(...)`)
4. Provider `iterate_ohlcv` delegates to REST connector iterator.
5. Connector iterator:
   - reads endpoint `ChunkPolicy`, `ChunkHint`, `WeightPolicy`
   - builds plans via `ChunkPlanner`
   - executes plans via `ChunkExecutor.iterate(...)`
6. `ChunkExecutor` behavior:
   - fetches chunks with bounded parallelism
   - preserves plan order in yielded data
   - deduplicates by timestamp
   - coalesces multiple network chunks before yielding to app (`yield_points`)
7. Yields chunked `OHLCV` batches (application chunking, not necessarily one HTTP page per yield).

## 4. Important Separation of Concerns

- **Network fetch size**
  - Controlled by endpoint max and per-chunk plan limits (e.g., Binance OHLCV max 1000).
- **Application yield size**
  - Controlled by `yield_chunk_size` (`yield_points` in executor).
  - Lets ingestion write larger DB batches without changing HTTP page size.
- **Parallelism**
  - Controlled by `fetch_concurrency`, then capped by:
    - yield demand (`ceil(yield_points / per_request_points)`)
    - weight safety cap (from endpoint `WeightPolicy` + exchange budget)

## 5. Current Exchange Coverage Note

- Binance path now has explicit `iterate_ohlcv` wiring through provider + REST connector + chunk executor.
- Bybit provider currently exposes `fetch_ohlcv` but does not yet expose `iterate_ohlcv` in the same manner.

## 6. Quick Mental Model

- `fetch_*` = "give me one assembled result object"
- `iterate_*` = "stream history in controllable batches"

Both rely on the same underlying stack (request model, capability checks, provider registry, endpoint specs), with `iterate_*` adding chunk planning/execution as a first-class runtime path.
