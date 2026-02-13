# Testing Guidelines

## Overview

This document covers testing guidelines for the Laakhay Data library.

## Test Structure

```
tests/
├── unit/           # Unit tests (no network)
├── integration/    # Integration tests (live APIs)
└── fixtures/       # Test fixtures and mocks
```

## Unit Tests

Unit tests should not make network calls. Use mocks instead.

### Mocking Providers

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from laakhay.data.api import DataAPI
from laakhay.data.models import OHLCV, SeriesMeta, Bar

@pytest.mark.asyncio
async def test_fetch_ohlcv():
    # Mock router
    mock_router = AsyncMock()
    mock_router.route.return_value = OHLCV(
        meta=SeriesMeta(symbol="BTC/USDT", timeframe="1h"),
        bars=[Bar(...)],
    )
    
    # Create API with mock
    async with DataAPI(router=mock_router) as api:
        ohlcv = await api.fetch_ohlcv("BTCUSDT", "1h", exchange="binance")
        assert len(ohlcv) > 0
```

### Mocking HTTP Client

```python
from unittest.mock import AsyncMock
import aiohttp

@pytest.mark.asyncio
async def test_http_client():
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.json.return_value = {"data": [...]}
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    # Use mock session
    # ...
```

## Integration Tests

Integration tests hit live exchange APIs. They should be skipped by default.

### Marking Integration Tests

```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_api():
    async with DataAPI() as api:
        ohlcv = await api.fetch_ohlcv(
            "BTCUSDT",
            Timeframe.H1,
            exchange="binance",
            limit=10,
        )
        assert len(ohlcv) > 0
```

### Running Integration Tests

```bash
# Skip integration tests (default)
pytest

# Run integration tests
RUN_LAAKHAY_NETWORK_TESTS=1 pytest tests/integration
```

## Test Fixtures

### Provider Fixtures

```python
import pytest
from laakhay.data import BinanceProvider, MarketType

@pytest.fixture
async def binance_provider():
    async with BinanceProvider(market_type=MarketType.SPOT) as provider:
        yield provider
```

### API Fixtures

```python
@pytest.fixture
async def data_api():
    async with DataAPI(
        default_exchange="binance",
        default_market_type=MarketType.SPOT,
    ) as api:
        yield api
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Speed**: Unit tests should be fast (< 1s each)
3. **Determinism**: Tests should produce consistent results
4. **Coverage**: Aim for high code coverage
5. **Mocking**: Mock external dependencies
6. **Fixtures**: Use fixtures for common setup

## Test Examples

### Testing Data Models

```python
def test_ohlcv_validation():
    # Valid OHLCV
    ohlcv = OHLCV(
        meta=SeriesMeta(symbol="BTC/USDT", timeframe="1h"),
        bars=[bar1, bar2, bar3],  # Sorted by timestamp
    )
    assert len(ohlcv) == 3
    
    # Invalid: unsorted bars
    with pytest.raises(ValueError):
        OHLCV(
            meta=SeriesMeta(symbol="BTC/USDT", timeframe="1h"),
            bars=[bar2, bar1, bar3],  # Not sorted
        )
```

### Testing URM

```python
@pytest.mark.asyncio
async def test_urm_resolution():
    registry = get_urm_registry()
    registry.register("test", TestURMMapper())
    
    spec = registry.urm_to_spec("BTCUSDT", exchange="test", market_type=MarketType.SPOT)
    assert spec.base == "BTC"
    assert spec.quote == "USDT"
```

### Testing Capabilities

```python
def test_capability_check():
    status = supports(
        feature=DataFeature.OHLCV,
        transport=TransportKind.REST,
        exchange="binance",
        market_type=MarketType.SPOT,
    )
    assert status.supported
    assert status.source == "static"
```

## See Also

- [Provider Development](./provider-development.md) - Adding new providers
- [Architecture Overview](../architecture/overview.md) - System design

