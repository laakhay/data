"""Bybit URM mapper.

Handles Bybit-specific symbol formats:
- Spot: BTCUSDT, ETHUSDT (standard format)
- Futures: BTCUSDT (perpetual)
"""

from __future__ import annotations

from ...core import InstrumentSpec, InstrumentType, MarketType
from ...core.exceptions import SymbolResolutionError


class BybitURM:
    """Bybit Universal Representation Mapper."""

    def to_spec(
        self,
        exchange_symbol: str,
        *,
        market_type: MarketType,
    ) -> InstrumentSpec:
        """Convert Bybit symbol to InstrumentSpec.

        Args:
            exchange_symbol: Bybit symbol (e.g., "BTCUSDT")
            market_type: Market type (spot or futures)

        Returns:
            Canonical InstrumentSpec

        Raises:
            SymbolResolutionError: If symbol cannot be parsed
        """
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

    def to_exchange_symbol(
        self,
        spec: InstrumentSpec,
        *,
        market_type: MarketType,
    ) -> str:
        """Convert InstrumentSpec to Bybit symbol.

        Args:
            spec: Canonical InstrumentSpec
            market_type: Market type (spot or futures)

        Returns:
            Bybit symbol string

        Raises:
            SymbolResolutionError: If spec cannot be converted
        """
        base_quote = f"{spec.base}{spec.quote}"

        if market_type == MarketType.FUTURES:
            if spec.instrument_type != InstrumentType.PERPETUAL:
                raise SymbolResolutionError(
                    f"Cannot convert {spec.instrument_type.value} to Bybit futures symbol. Only perpetuals supported",
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

    def _split_base_quote(self, symbol: str) -> tuple[str, str]:
        """Split symbol into base and quote."""
        quote_assets = [
            "USDT",
            "USD",
            "BTC",
            "ETH",
            "BNB",
            "BUSD",
            "DAI",
            "USDC",
            "TUSD",
            "USDP",
        ]

        for quote in quote_assets:
            if symbol.endswith(quote):
                base = symbol[: -len(quote)]
                if base:
                    return base, quote

        if len(symbol) >= 6:
            return symbol[:-4], symbol[-4:]
        elif len(symbol) >= 4:
            return symbol[:-3], symbol[-3:]
        else:
            raise SymbolResolutionError(
                f"Cannot split Bybit symbol '{symbol}' into base/quote",
                exchange="bybit",
                value=symbol,
            )
