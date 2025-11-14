# Laakhay Data

**Beta-stage async-first cryptocurrency market data aggregation library.**

> ⚠️ **Beta Software**: This library is in active development. Use with caution in production environments. APIs may change between versions.

Unified API for multi-exchange market data with support for **Binance**, **Bybit**, **OKX**, **Hyperliquid**, **Kraken**, and **Coinbase**. Modular provider architecture with REST/WebSocket abstraction, type-safe Pydantic models, and high-level streaming feeds.

## Installation

```bash
pip install laakhay-data
```

## Quick Start

### Using DataAPI (Recommended)

```python
import asyncio
from laakhay.data.core import DataAPI, MarketType, Timeframe

async def main():
    async with DataAPI() as api:
        # REST API - unified interface across all exchanges
        candles = await api.fetch_ohlcv(
            symbol="BTCUSDT",
            timeframe=Timeframe.M1,
            exchange="binance",
            market_type=MarketType.SPOT,
            limit=100,
        )
        order_book = await api.fetch_order_book(
            symbol="BTCUSDT",
            exchange="binance",
            market_type=MarketType.SPOT,
            depth=20,
        )
        
        # WebSocket streaming
        async for trade in api.stream_trades(
            symbol="BTCUSDT",
            exchange="binance",
            market_type=MarketType.SPOT,
        ):
            print(f"{trade.symbol}: ${trade.value:.2f} ({trade.side})")
            break

asyncio.run(main())
```

### Using Direct Providers (Still Supported)

```python
import asyncio
from laakhay.data import BinanceProvider, MarketType, Timeframe

async def main():
    async with BinanceProvider(market_type=MarketType.SPOT) as provider:
        # REST API
        candles = await provider.get_candles("BTCUSDT", Timeframe.M1, limit=100)
        order_book = await provider.get_order_book("BTCUSDT", limit=20)
        
        # WebSocket streaming
        async for trade in provider.stream_trades("BTCUSDT"):
            print(f"{trade.symbol}: ${trade.value:.2f} ({trade.side})")
            break

asyncio.run(main())
```

> **Note**: We recommend using `DataAPI` for new code. It provides better error messages, automatic capability validation, and URM symbol resolution. See the [Migration Guide](docs/migration-guide.md) for details.

## Supported Exchanges

| Exchange | Spot | Futures | REST | WebSocket |
|----------|------|---------|------|-----------|
| **Binance** | ✅ | ✅ | ✅ | ✅ |
| **Bybit** | ✅ | ✅ | ✅ | ✅ |
| **OKX** | ✅ | ✅ | ✅ | ✅ |
| **Hyperliquid** | ❌ | ✅ | ✅ | ✅ |
| **Kraken** | ✅ | ✅ | ✅ | ✅ |
| **Coinbase** | ✅ | ❌ | ✅ | ✅ |

All providers implement the unified `BaseProvider` interface—switch exchanges without code changes.

## Data Types & Coverage

| Type | REST | WebSocket | Markets | Notes |
|------|------|-----------|---------|-------|
| **OHLCV Bars** | ✅ | ✅ | Spot, Futures | Multi-symbol streaming supported |
| **Order Book** | ✅ | ✅ | Spot, Futures | Snapshot + incremental updates |
| **Trades** | ✅ | ✅ | Spot, Futures | Real-time trade flow |
| **Liquidations** | ❌ | ✅ | Futures | Large liquidation filtering |
| **Open Interest** | ✅ | ✅ | Futures | Historical + real-time |
| **Funding Rates** | ✅ | ✅ | Futures | Perpetual funding |
| **Mark Price** | ❌ | ✅ | Futures | Mark/index prices |
| **Symbol Metadata** | ✅ | ❌ | Spot, Futures | Exchange info |

## Architecture

```
laakhay/data/
├── core/              # BaseProvider, enums, exceptions, DataAPI, DataRouter
│   ├── api.py         # DataAPI facade (unified interface)
│   ├── router.py      # DataRouter (URM + capability + provider routing)
│   ├── registry.py    # ProviderRegistry (provider lifecycle management)
│   ├── capabilities.py # Capability store (feature support matrix)
│   ├── urm.py         # URM registry (symbol normalization)
│   └── relay.py       # StreamRelay (forward streams to sinks)
├── models/            # Pydantic models (Bar, OHLCV, OrderBook, Trade, etc.)
├── providers/         # Exchange implementations
│   ├── binance/       # Binance REST + WS
│   ├── bybit/         # Bybit REST + WS
│   ├── okx/           # OKX REST + WS
│   ├── hyperliquid/   # Hyperliquid REST + WS (Futures only)
│   ├── kraken/        # Kraken REST + WS
│   └── coinbase/      # Coinbase REST + WS (Spot only)
├── io/                # REST/WS abstraction layer
│   ├── rest/          # RESTProvider, HTTP transport, adapters
│   └── ws/            # WSProvider, WebSocket transport, message adapters
├── sinks/             # Stream sinks (InMemorySink, RedisStreamSink)
└── clients/           # High-level streaming feeds
    ├── ohlcv_feed.py
    ├── liquidation_feed.py
    └── open_interest_feed.py
```

