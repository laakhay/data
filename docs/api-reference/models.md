# Data Models Reference

## Overview

All data models are immutable Pydantic v2 models with validation and computed properties.

## Core Models

### Bar

Individual OHLCV candlestick/bar.

```python
from laakhay.data.models import Bar
from decimal import Decimal
from datetime import datetime

bar = Bar(
    timestamp=datetime.now(),
    open=Decimal("50000"),
    high=Decimal("51000"),
    low=Decimal("49000"),
    close=Decimal("50500"),
    volume=Decimal("100.5"),
    is_closed=True,
)
```

**Fields:**
- `timestamp`: Bar timestamp
- `open`: Opening price
- `high`: Highest price
- `low`: Lowest price
- `close`: Closing price
- `volume`: Trading volume
- `is_closed`: Whether bar is closed

### OHLCV

Time series of OHLCV bars.

```python
from laakhay.data.models import OHLCV, SeriesMeta

ohlcv = OHLCV(
    meta=SeriesMeta(symbol="BTC/USDT", timeframe="1h"),
    bars=[bar1, bar2, bar3],
)
```

**Fields:**
- `meta`: Series metadata (symbol, timeframe)
- `bars`: List of Bar objects (must be sorted by timestamp)

**Properties:**
- `latest`: Latest bar
- `earliest`: Earliest bar
- `start_time`: Start time of series
- `end_time`: End time of series
- `highest_price`: Highest price across all bars
- `lowest_price`: Lowest price across all bars
- `total_volume`: Total volume across all bars

**Methods:**
- `get_bars_in_range(start, end)`: Filter bars by time range
- `get_last_n_bars(n)`: Get last n bars
- `get_closed_bars()`: Get only closed bars
- `get_open_bars()`: Get only open bars
- `append_bar(bar)`: Create new OHLCV with additional bar
- `extend_bars(bars)`: Create new OHLCV with additional bars

### OrderBook

Order book snapshot with computed metrics.

```python
from laakhay.data.models import OrderBook

order_book = OrderBook(
    symbol="BTC/USDT",
    bids=[(price, quantity), ...],
    asks=[(price, quantity), ...],
    timestamp=datetime.now(),
)
```

**Computed Properties:**
- `spread`: Bid-ask spread
- `spread_bps`: Spread in basis points
- `mid_price`: Mid price
- `imbalance`: Order book imbalance (-1.0 to 1.0)
- `market_pressure`: Market pressure (bullish/bearish/neutral)
- `is_tight_spread`: Whether spread is tight (< 10 bps)

### Trade

Individual trade event.

```python
from laakhay.data.models import Trade

trade = Trade(
    symbol="BTC/USDT",
    price=Decimal("50000"),
    quantity=Decimal("0.1"),
    timestamp=datetime.now(),
    side="buy",
    trade_id="12345",
)
```

**Fields:**
- `symbol`: Trading symbol
- `price`: Trade price
- `quantity`: Trade quantity
- `timestamp`: Trade timestamp
- `side`: Trade side ("buy" or "sell")
- `trade_id`: Trade ID

**Properties:**
- `value`: Trade value (price * quantity)
- `is_buy`: Whether trade is a buy
- `is_sell`: Whether trade is a sell

### StreamingBar

Real-time bar update.

```python
from laakhay.data.models import StreamingBar

streaming_bar = StreamingBar(
    symbol="BTC/USDT",
    timestamp=datetime.now(),
    open=Decimal("50000"),
    high=Decimal("51000"),
    low=Decimal("49000"),
    close=Decimal("50500"),
    volume=Decimal("100.5"),
    is_closed=False,
    update_type="update",
)
```

**Fields:**
- All fields from `Bar`
- `update_type`: Update type ("new", "update", "close")

### Liquidation

Liquidation event (futures only).

```python
from laakhay.data.models import Liquidation

liquidation = Liquidation(
    symbol="BTC/USDT",
    price=Decimal("50000"),
    quantity=Decimal("1.0"),
    timestamp=datetime.now(),
    side="long",
    value_usdt=Decimal("50000"),
)
```

**Properties:**
- `is_large`: Whether liquidation is large
- `is_long_liquidation`: Whether it's a long liquidation
- `is_short_liquidation`: Whether it's a short liquidation

### OpenInterest

Open interest data (futures only).

```python
from laakhay.data.models import OpenInterest

oi = OpenInterest(
    symbol="BTC/USDT",
    open_interest=Decimal("1000.5"),
    timestamp=datetime.now(),
)
```

**Properties:**
- `open_interest_value`: Open interest in USD

### FundingRate

Funding rate data (futures only).

```python
from laakhay.data.models import FundingRate

rate = FundingRate(
    symbol="BTC/USDT",
    funding_rate=Decimal("0.0001"),
    timestamp=datetime.now(),
    next_funding_time=datetime.now(),
)
```

**Properties:**
- `funding_rate_percentage`: Funding rate as percentage

### MarkPrice

Mark price data (futures only).

```python
from laakhay.data.models import MarkPrice

mark_price = MarkPrice(
    symbol="BTC/USDT",
    mark_price=Decimal("50000"),
    index_price=Decimal("50010"),
    timestamp=datetime.now(),
)
```

### Symbol

Trading symbol metadata.

```python
from laakhay.data.models import Symbol

symbol = Symbol(
    symbol="BTC/USDT",
    base="BTC",
    quote="USDT",
    exchange="binance",
    market_type="spot",
    status="trading",
)
```

## Event Models

### DataEvent

Generic data event wrapper.

```python
from laakhay.data.models import DataEvent, DataEventType

event = DataEvent(
    type=DataEventType.BAR,
    data=streaming_bar,
    timestamp=datetime.now(),
)
```

### ConnectionEvent

Connection status event.

```python
from laakhay.data.models import ConnectionEvent, ConnectionStatus

event = ConnectionEvent(
    status=ConnectionStatus.CONNECTED,
    exchange="binance",
    timestamp=datetime.now(),
)
```

## Immutability

All models are frozen (immutable). To "modify" a model, create a new instance:

```python
# Create new OHLCV with additional bar
new_ohlcv = ohlcv.append_bar(new_bar)
# Original unchanged
assert ohlcv is not new_ohlcv
```

## Serialization

All models support JSON serialization:

```python
# To dict
data = ohlcv.model_dump()

# To JSON
json_str = ohlcv.model_dump_json()

# From dict
ohlcv = OHLCV.model_validate(data)
```

## See Also

- [Models Architecture](../architecture/models.md) - Design patterns
- [Pydantic Documentation](https://docs.pydantic.dev/) - Framework docs

