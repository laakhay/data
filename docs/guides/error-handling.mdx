# Error Handling Guide

## Overview

This guide covers error handling best practices when using the Laakhay Data library.

## Exception Types

### Capability Errors

When a requested feature is not supported:

```python
from laakhay.data.core import CapabilityError

try:
    ohlcv = await api.fetch_ohlcv(
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        exchange="coinbase",
        market_type=MarketType.FUTURES,  # Coinbase doesn't support futures
    )
except CapabilityError as e:
    print(f"Not supported: {e.message}")
    # Check for alternatives
    if e.recommendations:
        alt = e.recommendations[0]
        print(f"Try: {alt.exchange} {alt.market_type.value}")
```

### Rate Limiting

Handle rate limit errors with retry logic:

```python
from laakhay.data.core import RateLimitError
import asyncio

async def fetch_with_retry(api, symbol, timeframe, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await api.fetch_ohlcv(symbol, timeframe, ...)
        except RateLimitError as e:
            if attempt < max_retries - 1:
                print(f"Rate limited, waiting {e.retry_after}s")
                await asyncio.sleep(e.retry_after)
            else:
                raise
```

### Symbol Errors

Handle invalid symbols:

```python
from laakhay.data.core import InvalidSymbolError, SymbolResolutionError

try:
    ohlcv = await api.fetch_ohlcv("INVALID", ...)
except (InvalidSymbolError, SymbolResolutionError) as e:
    print(f"Symbol error: {e}")
    # Try alternative symbol format
    try:
        ohlcv = await api.fetch_ohlcv("urm://binance:btc/usdt:spot", ...)
    except:
        print("Symbol not found in any format")
```

### Provider Errors

Handle general provider errors:

```python
from laakhay.data.core import ProviderError

try:
    ohlcv = await api.fetch_ohlcv(...)
except ProviderError as e:
    print(f"Provider error: {e}")
    if e.status_code:
        print(f"HTTP status: {e.status_code}")
    # Log error, retry, or fallback
```

## Retry Strategies

### Exponential Backoff

```python
import asyncio
from laakhay.data.core import ProviderError, RateLimitError

async def fetch_with_backoff(api, symbol, timeframe, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await api.fetch_ohlcv(symbol, timeframe, ...)
        except (ProviderError, RateLimitError) as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # Exponential backoff
                if isinstance(e, RateLimitError):
                    wait = e.retry_after
                await asyncio.sleep(wait)
            else:
                raise
```

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failures = 0
        self.threshold = failure_threshold
        self.timeout = timeout
        self.last_failure = None
        self.open = False
    
    async def call(self, func, *args, **kwargs):
        if self.open:
            if time.time() - self.last_failure > self.timeout:
                self.open = False
                self.failures = 0
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure = time.time()
            if self.failures >= self.threshold:
                self.open = True
            raise
```

## Error Logging

```python
import logging

logger = logging.getLogger(__name__)

try:
    ohlcv = await api.fetch_ohlcv(...)
except CapabilityError as e:
    logger.warning(f"Capability not supported: {e.message}")
except RateLimitError as e:
    logger.warning(f"Rate limited: retry after {e.retry_after}s")
except ProviderError as e:
    logger.error(f"Provider error: {e}", exc_info=True)
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
```

## Graceful Degradation

```python
async def fetch_data_with_fallback(api, symbol, timeframe):
    exchanges = ["binance", "bybit", "okx"]
    
    for exchange in exchanges:
        try:
            return await api.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                exchange=exchange,
            )
        except (CapabilityError, ProviderError):
            continue
    
    raise Exception("All exchanges failed")
```

## See Also

- [Exceptions Reference](../api-reference/exceptions.md) - Complete exception docs
- [API Reference](../api-reference/data-api.md) - API documentation

