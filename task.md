## PR4: Introduce Connectors Namespace & Migrate Binance

### Goal
Prove the connector structure (`connectors/<exchange>/rest|ws|urm`) with Binance as the most complex exchange, following the ideal architecture.

### Architecture Overview
Based on `docs/laakhay-data-ideal-architecture.md`:
- **Connector Plane**: Exchange-specific REST/WS implementations, endpoint metadata, adapters, URM mappers
- **Structure**: `connectors/binance/rest/endpoints/<scope>/<endpoint>.py` - one module per endpoint (spec + adapter)
- **Provider shims**: `providers/binance/` wraps connectors for DataRouter consumption

### Tasks

#### Phase 1: Scaffold Connectors Structure
- [x] **connectors/binance: create package structure**
  - Create `laakhay/data/connectors/__init__.py`
  - Create `laakhay/data/connectors/binance/__init__.py`
  - Create `laakhay/data/connectors/binance/rest/__init__.py`
  - Create `laakhay/data/connectors/binance/rest/endpoints/__init__.py`
  - Create `laakhay/data/connectors/binance/rest/endpoints/common/__init__.py`
  - Create `laakhay/data/connectors/binance/rest/endpoints/spot/__init__.py`
  - Create `laakhay/data/connectors/binance/rest/endpoints/futures/__init__.py`
  - Create `laakhay/data/connectors/binance/ws/__init__.py`
  - Create `laakhay/data/connectors/binance/ws/endpoints/__init__.py`

#### Phase 2: Move URM and Constants
- [x] **connectors/binance: move URM mapper**
  - Move `providers/binance/urm.py` → `connectors/binance/urm.py`
  - Update imports in provider registration
  - Keep temporary import in `providers/binance/urm.py` for backward compatibility

- [x] **connectors/binance: move constants**
  - Move `providers/binance/constants.py` → `connectors/binance/config.py` (rename per architecture)
  - Update all imports

#### Phase 3: Port REST Endpoints to Modular Structure
- [x] **connectors/binance/rest/endpoints: port OHLCV endpoint**
  - Create `connectors/binance/rest/endpoints/common/ohlcv.py`
  - Move `candles_spec()` logic into module, export as `SPEC: RestEndpointSpec`
  - Move `CandlesResponseAdapter` from `providers/binance/rest/adapters.py`
  - Export `SPEC` and `Adapter` class

- [x] **connectors/binance/rest/endpoints: port exchange_info endpoint**
  - Create `connectors/binance/rest/endpoints/common/exchange_info.py`
  - Move `exchange_info_spec()` logic, export as `SPEC: RestEndpointSpec`
  - Move `ExchangeInfoSymbolsAdapter` from adapters.py

- [x] **connectors/binance/rest/endpoints: port remaining endpoints**
  - Port all endpoints from `providers/binance/rest/endpoints.py` to individual modules:
    - `order_book_spec()` → `spot/order_book.py` or `futures/order_book.py`
    - `open_interest_current_spec()` → `futures/open_interest_current.py`
    - `open_interest_hist_spec()` → `futures/open_interest_hist.py`
    - `recent_trades_spec()` → `common/trades.py`
    - `historical_trades_spec()` → `spot/historical_trades.py`
    - `funding_rate_spec()` → `futures/funding_rate.py`
  - Organize by scope: `common/`, `spot/`, `futures/`
  - Each module exports `SPEC: RestEndpointSpec` and `Adapter: ResponseAdapter`

- [x] **connectors/binance/rest: create endpoint registry**
  - Create `connectors/binance/rest/endpoints/__init__.py` that discovers and exports all endpoints
  - Implement `get_endpoint_spec(id: str) -> RestEndpointSpec | None`
  - Implement `get_endpoint_adapter(id: str) -> ResponseAdapter | None`
  - Export all endpoint specs and adapters for discovery

#### Phase 4: Create REST Connector Provider
- [x] **connectors/binance/rest: create provider.py**
  - Create `BinanceRESTConnector` class that composes endpoint registry
  - Implement methods that use endpoint definitions and adapters
  - Support direct use by researchers (no capability validation)
  - Register feature handlers via decorators

#### Phase 5: Port WebSocket Endpoints
- [x] **connectors/binance/ws/endpoints: port WS endpoint specs**
  - Move WS endpoint specs from `providers/binance/ws/endpoints.py`
  - Create individual modules per WS stream type
  - Each module exports `WSEndpointSpec` (or equivalent)

- [x] **connectors/binance/ws: create provider.py**
  - Create `BinanceWSConnector` class
  - Implement streaming methods using endpoint specs
  - Support direct use by researchers

#### Phase 6: Create Unified Provider
- [x] **connectors/binance: create provider.py**
  - Create unified `BinanceProvider` that composes REST + WS connectors
  - This is the provider used by DataRouter
  - Register all feature handlers

#### Phase 7: Convert Providers to Shims
- [x] **providers/binance: convert to shims**
  - Update `providers/binance/provider.py` to instantiate connectors
  - Keep same public interface for backward compatibility
  - Update `providers/binance/__init__.py` exports

- [ ] **providers/binance: update registration**
  - Update `register_binance()` to use connector-based provider
  - Ensure URM mapper imports from connectors

#### Phase 8: Update Discovery
- [x] **capability/discovery: update for connectors**
  - Update discovery to look in `connectors/<exchange>/rest/endpoints/`
  - Update discovery to look in `connectors/<exchange>/ws/endpoints/`
  - Ensure discovery finds all endpoint definitions

#### Phase 9: Tests and Cleanup
- [ ] **tests: update Binance tests**
  - Move/adapt Binance-specific unit tests to connector modules
  - Update test imports to use connector paths
  - Ensure all tests pass

- [ ] **cleanup: remove old endpoint files**
  - Delete `providers/binance/rest/endpoints.py` (replaced by modular structure)
  - Remove temporary shims once everything works
  - Update any remaining imports

#### Phase 10: Documentation
- [ ] **docs: update Binance documentation**
  - Document new connector structure
  - Update examples to show connector usage
  - Add notes about migration path

### Notes
- Keep backward compatibility during migration (temporary imports/shim files)
- Follow the ideal architecture structure exactly
- Each endpoint module should be self-contained (DEFINITION + Adapter)
- Connectors should be usable directly by researchers (no router required)
- Providers become thin shims that wrap connectors for DataRouter

