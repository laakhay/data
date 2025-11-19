# URM System

## Overview

The Universal Representation Mapping (URM) system normalizes symbols across
exchanges. It ensures that users can work with canonical identifiers while the
library handles exchange-specific quirks.

## Key Concepts

- **Canonical format**: `BASE/QUOTE` plus instrument type and optional
  qualifiers, exposed via URM IDs (`urm://exchange:base/quote:instrument`).
- **InstrumentSpec**: structured object describing base, quote, instrument type,
  expiry/strike, etc.
- **Mappers**: each provider supplies a `UniversalRepresentationMapper`
  implementation translating between exchange-native symbols and
  `InstrumentSpec`.

## Registry

`URMRegistry` maintains mapper registrations and caches results for 5 minutes to
avoid repeated parsing. It exposes:
- `register(exchange, mapper)`
- `urm_to_spec(exchange_symbol, exchange, market_type)`
- `urm_to_exchange_symbol(spec, exchange, market_type)`

## Usage

- DataRouter automatically resolves symbols before invoking providers.
- Advanced users can call the registry directly (see [URM guide](../guides/urm.md)).
- Persist URM IDs in databases to remain resilient to exchange ticker changes.
