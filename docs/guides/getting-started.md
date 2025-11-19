# Getting Started

## Installation

```bash
pip install laakhay-data
```

## Requirements

- Python 3.12+
- `pydantic>=2.0`
- `aiohttp>=3.8`
- `websockets>=10`

## Quick Start

### Basic REST API

```python
import asyncio
from laakhay.data.core import DataAPI, MarketType, Timeframe

async def main():
    async with DataAPI() as api:
        # Fetch OHLCV data
        ohlcv = await api.fetch_ohlcv(
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            exchange="binance",
            market_type=MarketType.SPOT,
            limit=100,
        )
        
        print(f"Fetched {len(ohlcv)} bars")
        print(f"Latest close: {ohlcv.latest.close}")

asyncio.run(main())
```

### Streaming Data

```python
import asyncio
from laakhay.data.core import DataAPI, MarketType, Timeframe

async def main():
    async with DataAPI() as api:
        # Stream real-time trades
        async for trade in api.stream_trades(
            symbol="BTCUSDT",
            exchange="binance",
            market_type=MarketType.SPOT,
        ):
            print(f"{trade.symbol}: ${trade.price} ({trade.side})")
            if trade.value > 100000:  # Large trade
                break

asyncio.run(main())
```

### Multi-Symbol Streaming

```python
import asyncio
from laakhay.data.core import DataAPI, MarketType, Timeframe

async def main():
    async with DataAPI() as api:
        # Stream multiple symbols
        async for bar in api.stream_ohlcv_multi(
            symbols=["BTCUSDT", "ETHUSDT"],
            timeframe=Timeframe.M1,
            exchange="binance",
            market_type=MarketType.SPOT,
        ):
            print(f"{bar.symbol}: {bar.close}")

asyncio.run(main())
```

## Using Defaults

Set default exchange and market type to reduce boilerplate:

```python
async with DataAPI(
    default_exchange="binance",
    default_market_type=MarketType.SPOT,
) as api:
    # No need to specify exchange/market_type
    ohlcv = await api.fetch_ohlcv(
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        limit=100,
    )
```

## Error Handling

```python
from laakhay.data.core import CapabilityError, SymbolResolutionError

try:
    ohlcv = await api.fetch_ohlcv(
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        exchange="coinbase",
        market_type=MarketType.FUTURES,  # Coinbase doesn't support futures
    )
except CapabilityError as e:
    print(f"Not supported: {e.message}")
    if e.recommendations:
        print(f"Try: {e.recommendations[0]}")
except SymbolResolutionError as e:
    print(f"Symbol error: {e}")
```

## Next Steps

- [Basic Usage](./basic-usage.md) - More examples
- [Advanced Usage](./advanced-usage.md) - Advanced patterns
- [API Reference](../api-reference/data-api.md) - Complete API docs

