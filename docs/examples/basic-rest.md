# Basic REST Examples

## Fetching OHLCV Data

### Single Symbol

```python
import asyncio
from laakhay.data.core import DataAPI, MarketType, Timeframe

async def main():
    async with DataAPI() as api:
        # Fetch 100 1-hour candles
        ohlcv = await api.fetch_ohlcv(
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            exchange="binance",
            market_type=MarketType.SPOT,
            limit=100,
        )
        
        print(f"Fetched {len(ohlcv)} bars")
        print(f"Symbol: {ohlcv.meta.symbol}")
        print(f"Timeframe: {ohlcv.meta.timeframe}")
        print(f"Latest close: {ohlcv.latest.close}")
        print(f"Highest price: {ohlcv.highest_price}")
        print(f"Total volume: {ohlcv.total_volume}")

asyncio.run(main())
```

### With Time Range

```python
from datetime import datetime, timedelta

async def fetch_historical():
    async with DataAPI() as api:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        
        ohlcv = await api.fetch_ohlcv(
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            exchange="binance",
            market_type=MarketType.SPOT,
            start_time=start_time,
            end_time=end_time,
        )
        
        print(f"Fetched {len(ohlcv)} bars from {ohlcv.start_time} to {ohlcv.end_time}")

asyncio.run(fetch_historical())
```

## Fetching Order Books

```python
async def fetch_order_book():
    async with DataAPI() as api:
        order_book = await api.fetch_order_book(
            symbol="BTCUSDT",
            exchange="binance",
            market_type=MarketType.SPOT,
            depth=20,
        )
        
        print(f"Spread: {order_book.spread_bps:.2f} bps")
        print(f"Mid Price: {order_book.mid_price}")
        print(f"Imbalance: {order_book.imbalance:.2f}")
        print(f"Market Pressure: {order_book.market_pressure}")
        print(f"Tight Spread: {order_book.is_tight_spread}")

asyncio.run(fetch_order_book())
```

## Fetching Trades

```python
async def fetch_trades():
    async with DataAPI() as api:
        trades = await api.fetch_recent_trades(
            symbol="BTCUSDT",
            exchange="binance",
            market_type=MarketType.SPOT,
            limit=100,
        )
        
        print(f"Fetched {len(trades)} recent trades")
        for trade in trades[:5]:  # Show first 5
            print(f"{trade.symbol}: ${trade.price} x {trade.quantity} ({trade.side})")

asyncio.run(fetch_trades())
```

## Multi-Exchange Comparison

```python
async def compare_exchanges():
    async with DataAPI() as api:
        exchanges = ["binance", "bybit", "okx"]
        symbol = "BTCUSDT"
        timeframe = Timeframe.H1
        
        for exchange in exchanges:
            try:
                ohlcv = await api.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    exchange=exchange,
                    market_type=MarketType.SPOT,
                    limit=10,
                )
                print(f"{exchange}: Latest close = {ohlcv.latest.close}")
            except Exception as e:
                print(f"{exchange}: Error - {e}")

asyncio.run(compare_exchanges())
```

## Using Defaults

```python
async def with_defaults():
    # Set defaults to reduce boilerplate
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
        
        order_book = await api.fetch_order_book(
            symbol="BTCUSDT",
            depth=20,
        )

asyncio.run(with_defaults())
```

## Error Handling

```python
from laakhay.data.core import CapabilityError, SymbolResolutionError

async def with_error_handling():
    async with DataAPI() as api:
        try:
            ohlcv = await api.fetch_ohlcv(
                symbol="INVALID",
                timeframe=Timeframe.H1,
                exchange="binance",
            )
        except CapabilityError as e:
            print(f"Capability not supported: {e.message}")
            if e.recommendations:
                print(f"Try: {e.recommendations[0]}")
        except SymbolResolutionError as e:
            print(f"Symbol error: {e}")
            print(f"Exchange: {e.exchange}")
        except Exception as e:
            print(f"Unexpected error: {e}")

asyncio.run(with_error_handling())
```

## See Also

- [Getting Started](../guides/getting-started.md) - Installation and setup
- [Basic Usage](../guides/basic-usage.md) - More examples
- [API Reference](../api-reference/data-api.md) - Complete API docs