### Provider Architecture

Each provider implements:
- **RESTProvider**: HTTP-based REST API client with response adapters
- **WSProvider**: WebSocket streaming with message adapters and reconnection
- **Unified Provider**: High-level `Provider` class combining REST + WS

Providers use modular components:
- **Endpoint Specs**: URL builders, parameter mapping, rate limits
- **Response/Message Adapters**: Exchange-specific data normalization
- **Transports**: HTTP client (aiohttp) and WebSocket client (websockets)

## Core Features

### Unified DataAPI

The new `DataAPI` provides a single interface for accessing data across all exchanges:

```python
from laakhay.data.core import DataAPI, MarketType, Timeframe

async with DataAPI(
    default_exchange="binance",
    default_market_type=MarketType.SPOT,
) as api:
    # Switch exchanges easily - same API
    binance_ohlcv = await api.fetch_ohlcv(
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        exchange="binance",
        limit=100,
    )
    
    bybit_ohlcv = await api.fetch_ohlcv(
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        exchange="bybit",
        limit=100,
    )
    
    # Automatic capability validation
    # Raises CapabilityError with recommendations if unsupported
```

### Universal Representation Mapping (URM)

Use global aliases, URM IDs, or exchange-native symbols:

```python
async with DataAPI() as api:
    # Global alias
    ohlcv1 = await api.fetch_ohlcv(
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        exchange="binance",
        market_type=MarketType.SPOT,
    )
    
    # URM ID
    ohlcv2 = await api.fetch_ohlcv(
        symbol="urm://binance:btc/usdt:spot",
        timeframe=Timeframe.H1,
        exchange="binance",
        market_type=MarketType.SPOT,
    )
    
    # Exchange-native (still works)
    ohlcv3 = await api.fetch_ohlcv(
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        exchange="binance",
        market_type=MarketType.SPOT,
    )
```

### Capability Discovery

Check what features are supported before making requests:

```python
from laakhay.data.core import supports, DataFeature, TransportKind, MarketType, InstrumentType

# Check if OHLCV REST is supported
status = supports(
    feature=DataFeature.OHLCV,
    transport=TransportKind.REST,
    exchange="binance",
    market_type=MarketType.SPOT,
    instrument_type=InstrumentType.SPOT,
)

if status.supported:
    print("Supported!")
    print(f"Constraints: {status.constraints}")
else:
    print(f"Not supported: {status.reason}")
    print(f"Alternatives: {status.recommendations}")
```

### Stream Relay

Forward streams to external sinks (Redis, Kafka, etc.):

```python
from laakhay.data.core import StreamRelay, DataRequest, DataFeature, TransportKind, MarketType
from laakhay.data.sinks import InMemorySink

relay = StreamRelay()
sink = InMemorySink()
relay.add_sink(sink)

request = DataRequest(
    feature=DataFeature.TRADES,
    transport=TransportKind.WS,
    exchange="binance",
    market_type=MarketType.SPOT,
    symbol="BTCUSDT",
)

await relay.relay(request)

# Consume from sink
async for event in sink.stream():
    print(event)
```

### Multi-Exchange Support

```python
from laakhay.data import BinanceProvider, BybitProvider, OKXProvider, HyperliquidProvider, KrakenProvider, CoinbaseProvider

# Same API across all exchanges
providers = [
    BinanceProvider(market_type=MarketType.FUTURES),
    BybitProvider(market_type=MarketType.FUTURES),
    OKXProvider(market_type=MarketType.FUTURES),
    HyperliquidProvider(market_type=MarketType.FUTURES),
    KrakenProvider(market_type=MarketType.FUTURES),
    CoinbaseProvider(market_type=MarketType.SPOT),  # Spot only
]

for provider in providers:
    async with provider:
        oi = await provider.get_open_interest("BTCUSDT", historical=False)
        print(f"{provider.name}: {oi[0].open_interest}")
```

### Order Book Analysis

```python
ob = await provider.get_order_book("BTCUSDT", limit=100)
print(f"Spread: {ob.spread_bps:.2f} bps")
print(f"Market Pressure: {ob.market_pressure}")  # bullish/bearish/neutral
print(f"Imbalance: {ob.imbalance:.2f}")  # -1.0 to 1.0
print(f"Tight Spread: {ob.is_tight_spread}")  # < 10 bps
```

