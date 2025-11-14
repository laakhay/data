"""Kraken URM mapper.

Handles Kraken-specific symbol formats and aliases:
- Spot: XBT/USD, ETH/USD (with separator, XBT = BTC)
- Futures: PI_XBTUSD, PI_ETHUSD (PI_ prefix for perpetuals, XBT = BTC)
"""

from __future__ import annotations

from ...core import InstrumentSpec, InstrumentType, MarketType
from ...core.exceptions import SymbolResolutionError


class KrakenURM:
    """Kraken Universal Representation Mapper."""

    # Asset alias mapping (Kraken uses XBT instead of BTC)
    ASSET_ALIASES: dict[str, str] = {
        "XBT": "BTC",
        "BTC": "XBT",  # Reverse mapping
    }

    def to_spec(
        self,
        exchange_symbol: str,
        *,
        market_type: MarketType,
    ) -> InstrumentSpec:
        """Convert Kraken symbol to InstrumentSpec.

        Args:
            exchange_symbol: Kraken symbol (e.g., "XBT/USD", "PI_XBTUSD")
            market_type: Market type (spot or futures)

        Returns:
            Canonical InstrumentSpec

        Raises:
            SymbolResolutionError: If symbol cannot be parsed
        """
        symbol_upper = exchange_symbol.upper()

        if market_type == MarketType.SPOT:
            # Spot format: BASE/QUOTE (e.g., XBT/USD)
            if "/" not in symbol_upper:
                raise SymbolResolutionError(
                    f"Invalid Kraken spot symbol format: {symbol_upper}. Expected BASE/QUOTE",
                    exchange="kraken",
                    value=exchange_symbol,
                    market_type=market_type,
                )

            base, quote = symbol_upper.split("/", 1)
            # Convert XBT -> BTC
            base = self._normalize_asset(base)
            quote = self._normalize_asset(quote)

            return InstrumentSpec(
                base=base,
                quote=quote,
                instrument_type=InstrumentType.SPOT,
            )
        else:
            # Futures format: PI_BASEQUOTE (e.g., PI_XBTUSD)
            if not symbol_upper.startswith("PI_"):
                raise SymbolResolutionError(
                    f"Invalid Kraken futures symbol format: {symbol_upper}. Expected PI_BASEQUOTE",
                    exchange="kraken",
                    value=exchange_symbol,
                    market_type=market_type,
                )

            base_quote = symbol_upper[3:]  # Remove PI_ prefix
            base, quote = self._split_base_quote(base_quote)

            # Convert XBT -> BTC
            base = self._normalize_asset(base)
            quote = self._normalize_asset(quote)

            # Kraken futures are perpetuals
            return InstrumentSpec(
                base=base,
                quote=quote,
                instrument_type=InstrumentType.PERPETUAL,
            )

    def to_exchange_symbol(
        self,
        spec: InstrumentSpec,
        *,
        market_type: MarketType,
    ) -> str:
        """Convert InstrumentSpec to Kraken symbol.

        Args:
            spec: Canonical InstrumentSpec
            market_type: Market type (spot or futures)

        Returns:
            Kraken symbol string

        Raises:
            SymbolResolutionError: If spec cannot be converted
        """
        # Convert BTC -> XBT for Kraken
        base = self._denormalize_asset(spec.base)
        quote = self._denormalize_asset(spec.quote)

        if market_type == MarketType.SPOT:
            if spec.instrument_type != InstrumentType.SPOT:
                raise SymbolResolutionError(
                    f"Cannot convert {spec.instrument_type.value} to Kraken spot symbol",
                    exchange="kraken",
                    value=str(spec),
                    market_type=market_type,
                )
            return f"{base}/{quote}"
        else:
            if spec.instrument_type != InstrumentType.PERPETUAL:
                raise SymbolResolutionError(
                    f"Cannot convert {spec.instrument_type.value} to Kraken futures symbol. Only perpetuals supported",
                    exchange="kraken",
                    value=str(spec),
                    market_type=market_type,
                )
            # Kraken futures use USD, not USDT - raise error if USDT is requested
            if spec.quote == "USDT":
                raise SymbolResolutionError(
                    "Kraken futures only support USD, not USDT",
                    exchange="kraken",
                    value=str(spec),
                    market_type=market_type,
                )
            return f"PI_{base}{quote}"

    def _normalize_asset(self, asset: str) -> str:
        """Normalize asset name (XBT -> BTC)."""
        return self.ASSET_ALIASES.get(asset, asset)

    def _denormalize_asset(self, asset: str) -> str:
        """Denormalize asset name (BTC -> XBT for Kraken)."""
        # Reverse lookup
        for kraken_name, canonical_name in self.ASSET_ALIASES.items():
            if canonical_name == asset:
                return kraken_name
        return asset

    def _split_base_quote(self, symbol: str) -> tuple[str, str]:
        """Split symbol into base and quote.

        Handles common quote assets: USD, USDT, etc.
        """
        # Common quote assets (longest first)
        quote_assets = [
            "USDT",
            "USD",
            "BTC",
            "ETH",
            "EUR",
            "GBP",
            "JPY",
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
                f"Cannot split Kraken symbol '{symbol}' into base/quote",
                exchange="kraken",
                value=symbol,
            )
