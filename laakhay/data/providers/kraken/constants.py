"""Shared Kraken provider constants.

This module centralizes URLs and interval mappings used by the REST and
WebSocket implementations so the main provider can stay small and focused.
"""

from ...core import MarketType, Timeframe

# Market-specific REST base URLs
# Kraken Futures API uses different base URL than Spot
BASE_URLS = {
    MarketType.SPOT: "https://api.kraken.com",
    MarketType.FUTURES: "https://futures.kraken.com/derivatives/api/v3",
}

# Market-specific WebSocket URLs
# Kraken uses different WebSocket endpoints for Spot and Futures
WS_PUBLIC_URLS = {
    MarketType.SPOT: "wss://ws.kraken.com/v2",
    MarketType.FUTURES: "wss://futures.kraken.com/ws/v1",
}

# Symbol normalization mapping
# Kraken uses XBT instead of BTC, and different symbol formats
# Standard format: BTCUSD, ETHUSD (no separator, base+quote)
# Kraken Spot: XBT/USD, ETH/USD (with separator)
# Kraken Futures: PI_XBTUSD, PI_ETHUSD (PI_ prefix for perpetuals)
SYMBOL_TO_KRAKEN_SPOT: dict[str, str] = {
    "BTCUSD": "XBT/USD",
    "BTCUSDT": "XBT/USDT",
    "ETHUSD": "ETH/USD",
    "ETHUSDT": "ETH/USDT",
    "SOLUSD": "SOL/USD",
    "SOLUSDT": "SOL/USDT",
    "ADAUSD": "ADA/USD",
    "ADAUSDT": "ADA/USDT",
    "AVAXUSD": "AVAX/USD",
    "AVAXUSDT": "AVAX/USDT",
}

KRAKEN_SPOT_TO_SYMBOL: dict[str, str] = {v: k for k, v in SYMBOL_TO_KRAKEN_SPOT.items()}

# Kraken Futures uses PI_ prefix for perpetuals
SYMBOL_TO_KRAKEN_FUTURES: dict[str, str] = {
    "BTCUSD": "PI_XBTUSD",
    "BTCUSDT": "PI_XBTUSD",  # Kraken Futures uses USD, not USDT
    "ETHUSD": "PI_ETHUSD",
    "ETHUSDT": "PI_ETHUSD",
    "SOLUSD": "PI_SOLUSD",
    "SOLUSDT": "PI_SOLUSD",
    "ADAUSD": "PI_ADAUSD",
    "ADAUSDT": "PI_ADAUSD",
    "AVAXUSD": "PI_AVAXUSD",
    "AVAXUSDT": "PI_AVAXUSD",
}

# Reverse mapping - prefer USD over USDT when multiple symbols map to same Kraken symbol
KRAKEN_FUTURES_TO_SYMBOL: dict[str, str] = {}
for standard_symbol, kraken_symbol in SYMBOL_TO_KRAKEN_FUTURES.items():
    # Prefer USD over USDT (e.g., PI_XBTUSD -> BTCUSD not BTCUSDT)
    if (
        kraken_symbol not in KRAKEN_FUTURES_TO_SYMBOL
        or standard_symbol.endswith("USD")
        and not standard_symbol.endswith("USDT")
    ):
        KRAKEN_FUTURES_TO_SYMBOL[kraken_symbol] = standard_symbol


