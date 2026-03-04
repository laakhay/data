# OHLCV Chunking Core Rollout (#1, #2, #3)

This documents the completed rollout for:

1. Unified fetch + iterate execution path
2. Router-native REST iteration
3. Reusable core OHLCV chunk service

## What Changed

## 1) Unified `fetch_ohlcv` + `iterate_ohlcv`

All REST connectors now use a single core orchestration path via `OHLCVChunkService`.

- `fetch_ohlcv(...)` now aggregates from iterator execution (`service.fetch(...)` wraps `service.iterate(...)`)
- `iterate_ohlcv(...)` uses the same planning/execution core and yields chunked `OHLCV`
- Connector-specific duplicate chunk loops were removed from:
  - Binance
  - Bybit
  - Coinbase
  - Kraken
  - MEXC
  - OKX
  - Hyperliquid

## 2) Router-Native REST Iteration

`DataRouter` now exposes:

- `route_iter(request: DataRequest) -> AsyncIterator[Any]`

Behavior:

- validates capability
- resolves symbols via URM
- resolves provider
- resolves iterator handler name (`iterate_...`) from feature/handler metadata
- forwards async yields

`DataAPI.iterate_ohlcv(...)` now routes through `self._router.route_iter(request)`.
It no longer reaches into router private internals.

## 3) Reusable Core Service

Added:

- `laakhay/data/runtime/chunking/ohlcv_service.py`
- exported as `OHLCVChunkService` from `runtime/chunking/__init__.py`

Service responsibilities:

- extract chunking metadata from endpoint specs (`chunk_policy`, `chunk_hint`, `weight_policy`)
- decide single-fetch vs chunked execution
- plan chunk windows (`ChunkPlanner`)
- execute chunk fetches (`ChunkExecutor`)
- support parallel fetch (`fetch_concurrency`) and coalesced yields (`yield_chunk_size`)
- aggregate iterator results for fetch API

## End-to-End Objects and Services

Request path for REST OHLCV:

1. `DataAPI.fetch_ohlcv(...)` / `DataAPI.iterate_ohlcv(...)`
2. build `DataRequest` (`extra_params` carries `fetch_concurrency` / `yield_chunk_size` for iterate)
3. `DataRouter.route(...)` or `DataRouter.route_iter(...)`
4. capability check (`CapabilityService`)
5. symbol normalization (`URM` mapper)
6. provider resolution (`ProviderRegistry`)
7. connector `fetch_ohlcv` / `iterate_ohlcv`
8. connector delegates to `OHLCVChunkService`
9. service uses endpoint chunk metadata + `ChunkPlanner` + `ChunkExecutor`
10. yields chunked `OHLCV` or returns aggregated `OHLCV`

## Notes on Weight and Concurrency

- Weight policy is extracted from endpoint spec automatically.
- Exchange-level weight budget is auto-resolved in core service from exchange defaults
  (Binance/Bybit/Coinbase/Kraken/MEXC/OKX/Hyperliquid).
- `ChunkExecutor` still supports optional weight-aware concurrency capping.
- `fetch_ohlcv` keeps `yield_points=None`, so fetch path is not yield-capped.
- For limit-only requests without explicit time bounds, backward backfill is enabled for Binance
  in core service to preserve multi-page latest-bar fetching semantics.

## Validation

Validated with:

- `ruff check` on all touched files
- provider/core/chunking unit tests
- result: `294 passed, 1 xfailed, 1 xpassed`
