"""Shared Coinbase provider constants.

This module centralizes URLs, interval mappings, and symbol normalization
used by the REST and WebSocket providers.
"""

from ...core import MarketType, Timeframe

# Market-specific REST base URLs
# Coinbase Exchange API (public, no auth) for market data
# Coinbase Advanced Trade API requires authentication - use Exchange API for public data
BASE_URLS = {
    MarketType.SPOT: "https://api.exchange.coinbase.com",
}

# Market-specific WebSocket URLs
# Coinbase Exchange API WebSocket (public, no auth) for market data
# Advanced Trade WebSocket requires authentication - use Exchange API for public feeds
WS_PUBLIC_URLS = {
    MarketType.SPOT: "wss://ws-feed.exchange.coinbase.com",
}

# Coinbase interval mapping
# Coinbase uses ISO 8601 duration format (e.g., "ONE_MINUTE", "FIVE_MINUTE")
# or numeric seconds. Based on API docs, using the granularity format.
INTERVAL_MAP = {
    Timeframe.M1: "ONE_MINUTE",
    Timeframe.M5: "FIVE_MINUTE",
    Timeframe.M15: "FIFTEEN_MINUTE",
    Timeframe.M30: "THIRTY_MINUTE",
    Timeframe.H1: "ONE_HOUR",
    Timeframe.H2: "TWO_HOUR",
    Timeframe.H4: "FOUR_HOUR",
    Timeframe.H6: "SIX_HOUR",
    Timeframe.H12: "TWELVE_HOUR",
    Timeframe.D1: "ONE_DAY",
    Timeframe.W1: "ONE_WEEK",
    # Note: Coinbase may not support all intervals - verify in API docs
}

# Symbol normalization maps
# Coinbase uses hyphenated format: BTC-USD, ETH-USD
# Standard format: BTCUSD, ETHUSD

# Map from standard format to Coinbase format
# Note: Coinbase Advanced Trade API only supports USD pairs, not USDT pairs
# So BTCUSDT -> BTC-USD (not BTC-USDT)
SYMBOL_TO_COINBASE: dict[str, str] = {
    # Major pairs - USD pairs
    "BTCUSD": "BTC-USD",
    "ETHUSD": "ETH-USD",
    "SOLUSD": "SOL-USD",
    # USDT pairs map to USD pairs (Coinbase doesn't support USDT)
    "BTCUSDT": "BTC-USD",
    "ETHUSDT": "ETH-USD",
    "SOLUSDT": "SOL-USD",
    # Add more as needed - this will be populated dynamically from /products endpoint
}

# Map from Coinbase format to standard format
SYMBOL_FROM_COINBASE: dict[str, str] = {
    "BTC-USD": "BTCUSD",
    "ETH-USD": "ETHUSD",
    "BTC-USDT": "BTCUSDT",
    "ETH-USDT": "ETHUSDT",
    # Add more as needed
}


# Reverse mapping helper
def normalize_symbol_to_coinbase(symbol: str) -> str:
    """Convert standard format (BTCUSD) to Coinbase format (BTC-USD).

    If symbol is already in Coinbase format, returns as-is.
    If not found in map, attempts to infer format by splitting.
    """
    # If already hyphenated, assume Coinbase format
    if "-" in symbol:
        return symbol.upper()

    # Check explicit mapping
    if symbol in SYMBOL_TO_COINBASE:
        return SYMBOL_TO_COINBASE[symbol]

    # Attempt to infer: split base/quote
    # Coinbase only supports USD pairs, so USDT pairs map to USD pairs
    # This is a fallback - ideally we'd query /products first
    if symbol.endswith("USD"):
        base = symbol[:-3]
        return f"{base}-USD"
    elif symbol.endswith("USDT"):
        # Coinbase doesn't support USDT pairs - map to USD instead
        base = symbol[:-4]
        return f"{base}-USD"

    # Return as-is if can't determine
    return symbol.upper()


def normalize_symbol_from_coinbase(symbol: str) -> str:
    """Convert Coinbase format (BTC-USD) to standard format (BTCUSD).

    If symbol is already in standard format, returns as-is.
    """
    # If no hyphen, assume already standard format
    if "-" not in symbol:
        return symbol.upper()

    # Check explicit mapping
    if symbol in SYMBOL_FROM_COINBASE:
        return SYMBOL_FROM_COINBASE[symbol]

    # Remove hyphen as fallback
    return symbol.replace("-", "").upper()
