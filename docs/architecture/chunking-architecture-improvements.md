# Chunking Architecture Improvements

This document captures practical, high-impact improvements for the current chunking architecture used by `fetch_ohlcv` and `iterate_ohlcv`.

## Current Strengths

- Shared core chunking runtime (`ChunkPlanner` + `ChunkExecutor`) now powers multiple exchanges.
- `iterate_ohlcv` supports:
  - parallel fetches
  - coalesced yield batching
  - yield-aware concurrency capping
  - optional weight-aware safety capping
- Exchange-specific limits/policies are mostly declarative through endpoint specs.

## Priority Improvements

## 1) Unify Fetch + Iterate Execution Path

### Problem
`fetch_ohlcv` and `iterate_ohlcv` still have duplicated orchestration in connectors.

### Improvement
Make `fetch_ohlcv` a thin wrapper over `iterate_ohlcv`:
- call iterator internally
- aggregate yielded bars
- return a single `OHLCV`

### Benefit
- one authoritative execution path
- fewer behavioral drifts/bugs between fetch and iterate
- simpler connector maintenance

## 2) Router-Native REST Iteration

### Problem
`DataAPI.iterate_ohlcv` currently bypasses router internals directly for provider lookup/symbol resolution.

### Improvement
Add router support for REST async generators, e.g. `route_iter(request)`:
- capability validation
- symbol normalization
- provider/handler dispatch
- async yield forwarding

### Benefit
- keeps `DataAPI` on public router surface only
- removes private coupling to router internals
- cleaner layering

## 3) Create a Reusable `OHLCVChunkService`

### Problem
Many connectors repeat the same setup:
- extract policy/hints/weights
- build plans
- define `fetch_chunk`
- run executor
- reconstruct `OHLCV`

### Improvement
Introduce a core service (e.g. `runtime/chunking/ohlcv_service.py`) that does all of this.
Connectors only provide:
- endpoint spec lookup
- param mapping function for chunk plans

### Benefit
- massively reduces connector duplication
- easier to roll out new chunking features globally
- consistent semantics across exchanges

## 4) Dynamic Rate-Limit Governor

### Problem
Current weight capping is static/assumed (budget + latency estimate).

### Improvement
Implement provider-level token bucket governor:
- consume by request weight
- replenish over time
- adjust via headers/429 feedback when available

### Benefit
- better throughput without blind over-throttling
- safer against burst 429s
- adapts to real exchange behavior

## 5) Built-in Retry Strategy in Executor

### Problem
Chunk retry behavior is not centralized.

### Improvement
Add executor-level retry policy for retryable failures:
- retry classes: timeout, 429, 5xx
- exponential backoff + jitter
- max attempts per chunk

### Benefit
- resilient ingestion
- standardized failure handling
- fewer partial runs due to transient exchange issues

## 6) Two-Stage Execution Pipeline

### Problem
Current execution batches and yields in one flow; can be improved for backpressure and throughput.

### Improvement
Split into:
- Stage A: fetch workers
- Stage B: ordered merge + dedupe + yield batcher

### Benefit
- better overlap of network + batching
- improved cancellation behavior
- clearer control over memory/backpressure

## 7) Stronger Endpoint Chunk Contract

### Problem
Some connector assumptions remain implicit (ordering, cursor semantics, window semantics).

### Improvement
Extend endpoint spec metadata with explicit capabilities:
- supports_time_windows
- stable_ordering
- cursor_mode/time_mode
- hard_max_points

### Benefit
- less implicit connector knowledge
- safer generic executor logic
- easier validation and debugging

## 8) Better Telemetry and Tuning Signals

### Problem
Tuning decisions (`fetch_concurrency`, `yield_chunk_size`) are mostly manual.

### Improvement
Emit structured metrics:
- planned chunks
- effective concurrency (requested vs capped)
- weight consumed
- retries/429 count
- bars/sec
- yield batch sizes

### Benefit
- objective tuning and regression detection
- easier production observability

## Suggested Implementation Order

1. Unify fetch + iterate path (#1)  
2. Add reusable `OHLCVChunkService` (#3)  
3. Add router-native REST iteration (#2)  
4. Add retries + dynamic governor (#5 + #4)  
5. Add richer contracts + telemetry (#7 + #8)

This sequence gives the best ratio of immediate simplification to performance and reliability gains.
