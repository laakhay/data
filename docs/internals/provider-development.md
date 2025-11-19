# Provider Development Guide

## Overview

This guide explains how to add a new exchange provider to the Laakhay Data library.

## Provider Structure

Each provider consists of:

1. **Provider Class** - Main provider interface
2. **REST Provider** - REST API implementation
3. **WS Provider** - WebSocket streaming implementation
4. **URM Mapper** - Symbol normalization
5. **Adapters** - Response/message normalization
6. **Endpoints** - API endpoint specifications

## Step-by-Step Guide

### 1. Create Provider Directory

```
laakhay/data/providers/new_exchange/
├── __init__.py
├── provider.py
├── constants.py
├── urm.py
├── rest/
│   ├── __init__.py
│   ├── provider.py
│   ├── adapters.py
│   └── endpoints.py
└── ws/
    ├── __init__.py
    ├── provider.py
    ├── adapters.py
    ├── endpoints.py
    └── transport.py
```

### 2. Implement REST Provider

```python
from laakhay.data.io.rest import RESTProvider
from laakhay.data.models import OHLCV, OrderBook, Trade

class NewExchangeRESTProvider(RESTProvider):
    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> OHLCV:
        # Implement REST API call
        # Normalize response via adapter
        # Return OHLCV model
        pass
```

### 3. Implement WS Provider

```python
from laakhay.data.io.ws import WSProvider
from laakhay.data.models import StreamingBar

class NewExchangeWSProvider(WSProvider):
    async def stream_ohlcv(
        self,
        symbol: str,
        interval: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        # Implement WebSocket connection
        # Parse messages via adapter
        # Yield StreamingBar objects
        pass
```

### 4. Implement URM Mapper

```python
from laakhay.data.core.urm import UniversalRepresentationMapper
from laakhay.data.core.enums import InstrumentSpec, MarketType

class NewExchangeURMMapper:
    def to_spec(
        self,
        exchange_symbol: str,
        *,
        market_type: MarketType,
    ) -> InstrumentSpec:
        # Convert exchange symbol to InstrumentSpec
        pass
    
    def to_exchange_symbol(
        self,
        spec: InstrumentSpec,
        *,
        market_type: MarketType,
    ) -> str:
        # Convert InstrumentSpec to exchange symbol
        pass
```

### 5. Register Provider

```python
from laakhay.data.core import get_provider_registry, get_urm_registry
from laakhay.data.core.registry import collect_feature_handlers

# Register provider
registry = get_provider_registry()
registry.register(
    exchange="new_exchange",
    provider_class=NewExchangeProvider,
    market_types=[MarketType.SPOT, MarketType.FUTURES],
    urm_mapper=NewExchangeURMMapper(),
    feature_handlers=collect_feature_handlers(NewExchangeProvider),
)

# Register URM mapper
urm_registry = get_urm_registry()
urm_registry.register("new_exchange", NewExchangeURMMapper())
```

## Feature Handler Registration

Use decorators to register feature handlers:

```python
from laakhay.data.core.registry import register_feature_handler
from laakhay.data.core.enums import DataFeature, TransportKind

class NewExchangeRESTProvider(RESTProvider):
    @register_feature_handler(DataFeature.OHLCV, TransportKind.REST)
    async def fetch_ohlcv(self, ...):
        # Implementation
        pass
```

## Testing

### Unit Tests

```python
import pytest
from laakhay.data.providers.new_exchange import NewExchangeProvider

@pytest.mark.asyncio
async def test_fetch_ohlcv():
    async with NewExchangeProvider() as provider:
        ohlcv = await provider.fetch_ohlcv("BTCUSDT", Timeframe.H1)
        assert len(ohlcv) > 0
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_api():
    async with NewExchangeProvider() as provider:
        ohlcv = await provider.fetch_ohlcv("BTCUSDT", Timeframe.H1)
        assert ohlcv.latest is not None
```

## Best Practices

1. **Error Handling**: Handle rate limits, network errors, invalid symbols
2. **Rate Limiting**: Respect exchange rate limits
3. **Symbol Normalization**: Use URM for consistent symbol handling
4. **Response Normalization**: Use adapters to normalize exchange responses
5. **Type Safety**: Use Pydantic models for all data
6. **Async**: All operations should be async
7. **Resource Cleanup**: Implement proper cleanup in `close()`

## See Also

- [Architecture Overview](../architecture/overview.md) - System architecture
- [I/O Layer](../architecture/io-layer.md) - Transport abstractions
- [URM System](../architecture/urm-system.md) - Symbol normalization
