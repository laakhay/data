# Laakhay-Data Capabilities API Plan

## Overview

Add a consistent capabilities API to `laakhay-data` that allows consumers (like the backend) to programmatically discover:
- All supported exchanges
- Market types supported per exchange (spot/futures)
- Available timeframes (from enum + exchange-specific)
- Data types supported per exchange (OHLCV, OrderBook, Trades, Liquidations, etc.)
- REST vs WebSocket support

## Design Goals

1. **Static where possible**: Use enums and constants, avoid instantiating providers
2. **Consistent API**: Single entry point for all capability queries
3. **Type-safe**: Return structured data (Pydantic models or TypedDict)
4. **Extensible**: Easy to add new exchanges or capabilities
5. **Backend-friendly**: Backend can call without provider instances

## Implementation Plan

### 1. Create `laakhay/data/core/capabilities.py`

**Structure:**
```python
from typing import TypedDict, Literal
from enum import Enum

class ExchangeCapability(TypedDict):
    name: str
    display_name: str
    supported_market_types: list[str]  # ["spot", "futures"]
    default_market_type: str | None
    supported_timeframes: list[str]  # From Timeframe enum
    data_types: dict[str, dict[str, bool]]  # {"ohlcv": {"rest": True, "ws": True}, ...}
    notes: str | None  # e.g., "Spot only" for Coinbase

# Exchange metadata registry
EXCHANGE_METADATA: dict[str, ExchangeCapability] = {
    "binance": {...},
    "bybit": {...},
    ...
}

# Functions:
def get_all_exchanges() -> list[str]
def get_exchange_capability(exchange: str) -> ExchangeCapability | None
def get_all_capabilities() -> dict[str, ExchangeCapability]
def get_supported_market_types(exchange: str) -> list[str] | None
def get_supported_timeframes(exchange: str | None = None) -> list[str]
def get_supported_data_types(exchange: str) -> dict[str, dict[str, bool]] | None
```

### 2. Exchange Metadata

Based on README.md and provider implementations:

| Exchange | Spot | Futures | Default | Notes |
|----------|------|---------|---------|-------|
| Binance | ✅ | ✅ | SPOT | Full support |
| Bybit | ✅ | ✅ | SPOT | Full support |
| OKX | ✅ | ✅ | SPOT | Full support |
| Hyperliquid | ❌ | ✅ | FUTURES | Futures-focused |
| Kraken | ✅ | ✅ | SPOT | Full support |
| Coinbase | ✅ | ❌ | SPOT | Spot only (enforced) |

### 3. Data Types Support Matrix

From README.md:

| Data Type | Binance | Bybit | OKX | Hyperliquid | Kraken | Coinbase |
|-----------|---------|-------|-----|-------------|--------|----------|
| OHLCV (REST) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| OHLCV (WS) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| OrderBook (REST) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| OrderBook (WS) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Trades (REST) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Trades (WS) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Liquidations (WS) | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Open Interest (REST) | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Open Interest (WS) | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Funding Rates (REST) | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Funding Rates (WS) | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Mark Price (WS) | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Symbol Metadata (REST) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 4. Timeframes

All exchanges support the full `Timeframe` enum:
- Minutes: `1m`, `3m`, `5m`, `15m`, `30m`
- Hours: `1h`, `2h`, `4h`, `6h`, `8h`, `12h`
- Days/Weeks/Months: `1d`, `3d`, `1w`, `1M`

Some exchanges may have limitations (e.g., Kraken has fallbacks), but the enum represents the standard set.

### 5. Export from `__init__.py`

Add to `laakhay/data/__init__.py`:
```python
from .core.capabilities import (
    get_all_exchanges,
    get_exchange_capability,
    get_all_capabilities,
    get_supported_market_types,
    get_supported_timeframes,
    get_supported_data_types,
    EXCHANGE_METADATA,
)
```

## Usage Examples

### Backend Usage

```python
from laakhay.data import get_all_capabilities, get_exchange_capability

# Get all capabilities
all_caps = get_all_capabilities()
print(all_caps["binance"]["supported_market_types"])  # ["spot", "futures"]

# Get specific exchange
binance_cap = get_exchange_capability("binance")
print(binance_cap["supported_timeframes"])  # ["1m", "3m", ...]

# Get all supported exchanges
exchanges = get_all_exchanges()  # ["binance", "bybit", ...]

# Get timeframes (all or per-exchange)
timeframes = get_supported_timeframes()  # All from enum
timeframes = get_supported_timeframes("binance")  # Same, but could be exchange-specific
```

## Implementation Steps

1. ✅ Create plan document
2. Create `core/capabilities.py` with metadata registry
3. Add functions for querying capabilities
4. Export from `core/__init__.py`
5. Export from main `__init__.py`
6. Update backend to use new API
7. Test with backend integration

## Notes

- Keep metadata static (no provider instantiation needed)
- Use TypedDict for type safety without Pydantic dependency
- Consider future: Could add dynamic capabilities (e.g., actual symbols from exchange API)
- Consider future: Could add provider version/API version info

