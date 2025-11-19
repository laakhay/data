# URM (Universal Representation Mapping) Guide

## Why URM?

Every exchange uses different symbol formats. URM provides a canonical
representation so applications can store and compare symbols without worrying
about exchange quirks.

## Canonical Format

```
urm://{exchange|*}:{base}/{quote}:{instrument_type}[:qualifiers]
```

- Exchange: specific exchange or `*` for wildcard
- Base/Quote: normalized asset codes
- Instrument type: `spot`, `perpetual`, `future`, etc.
- Qualifiers: e.g., expiry date for futures/options

## Basic Usage

```python
from laakhay.data.core.urm import get_urm_registry
from laakhay.data.core.enums import MarketType

registry = get_urm_registry()

# Exchange → canonical
spec = registry.urm_to_spec("BTCUSDT", exchange="binance", market_type=MarketType.SPOT)
print(spec.base, spec.quote)  # BTC USDT

# Canonical → exchange
symbol = registry.urm_to_exchange_symbol(spec, exchange="kraken", market_type=MarketType.SPOT)
print(symbol)  # XBT/USD
```

## Storing Symbols

- Prefer URM IDs when persisting symbols. Example:
  `urm://binance:btc/usdt:spot`.
- Use `spec.to_urm()` (when available) or build the ID from `InstrumentSpec`.

## Extra Tips

- URM registry caches conversions for 5 minutes. For long-lived processes,
  ensure provider registration occurs before conversions.
- When adding a provider, implement its mapper carefully (handle spot/futures
  differences, contract codes, etc.).
- For wildcard alerts/strategies, store URM IDs with `exchange=*` to signal that
  any exchange matching the base/quote pair is acceptable.
