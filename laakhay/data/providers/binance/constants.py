"""Shared Binance provider constants.

This module centralizes URLs and interval mappings used by the REST and
WebSocket mixins so the main provider can stay small and focused.
"""

from ...core import MarketType, TimeInterval

# Market-specific REST base URLs
BASE_URLS = {
    MarketType.SPOT: "https://api.binance.com",
    MarketType.FUTURES: "https://fapi.binance.com",
}

# Market-specific WebSocket URLs
#  - Single stream:   wss://<host>/ws/<stream-name>
#  - Combined stream: wss://<host>/stream?streams=<stream1>/<stream2>/...
WS_SINGLE_URLS = {
    MarketType.SPOT: "wss://stream.binance.com:9443/ws",
    MarketType.FUTURES: "wss://fstream.binance.com/ws",
}

WS_COMBINED_URLS = {
    MarketType.SPOT: "wss://stream.binance.com:9443/stream",
    MarketType.FUTURES: "wss://fstream.binance.com/stream",
}

# Binance interval mapping
INTERVAL_MAP = {
    TimeInterval.M1: "1m",
    TimeInterval.M3: "3m",
    TimeInterval.M5: "5m",
    TimeInterval.M15: "15m",
    TimeInterval.M30: "30m",
    TimeInterval.H1: "1h",
    TimeInterval.H2: "2h",
    TimeInterval.H4: "4h",
    TimeInterval.H6: "6h",
    TimeInterval.H8: "8h",
    TimeInterval.H12: "12h",
    TimeInterval.D1: "1d",
    TimeInterval.D3: "3d",
    TimeInterval.W1: "1w",
    TimeInterval.MO1: "1M",
}
