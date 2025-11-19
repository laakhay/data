# Laakhay Data

**Beta-stage async-first cryptocurrency market data aggregation library.**

> ⚠️ **Beta Software**: This library is in active development. Use with caution in production environments. APIs may change between versions.

Unified API for multi-exchange market data with support for **Binance**, **Bybit**, **OKX**, **Hyperliquid**, **Kraken**, and **Coinbase**. Modular provider architecture with REST/WebSocket abstraction, type-safe Pydantic models, and high-level streaming feeds.

## Installation

```bash
pip install laakhay-data
```

## Quick Start

```python
import asyncio
from laakhay.data.core import DataAPI, MarketType, Timeframe

async def main():
    async with DataAPI() as api:
        # Fetch OHLCV data
        ohlcv = await api.fetch_ohlcv(
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            exchange="binance",
            market_type=MarketType.SPOT,
            limit=100,
        )
        print(f"Fetched {len(ohlcv)} bars")
        
        # Stream real-time trades
        async for trade in api.stream_trades(
            symbol="BTCUSDT",
            exchange="binance",
            market_type=MarketType.SPOT,
        ):
            print(f"{trade.symbol}: ${trade.price} ({trade.side})")
            break

asyncio.run(main())
```

## Supported Exchanges

| Exchange | Spot | Futures | REST | WebSocket |
|----------|------|---------|------|-----------|
| **Binance** | ✅ | ✅ | ✅ | ✅ |
| **Bybit** | ✅ | ✅ | ✅ | ✅ |
| **OKX** | ✅ | ✅ | ✅ | ✅ |
| **Hyperliquid** | ❌ | ✅ | ✅ | ✅ |
| **Kraken** | ✅ | ✅ | ✅ | ✅ |
| **Coinbase** | ✅ | ❌ | ✅ | ✅ |

## Data Types

| Type | REST | WebSocket | Markets |
|------|------|-----------|---------|
| **OHLCV Bars** | ✅ | ✅ | Spot, Futures |
| **Order Book** | ✅ | ✅ | Spot, Futures |
| **Trades** | ✅ | ✅ | Spot, Futures |
| **Liquidations** | ❌ | ✅ | Futures |
| **Open Interest** | ✅ | ✅ | Futures |
| **Funding Rates** | ✅ | ✅ | Futures |
| **Mark Price** | ❌ | ✅ | Futures |
| **Symbol Metadata** | ✅ | ❌ | Spot, Futures |

## Key Features

- **Unified DataAPI**: Single interface across all exchanges
- **Universal Symbol Mapping (URM)**: Use any symbol format
- **Capability Discovery**: Check feature support before requests
- **Type-Safe Models**: Immutable Pydantic v2 models
- **High-Level Feeds**: OHLCV, liquidation, and open interest feeds
- **Stream Relay**: Forward streams to Redis, Kafka, or custom sinks

## Documentation

Comprehensive documentation is available in the [`docs/`](./docs/) directory:

- **[Getting Started](./docs/guides/getting-started.md)** - Quick start guide
- **[Examples](./docs/examples/)** - Code examples for common use cases
- **[API Reference](./docs/api-reference/)** - Complete API documentation
- **[Architecture](./docs/architecture/)** - System architecture and design decisions
- **[Guides](./docs/guides/)** - Usage guides and best practices

See the [Documentation Index](./docs/INDEX.md) for complete navigation.

## Requirements

- Python 3.12+
- `pydantic>=2.0`
- `aiohttp>=3.8`
- `websockets>=10`

## License

MIT License - see [LICENSE](LICENSE)

---

Built by [Laakhay Corporation](https://laakhay.com)
