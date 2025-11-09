"""Shared OKX provider constants.

This module centralizes URLs and interval mappings used by the REST and
WebSocket implementations so the main provider can stay small and focused.
"""

from ...core import MarketType, Timeframe

# Market-specific REST base URLs
# OKX uses unified API v5 with instType parameter
BASE_URLS = {
    MarketType.SPOT: "https://www.okx.com",
    MarketType.FUTURES: "https://www.okx.com",  # Same base, different instType
}

# Market-specific WebSocket URLs
# OKX v5 public WebSocket endpoints
WS_PUBLIC_URLS = {
    MarketType.SPOT: "wss://ws.okx.com:8443/ws/v5/public",
    MarketType.FUTURES: "wss://ws.okx.com:8443/ws/v5/public",  # Same URL, different instType
}

# Instrument type mapping for OKX API v5
# OKX uses 'instType' parameter to distinguish market types
INST_TYPE_MAP = {
    MarketType.SPOT: "SPOT",
    MarketType.FUTURES: "SWAP",  # USDT perpetuals
}

# OKX interval mapping
# OKX uses: 1m, 3m, 5m, 15m, 30m, 1H, 2H, 4H, 6H, 12H, 1D, 1W, 1M, 3M
INTERVAL_MAP = {
    Timeframe.M1: "1m",
    Timeframe.M3: "3m",
    Timeframe.M5: "5m",
    Timeframe.M15: "15m",
    Timeframe.M30: "30m",
    Timeframe.H1: "1H",
    Timeframe.H2: "2H",
    Timeframe.H4: "4H",
    Timeframe.H6: "6H",
    Timeframe.H12: "12H",
    Timeframe.D1: "1D",
    Timeframe.D3: "3D",  # OKX doesn't have 3D, use 1D as fallback
    Timeframe.W1: "1W",
    Timeframe.MO1: "1M",
}

# Reverse mapping for WebSocket topics (interval string -> Timeframe)
INTERVAL_REVERSE_MAP = {v: k for k, v in INTERVAL_MAP.items()}

# Open Interest period mapping
# OKX supports: 5m, 15m, 30m, 1H, 2H, 4H, 6H, 12H, 1D
OI_PERIOD_MAP = {
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1H",
    "2h": "2H",
    "4h": "4H",
    "6h": "6H",
    "12h": "12H",
    "1d": "1D",
}

# Order book depth options
# OKX supports: 1, 5, 10, 20, 50, 100, 200, 400
ORDER_BOOK_DEPTHS = [1, 5, 10, 20, 50, 100, 200, 400]


def to_okx_symbol(symbol: str) -> str:
    """Convert symbol from BTCUSDT format to BTC-USDT format for OKX API.

    OKX uses hyphenated format (BTC-USDT) while most exchanges use concatenated (BTCUSDT).
    This function handles the conversion.
    """
    symbol = symbol.upper()
    # If already hyphenated, return as-is
    if "-" in symbol:
        return symbol

    # Common quote assets to detect
    quote_assets = ["USDT", "USDC", "BUSD", "BTC", "ETH", "BNB", "DAI", "TUSD", "USDP"]

    for quote in quote_assets:
        if symbol.endswith(quote):
            base = symbol[: -len(quote)]
            return f"{base}-{quote}"

    # If no match, return as-is (might be a non-standard symbol)
    return symbol


def from_okx_symbol(symbol: str) -> str:
    """Convert symbol from BTC-USDT format to BTCUSDT format.

    Reverse of to_okx_symbol - removes hyphens to normalize to standard format.
    """
    return symbol.replace("-", "").upper()
