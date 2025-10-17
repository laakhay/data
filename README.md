# Laakhay Data

**Professional Python library for cryptocurrency market data.**

Async-first market data toolkit with REST/WS providers, reusable transport, and a high-level OHLCV feed. Supports OHLCV, order books, trades, liquidations, open interest, and funding rates.

## Install

```bash
pip install -e .
```

## Quick Start

```python
import asyncio
from laakhay.data import BinanceProvider, MarketType, Timeframe


async def main():
    async with BinanceProvider(market_type=MarketType.SPOT) as provider:
        candles = await provider.get_candles("BTCUSDT", Timeframe.M1, limit=100)
        print(f"{candles.meta.symbol} bars fetched: {len(candles)}")

        order_book = await provider.get_order_book("BTCUSDT", limit=20)
        print(f"Spread: {order_book.spread_bps:.2f} bps")

        # Streaming helpers use WebSocket under the hood
        async for trade in provider.stream_trades("BTCUSDT"):
            print(f"{trade.symbol} trade value: {trade.value}")
            break  # exit after first update


asyncio.run(main())
```

## Supported Data Types

| Type | REST | WebSocket | Markets |
|------|------|-----------|---------|
| OHLCV Bars | ✅ | ✅ | Spot, Futures |
| Symbols | ✅ | - | Spot, Futures |
| Order Book | ✅ | ✅ | Spot, Futures |
| Trades | ❌ | ✅ | Spot, Futures |
| Liquidations | ❌ | ✅ | Futures |
| Open Interest | ❌ | ✅ | Futures |
| Funding Rates | ❌ | ✅ | Futures |
| Mark Price | ❌ | ✅ | Futures |

> REST coverage currently includes candles, symbol metadata, and order books.

## Key Features

### Order Book Analysis
```python
ob = await provider.get_order_book("BTCUSDT")
print(ob.spread_bps)          # Spread in basis points
print(ob.market_pressure)     # bullish/bearish/neutral
print(ob.imbalance)           # -1.0 to 1.0
print(ob.is_tight_spread)     # < 10 bps
```

### Trade Flow
```python
async for trade in provider.stream_trades("BTCUSDT"):
    print(f"{trade.side}: ${trade.value:.2f} ({trade.size_category})")
    break
```

### Liquidations (Futures)
```python
async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
    async for liq in provider.stream_liquidations():
        if liq.is_large:
            print(f"{liq.symbol}: ${liq.value_usdt:.2f} {liq.side}")
        break
```

### Open Interest (Futures)
```python
async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
    async for oi in provider.stream_open_interest(["BTCUSDT"], period="5m"):
        print(f"OI: {oi.open_interest}")
        break
```

### Funding Rates (Futures)
```python
async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
    async for rate in provider.stream_funding_rate(["BTCUSDT"]):
        print(f"Funding: {rate.funding_rate_percentage:.4f}%")
        break
```


## Architecture

```
laakhay/data/
├── core/           # Base classes, enums, exceptions
├── models/         # Pydantic models (Bar, OHLCV, OrderBook, Trade, etc.)
├── providers/      # Exchange implementations
│   └── binance/    # Binance provider + WebSocket mixin
├── clients/        # High-level clients
└── io/             # REST/WS providers, transports, and clients

## Examples

Run examples from `data/examples/`:

```bash
# REST
python data/examples/binance_rest_ohlcv.py BTCUSDT M1 10 SPOT
python data/examples/binance_rest_order_book.py BTCUSDT 50 SPOT
python data/examples/binance_rest_open_interest.py BTCUSDT current
python data/examples/binance_rest_open_interest.py BTCUSDT hist 5m 100
python data/examples/binance_rest_recent_trades.py BTCUSDT 50 SPOT
python data/examples/binance_rest_funding_rate.py BTCUSDT 50

# WebSocket
python data/examples/binance_ws_ohlcv_multi.py BTCUSDT ETHUSDT M1 SPOT
python data/examples/binance_ws_trades.py BTCUSDT SPOT

# High-level OHLCV Feed
python data/examples/ohlcv_feed_quickstart.py BTCUSDT ETHUSDT M1 SPOT 30
```

**Principles:**
- Async-first (aiohttp, asyncio)
- Type-safe (Pydantic models)
- Explicit APIs
- Comprehensive testing

## Models

All models are immutable Pydantic models with validation:

```python
from laakhay.data.models import (
    Bar,           # Individual OHLCV bar
    OHLCV,         # OHLCV series with metadata
    Symbol,        # Trading pairs
    OrderBook,     # Market depth (25+ properties)
    Trade,         # Individual trades
    Liquidation,   # Forced closures
    OpenInterest,  # Outstanding contracts
    FundingRate,   # Perpetual funding
    MarkPrice,     # Mark/index prices
)
```

## Exception Handling

```python
from laakhay.data.core import (
    LaakhayDataError,      # Base exception
    ProviderError,         # API errors
    InvalidSymbolError,    # Symbol not found
    InvalidIntervalError,  # Invalid interval
)

try:
    ohlcv = await provider.get_candles("INVALID", Timeframe.M1)
except InvalidSymbolError:
    print("Symbol not found")
except ProviderError as e:
    print(f"API error: {e}")
```

## Integration Tests

Integration tests hit the live Binance API and are skipped by default. Enable them explicitly when you have network access and credentials configured:

```bash
RUN_LAAKHAY_NETWORK_TESTS=1 pytest tests/integration
```

## License

MIT License - see [LICENSE](LICENSE)

## Contact

- Issues: [GitHub Issues](https://github.com/laakhay/data/issues)
- Email: laakhay.corp@gmail.com

---

Built by [Laakhay Corporation](https://laakhay.com)
