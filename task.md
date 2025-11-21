# Coinbase Connector Migration

## Goal
Migrate Coinbase provider to the connector structure, following Binance's pattern.

## Tasks

### Phase 1: Scaffold Connector Structure
- [ ] Create `connectors/coinbase/` directory structure
- [ ] Create `__init__.py` files for all packages
- [ ] Move/create `config.py` (constants, mappings)
- [ ] Move/create `urm.py` (Unified Resource Mapper)

### Phase 2: Migrate REST Endpoints
- [ ] Create `connectors/coinbase/rest/endpoints/` structure
- [ ] Break down REST endpoints into individual modules (common/, spot/, futures/)
- [ ] Each endpoint module exports `SPEC` (RestEndpointSpec) and `Adapter` (ResponseAdapter)
- [ ] Create `connectors/coinbase/rest/endpoints/__init__.py` as endpoint registry
- [ ] Create `connectors/coinbase/rest/provider.py` (REST connector)

### Phase 3: Migrate WebSocket Endpoints
- [ ] Create `connectors/coinbase/ws/endpoints/` structure
- [ ] Break down WS endpoints into individual modules
- [ ] Each endpoint module exports `build_spec` function and `Adapter`
- [ ] Create `connectors/coinbase/ws/endpoints/__init__.py` as endpoint registry
- [ ] Create `connectors/coinbase/ws/provider.py` (WS connector)

### Phase 4: Create Unified Provider
- [ ] Create `connectors/coinbase/provider.py` (unified provider)
- [ ] Compose REST and WS connectors
- [ ] Implement BaseProvider interface

### Phase 5: Convert Providers to Shims
- [ ] Update `providers/coinbase/provider.py` to be a shim
- [ ] Update `providers/coinbase/rest/provider.py` to be a shim
- [ ] Update `providers/coinbase/ws/provider.py` to be a shim
- [ ] Update `providers/coinbase/__init__.py` imports

### Phase 6: Cleanup
- [ ] Remove old `providers/coinbase/rest/endpoints.py` (if exists)
- [ ] Remove old `providers/coinbase/rest/adapters.py` (if exists)
- [ ] Remove old `providers/coinbase/ws/endpoints.py` (if exists)
- [ ] Remove old `providers/coinbase/ws/adapters.py` (if exists)
- [ ] Update discovery to check connectors/coinbase paths
- [ ] Update all imports in tests

### Phase 7: Testing & Validation
- [ ] Run `ruff format` and `ruff check`
- [ ] Run `uv run pytest` - ensure all tests pass
- [ ] Verify backward compatibility

