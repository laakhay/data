# Basic Streaming Examples

## Streaming OHLCV

### Single Symbol

```python
import asyncio
from laakhay.data.core import DataAPI, MarketType, Timeframe

async def stream_ohlcv():
    async with DataAPI() as api:
        async for bar in api.stream_ohlcv(
            symbol="BTCUSDT",
            timeframe=Timeframe.M1,
            exchange="binance",
            market_type=MarketType.SPOT,
            only_closed=True,  # Only closed bars
        ):
            print(f"{bar.symbol}: {bar.close} @ {bar.timestamp}")
            # Break after 10 bars for example
            if bar.is_closed:
                break

asyncio.run(stream_ohlcv())
```

### Multiple Symbols

```python
async def stream_multiple():
    async with DataAPI() as api:
        async for bar in api.stream_ohlcv_multi(
            symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            timeframe=Timeframe.M1,
            exchange="binance",
            market_type=MarketType.SPOT,
        ):
            print(f"{bar.symbol}: {bar.close}")
            # Process bars from different symbols

asyncio.run(stream_multiple())
```

## Streaming Trades

```python
async def stream_trades():
    async with DataAPI() as api:
        async for trade in api.stream_trades(
            symbol="BTCUSDT",
            exchange="binance",
            market_type=MarketType.SPOT,
        ):
            print(f"{trade.symbol}: ${trade.price} x {trade.quantity} ({trade.side})")
            
            # Filter large trades
            if trade.value > 100000:
                print(f"Large trade: ${trade.value:,.2f}")
            
            # Break after 10 trades for example
            break

asyncio.run(stream_trades())
```

## Streaming with Filters

```python
async def stream_filtered():
    async with DataAPI() as api:
        count = 0
        async for trade in api.stream_trades(
            symbol="BTCUSDT",
            exchange="binance",
            market_type=MarketType.SPOT,
        ):
            # Only process buy trades
            if trade.is_buy:
                print(f"Buy: ${trade.price} x {trade.quantity}")
                count += 1
                if count >= 10:
                    break

asyncio.run(stream_filtered())
```

## Multi-Exchange Streaming

```python
async def stream_multiple_exchanges():
    async with DataAPI() as api:
        exchanges = ["binance", "bybit"]
        
        # Stream from multiple exchanges
        tasks = []
        for exchange in exchanges:
            async def stream_exchange(exchange):
                async for bar in api.stream_ohlcv(
                    symbol="BTCUSDT",
                    timeframe=Timeframe.M1,
                    exchange=exchange,
                    market_type=MarketType.SPOT,
                ):
                    print(f"{exchange}: {bar.close}")
                    break  # Just one bar per exchange for example
            
            tasks.append(stream_exchange(exchange))
        
        await asyncio.gather(*tasks)

asyncio.run(stream_multiple_exchanges())
```

## Streaming with Timeout

```python
async def stream_with_timeout():
    async with DataAPI() as api:
        try:
            async for bar in asyncio.wait_for(
                api.stream_ohlcv(
                    symbol="BTCUSDT",
                    timeframe=Timeframe.M1,
                    exchange="binance",
                    market_type=MarketType.SPOT,
                ),
                timeout=30.0,  # 30 second timeout
            ):
                print(f"{bar.symbol}: {bar.close}")
        except asyncio.TimeoutError:
            print("Stream timeout")

asyncio.run(stream_with_timeout())
```

## See Also

- [Basic REST](./basic-rest.md) - REST API examples
- [Feeds](./feeds.md) - High-level feed examples
- [API Reference](../api-reference/data-api.md) - Complete API docs