### Multi-Symbol Streaming

```python
# Stream OHLCV for multiple symbols
async for bar in provider.stream_ohlcv_multi(["BTCUSDT", "ETHUSDT"], Timeframe.M1):
    print(f"{bar.symbol}: {bar.close}")

# Stream trades for multiple symbols
async for trade in provider.stream_trades_multi(["BTCUSDT", "ETHUSDT"]):
    print(f"{trade.symbol}: {trade.value}")
```

### High-Level Feeds

```python
from laakhay.data import OHLCVFeed

feed = OHLCVFeed(
    provider=BinanceProvider(market_type=MarketType.SPOT),
    symbols=["BTCUSDT", "ETHUSDT"],
    timeframe=Timeframe.M1,
)

async for event in feed:
    if event.type == DataEventType.BAR:
        print(f"New bar: {event.data.symbol} @ {event.data.close}")
    elif event.type == DataEventType.CONNECTION:
        print(f"Connection: {event.data.status}")
```

### Liquidations (Futures)

```python
async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
    async for liq in provider.stream_liquidations():
        if liq.is_large:  # Filters large liquidations
            print(f"{liq.symbol}: ${liq.value_usdt:.2f} {liq.side}")
            print(f"Long: {liq.is_long_liquidation}")
```

### Open Interest (Futures)

```python
# Historical
oi_history = await provider.get_open_interest(
    "BTCUSDT", 
    historical=True, 
    period="5m", 
    limit=100
)

# Real-time streaming
async for oi in provider.stream_open_interest(["BTCUSDT"], period="5m"):
    print(f"OI: {oi.open_interest} ({oi.open_interest_value} USD)")
```

### Funding Rates (Futures)

```python
# Historical
rates = await provider.get_funding_rate("BTCUSDT", limit=50)

# Real-time streaming
async for rate in provider.stream_funding_rate(["BTCUSDT"]):
    print(f"Funding: {rate.funding_rate_percentage:.4f}%")
    print(f"Mark Price: {rate.mark_price}")
```

## Data Models

All models are immutable Pydantic v2 models with validation:

```python
from laakhay.data.models import (
    Bar,              # Individual OHLCV bar
    OHLCV,            # OHLCV series with SeriesMeta
    StreamingBar,     # Real-time bar updates
    Symbol,           # Trading pair metadata
    OrderBook,        # Market depth (25+ computed properties)
    Trade,            # Individual trades with size categorization
    Liquidation,      # Forced closures with large liquidation detection
    OpenInterest,     # Outstanding contracts
    FundingRate,      # Perpetual funding rates
    MarkPrice,        # Mark/index prices
    ConnectionEvent,  # WebSocket connection events
    DataEvent,        # Typed data events for feeds
)
```

## Exception Handling

```python
from laakhay.data.core import (
    DataError,           # Base exception
    ProviderError,       # API errors
    RateLimitError,      # Rate limit exceeded
    InvalidSymbolError,  # Symbol not found
    InvalidIntervalError,# Invalid timeframe
    ValidationError,     # Data validation errors
)

try:
    ohlcv = await provider.get_candles("INVALID", Timeframe.M1)
except InvalidSymbolError:
    print("Symbol not found")
except RateLimitError as e:
    print(f"Rate limit: {e.retry_after}")
except ProviderError as e:
    print(f"API error: {e}")
```

## Symbol Normalization

Providers handle exchange-specific symbol formats automatically:

- **Binance/Bybit/OKX**: `BTCUSDT` (standard format)
- **Hyperliquid**: `BTC` → normalized to `BTCUSDT`
- **Kraken Spot**: `XBT/USD` → normalized to `BTCUSD`
- **Kraken Futures**: `PI_XBTUSD` → normalized to `BTCUSD`
- **Coinbase**: `BTC-USD` → normalized to `BTCUSD` (USDT pairs map to USD)

## Testing

### Unit Tests

```bash
pytest tests/unit
```

### Integration Tests

Integration tests hit live exchange APIs and are skipped by default:

```bash
RUN_LAAKHAY_NETWORK_TESTS=1 pytest tests/integration
```

## Design Principles

- **Async-first**: Built on `asyncio`, `aiohttp`, and `websockets`
- **Type-safe**: Full Pydantic v2 validation with type hints
- **Modular**: Provider-agnostic architecture with pluggable transports
- **DRY**: Shared REST/WS infrastructure across providers

## Requirements

- Python 3.12+
- `pydantic>=2.0`
- `aiohttp>=3.8`
- `websockets>=10`

## License

MIT License - see [LICENSE](LICENSE)

---

Built by [Laakhay Corporation](https://laakhay.com)
