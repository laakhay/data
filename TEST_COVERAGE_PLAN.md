# Test Coverage Improvement Plan

**Current Coverage**: 53%  
**Target Coverage**: >90%  
**Branch**: `test/sn/improve-coverage`

## Executive Summary

This plan focuses on adding **impactful, sharp, and precise** unit tests to improve coverage from 53% to >90%. We prioritize:
1. **Core infrastructure** (API, Router, Request handling)
2. **IO layer** (REST/WebSocket transport)
3. **Client feeds** (OHLCV, liquidation, open interest)
4. **Provider adapters** (data transformation logic)

## Coverage Analysis

### Critical Gaps (< 50% coverage)

| Module | Current | Missing | Priority | Impact |
|--------|---------|---------|----------|--------|
| `core/api.py` | 25% | 98/130 | **P0** | 🔴 Critical - Main user-facing API |
| `io/rest/http.py` | 20% | 87/109 | **P0** | 🔴 Critical - HTTP transport layer |
| `io/ws/runner.py` | 23% | 73/95 | **P0** | 🔴 Critical - WebSocket execution |
| `core/request.py` | 40% | 85/141 | **P1** | 🟠 High - Request building/validation |
| `io/ws/client.py` | 45% | 58/106 | **P1** | 🟠 High - WebSocket client |
| `io/ws/transport.py` | 46% | 29/54 | **P1** | 🟠 High - WebSocket transport |

### Medium Priority (50-80% coverage)

| Module | Current | Missing | Priority | Impact |
|--------|---------|---------|----------|--------|
| `clients/ohlcv_feed.py` | 54% | 138/302 | **P1** | 🟠 High - Complex feed logic |
| `core/capability_service.py` | 63% | 7/19 | **P2** | 🟡 Medium - Capability validation |
| `clients/base_feed.py` | 80% | 37/184 | **P2** | 🟡 Medium - Base feed functionality |
| `clients/open_interest_feed.py` | 77% | 11/47 | **P2** | 🟡 Medium - OI feed |

### Well Covered (> 80% coverage)

- Models (most are >85%)
- Enums, Exceptions (100%)
- Registry (95%)
- URM (88%)
- Router (84%)

---

## Phase 1: Core Infrastructure (Target: 85%+ coverage)

### 1.1 DataAPI (`core/api.py`) - 25% → 85%

**Current**: Only basic initialization tested  
**Missing**: All fetch_* and stream_* methods

**Test Strategy**:
- ✅ Mock DataRouter to isolate API layer
- ✅ Test all `fetch_*` methods (ohlcv, order_book, trades, symbols, etc.)
- ✅ Test all `stream_*` methods (ohlcv, trades, liquidations, etc.)
- ✅ Test parameter resolution (defaults, overrides)
- ✅ Test error handling and propagation
- ✅ Test context manager (async enter/exit)

**Test File**: `tests/unit/core/test_api.py` (NEW)

**Key Test Cases**:
```python
# Parameter resolution
- test_default_exchange_resolution
- test_default_market_type_resolution
- test_parameter_override

# REST methods
- test_fetch_ohlcv_success
- test_fetch_ohlcv_with_pagination
- test_fetch_order_book
- test_fetch_recent_trades
- test_fetch_symbols
- test_fetch_open_interest
- test_fetch_funding_rates
- test_fetch_mark_price

# WebSocket methods
- test_stream_ohlcv
- test_stream_ohlcv_multi
- test_stream_trades
- test_stream_trades_multi
- test_stream_order_book
- test_stream_liquidations
- test_stream_open_interest
- test_stream_funding_rates
- test_stream_mark_price

# Error handling
- test_capability_error_propagation
- test_symbol_resolution_error
- test_provider_error_handling
- test_invalid_parameters
```

**Estimated Coverage Gain**: +60% (75 statements)

---

### 1.2 DataRequest (`core/request.py`) - 40% → 85%

**Current**: Basic structure tested  
**Missing**: Builder methods, validation, serialization

**Test Strategy**:
- ✅ Test all builder methods (for_ohlcv, for_trades, etc.)
- ✅ Test parameter validation
- ✅ Test request serialization/deserialization
- ✅ Test constraint enforcement

