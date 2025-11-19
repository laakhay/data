# Advanced Usage Guide

This guide covers patterns that go beyond the basic REST/streaming examples.

## 1. Capability-Driven UX

Use capability helpers to tailor user interfaces or automated planners:

```python
from laakhay.data.core.capabilities import supports
from laakhay.data.core import DataFeature, TransportKind, MarketType

status = supports(
    feature=DataFeature.LIQUIDATIONS,
    transport=TransportKind.WS,
    exchange="binance",
    market_type=MarketType.FUTURES,
)

if not status.supported and status.recommendations:
    print("Try:", status.recommendations[0].exchange)
```

## 2. Direct Provider Access

Advanced users can instantiate providers directly for fine-grained control:

```python
from laakhay.data import BinanceProvider, MarketType, Timeframe

async with BinanceProvider(market_type=MarketType.SPOT) as provider:
    candles = await provider.get_candles("BTCUSDT", Timeframe.M1, limit=200)
    async for trade in provider.stream_trades("BTCUSDT"):
        ...
```

Use this when you need custom transports, debugging, or exchange-specific APIs
that DataAPI does not expose yet.

## 3. URM Workflows

When storing symbols or building cross-exchange tooling, leverage URM:

```python
from laakhay.data.core.urm import get_urm_registry
from laakhay.data.core.enums import MarketType

registry = get_urm_registry()
spec = registry.urm_to_spec(
    "BTCUSDT",
    exchange="binance",
    market_type=MarketType.SPOT,
)
print(spec.base, spec.quote)
```

## 4. Streaming Feeds with Sinks

Combine feeds and sinks to forward events to Redis Streams:

```python
from laakhay.data.clients import OHLCVFeed
from laakhay.data.sinks.redis import RedisStreamSink

feed = OHLCVFeed(ws_provider, rest_provider)
sink = RedisStreamSink(redis_client, stream_name="stream:ohlcv")

feed.subscribe_sink(sink)
await feed.start(symbols=["BTC/USDT", "ETH/USDT"], interval=Timeframe.M1)
```

## 5. Stream Relay Fan-Out

`StreamRelay` forwards stream events to multiple sinks/callbacks:

```python
from laakhay.data.core.relay import StreamRelay

relay = StreamRelay()
relay.add_sink(my_sink)
relay.add_sink(other_sink)

async for trade in api.stream_trades("BTCUSDT"):
    relay.publish(trade)
```

## 6. Custom Transports / Sessions

Inject custom aiohttp sessions (proxies, headers):

```python
import aiohttp
from laakhay.data import BinanceProvider, MarketType

session = aiohttp.ClientSession(headers={"User-Agent": "custom"})
async with BinanceProvider(market_type=MarketType.SPOT, http_session=session) as provider:
    ...
```

## 7. Testing with Fakes

Mock routers/providers when unit testing application code:

```python
from unittest.mock import AsyncMock
from laakhay.data.core import DataAPI

mock_router = AsyncMock()
mock_router.route.return_value = fake_ohlcv

async with DataAPI(router=mock_router) as api:
    ...
```

See [Testing guide](./testing.md) for more patterns.

## 8. Error Recovery Strategies

Pair custom retry logic with specific exceptions:

```python
from laakhay.data.core import ProviderError, RateLimitError

async def safe_fetch(func, *args, retries=3):
    for attempt in range(retries):
        try:
            return await func(*args)
        except RateLimitError as e:
            await asyncio.sleep(e.retry_after)
        except ProviderError as e:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
```

Refer back to [Error handling guide](./error-handling.md) for more detail.
