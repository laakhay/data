# Laakhay Data

**Professional Python library for cryptocurrency market data.**

Async-first, type-safe wrapper for exchange APIs. Supports candles, order books, trades, liquidations, open interest, funding rates, and more.

## Install

```bash
pip install -e .
```

## Quick Start

```python
import asyncio
from laakhay.data.providers.binance import BinanceProvider
from laakhay.data.core import Timeframe, MarketType

async def main():
    # Spot market
    async with BinanceProvider(market_type=MarketType.SPOT) as provider:
        # OHLCV Bars
        candles = await provider.get_candles("BTCUSDT", Timeframe.M1, limit=100)
        
        # Order book
        ob = await provider.get_order_book("BTCUSDT", limit=20)
        print(f"Spread: {ob.spread_bps:.2f} bps, Pressure: {ob.market_pressure}")
        
        # Recent trades
        trades = await provider.get_recent_trades("BTCUSDT", limit=100)
        print(f"Buy volume: {sum(t.value for t in trades if t.is_buy)}")

asyncio.run(main())
```

## Supported Data Types

| Type | REST | WebSocket | Markets |
|------|------|-----------|---------|
| OHLCV Bars | ✅ | ✅ | Spot, Futures |
| Symbols | ✅ | - | Spot, Futures |
| Order Book | ✅ | ✅ | Spot, Futures |
| Trades | ✅ | ✅ | Spot, Futures |
| Liquidations | - | ✅ | Futures |
| Open Interest | ✅ | ✅ | Futures |
| Funding Rates | ✅ | ✅ | Futures |
| Mark Price | - | ✅ | Futures |

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
trades = await provider.get_recent_trades("BTCUSDT")
for trade in trades:
    print(f"{trade.side}: ${trade.value:.2f} ({trade.size_category})")
```

### Liquidations (Futures)
```python
async with BinanceProvider(market_type=MarketType.FUTURES) as provider:
    async for liq in provider.stream_liquidations():
        if liq.is_large:
            print(f"{liq.symbol}: ${liq.value_usdt:.2f} {liq.side}")
```

### Open Interest (Futures)
```python
oi_list = await provider.get_open_interest("BTCUSDT", historical=True)
async for oi in provider.stream_open_interest(["BTCUSDT"], period="5m"):
    print(f"OI: {oi.open_interest}")
```

### Funding Rates (Futures)
```python
# Historical (applied rates)
rates = await provider.get_funding_rate("BTCUSDT", limit=10)

# Real-time (predicted rates)
async for rate in provider.stream_funding_rate(["BTCUSDT"]):
    print(f"Funding: {rate.funding_rate_percentage:.4f}%")
```


## Architecture

```
laakhay/data/
├── core/           # Base classes, enums, exceptions
├── models/         # Pydantic models (Bar, OHLCV, OrderBook, Trade, etc.)
├── providers/      # Exchange implementations
│   └── binance/    # Binance provider + WebSocket mixin
├── clients/        # High-level clients
└── utils/          # HTTP, retry, WebSocket utilities
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
    candles = await provider.get_candles("INVALID", Timeframe.M1)
except InvalidSymbolError:
    print("Symbol not found")
except ProviderError as e:
    print(f"API error: {e}")
```

## License

MIT License - see [LICENSE](LICENSE)

## Contact

- Issues: [GitHub Issues](https://github.com/laakhay/data/issues)
- Email: laakhay.corp@gmail.com

---

Built by [Laakhay Corporation](https://laakhay.com)
