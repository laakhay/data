"""Binance URM mapper.

Handles Binance-specific symbol formats:
- Spot: BTCUSDT, ETHUSDT (standard format)
- Futures: BTCUSDT (perpetual), BTCUSDT_240329 (dated future with delivery date)
"""

from __future__ import annotations

from datetime import datetime

from ...core import InstrumentSpec, InstrumentType, MarketType
from ...core.exceptions import SymbolResolutionError


class BinanceURM:
    """Binance Universal Representation Mapper."""

    def to_spec(
        self,
        exchange_symbol: str,
        *,
        market_type: MarketType,
    ) -> InstrumentSpec:
        """Convert Binance symbol to InstrumentSpec.

        Args:
            exchange_symbol: Binance symbol (e.g., "BTCUSDT", "BTCUSDT_240329")
            market_type: Market type (spot or futures)

        Returns:
            Canonical InstrumentSpec

        Raises:
            SymbolResolutionError: If symbol cannot be parsed
        """
        symbol_upper = exchange_symbol.upper()

        # Handle dated futures (format: BASEQUOTE_YYMMDD)
        if market_type == MarketType.FUTURES and "_" in symbol_upper:
            parts = symbol_upper.split("_", 1)
            if len(parts) == 2 and len(parts[1]) == 6 and parts[1].isdigit():
                base_quote = parts[0]
                date_str = parts[1]
                try:
                    # Binance uses 2-digit year (YYMMDD)
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
            # Binance futures are typically perpetuals unless they have delivery date
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
        """Convert InstrumentSpec to Binance symbol.

        Args:
            spec: Canonical InstrumentSpec
            market_type: Market type (spot or futures)

        Returns:
            Binance symbol string

        Raises:
            SymbolResolutionError: If spec cannot be converted
        """
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
                    f"Cannot convert {spec.instrument_type.value} to Binance futures symbol",
                    exchange="binance",
                    value=str(spec),
                    market_type=market_type,
                )
        else:
            # Spot: just BASEQUOTE
            if spec.instrument_type != InstrumentType.SPOT:
                raise SymbolResolutionError(
                    f"Cannot convert {spec.instrument_type.value} to Binance spot symbol",
                    exchange="binance",
                    value=str(spec),
                    market_type=market_type,
                )
            return base_quote

    def _split_base_quote(self, symbol: str) -> tuple[str, str]:
        """Split symbol into base and quote.

        Handles common quote assets: USDT, USD, BTC, ETH, BNB, BUSD, etc.
        """
        # Common quote assets (longest first to avoid partial matches)
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
            "PAX",
            "USDP",
        ]

        for quote in quote_assets:
            if symbol.endswith(quote):
                base = symbol[: -len(quote)]
                if base:
                    return base, quote

        # Fallback: assume last 3-4 chars are quote
        if len(symbol) >= 6:
            return symbol[:-4], symbol[-4:]
        elif len(symbol) >= 4:
            return symbol[:-3], symbol[-3:]
        else:
            raise SymbolResolutionError(
                f"Cannot split Binance symbol '{symbol}' into base/quote",
                exchange="binance",
                value=symbol,
            )
