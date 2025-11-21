# Basic Usage Guide

## Fetching OHLCV Data

### Single Symbol

```python
from laakhay.data.api import DataAPI
from laakhay.data.core import MarketType, Timeframe

async with DataAPI() as api:
    ohlcv = await api.fetch_ohlcv(
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        exchange="binance",
        market_type=MarketType.SPOT,
        limit=100,
    )
    
    # Access properties
    print(f"Symbol: {ohlcv.meta.symbol}")
    print(f"Timeframe: {ohlcv.meta.timeframe}")
    print(f"Bars: {len(ohlcv)}")
    print(f"Latest: {ohlcv.latest.close}")
    print(f"Highest: {ohlcv.highest_price}")
    print(f"Total Volume: {ohlcv.total_volume}")
```

### With Time Range

```python
from datetime import datetime, timedelta

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
```

## Fetching Order Books

```python
order_book = await api.fetch_order_book(
    symbol="BTCUSDT",
    exchange="binance",
    market_type=MarketType.SPOT,
    depth=20,
)

# Access computed metrics
print(f"Spread: {order_book.spread_bps:.2f} bps")
print(f"Mid Price: {order_book.mid_price}")
print(f"Imbalance: {order_book.imbalance:.2f}")
print(f"Market Pressure: {order_book.market_pressure}")
```

## Fetching Trades

```python
trades = await api.fetch_recent_trades(
    symbol="BTCUSDT",
    exchange="binance",
    market_type=MarketType.SPOT,
    limit=100,
)

for trade in trades:
    print(f"{trade.symbol}: ${trade.price} x {trade.quantity} ({trade.side})")
```

## Streaming OHLCV

### Single Symbol

```python
async for bar in api.stream_ohlcv(
    symbol="BTCUSDT",
    timeframe=Timeframe.M1,
    exchange="binance",
    market_type=MarketType.SPOT,
    only_closed=True,  # Only closed bars
):
    print(f"{bar.symbol}: {bar.close} @ {bar.timestamp}")
```

### Multiple Symbols

```python
async for bar in api.stream_ohlcv_multi(
    symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
    timeframe=Timeframe.M1,
    exchange="binance",
    market_type=MarketType.SPOT,
):
    print(f"{bar.symbol}: {bar.close}")
```

## Streaming Trades

```python
async for trade in api.stream_trades(
    symbol="BTCUSDT",
    exchange="binance",
    market_type=MarketType.SPOT,
):
    if trade.value > 100000:  # Large trades
        print(f"Large trade: ${trade.value:,.2f}")
```

## Working with Data Models

### OHLCV Series

```python
# Filter by time range
filtered = ohlcv.get_bars_in_range(start_time, end_time)

# Get last N bars
recent = ohlcv.get_last_n_bars(10)

# Get only closed bars
closed = ohlcv.get_closed_bars()

# Iterate over bars
for bar in ohlcv:
    print(f"{bar.timestamp}: {bar.close}")
```

### Order Book Analysis

```python
# Check spread tightness
if order_book.is_tight_spread:
    print("Tight spread - good liquidity")

# Analyze market pressure
if order_book.market_pressure == "bullish":
    print("Bullish pressure")
elif order_book.market_pressure == "bearish":
    print("Bearish pressure")
```

## Symbol Formats

DataAPI accepts symbols in multiple formats:

```python
# Global alias (recommended)
ohlcv1 = await api.fetch_ohlcv("BTCUSDT", Timeframe.H1, exchange="binance")

# URM ID
ohlcv2 = await api.fetch_ohlcv(
    "urm://binance:btc/usdt:spot",
    Timeframe.H1,
    exchange="binance",
)

# Exchange-native (still works)
ohlcv3 = await api.fetch_ohlcv("BTCUSDT", Timeframe.H1, exchange="binance")
```

## See Also

- [Getting Started](./getting-started.md) - Installation and quick start
- [Advanced Usage](./advanced-usage.md) - Advanced patterns
- [API Reference](../api-reference/data-api.md) - Complete API docs

