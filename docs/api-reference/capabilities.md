# Capability & URM Reference

## Capability Helpers

Located in `laakhay.data.core.capabilities`.

### supports

```python
from laakhay.data.core.capabilities import supports
from laakhay.data.core import DataFeature, TransportKind, MarketType

status = supports(
    feature=DataFeature.OHLCV,
    transport=TransportKind.WS,
    exchange="binance",
    market_type=MarketType.SPOT,
)
```

Returns `CapabilityStatus` with fields:
- `supported`: bool
- `reason`: optional string
- `source`: `"static"` or `"runtime"`
- `recommendations`: list of alternative capability keys

### is_exchange_supported

```python
from laakhay.data.core.capabilities import is_exchange_supported

if not is_exchange_supported("hyperliquid"):
    ...
```

### get_exchange_capability

Retrieve the full capability entry for introspection (e.g., building UI).

```python
from laakhay.data.core.capabilities import get_exchange_capability

cap = get_exchange_capability("binance")
```

## CapabilityStatus Object

Expose additional metadata (e.g., stream variants, notes) so consumers can
provide better UX. Check `status.recommendations` for fallback suggestions.

## URM Utilities

Located in `laakhay.data.core.urm`.

### get_urm_registry

```python
from laakhay.data.core.urm import get_urm_registry
from laakhay.data.core.enums import MarketType

registry = get_urm_registry()
spec = registry.urm_to_spec("BTCUSDT", exchange="binance", market_type=MarketType.SPOT)
symbol = registry.urm_to_exchange_symbol(spec, exchange="bybit", market_type=MarketType.FUTURES)
```

### UniversalRepresentationMapper Protocol

Implement `to_spec` and `to_exchange_symbol` when adding new providers. See
[Provider development guide](../internals/provider-development.md).

### URM IDs

Canonical URM ID format: `urm://{exchange|*}:{base}/{quote}:{instrument_type}[:qualifiers]`.

Use URM IDs when storing symbols in databases to avoid ambiguity.
