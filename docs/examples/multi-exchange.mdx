# Multi-Exchange Examples

## Comparing Prices Across Exchanges

```python
import asyncio
from laakhay.data.api import DataAPI
from laakhay.data.core import MarketType, Timeframe

async def compare_prices():
    async with DataAPI() as api:
        exchanges = ["binance", "bybit", "okx", "kraken"]
        symbol = "BTCUSDT"
        
        prices = {}
        for exchange in exchanges:
            try:
                ohlcv = await api.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=Timeframe.M1,
                    exchange=exchange,
                    market_type=MarketType.SPOT,
                    limit=1,
                )
                prices[exchange] = ohlcv.latest.close
            except Exception as e:
                print(f"{exchange}: Error - {e}")
        
        # Find best price
        if prices:
            best_buy = max(prices.items(), key=lambda x: x[1])
            best_sell = min(prices.items(), key=lambda x: x[1])
            print(f"Best buy price: {best_buy[0]} @ {best_buy[1]}")
            print(f"Best sell price: {best_sell[0]} @ {best_sell[1]}")
            print(f"Arbitrage opportunity: {best_buy[1] - best_sell[1]}")

asyncio.run(compare_prices())
```

## Aggregating Data from Multiple Exchanges

```python
async def aggregate_volume():
    async with DataAPI() as api:
        exchanges = ["binance", "bybit", "okx"]
        symbol = "BTCUSDT"
        timeframe = Timeframe.H1
        
        total_volume = 0
        exchange_volumes = {}
        
        for exchange in exchanges:
            try:
                ohlcv = await api.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    exchange=exchange,
                    market_type=MarketType.SPOT,
                    limit=24,  # Last 24 hours
                )
                volume = ohlcv.total_volume
                exchange_volumes[exchange] = volume
                total_volume += volume
            except Exception as e:
                print(f"{exchange}: Error - {e}")
        
        print(f"Total volume across exchanges: {total_volume}")
        for exchange, volume in exchange_volumes.items():
            percentage = (volume / total_volume * 100) if total_volume > 0 else 0
            print(f"{exchange}: {volume} ({percentage:.1f}%)")

asyncio.run(aggregate_volume())
```

## Exchange-Specific Features

```python
async def exchange_features():
    async with DataAPI() as api:
        # Binance: Futures liquidations
        try:
            async for liq in api.stream_liquidations(
                exchange="binance",
                market_type=MarketType.FUTURES,
            ):
                if liq.is_large:
                    print(f"Large liquidation: {liq.symbol} ${liq.value_usdt:,.2f}")
                    break
        except Exception as e:
            print(f"Liquidations not available: {e}")
        
        # Bybit: Funding rates
        try:
            rates = await api.fetch_funding_rate(
                symbol="BTCUSDT",
                exchange="bybit",
                market_type=MarketType.FUTURES,
                limit=10,
            )
            for rate in rates:
                print(f"Funding rate: {rate.funding_rate_percentage:.4f}%")
        except Exception as e:
            print(f"Funding rates not available: {e}")

asyncio.run(exchange_features())
```

## Fallback Strategy

```python
async def fetch_with_fallback():
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
                    limit=100,
                )
                print(f"Successfully fetched from {exchange}")
                return ohlcv
            except Exception as e:
                print(f"{exchange} failed: {e}")
                continue
        
        raise Exception("All exchanges failed")

asyncio.run(fetch_with_fallback())
```

## Parallel Fetching

```python
async def fetch_parallel():
    async with DataAPI() as api:
        exchanges = ["binance", "bybit", "okx"]
        symbol = "BTCUSDT"
        timeframe = Timeframe.H1
        
        async def fetch_exchange(exchange):
            try:
                return await api.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    exchange=exchange,
                    market_type=MarketType.SPOT,
                    limit=10,
                )
            except Exception as e:
                print(f"{exchange}: {e}")
                return None
        
        # Fetch from all exchanges in parallel
        results = await asyncio.gather(*[
            fetch_exchange(exchange) for exchange in exchanges
        ])
        
        # Process results
        for exchange, ohlcv in zip(exchanges, results):
            if ohlcv:
                print(f"{exchange}: {ohlcv.latest.close}")

asyncio.run(fetch_parallel())
```

## See Also

- [Basic REST](./basic-rest.md) - REST API examples
- [Basic Streaming](./basic-streaming.md) - Streaming examples
- [API Reference](../api-reference/data-api.md) - Complete API docs

