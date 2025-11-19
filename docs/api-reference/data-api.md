# DataAPI Reference

## Overview

`DataAPI` is the high-level facade that provides a unified interface for accessing market data across all exchanges. It handles capability validation, symbol normalization (URM), and provider routing automatically.

## Class: DataAPI

```python
from laakhay.data.core import DataAPI, MarketType, Timeframe

async with DataAPI(
    default_exchange: str | None = None,
    default_market_type: MarketType | None = None,
    default_instrument_type: InstrumentType | None = None,
    router: DataRouter | None = None,
) as api:
    # Use API
```

### Parameters

- `default_exchange`: Default exchange name (e.g., "binance")
- `default_market_type`: Default market type (SPOT or FUTURES)
- `default_instrument_type`: Default instrument type (SPOT, PERPETUAL, FUTURE)
- `router`: Optional DataRouter instance (for testing)

### Methods

#### fetch_health

Fetch health/status information for an exchange.

```python
health: dict[str, Any] = await api.fetch_health(
    *,
    exchange: str | None = None,
    market_type: MarketType | None = None,
    instrument_type: InstrumentType | None = None,
) -> dict[str, Any]
```

**Parameters:**
- `exchange`: Exchange name (uses default if None)
- `market_type`: Market type (uses default if None)
- `instrument_type`: Instrument type (optional for completeness)

**Returns:** Dictionary containing health metadata (status, latency, endpoint, etc.)

**Raises:**
- `CapabilityError`: If health endpoint not supported
- `ProviderError`: If provider operation fails

#### fetch_ohlcv

Fetch OHLCV (candlestick) data.

```python
ohlcv: OHLCV = await api.fetch_ohlcv(
    symbol: str,
    timeframe: Timeframe | str,
    *,
    exchange: str | None = None,
    market_type: MarketType | None = None,
    instrument_type: InstrumentType | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int | None = None,
) -> OHLCV
```

**Parameters:**
- `symbol`: Symbol in any format (alias, URM ID, exchange-native)
- `timeframe`: Timeframe (e.g., Timeframe.H1, "1h")
- `exchange`: Exchange name (uses default if None)
- `market_type`: Market type (uses default if None)
- `instrument_type`: Instrument type (uses default if None)
- `start_time`: Optional start time
- `end_time`: Optional end time
- `limit`: Maximum number of bars

**Returns:** `OHLCV` series with metadata and bars

**Raises:**
- `CapabilityError`: If capability not supported
- `SymbolResolutionError`: If symbol cannot be resolved
- `ProviderError`: If provider operation fails

#### fetch_order_book

Fetch order book snapshot.

```python
order_book: OrderBook = await api.fetch_order_book(
    symbol: str,
    *,
    exchange: str | None = None,
    market_type: MarketType | None = None,
    instrument_type: InstrumentType | None = None,
    depth: int = 100,
) -> OrderBook
```

**Parameters:**
- `symbol`: Symbol in any format
- `exchange`: Exchange name (uses default if None)
- `market_type`: Market type (uses default if None)
- `instrument_type`: Instrument type (uses default if None)
- `depth`: Order book depth (default: 100)

**Returns:** `OrderBook` with bids, asks, and computed metrics

#### fetch_trades

Fetch recent trades.

```python
trades: list[Trade] = await api.fetch_trades(
    symbol: str,
    *,
    exchange: str | None = None,
    market_type: MarketType | None = None,
    instrument_type: InstrumentType | None = None,
    limit: int = 500,
) -> list[Trade]
```

**Parameters:**
- `symbol`: Symbol in any format
- `exchange`: Exchange name (uses default if None)
- `market_type`: Market type (uses default if None)
- `instrument_type`: Instrument type (uses default if None)
- `limit`: Maximum number of trades (default: 500)

**Returns:** List of `Trade` objects

#### stream_ohlcv

Stream real-time OHLCV updates.

```python
async for bar in api.stream_ohlcv(
    symbol: str,
    timeframe: Timeframe | str,
    *,
    exchange: str | None = None,
    market_type: MarketType | None = None,
    instrument_type: InstrumentType | None = None,
    only_closed: bool = False,
    throttle_ms: int | None = None,
    dedupe_same_candle: bool = False,
):
    # Process bar
```

**Parameters:**
- `symbol`: Symbol in any format
- `timeframe`: Timeframe (e.g., Timeframe.M1)
- `exchange`: Exchange name (uses default if None)
- `market_type`: Market type (uses default if None)
- `instrument_type`: Instrument type (uses default if None)
- `only_closed`: Only yield closed bars (default: False)
- `throttle_ms`: Throttle updates (milliseconds)
- `dedupe_same_candle`: Deduplicate same candle updates

**Yields:** `StreamingBar` objects

#### stream_ohlcv_multi

Stream OHLCV for multiple symbols.

```python
async for bar in api.stream_ohlcv_multi(
    symbols: list[str],
    timeframe: Timeframe | str,
    *,
    exchange: str | None = None,
    market_type: MarketType | None = None,
    instrument_type: InstrumentType | None = None,
    only_closed: bool = False,
    throttle_ms: int | None = None,
    dedupe_same_candle: bool = False,
):
    # Process bar
```

**Parameters:**
- `symbols`: List of symbols
- `timeframe`: Timeframe
- Other parameters same as `stream_ohlcv`

**Yields:** `StreamingBar` objects (may be from different symbols)

#### stream_trades

Stream real-time trades.

```python
async for trade in api.stream_trades(
    symbol: str,
    *,
    exchange: str | None = None,
    market_type: MarketType | None = None,
    instrument_type: InstrumentType | None = None,
):
    # Process trade
```

**Yields:** `Trade` objects

## Examples

### Basic Usage

```python
from laakhay.data.core import DataAPI, MarketType, Timeframe

async with DataAPI(
    default_exchange="binance",
    default_market_type=MarketType.SPOT,
) as api:
    # Fetch OHLCV
    ohlcv = await api.fetch_ohlcv(
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        limit=100,
    )
    
    # Stream trades
    async for trade in api.stream_trades("BTCUSDT"):
        print(f"{trade.symbol}: ${trade.price}")
        break
```

### Multi-Exchange

```python
async with DataAPI() as api:
    # Binance
    binance_ohlcv = await api.fetch_ohlcv(
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        exchange="binance",
        limit=100,
    )
    
    # Bybit
    bybit_ohlcv = await api.fetch_ohlcv(
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        exchange="bybit",
        limit=100,
    )
```

### Error Handling

```python
from laakhay.data.core import CapabilityError, SymbolResolutionError

try:
    ohlcv = await api.fetch_ohlcv(
        symbol="INVALID",
        timeframe=Timeframe.H1,
        exchange="binance",
    )
except CapabilityError as e:
    print(f"Not supported: {e.message}")
    print(f"Alternatives: {e.recommendations}")
except SymbolResolutionError as e:
    print(f"Symbol error: {e}")
```

## See Also

- [Architecture Overview](../architecture/overview.md) - System architecture
- [Design Decisions](../architecture/design-decisions.md) - ADR-001: Facade Pattern
- [Core API Source](../../laakhay/data/core/api.py) - Implementation

