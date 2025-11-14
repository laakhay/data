"""Coinbase URM mapper.

Handles Coinbase-specific symbol formats:
- Spot: BTC-USD, ETH-USD (hyphenated format, USD only, not USDT)
"""

from __future__ import annotations

from ...core import InstrumentSpec, InstrumentType, MarketType
from ...core.exceptions import SymbolResolutionError


class CoinbaseURM:
    """Coinbase Universal Representation Mapper."""

    def to_spec(
        self,
        exchange_symbol: str,
        *,
        market_type: MarketType,
    ) -> InstrumentSpec:
        """Convert Coinbase symbol to InstrumentSpec.

        Args:
            exchange_symbol: Coinbase symbol (e.g., "BTC-USD")
            market_type: Market type (spot only for Coinbase)

        Returns:
            Canonical InstrumentSpec

        Raises:
            SymbolResolutionError: If symbol cannot be parsed
        """
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

    def to_exchange_symbol(
        self,
        spec: InstrumentSpec,
        *,
        market_type: MarketType,
    ) -> str:
        """Convert InstrumentSpec to Coinbase symbol.

        Args:
            spec: Canonical InstrumentSpec
            market_type: Market type (spot only for Coinbase)

        Returns:
            Coinbase symbol string

        Raises:
            SymbolResolutionError: If spec cannot be converted
        """
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
