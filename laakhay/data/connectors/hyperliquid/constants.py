"""Shared Hyperliquid provider constants.

This module centralizes URLs and interval mappings used by the REST and
WebSocket implementations so the main provider can stay small and focused.

Hyperliquid supports both Spot and Perpetual Futures markets.
API documentation: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/
"""

from ...core import MarketType, Timeframe

# Market-specific REST base URLs
# Hyperliquid supports both Spot and Futures - same base URL
BASE_URLS = {
    MarketType.SPOT: "https://api.hyperliquid.xyz",
    MarketType.FUTURES: "https://api.hyperliquid.xyz",
}

# Market-specific WebSocket URLs
# Hyperliquid public WebSocket endpoint - same URL for both markets
WS_PUBLIC_URLS = {
    MarketType.SPOT: "wss://api.hyperliquid.xyz/ws",
    MarketType.FUTURES: "wss://api.hyperliquid.xyz/ws",
}

# Hyperliquid interval mapping
# Supported intervals per API docs: "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "8h", "12h", "1d", "3d", "1w", "1M"
INTERVAL_MAP = {
    Timeframe.M1: "1m",
    Timeframe.M3: "3m",
    Timeframe.M5: "5m",
    Timeframe.M15: "15m",
    Timeframe.M30: "30m",
    Timeframe.H1: "1h",
    Timeframe.H2: "2h",
    Timeframe.H4: "4h",
    Timeframe.H6: "6h",
    Timeframe.H8: "8h",
    Timeframe.H12: "12h",
    Timeframe.D1: "1d",
    Timeframe.D3: "3d",
    Timeframe.W1: "1w",
    Timeframe.MO1: "1M",
}

# Reverse mapping for WebSocket topics (interval string -> Timeframe)
INTERVAL_REVERSE_MAP = {v: k for k, v in INTERVAL_MAP.items()}

# Open Interest period mapping
# Hyperliquid uses same intervals as candles
OI_PERIOD_MAP = {
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

# Symbol format notes:
# - Perpetuals: Use coin name from meta response (e.g., "BTC", "ETH")
# - Spot: Use "@{index}" format (e.g., "@107") or "PURR/USDC" for PURR
# See: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/asset-ids

# Order book depth options
# Hyperliquid l2Book returns at most 20 levels per side
ORDER_BOOK_DEPTHS = [10, 20]
