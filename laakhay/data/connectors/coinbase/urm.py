"""Coinbase URM mapper.

Handles Coinbase-specific symbol formats:
- Spot: BTC-USD, ETH-USD (hyphenated format, USD only, not USDT)
"""

from __future__ import annotations

from laakhay.core import BaseURMMapper, InstrumentSpec, InstrumentType, MarketType
from laakhay.core.exceptions import SymbolResolutionError


class CoinbaseURM(BaseURMMapper):
    """Coinbase Universal Representation Mapper."""

    def _to_spec_impl(
        self,
        exchange_symbol: str,
        *,
        market_type: MarketType,
    ) -> InstrumentSpec:
        if market_type != MarketType.SPOT:
            raise SymbolResolutionError(
                "Coinbase only supports spot markets",
                exchange="coinbase",
                value=exchange_symbol,
                market_type=market_type,
            )

        symbol_upper = exchange_symbol.upper()

        # Parse hyphenated format
        if "-" not in symbol_upper:
            raise SymbolResolutionError(
                f"Invalid Coinbase symbol format: {exchange_symbol}. Expected BASE-USD format",
                exchange="coinbase",
                value=exchange_symbol,
                market_type=market_type,
            )

        base, quote = symbol_upper.split("-", 1)

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
        if market_type != MarketType.SPOT:
            raise SymbolResolutionError(
                "Coinbase only supports spot markets",
                exchange="coinbase",
                value=str(spec),
                market_type=market_type,
            )

        if spec.instrument_type != InstrumentType.SPOT:
            raise SymbolResolutionError(
                f"Cannot convert {spec.instrument_type.value} to Coinbase symbol. Only spot supported",
                exchange="coinbase",
                value=str(spec),
                market_type=market_type,
            )

        # Coinbase only supports USD pairs, not USDT
        if spec.quote == "USDT":
            raise SymbolResolutionError(
                "Coinbase only supports USD pairs, not USDT",
                exchange="coinbase",
                value=str(spec),
                market_type=market_type,
            )

        return f"{spec.base}-{spec.quote}"
