# Feed Examples

## OHLCV Feed

### Basic Usage

```python
import asyncio
from laakhay.data import OHLCVFeed, BinanceProvider, MarketType, Timeframe
from laakhay.data.models import DataEventType

async def basic_feed():
    provider = BinanceProvider(market_type=MarketType.SPOT)
    
    feed = OHLCVFeed(
        ws_provider=provider,
        rest_provider=provider,  # For warm-up
    )
    
    # Subscribe to bar updates
    def on_bar(bar):
        print(f"New bar: {bar.symbol} @ {bar.close}")
    
    feed.subscribe_bar(on_bar, symbols={"BTCUSDT"}, interval=Timeframe.M1)
    
    # Start streaming
    await feed.start(
        symbols=["BTCUSDT"],
        interval=Timeframe.M1,
        warm_up=100,  # Fetch 100 bars from REST first
    )
    
    # Run for a bit
    await asyncio.sleep(60)
    
    # Stop
    await feed.stop()
    await provider.close()

asyncio.run(basic_feed())
```

### Multiple Symbols

```python
async def multi_symbol_feed():
    provider = BinanceProvider(market_type=MarketType.SPOT)
    feed = OHLCVFeed(ws_provider=provider, rest_provider=provider)
    
    def on_bar(bar):
        print(f"{bar.symbol}: {bar.close}")
    
    feed.subscribe_bar(
        on_bar,
        symbols={"BTCUSDT", "ETHUSDT", "BNBUSDT"},
        interval=Timeframe.M1,
    )
    
    await feed.start(
        symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
        interval=Timeframe.M1,
    )
    
    await asyncio.sleep(60)
    await feed.stop()
    await provider.close()

asyncio.run(multi_symbol_feed())
```

### Event Subscriptions

```python
async def event_feed():
    provider = BinanceProvider(market_type=MarketType.SPOT)
    feed = OHLCVFeed(ws_provider=provider)
    
    def on_event(event):
        if event.type == DataEventType.BAR:
            print(f"Bar: {event.data.symbol} @ {event.data.close}")
        elif event.type == DataEventType.CONNECTION:
            print(f"Connection: {event.data.status}")
    
    feed.subscribe_event(on_event, event_types={DataEventType.BAR, DataEventType.CONNECTION})
    
    await feed.start(symbols=["BTCUSDT"], interval=Timeframe.M1)
    await asyncio.sleep(60)
    await feed.stop()
    await provider.close()

asyncio.run(event_feed())
```

## Liquidation Feed

```python
from laakhay.data import LiquidationFeed, BinanceProvider, MarketType

async def liquidation_feed():
    provider = BinanceProvider(market_type=MarketType.FUTURES)
    feed = LiquidationFeed(ws_provider=provider)
    
    def on_liquidation(liq):
        if liq.is_large:
            print(f"Large liquidation: {liq.symbol} ${liq.value_usdt:,.2f} ({liq.side})")
    
    feed.subscribe(on_liquidation, keys={"BTCUSDT"})
    
    await feed.start(symbols=["BTCUSDT"])
    await asyncio.sleep(60)
    await feed.stop()
    await provider.close()

asyncio.run(liquidation_feed())
```

## Open Interest Feed

```python
from laakhay.data import OpenInterestFeed, BinanceProvider, MarketType

async def open_interest_feed():
    provider = BinanceProvider(market_type=MarketType.FUTURES)
    feed = OpenInterestFeed(ws_provider=provider)
    
    def on_oi(oi):
        print(f"OI: {oi.symbol} = {oi.open_interest} ({oi.open_interest_value} USD)")
    
    feed.subscribe(on_oi, keys={"BTCUSDT"})
    
    await feed.start(symbols=["BTCUSDT"], period="5m")
    await asyncio.sleep(60)
    await feed.stop()
    await provider.close()

asyncio.run(open_interest_feed())
```

## Feed with History

```python
async def feed_with_history():
    provider = BinanceProvider(market_type=MarketType.SPOT)
    feed = OHLCVFeed(
        ws_provider=provider,
        rest_provider=provider,
        max_bar_history=100,  # Keep last 100 bars
    )
    
    def on_bar(bar):
        # Get history for this symbol
        history = feed.get_bar_history(bar.symbol, Timeframe.M1)
        if history:
            print(f"Current: {bar.close}, Avg: {sum(b.close for b in history) / len(history)}")
    
    feed.subscribe_bar(on_bar, symbols={"BTCUSDT"}, interval=Timeframe.M1)
    
    await feed.start(symbols=["BTCUSDT"], interval=Timeframe.M1, warm_up=100)
    await asyncio.sleep(60)
    await feed.stop()
    await provider.close()

asyncio.run(feed_with_history())
```

## See Also

- [Basic Streaming](./basic-streaming.md) - Basic streaming examples
- [Clients Architecture](../architecture/clients.md) - Feed architecture
- [API Reference](../api-reference/data-api.md) - Complete API docs