**Test File**: `tests/unit/core/test_request.py` (NEW)

**Key Test Cases**:
```python
# Builder methods
- test_for_ohlcv_builder
- test_for_order_book_builder
- test_for_trades_builder
- test_for_liquidations_builder
- test_for_open_interest_builder
- test_for_funding_rates_builder

# Validation
- test_required_parameters
- test_invalid_timeframe
- test_invalid_depth
- test_invalid_limit

# Serialization
- test_to_dict
- test_from_dict
- test_json_serialization
```

**Estimated Coverage Gain**: +45% (64 statements)

---

### 1.3 CapabilityService (`core/capability_service.py`) - 63% → 90%

**Current**: Basic validation tested  
**Missing**: Error message generation, recommendations

**Test File**: `tests/unit/core/test_capability_service.py` (NEW)

**Key Test Cases**:
```python
- test_validate_request_success
- test_validate_request_unsupported_feature
- test_validate_request_unsupported_transport
- test_validate_request_unsupported_market_type
- test_error_message_generation
- test_fallback_recommendations
```

**Estimated Coverage Gain**: +27% (5 statements)

---

## Phase 2: IO Layer (Target: 80%+ coverage)

### 2.1 REST HTTP (`io/rest/http.py`) - 20% → 80%

**Current**: Minimal coverage  
**Missing**: Request building, response handling, error handling, retries

**Test Strategy**:
- ✅ Mock aiohttp client
- ✅ Test GET/POST request building
- ✅ Test response parsing
- ✅ Test error handling (4xx, 5xx)
- ✅ Test rate limit handling
- ✅ Test retry logic
- ✅ Test timeout handling

**Test File**: `tests/unit/infrastructure/test_http.py` (ENHANCE)

**Key Test Cases**:
```python
# Request building
- test_build_get_request
- test_build_post_request
- test_build_request_with_params
- test_build_request_with_headers
- test_build_request_with_auth

# Response handling
- test_parse_json_response
- test_parse_text_response
- test_handle_empty_response

# Error handling
- test_handle_400_error
- test_handle_401_error
- test_handle_403_error
- test_handle_404_error
- test_handle_429_rate_limit
- test_handle_500_error
- test_handle_network_timeout
- test_handle_connection_error

# Retry logic
- test_retry_on_transient_error
- test_retry_exhausted
- test_retry_backoff
```

**Estimated Coverage Gain**: +60% (65 statements)

---

### 2.2 WebSocket Client (`io/ws/client.py`) - 45% → 80%

**Current**: Basic connection tested  
**Missing**: Message handling, reconnection, error recovery

**Test Strategy**:
- ✅ Mock websockets library
- ✅ Test connection establishment
- ✅ Test message sending/receiving
- ✅ Test reconnection logic
- ✅ Test error recovery
- ✅ Test ping/pong handling

**Test File**: `tests/unit/infrastructure/test_websocket.py` (ENHANCE)

**Key Test Cases**:
```python
# Connection
- test_connect_success
- test_connect_failure
- test_connect_timeout
- test_disconnect

# Message handling
- test_send_message
- test_receive_message
- test_receive_binary_message
- test_message_queue

# Reconnection
- test_auto_reconnect_on_disconnect
- test_reconnect_backoff
- test_max_reconnect_attempts
- test_reconnect_success

# Error handling
- test_handle_connection_error
- test_handle_protocol_error
- test_handle_timeout
```

**Estimated Coverage Gain**: +35% (37 statements)

---

### 2.3 WebSocket Runner (`io/ws/runner.py`) - 23% → 80%

**Current**: Minimal coverage  
**Missing**: Stream execution, message processing, error handling

**Test Strategy**:
- ✅ Mock WebSocket client
- ✅ Test stream execution
- ✅ Test message processing pipeline
- ✅ Test error handling and recovery

**Test File**: `tests/unit/infrastructure/test_ws_runner.py` (NEW)

**Key Test Cases**:
```python
- test_run_stream_success
- test_run_stream_with_message_adapter
- test_run_stream_error_handling
- test_run_stream_reconnection
- test_message_processing_pipeline
- test_stream_cleanup
```

