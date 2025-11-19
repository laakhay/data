# Exceptions Reference

## Exception Hierarchy

```
DataError (base)
├── CapabilityError
├── ProviderError
│   ├── RateLimitError
│   ├── InvalidSymbolError
│   └── InvalidIntervalError
├── ValidationError
├── SymbolResolutionError
└── RelayError
```

## DataError

Base exception for all library errors.

```python
from laakhay.data.core import DataError

try:
    # Some operation
    pass
except DataError as e:
    print(f"Library error: {e}")
```

## CapabilityError

Raised when a requested capability is not supported.

```python
from laakhay.data.core import CapabilityError

try:
    ohlcv = await api.fetch_ohlcv(
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        exchange="coinbase",
        market_type=MarketType.FUTURES,  # Not supported
    )
except CapabilityError as e:
    print(f"Not supported: {e.message}")
    print(f"Key: {e.key}")
    print(f"Status: {e.status}")
    print(f"Recommendations: {e.recommendations}")
```

**Attributes:**
- `message`: Error message
- `key`: CapabilityKey identifying the capability
- `status`: CapabilityStatus with details
- `recommendations`: List of FallbackOption suggestions

## ProviderError

Base exception for provider-specific errors.

```python
from laakhay.data.core import ProviderError

try:
    ohlcv = await api.fetch_ohlcv(...)
except ProviderError as e:
    print(f"Provider error: {e}")
    print(f"Status code: {e.status_code}")
```

**Attributes:**
- `message`: Error message
- `status_code`: HTTP status code (if applicable)

## RateLimitError

Raised when rate limit is exceeded.

```python
from laakhay.data.core import RateLimitError

try:
    ohlcv = await api.fetch_ohlcv(...)
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
    print(f"Retry after: {e.retry_after} seconds")
```

**Attributes:**
- `message`: Error message
- `status_code`: Always 429
- `retry_after`: Seconds to wait before retrying

## InvalidSymbolError

Raised when symbol does not exist or is not tradeable.

```python
from laakhay.data.core import InvalidSymbolError

try:
    ohlcv = await api.fetch_ohlcv("INVALID", ...)
except InvalidSymbolError:
    print("Symbol not found")
```

## InvalidIntervalError

Raised when timeframe is not supported.

```python
from laakhay.data.core import InvalidIntervalError

try:
    ohlcv = await api.fetch_ohlcv(..., timeframe="invalid")
except InvalidIntervalError:
    print("Timeframe not supported")
```

## ValidationError

Raised when data validation fails.

```python
from laakhay.data.core import ValidationError

try:
    # Invalid data
    pass
except ValidationError as e:
    print(f"Validation error: {e}")
```

## SymbolResolutionError

Raised when URM cannot resolve a symbol.

```python
from laakhay.data.core import SymbolResolutionError

try:
    ohlcv = await api.fetch_ohlcv("invalid_symbol", ...)
except SymbolResolutionError as e:
    print(f"Symbol resolution error: {e}")
    print(f"Exchange: {e.exchange}")
    print(f"Value: {e.value}")
    print(f"Market type: {e.market_type}")
```

**Attributes:**
- `message`: Error message
- `exchange`: Exchange name
- `value`: Symbol value that failed
- `market_type`: Market type
- `known_aliases`: Dictionary of known aliases

## RelayError

Raised by StreamRelay when a sink fails repeatedly.

```python
from laakhay.data.core import RelayError

try:
    await relay.relay(request)
except RelayError as e:
    print(f"Relay error: {e}")
    print(f"Sink: {e.sink_name}")
    print(f"Failures: {e.consecutive_failures}")
```

**Attributes:**
- `message`: Error message
- `sink_name`: Name of failing sink
- `consecutive_failures`: Number of consecutive failures

## Error Handling Best Practices

### Catch Specific Exceptions

```python
try:
    ohlcv = await api.fetch_ohlcv(...)
except CapabilityError:
    # Handle unsupported capability
    pass
except RateLimitError as e:
    # Handle rate limiting
    await asyncio.sleep(e.retry_after)
except ProviderError:
    # Handle provider errors
    pass
```

### Use Exception Context

```python
try:
    ohlcv = await api.fetch_ohlcv(...)
except CapabilityError as e:
    if e.recommendations:
        # Try alternative
        alt = e.recommendations[0]
        ohlcv = await api.fetch_ohlcv(
            exchange=alt.exchange,
            ...
        )
```

## See Also

- [Core Exceptions](../../laakhay/data/core/exceptions.py) - Implementation
- [Error Handling Guide](../guides/error-handling.md) - Best practices

