"""MEXC URM mapper.

Handles MEXC-specific symbol formats:
- Spot: BTCUSDT, ETHUSDT (standard format)
- Futures: BTCUSDT (perpetual), BTCUSDT_240329 (dated future with delivery date)
"""

from __future__ import annotations

from datetime import datetime

from laakhay.core import BaseURMMapper, InstrumentSpec, InstrumentType, MarketType
from laakhay.core.exceptions import SymbolResolutionError


class MEXCURM(BaseURMMapper):
    """MEXC Universal Representation Mapper."""

    def _to_spec_impl(
        self,
        exchange_symbol: str,
        *,
        market_type: MarketType,
    ) -> InstrumentSpec:
        symbol_upper = exchange_symbol.upper()

        # Handle dated futures (format: BASEQUOTE_YYMMDD)
        if market_type == MarketType.FUTURES and "_" in symbol_upper:
            parts = symbol_upper.split("_", 1)
            if len(parts) == 2 and len(parts[1]) == 6 and parts[1].isdigit():
                base_quote = parts[0]
                date_str = parts[1]
                try:
                    # MEXC uses 2-digit year (YYMMDD)
                    expiry = datetime.strptime(date_str, "%y%m%d")
                    base, quote = self._split_base_quote(base_quote)
                    return InstrumentSpec(
                        base=base,
                        quote=quote,
                        instrument_type=InstrumentType.FUTURE,
                        expiry=expiry,
                    )
                except ValueError:
                    pass

        # Handle perpetual futures or spot
        base, quote = self._split_base_quote(symbol_upper)

        if market_type == MarketType.FUTURES:
            # MEXC futures are typically perpetuals unless they have delivery date
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
            # Dated futures: BASEQUOTE_YYMMDD (2-digit year)
            if spec.instrument_type == InstrumentType.FUTURE and spec.expiry:
                date_str = spec.expiry.strftime("%y%m%d")
                return f"{base_quote}_{date_str}"
            # Perpetual: just BASEQUOTE
            elif spec.instrument_type == InstrumentType.PERPETUAL:
                return base_quote
            else:
                raise SymbolResolutionError(
                    f"Cannot convert {spec.instrument_type.value} to MEXC futures symbol",
                    exchange="mexc",
                    value=str(spec),
                    market_type=market_type,
                )
        else:
            # Spot: just BASEQUOTE
            if spec.instrument_type != InstrumentType.SPOT:
                raise SymbolResolutionError(
                    f"Cannot convert {spec.instrument_type.value} to MEXC spot symbol",
                    exchange="mexc",
                    value=str(spec),
                    market_type=market_type,
                )
            return base_quote
