# Capability System

## Goals

- Describe which exchanges support which features (REST vs WS, spot vs futures).
- Fail fast with actionable errors when a capability is unavailable.
- Provide metadata so applications can tailor UX or fallbacks.

## Structure

Capabilities are stored hierarchically:

```
Exchange → MarketType → InstrumentType → Feature → Transport → CapabilityStatus
```

Each `CapabilityStatus` includes:
- `supported`: bool
- `reason`: optional text
- `source`: `static` or `runtime`
- `recommendations`: alternative capability keys

## Usage

- **Validation**: `CapabilityService.validate_request(request)` raises
  `CapabilityError` before routing when unsupported.
- **Introspection**: helper functions `supports`, `is_exchange_supported`,
  `get_exchange_capability` expose capability data to consumers.
- **Documentation**: capability tables feed API/UX docs so users know what is
  available per exchange.

## Maintenance

- Update `core/capabilities.py` whenever providers gain/lose support for a
  feature.
- For dynamic capabilities (e.g., temporary outages), future work may include
  runtime overrides sourced from config or health checks.
