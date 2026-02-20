"""Bybit URM mapper.

Handles Bybit-specific symbol formats:
- Spot: BTCUSDT, ETHUSDT (standard format)
- Futures: BTCUSDT (perpetual)
"""

from __future__ import annotations

from laakhay.core import BaseURMMapper, InstrumentSpec, InstrumentType, MarketType
from laakhay.core.exceptions import SymbolResolutionError


class BybitURM(BaseURMMapper):
    """Bybit Universal Representation Mapper."""

    def _to_spec_impl(
        self,
        exchange_symbol: str,
        *,
        market_type: MarketType,
    ) -> InstrumentSpec:
        symbol_upper = exchange_symbol.upper()
        base, quote = self._split_base_quote(symbol_upper)

        if market_type == MarketType.FUTURES:
            # Bybit futures are perpetuals
            return InstrumentSpec(
                base=base,
                quote=quote,
                instrument_type=InstrumentType.PERPETUAL,
            )
        else:
            return InstrumentSpec(
                base=base,
                quote=quote,
                instrument_type=InstrumentType.SPOT,
            )

    def _to_exchange_symbol_impl(
        self,
        spec: InstrumentSpec,
        *,
        market_type: MarketType,
    ) -> str:
        base_quote = f"{spec.base}{spec.quote}"

        if market_type == MarketType.FUTURES:
            if spec.instrument_type != InstrumentType.PERPETUAL:
                raise SymbolResolutionError(
                    f"Cannot convert {spec.instrument_type.value} to Bybit futures symbol. "
                    "Only perpetuals supported",
                    exchange="bybit",
                    value=str(spec),
                    market_type=market_type,
                )
            return base_quote
        else:
            if spec.instrument_type != InstrumentType.SPOT:
                raise SymbolResolutionError(
                    f"Cannot convert {spec.instrument_type.value} to Bybit spot symbol",
                    exchange="bybit",
                    value=str(spec),
                    market_type=market_type,
                )
            return base_quote
