"""Shared Bybit provider constants.

This module centralizes URLs and interval mappings used by the REST and
WebSocket implementations so the main provider can stay small and focused.
"""

from ...core import MarketType, Timeframe

# Market-specific REST base URLs
# Bybit uses unified API v5 with category parameter
BASE_URLS = {
    MarketType.SPOT: "https://api.bybit.com",
    MarketType.FUTURES: "https://api.bybit.com",  # Same base, different category
}

# Market-specific WebSocket URLs
# Bybit v5 public WebSocket endpoints
WS_PUBLIC_URLS = {
    MarketType.SPOT: "wss://stream.bybit.com/v5/public/spot",
    MarketType.FUTURES: "wss://stream.bybit.com/v5/public/linear",  # USDT perpetuals
}

# Category mapping for Bybit API v5
# Bybit uses 'category' parameter to distinguish market types
CATEGORY_MAP = {
    MarketType.SPOT: "spot",
    MarketType.FUTURES: "linear",  # USDT perpetuals
}

# Bybit interval mapping
# Bybit uses numeric intervals: 1, 3, 5, 15, 30 (minutes), 60, 120, 240, 360, 720 (hours in minutes)
# And D, W, M for day, week, month
INTERVAL_MAP = {
    Timeframe.M1: "1",
    Timeframe.M3: "3",
    Timeframe.M5: "5",
    Timeframe.M15: "15",
    Timeframe.M30: "30",
    Timeframe.H1: "60",
    Timeframe.H2: "120",
    Timeframe.H4: "240",
    Timeframe.H6: "360",
    Timeframe.H12: "720",
    Timeframe.D1: "D",
    Timeframe.D3: "3",  # Bybit doesn't have 3d, use 3 minutes as fallback
    Timeframe.W1: "W",
    Timeframe.MO1: "M",
}

# Reverse mapping for WebSocket topics (interval string -> Timeframe)
INTERVAL_REVERSE_MAP = {v: k for k, v in INTERVAL_MAP.items()}

# Open Interest period mapping
# Bybit supports: 5min, 15min, 30min, 1h, 4h, 1d
OI_PERIOD_MAP = {
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

# Order book depth options
# Bybit supports: 1, 25, 50, 100, 200
ORDER_BOOK_DEPTHS = [1, 25, 50, 100, 200]
