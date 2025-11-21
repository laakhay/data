"""Kraken connector constants and helper functions.

This module provides constants and utility functions for Kraken symbol
normalization, re-exporting from config and providing convenience functions
that wrap the URM mapper.
"""

from laakhay.data.connectors.kraken.config import INTERVAL_MAP
from laakhay.data.connectors.kraken.urm import KrakenURM
from laakhay.data.core import MarketType

# Re-export INTERVAL_MAP from config
__all__ = ["INTERVAL_MAP", "normalize_symbol_to_kraken", "normalize_symbol_from_kraken"]

# Create a singleton URM instance for convenience functions
_urm = KrakenURM()


def normalize_symbol_to_kraken(symbol: str, market_type: MarketType) -> str:
    """Convert standard symbol format to Kraken format.

    Args:
        symbol: Standard symbol (e.g., "BTCUSD")
        market_type: Market type (spot or futures)

    Returns:
        Kraken-formatted symbol (e.g., "XBT/USD" for spot, "PI_XBTUSD" for futures)
    """
    from laakhay.data.core import InstrumentSpec, InstrumentType

    # Parse the symbol into base and quote
    # Simple heuristic: if it ends with common quote currencies, split there
    quote_currencies = ["USDT", "USD", "EUR", "GBP", "BTC", "ETH"]
    base = symbol
    quote = "USD"  # Default

    for qc in quote_currencies:
        if symbol.endswith(qc):
            base = symbol[: -len(qc)]
            quote = qc
            break

    # Create spec
    instrument_type = (
        InstrumentType.SPOT if market_type == MarketType.SPOT else InstrumentType.PERPETUAL
    )
    spec = InstrumentSpec(base=base, quote=quote, instrument_type=instrument_type)

    # Use URM to convert
    return _urm.to_exchange_symbol(spec, market_type=market_type)


def normalize_symbol_from_kraken(symbol: str, market_type: MarketType) -> str:
    """Convert Kraken symbol format to standard format.

    Args:
        symbol: Kraken symbol (e.g., "XBT/USD", "PI_XBTUSD")
        market_type: Market type (spot or futures)

    Returns:
        Standard symbol format (e.g., "BTCUSD")
    """
    # Use URM to convert
    spec = _urm.to_spec(symbol, market_type=market_type)

    # Convert back to standard format
    return f"{spec.base}{spec.quote}"