**Estimated Coverage Gain**: +57% (54 statements)

---

### 2.4 WebSocket Transport (`io/ws/transport.py`) - 46% → 80%

**Test File**: `tests/unit/infrastructure/test_ws_transport.py` (NEW)

**Key Test Cases**:
```python
- test_transport_initialization
- test_connect
- test_send
- test_receive
- test_close
- test_error_handling
```

**Estimated Coverage Gain**: +34% (18 statements)

---

## Phase 3: Client Feeds (Target: 85%+ coverage)

### 3.1 OHLCV Feed (`clients/ohlcv_feed.py`) - 54% → 85%

**Current**: Basic functionality tested  
**Missing**: Complex buffering, windowing, event handling

**Test Strategy**:
- ✅ Mock provider
- ✅ Test bar buffering logic
- ✅ Test windowing (rolling windows)
- ✅ Test event generation (BAR, CONNECTION)
- ✅ Test multi-symbol handling
- ✅ Test error recovery

**Test File**: `tests/unit/feeds/test_ohlcv_feed.py` (ENHANCE)

**Key Test Cases**:
```python
# Buffering
- test_buffer_incoming_bars
- test_buffer_overflow_handling
- test_buffer_cleanup

# Windowing
- test_rolling_window_calculation
- test_window_size_validation
- test_window_sliding

# Events
- test_bar_event_generation
- test_connection_event_generation
- test_error_event_generation

# Multi-symbol
- test_multi_symbol_streaming
- test_symbol_specific_buffering
- test_symbol_error_isolation

# Error handling
- test_provider_error_recovery
- test_connection_loss_recovery
- test_data_validation_errors
```

**Estimated Coverage Gain**: +31% (94 statements)

---

### 3.2 Base Feed (`clients/base_feed.py`) - 80% → 90%

**Test File**: `tests/unit/feeds/test_base_feed.py` (NEW)

**Key Test Cases**:
```python
- test_feed_initialization
- test_feed_start
- test_feed_stop
- test_feed_cleanup
- test_event_callback_handling
- test_error_callback_handling
```

**Estimated Coverage Gain**: +10% (18 statements)

---

### 3.3 Open Interest Feed (`clients/open_interest_feed.py`) - 77% → 90%

**Test File**: `tests/unit/feeds/test_open_interest_feed.py` (ENHANCE)

**Key Test Cases**:
```python
- test_oi_feed_initialization
- test_oi_streaming
- test_oi_event_generation
- test_multi_symbol_oi
- test_error_handling
```

**Estimated Coverage Gain**: +13% (6 statements)

---

## Phase 4: Provider Adapters (Target: 85%+ coverage)

### 4.1 REST Adapters (All Providers)

**Focus**: Data transformation logic

**Test Strategy**:
- ✅ Test response → model conversion
- ✅ Test error response handling
- ✅ Test edge cases (empty data, malformed data)

**Test Files**:
- `tests/unit/providers/binance/test_rest_adapters.py` (NEW)
- `tests/unit/providers/bybit/test_rest_adapters.py` (NEW)
- `tests/unit/providers/okx/test_rest_adapters.py` (NEW)
- Similar for other providers

**Key Test Cases** (per provider):
```python
# OHLCV adapter
- test_ohlcv_adapter_success
- test_ohlcv_adapter_empty_response
- test_ohlcv_adapter_malformed_data

# Order book adapter
- test_order_book_adapter_success
- test_order_book_adapter_empty_book

# Trade adapter
- test_trade_adapter_success
- test_trade_adapter_side_detection

# Symbol adapter
- test_symbol_adapter_success
- test_symbol_adapter_filtering
```

**Estimated Coverage Gain**: +15% (across all providers)

---

### 4.2 WebSocket Adapters (All Providers)

**Test Strategy**: Similar to REST adapters

**Test Files**:
- `tests/unit/providers/binance/test_ws_adapters.py` (NEW)
- Similar for other providers

**Key Test Cases**:
```python
- test_message_parsing
- test_subscription_message
- test_data_message_parsing
- test_error_message_handling
- test_heartbeat_handling
```