def normalize_symbol_to_kraken(symbol: str, market_type: MarketType) -> str:
    """Convert standard symbol format (BTCUSD) to Kraken format.

    Args:
        symbol: Standard symbol format (e.g., BTCUSD or BTCUSDT)
        market_type: Market type (SPOT or FUTURES)

    Returns:
        Kraken-formatted symbol (e.g., XBT/USD for Spot, PI_XBTUSD for Futures)

    Note:
        For Spot: Kraken doesn't support USDT pairs, so USDT is converted to USD
        For Futures: USDT symbols map to USD-based perpetuals
    """
    symbol_upper = symbol.upper()

    if market_type == MarketType.SPOT:
        # Kraken Spot doesn't support USDT pairs - convert to USD
        # First try direct mapping
        if symbol_upper in SYMBOL_TO_KRAKEN_SPOT:
            return SYMBOL_TO_KRAKEN_SPOT[symbol_upper]
        # Convert USDT to USD for Spot (Kraken Spot uses USD, not USDT)
        spot_symbol = symbol_upper.replace("USDT", "USD")
        if spot_symbol in SYMBOL_TO_KRAKEN_SPOT:
            return SYMBOL_TO_KRAKEN_SPOT[spot_symbol]
        # Fallback: add separator and convert XBT
        normalized = spot_symbol.replace("XBT", "BTC").replace("BTC", "XBT")
        if "/" not in normalized:
            # Add separator before USD/USDT
            if normalized.endswith("USD"):
                normalized = normalized[:-3] + "/USD"
            elif normalized.endswith("USDT"):
                normalized = normalized[:-4] + "/USD"  # Convert USDT to USD
        return normalized
    else:  # FUTURES
        return SYMBOL_TO_KRAKEN_FUTURES.get(symbol_upper, f"PI_{symbol_upper}")


def normalize_symbol_from_kraken(kraken_symbol: str, market_type: MarketType) -> str:
    """Convert Kraken symbol format to standard format (BTCUSD).

    Args:
        kraken_symbol: Kraken-formatted symbol (e.g., XBT/USD or PI_XBTUSD)
        market_type: Market type (SPOT or FUTURES)

    Returns:
        Standard symbol format (e.g., BTCUSD)
    """
    symbol_upper = kraken_symbol.upper()

    if market_type == MarketType.SPOT:
        # Try direct mapping first
        if symbol_upper in KRAKEN_SPOT_TO_SYMBOL:
            return KRAKEN_SPOT_TO_SYMBOL[symbol_upper]
        # Fallback: remove separator and convert XBT to BTC
        normalized = symbol_upper.replace("/", "").replace("XBT", "BTC")
        # Ensure we return USD not USDT if original was USD
        if "/USD" in symbol_upper and normalized.endswith("USDT"):
            normalized = normalized.replace("USDT", "USD")
        return normalized
    else:  # FUTURES
        # Try direct mapping first
        if symbol_upper in KRAKEN_FUTURES_TO_SYMBOL:
            return KRAKEN_FUTURES_TO_SYMBOL[symbol_upper]
        # Fallback: remove PI_ prefix and convert XBT to BTC
        normalized = symbol_upper.replace("PI_", "").replace("XBT", "BTC")
        # Kraken Futures uses USD, not USDT
        if normalized.endswith("USDT"):
            normalized = normalized.replace("USDT", "USD")
        return normalized


# Kraken interval mapping
# Kraken Futures API uses numeric intervals in minutes: 1, 5, 15, 30, 60, 240, 1440, 10080, 21600
# Kraken Spot API uses different format: 1, 5, 15, 30, 60, 240, 1440, 10080, 21600
INTERVAL_MAP = {
    Timeframe.M1: "1",
    Timeframe.M3: "3",  # May not be supported, fallback to 1
    Timeframe.M5: "5",
    Timeframe.M15: "15",
    Timeframe.M30: "30",
    Timeframe.H1: "60",
    Timeframe.H2: "120",  # May not be supported, fallback to 60
    Timeframe.H4: "240",
    Timeframe.H6: "360",  # May not be supported, fallback to 240
    Timeframe.H8: "480",  # May not be supported, fallback to 240
    Timeframe.H12: "720",  # May not be supported, fallback to 240
    Timeframe.D1: "1440",
    Timeframe.D3: "4320",  # May not be supported, fallback to 1440
    Timeframe.W1: "10080",
    Timeframe.MO1: "21600",  # Approximate, may not be exact
}

# Reverse mapping for WebSocket topics (interval string -> Timeframe)
INTERVAL_REVERSE_MAP = {v: k for k, v in INTERVAL_MAP.items()}

# Order book depth options
# Kraken supports various depth levels, typically: 10, 25, 50, 100, 500, 1000
ORDER_BOOK_DEPTHS = [10, 25, 50, 100, 500, 1000]
