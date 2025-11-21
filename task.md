# Generic Chunking Layer - Task List

## Goal
Extract reusable chunking logic from exchange-specific implementations into a generic `runtime/chunking/` layer that can handle pagination, limit extension, and deduplication for any endpoint based on metadata.

## Architecture Reference
Based on `docs/laakhay-data-ideal-architecture.md` Section 5:
- **Chunk planners** read `EndpointDefinition` metadata (max_points, has_cursor, timestamp_key, weight tiers)
- **Executors** call endpoint runner repeatedly, feeding start/end/cursor parameters
- **Result builders** stitch typed results using adapter output
- **Policies** (strict vs clamp) handle exchanges that reject out-of-range requests

## Current State
- Chunking logic exists in `providers/binance/rest/provider.py` (shim, for backward compatibility)
- Each exchange would need to reimplement similar chunking logic
- No metadata-driven automatic chunking

## Target Structure
```
runtime/chunking/
├── __init__.py
├── definitions.py      # ChunkPolicy, ChunkHint, chunk semantics from EndpointDefinition
├── planners.py         # ChunkPlanner - timeframe-aware window planning
├── executors.py        # ChunkExecutor - generic chunk execution / dedupe
└── telemetry.py        # Structured logs + metrics
```

## Task Breakdown

### Phase 1: Define Chunking Abstractions
- [x] **chunking/definitions.py: create chunk metadata structures**
  - Define `ChunkPolicy` dataclass (max_points, max_chunks, requires_start_time, supports_auto_chunking)
  - Define `ChunkHint` dataclass (cursor_field, timestamp_key, limit_field)
  - Define `ChunkResult` dataclass (aggregated data, chunks_used, weight_consumed, throttle_applied)
  - Helper to extract chunk metadata from `RestEndpointSpec`

### Phase 2: Implement Chunk Planner
- [x] **chunking/planners.py: create ChunkPlanner**
  - `plan()` method: takes user request (limit, start_time, end_time) + chunk policy
  - Determine base page size = min(limit_policy.max_points, user_limit)
  - If time range provided, align windows on timeframe boundaries
  - Respect max_chunks and requires_start_time
  - Return list of chunk plans (start_time, end_time, limit per chunk)

### Phase 3: Implement Chunk Executor
- [ ] **chunking/executors.py: create ChunkExecutor**
  - `execute()` method: takes chunk plans + fetch function + adapter
  - For each chunk: call fetch, parse with adapter, deduplicate
  - Deduplicate using (symbol, timeframe, timestamp) key
  - Drop bars older than last appended
  - Stop early when endpoint returns fewer than requested
  - Track rate-limit weights for telemetry
  - Return aggregated result

### Phase 4: Integrate with Binance Connector
- [ ] **connectors/binance/rest/provider.py: use generic chunking**
  - Remove manual chunking logic from `fetch_ohlcv`
  - Use `ChunkPlanner` and `ChunkExecutor` instead
  - Ensure endpoint specs expose chunk metadata
  - Test that chunking still works correctly

### Phase 5: Add Telemetry
- [ ] **chunking/telemetry.py: structured logging**
  - Log chunk_completed events (chunk_idx, rows_aggregated, weight)
  - Log chunk_plan events (total_chunks, window_size)
  - Provide metrics hooks for observability

### Phase 6: Update Tests
- [ ] **tests: add chunking layer tests**
  - Unit tests for ChunkPlanner (various scenarios)
  - Unit tests for ChunkExecutor (deduplication, early stopping)
  - Integration test with Binance connector
  - Ensure backward compatibility

### Phase 7: Documentation
- [ ] **docs: document chunking layer**
  - Add usage examples
  - Document chunk policies and hints
  - Update architecture docs if needed

## Notes
- Keep backward compatibility during migration
- Chunking should work for any endpoint with proper metadata
- Support both time-based and cursor-based pagination
- Handle edge cases (limit=0, start>end, no data returned)
