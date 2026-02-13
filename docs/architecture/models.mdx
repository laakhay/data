# Data Models Architecture

## Overview

The `models/` directory contains all Pydantic v2 data models used throughout the library. These models provide type-safe, validated representations of market data with immutable semantics.

## Design Principles

### Immutability
All models are frozen (`frozen=True` in Pydantic config), ensuring:
- Data integrity: Models cannot be accidentally modified
- Thread safety: Immutable objects are safe to share across threads
- Functional style: Operations return new instances

### Type Safety
- Pydantic v2 validation ensures data correctness
- Type hints throughout for IDE support and static analysis
- Decimal for financial calculations (precision)

### Computed Properties
Many models provide computed properties for derived metrics:
- OrderBook: Spread, imbalance, market pressure
- OHLCV: Highest/lowest price, total volume
- Liquidation: Large liquidation detection

## Model Categories

### Market Data Models

#### Bar
Individual OHLCV candlestick/bar with:
- OHLC prices (Decimal for precision)
- Volume
- Timestamp
- Closed/open status

#### OHLCV
Time series of bars with:
- Series metadata (symbol, timeframe)
- List of bars (sorted by timestamp)
- Computed properties (price statistics, time ranges)
- Convenience methods (filtering, selection)

#### OrderBook
Order book snapshot with:
- Bids and asks (price/quantity pairs)
- Computed metrics: spread, imbalance, market pressure
- Depth management

#### Trade
Individual trade event with:
- Price, quantity, timestamp
- Side (buy/sell)
- Trade ID

### Derivatives Models

#### Liquidation
Liquidation event with:
- Symbol, price, quantity
- Side (long/short)
- Large liquidation detection

#### OpenInterest
Open interest data with:
- Symbol, value, timestamp
- Historical tracking

#### FundingRate
Funding rate data with:
- Symbol, rate, timestamp
- Next funding time

#### MarkPrice
Mark price data with:
- Symbol, price, timestamp
- Index price reference

### Metadata Models

#### Symbol
Trading symbol metadata:
- Symbol name, base, quote
- Exchange, market type
- Status, precision

#### SeriesMeta
Series metadata:
- Symbol, timeframe
- Exchange, market type

### Event Models

#### DataEvent
Generic data event wrapper:
- Event type
- Payload (any model)
- Timestamp

#### ConnectionEvent
Connection status events:
- Status (connected, disconnected, error)
- Exchange, timestamp
- Error details

### Streaming Models

#### StreamingBar
Real-time bar updates:
- Extends Bar with streaming-specific fields
- Update type (new, update, close)

## Usage Patterns

### Creating Models

```python
from laakhay.data.models import Bar, OHLCV, SeriesMeta
from decimal import Decimal
from datetime import datetime

# Create a bar
bar = Bar(
    timestamp=datetime.now(),
    open=Decimal("50000"),
    high=Decimal("51000"),
    low=Decimal("49000"),
    close=Decimal("50500"),
    volume=Decimal("100.5"),
    is_closed=True
)

# Create OHLCV series
meta = SeriesMeta(symbol="BTC/USDT", timeframe="1h")
ohlcv = OHLCV(meta=meta, bars=[bar])
```

### Immutability Pattern

```python
# "Modification" returns new instance
new_ohlcv = ohlcv.append_bar(new_bar)
# Original unchanged
assert ohlcv is not new_ohlcv
```

### Computed Properties

```python
# Access computed metrics
spread = order_book.spread
highest = ohlcv.highest_price
total_vol = ohlcv.total_volume
```

## Validation

Pydantic validators ensure data integrity:
- OHLCV: Bars must be sorted by timestamp
- OrderBook: Bids/asks must be sorted correctly
- Type validation: All fields validated on creation

## Serialization

All models support:
- JSON serialization via Pydantic
- Dictionary conversion
- Custom serialization methods where needed

## See Also

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Core enums source](../../laakhay/data/core/enums.py) - InstrumentSpec, Timeframe, etc.
- [API surface summary](../api.md) - Where models appear in the API
