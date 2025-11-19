# Provider System Architecture

## Overview

Providers encapsulate all exchange-specific logic. Each provider implements a
unified surface (REST + WebSocket) and registers feature handlers with the
global registry so higher layers (DataAPI/DataRouter) can stay exchange-agnostic.

## Components

```
providers/<exchange>/
├── provider.py        # Unified provider (inherits BaseProvider)
├── constants.py       # Base URLs, rate limits
├── urm.py             # Exchange-specific URM mapper
├── rest/
│   ├── provider.py    # RESTProvider implementation
│   ├── adapters.py    # Response normalization
│   └── endpoints.py   # URL builders & params
└── ws/
    ├── provider.py    # WSProvider implementation
    ├── adapters.py    # Message normalization
    └── transport.py   # Connection helpers (if needed)
```

## Lifecycle

1. **Registration** – `register_all()` registers provider classes, feature
   handlers, and URM mapper with the global registries.
2. **Instantiation** – `ProviderRegistry` lazily creates provider instances per
   `(exchange, market_type)` when routed requests arrive.
3. **Usage** – Providers expose coroutine methods (REST + WS) invoked via the
   router or directly by advanced users.
4. **Cleanup** – Providers implement `close()` to tear down HTTP sessions and
   WebSocket connections; registry ensures cleanup on shutdown.

## Feature Handlers

Use `@register_feature_handler(DataFeature, TransportKind)` to map provider
methods to capability entries. The router consults these mappings to find the
right method for each request.

## URM Integration

Each provider ships an `UniversalRepresentationMapper` implementation translating
between exchange-native symbols and canonical `InstrumentSpec`. Registration
occurs alongside provider registration so DataRouter can normalize symbols before
invoking handlers.

## Direct Usage

Providers remain part of the public API for advanced consumers:

```python
from laakhay.data import BinanceProvider, MarketType, Timeframe

async with BinanceProvider(market_type=MarketType.SPOT) as provider:
    bars = await provider.get_candles("BTCUSDT", Timeframe.M1)
```

Documenting this layer clarifies that the system is intentionally modular and
open for extension, even though most users will stick with DataAPI.
