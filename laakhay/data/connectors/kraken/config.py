"""Shared Kraken connector constants.

This module centralizes URLs and interval mappings used by the REST and
WebSocket connectors so the main provider can stay small and focused.
"""

from laakhay.data.core import MarketType, Timeframe

# Market-specific REST base URLs
BASE_URLS = {
    MarketType.SPOT: "https://api.kraken.com",
    MarketType.FUTURES: "https://futures.kraken.com/derivatives/api/v3",
}

# Market-specific WebSocket URLs
# Kraken uses different WebSocket endpoints for Spot and Futures
WS_SINGLE_URLS = {
    MarketType.SPOT: "wss://ws.kraken.com/v2",
    MarketType.FUTURES: "wss://futures.kraken.com/ws/v1",
}

WS_COMBINED_URLS = {
    MarketType.SPOT: "wss://ws.kraken.com/v2",
    MarketType.FUTURES: "wss://futures.kraken.com/ws/v1",
}

# Kraken interval mapping
# Kraken uses numeric intervals in minutes
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
    Timeframe.H8: "480",
    Timeframe.H12: "720",
    Timeframe.D1: "1440",
    Timeframe.D3: "4320",
    Timeframe.W1: "10080",
    Timeframe.MO1: "21600",
}

# Open Interest period mapping - reuse the same interval map
OI_PERIOD_MAP = {
    v: v for v in INTERVAL_MAP.values() if v in ["1", "5", "15", "30", "60", "240", "1440"]
}