**Estimated Coverage Gain**: +10% (across all providers)

---

## Phase 5: Edge Cases & Error Paths

### 5.1 Error Handling

**Focus**: Ensure all error paths are tested

- Invalid parameters
- Network failures
- Malformed responses
- Rate limiting
- Timeout handling
- Connection failures

### 5.2 Boundary Conditions

- Empty data sets
- Maximum limits
- Minimum values
- Null/None handling
- Type validation

---

## Implementation Strategy

### Week 1: Core Infrastructure
- [ ] DataAPI tests (Phase 1.1)
- [ ] DataRequest tests (Phase 1.2)
- [ ] CapabilityService tests (Phase 1.3)

**Target**: Core coverage → 85%

### Week 2: IO Layer
- [ ] REST HTTP tests (Phase 2.1)
- [ ] WebSocket client tests (Phase 2.2)
- [ ] WebSocket runner tests (Phase 2.3)
- [ ] WebSocket transport tests (Phase 2.4)

**Target**: IO coverage → 80%

### Week 3: Client Feeds
- [ ] OHLCV feed tests (Phase 3.1)
- [ ] Base feed tests (Phase 3.2)
- [ ] Open interest feed tests (Phase 3.3)

**Target**: Feed coverage → 85%

### Week 4: Provider Adapters & Polish
- [ ] REST adapter tests (Phase 4.1)
- [ ] WebSocket adapter tests (Phase 4.2)
- [ ] Edge cases & error paths (Phase 5)
- [ ] Coverage verification

**Target**: Overall coverage → 90%+

---

## Testing Best Practices

### 1. Use Mocks Strategically
- Mock external dependencies (aiohttp, websockets)
- Mock provider responses
- Keep mocks focused and realistic

### 2. Test Structure
```python
class TestDataAPIFetchOHLCV:
    """Test DataAPI.fetch_ohlcv method."""
    
    @pytest.fixture
    def mock_router(self):
        """Mock DataRouter."""
        ...
    
    async def test_fetch_ohlcv_success(self, mock_router):
        """Test successful OHLCV fetch."""
        ...
    
    async def test_fetch_ohlcv_invalid_symbol(self, mock_router):
        """Test OHLCV fetch with invalid symbol."""
        ...
```

### 3. Coverage Goals
- **Statements**: >90%
- **Branches**: >85%
- **Functions**: >90%
- **Lines**: >90%

### 4. Test Quality
- ✅ One assertion per test (when possible)
- ✅ Clear test names describing behavior
- ✅ Test both success and failure paths
- ✅ Test edge cases and boundaries
- ✅ Use fixtures for common setup

---

## Metrics & Tracking

### Coverage Targets by Module

| Module Category | Current | Target | Priority |
|----------------|---------|--------|----------|
| Core (api, router, request) | 25-84% | 85%+ | P0 |
| IO Layer (rest, ws) | 20-46% | 80%+ | P0 |
| Client Feeds | 54-80% | 85%+ | P1 |
| Provider Adapters | ~60% | 85%+ | P2 |
| Models | 84-100% | 90%+ | P3 |

### Success Criteria

- ✅ Overall coverage >90%
- ✅ All P0 modules >80%
- ✅ All P1 modules >85%
- ✅ No critical paths untested
- ✅ All error paths covered

---

## Tools & Commands

### Run Coverage Report
```bash
cd data/
pytest --cov=laakhay.data --cov-report=term-missing --cov-report=html
```

### Run Specific Test Suite
```bash
# Core tests
pytest tests/unit/core/ -v

# IO tests
pytest tests/unit/infrastructure/ -v

# Feed tests
pytest tests/unit/feeds/ -v
```

### Generate HTML Report
```bash
pytest --cov=laakhay.data --cov-report=html
open htmlcov/index.html
```

---

## Notes

- Focus on **unit tests** only (no network calls)
- Use mocks for all external dependencies
- Keep tests fast (< 1 second per test)
- Ensure tests are deterministic
- Document complex test scenarios

---

**Next Steps**: Start with Phase 1.1 (DataAPI tests) as it has the highest impact and lowest current coverage.

