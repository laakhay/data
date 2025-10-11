# Laakhay Data

**Minimal, professional Python library for fetching market data.**

A thin, explicit wrapper around exchange APIs with type-safe models and async support. Built for microservices that need clean access to OHLCV candles and trading pairs.

## Features

- [X] **Async/await** - Non-blocking I/O with `aiohttp`
- [X] **Type-safe** - Pydantic models with validation
- [X] **Explicit** - No magic, clear interfaces
- [X] **Tested** - 33 tests (30 unit + 3 integration)
- [X] **Extensible** - Easy to add new exchanges

## Installation

```bash
pip install laakhay-data
```

## Quick Start

### Fetch OHLCV Candles

```python
import asyncio
from laakhay.data.providers import BinanceProvider
from laakhay.data.core import TimeInterval

async def main():
    async with BinanceProvider() as provider:
        # Fetch last 100 1-minute candles for BTCUSDT
        candles = await provider.get_candles(
            symbol="BTCUSDT",
            interval=TimeInterval.M1,
            limit=100
        )
      
        for candle in candles:
            print(f"{candle.timestamp}: O={candle.open} H={candle.high} L={candle.low} C={candle.close}")

asyncio.run(main())
```

### Fetch Trading Symbols

```python
async def main():
    async with BinanceProvider() as provider:
        symbols = await provider.get_symbols()
      
        # Filter for USDT pairs
        usdt_pairs = [s for s in symbols if s.quote_asset == "USDT"]
        print(f"Found {len(usdt_pairs)} USDT trading pairs")

asyncio.run(main())
```

### Time Range Queries

```python
from datetime import datetime, timedelta

async def main():
    async with BinanceProvider() as provider:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
      
        candles = await provider.get_candles(
            symbol="ETHUSDT",
            interval=TimeInterval.H1,
            start_time=start_time,
            end_time=end_time
        )
      
        print(f"Fetched {len(candles)} hourly candles for last 24h")

asyncio.run(main())
```

## API Reference

### BinanceProvider

```python
from laakhay.data.providers import BinanceProvider

# Initialize (no credentials needed for public data)
provider = BinanceProvider()

# With credentials (for private endpoints - future)
provider = BinanceProvider(
    api_key="your_api_key",
    api_secret="your_api_secret"
)
```

#### Methods

##### `get_candles(symbol, interval, start_time=None, end_time=None, limit=None)`

Fetch OHLCV candlestick data.

**Parameters:**

- `symbol` (str): Trading pair (e.g., "BTCUSDT")
- `interval` (TimeInterval): Candle interval (M1, M5, H1, D1, etc.)
- `start_time` (datetime, optional): Start timestamp
- `end_time` (datetime, optional): End timestamp
- `limit` (int, optional): Max candles to return (default/max: 1000)

**Returns:** `List[Candle]`

##### `get_symbols()`

Fetch all available trading pairs.

**Returns:** `List[Symbol]`

### TimeInterval

Available intervals:

```python
from laakhay.data.core import TimeInterval

# Minutes
TimeInterval.M1   # 1 minute
TimeInterval.M3   # 3 minutes
TimeInterval.M5   # 5 minutes
TimeInterval.M15  # 15 minutes
TimeInterval.M30  # 30 minutes

# Hours
TimeInterval.H1   # 1 hour
TimeInterval.H2   # 2 hours
TimeInterval.H4   # 4 hours
TimeInterval.H6   # 6 hours
TimeInterval.H8   # 8 hours
TimeInterval.H12  # 12 hours

# Days/Weeks/Months
TimeInterval.D1   # 1 day
TimeInterval.D3   # 3 days
TimeInterval.W1   # 1 week
TimeInterval.MO1  # 1 month
```

### Models

#### Candle

```python
from laakhay.data.models import Candle

candle.symbol      # str: "BTCUSDT"
candle.timestamp   # datetime: UTC timestamp
candle.open        # Decimal: Opening price
candle.high        # Decimal: Highest price
candle.low         # Decimal: Lowest price
candle.close       # Decimal: Closing price
candle.volume      # Decimal: Trading volume
```

#### Symbol

```python
from laakhay.data.models import Symbol

symbol.symbol       # str: "BTCUSDT"
symbol.base_asset   # str: "BTC"
symbol.quote_asset  # str: "USDT"
```

## Error Handling

```python
from laakhay.data.core import (
    DataError,              # Base exception
    ProviderError,          # API errors
    RateLimitError,         # Rate limit exceeded
    InvalidSymbolError,     # Symbol not found
    InvalidIntervalError,   # Interval not supported
    ValidationError,        # Data validation failed
)

async def main():
    provider = BinanceProvider()
  
    try:
        candles = await provider.get_candles("INVALID", TimeInterval.M1)
    except InvalidSymbolError as e:
        print(f"Symbol error: {e}")
    except RateLimitError as e:
        print(f"Rate limited, retry after {e.retry_after}s")
    except ProviderError as e:
        print(f"Provider error: {e} (status: {e.status_code})")
    finally:
        await provider.close()
```

## Architecture

```
laakhay/data/
├── core/           # Base classes, enums, exceptions
├── models/         # Pydantic data models (Candle, Symbol)
├── providers/      # Exchange implementations (Binance, ...)
└── utils/          # HTTP client, retry logic
```

**Design principles:**

- **Explicit over implicit** - Direct imports, clear interfaces
- **Async-first** - Non-blocking I/O for performance
- **Type-safe** - Pydantic validation, strict typing
- **Minimal** - No unnecessary abstractions

## Development

### Setup

```bash
git clone https://github.com/laakhay/data.git
cd laakhay-data
pip install -e ".[dev]"
```

### Run Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires internet)
pytest tests/integration/ -v

# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=laakhay.data --cov-report=term-missing
```

### Code Quality

```bash
# Format
black laakhay/ tests/

# Lint
ruff check laakhay/ tests/

# Type check
mypy laakhay/
```

## Roadmap

- [X] Binance provider (spot market)
- [ ] Additional exchanges (Coinbase, Kraken, etc.)
- [ ] WebSocket streaming support
- [ ] Historical data export
- [ ] Advanced retry strategies

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/laakhay/data/issues)
- **Email**: laakhay.corp@gmail.com
- **Website**: [laakhay.com](https://laakhay.com)

---

Built with ♥︎ by [Laakhay Corporation](https://laakhay.com)
