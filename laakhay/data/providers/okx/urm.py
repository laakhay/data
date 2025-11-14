"""OKX URM mapper.

Handles OKX-specific symbol formats:
- Spot: BTC-USDT, ETH-USDT (hyphenated format)
- Futures: BTC-USDT-SWAP (perpetual with -SWAP suffix)
"""

from __future__ import annotations

from ...core import InstrumentSpec, InstrumentType, MarketType
from ...core.exceptions import SymbolResolutionError


class OKXURM:
    """OKX Universal Representation Mapper."""

    def to_spec(
        self,
        exchange_symbol: str,
        *,
        market_type: MarketType,
    ) -> InstrumentSpec:
        """Convert OKX symbol to InstrumentSpec.

        Args:
            exchange_symbol: OKX symbol (e.g., "BTC-USDT", "BTC-USDT-SWAP")
            market_type: Market type (spot or futures)

        Returns:
            Canonical InstrumentSpec

        Raises:
            SymbolResolutionError: If symbol cannot be parsed
        """
        symbol_upper = exchange_symbol.upper()

        # Remove -SWAP suffix for futures
        if market_type == MarketType.FUTURES and symbol_upper.endswith("-SWAP"):
            symbol_upper = symbol_upper[:-5]

        # Parse hyphenated format
        if "-" not in symbol_upper:
            raise SymbolResolutionError(
                f"Invalid OKX symbol format: {exchange_symbol}. Expected BASE-QUOTE format",
                exchange="okx",
                value=exchange_symbol,
                market_type=market_type,
            )

        base, quote = symbol_upper.split("-", 1)

        if market_type == MarketType.FUTURES:
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

    def to_exchange_symbol(
        self,
        spec: InstrumentSpec,
        *,
        market_type: MarketType,
    ) -> str:
        """Convert InstrumentSpec to OKX symbol.

        Args:
            spec: Canonical InstrumentSpec
            market_type: Market type (spot or futures)

        Returns:
            OKX symbol string

        Raises:
            SymbolResolutionError: If spec cannot be converted
        """
        symbol = f"{spec.base}-{spec.quote}"

        if market_type == MarketType.FUTURES:
            if spec.instrument_type != InstrumentType.PERPETUAL:
                raise SymbolResolutionError(
                    f"Cannot convert {spec.instrument_type.value} to OKX futures symbol. Only perpetuals supported",
                    exchange="okx",
                    value=str(spec),
                    market_type=market_type,
                )
            return f"{symbol}-SWAP"
        else:
            if spec.instrument_type != InstrumentType.SPOT:
                raise SymbolResolutionError(
                    f"Cannot convert {spec.instrument_type.value} to OKX spot symbol",
                    exchange="okx",
                    value=str(spec),
                    market_type=market_type,
                )
            return symbol
