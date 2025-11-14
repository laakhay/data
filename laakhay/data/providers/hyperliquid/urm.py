"""Hyperliquid URM mapper.

Handles Hyperliquid-specific symbol formats:
- Spot: Uses "@{index}" format or "PURR/USDC" format
- Futures: Uses coin names (e.g., "BTC", "ETH") for perpetuals
"""

from __future__ import annotations

from ...core import InstrumentSpec, InstrumentType, MarketType
from ...core.exceptions import SymbolResolutionError


class HyperliquidURM:
    """Hyperliquid Universal Representation Mapper."""

    def to_spec(
        self,
        exchange_symbol: str,
        *,
        market_type: MarketType,
    ) -> InstrumentSpec:
        """Convert Hyperliquid symbol to InstrumentSpec.

        Args:
            exchange_symbol: Hyperliquid symbol (e.g., "BTC" for futures, "BTC/USDC" for spot)
            market_type: Market type (spot or futures)

        Returns:
            Canonical InstrumentSpec

        Raises:
            SymbolResolutionError: If symbol cannot be parsed
        """
        symbol_upper = exchange_symbol.upper()

        if market_type == MarketType.FUTURES:
            # Futures use coin names (e.g., "BTC", "ETH")
            # Assume USDT as quote for perpetuals (Hyperliquid perpetuals are typically USDT-margined)
            return InstrumentSpec(
                base=symbol_upper,
                quote="USDT",
                instrument_type=InstrumentType.PERPETUAL,
            )
        else:
            # Spot can be BASE/QUOTE format or @{index} format
            if "/" in symbol_upper:
                base, quote = symbol_upper.split("/", 1)
                return InstrumentSpec(
                    base=base,
                    quote=quote,
                    instrument_type=InstrumentType.SPOT,
                )
            elif symbol_upper.startswith("@"):
                # Index format - cannot determine base/quote without metadata
                raise SymbolResolutionError(
                    f"Cannot parse Hyperliquid index symbol '{exchange_symbol}' without metadata. Use BASE/QUOTE format",
                    exchange="hyperliquid",
                    value=exchange_symbol,
                    market_type=market_type,
                )
            else:
                # Assume single coin name, default to USDC quote for spot
                return InstrumentSpec(
                    base=symbol_upper,
                    quote="USDC",
                    instrument_type=InstrumentType.SPOT,
                )

    def to_exchange_symbol(
        self,
        spec: InstrumentSpec,
        *,
        market_type: MarketType,
    ) -> str:
        """Convert InstrumentSpec to Hyperliquid symbol.

        Args:
            spec: Canonical InstrumentSpec
            market_type: Market type (spot or futures)

        Returns:
            Hyperliquid symbol string

        Raises:
            SymbolResolutionError: If spec cannot be converted
        """
        if market_type == MarketType.FUTURES:
            if spec.instrument_type != InstrumentType.PERPETUAL:
                raise SymbolResolutionError(
                    f"Cannot convert {spec.instrument_type.value} to Hyperliquid futures symbol. Only perpetuals supported",
                    exchange="hyperliquid",
                    value=str(spec),
                    market_type=market_type,
                )
            # Futures use just the base coin name
            return spec.base
        else:
            if spec.instrument_type != InstrumentType.SPOT:
                raise SymbolResolutionError(
                    f"Cannot convert {spec.instrument_type.value} to Hyperliquid spot symbol",
                    exchange="hyperliquid",
                    value=str(spec),
                    market_type=market_type,
                )
            # Spot uses BASE/QUOTE format
            return f"{spec.base}/{spec.quote}"
