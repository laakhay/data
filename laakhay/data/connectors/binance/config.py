"""Shared Binance provider constants.

This module centralizes URLs and interval mappings used by the REST and
WebSocket mixins so the main provider can stay small and focused.
"""

from __future__ import annotations

from laakhay.data.core import MarketType, MarketVariant, Timeframe

# Market-specific REST base URLs
# Binance uses different base URLs:
# - Spot: api.binance.com
# - Linear perpetuals (USD-M): fapi.binance.com
# - Inverse perpetuals (COIN-M): dapi.binance.com
BASE_URLS = {
    MarketType.SPOT: "https://api.binance.com",
    MarketType.FUTURES: "https://fapi.binance.com",  # Default to linear (backward compatibility)
}


def get_base_url(market_type: MarketType, market_variant: MarketVariant | None = None) -> str:
    """Get Binance REST base URL based on market type and variant.

    Args:
        market_type: Market type (spot or futures)
        market_variant: Optional market variant (for FUTURES: linear_perp or inverse_perp)

    Returns:
        Base URL string

    Examples:
        >>> get_base_url(MarketType.SPOT)
        'https://api.binance.com'
        >>> get_base_url(MarketType.FUTURES, MarketVariant.LINEAR_PERP)
        'https://fapi.binance.com'
        >>> get_base_url(MarketType.FUTURES, MarketVariant.INVERSE_PERP)
        'https://dapi.binance.com'
    """
    if market_type == MarketType.SPOT:
        return BASE_URLS[MarketType.SPOT]

    # For FUTURES, check variant
    if market_type == MarketType.FUTURES:
        if market_variant == MarketVariant.INVERSE_PERP:
            return "https://dapi.binance.com"  # COIN-M (inverse) perpetuals
        # Default to linear (fapi) for backward compatibility
        return "https://fapi.binance.com"  # USD-M (linear) perpetuals

    # Fallback to default
    return BASE_URLS.get(market_type, BASE_URLS[MarketType.SPOT])


def get_api_path_prefix(
    market_type: MarketType, market_variant: MarketVariant | None = None
) -> str:
    """Get API path prefix based on market type and variant.

    Args:
        market_type: Market type (spot or futures)
        market_variant: Optional market variant (for FUTURES: linear_perp or inverse_perp)

    Returns:
        API path prefix: "/api/v3", "/fapi/v1", or "/dapi/v1"

    Examples:
        >>> get_api_path_prefix(MarketType.SPOT)
        '/api/v3'
        >>> get_api_path_prefix(MarketType.FUTURES, MarketVariant.LINEAR_PERP)
        '/fapi/v1'
        >>> get_api_path_prefix(MarketType.FUTURES, MarketVariant.INVERSE_PERP)
        '/dapi/v1'
    """
    if market_type == MarketType.SPOT:
        return "/api/v3"

    # For FUTURES, check variant
    if market_type == MarketType.FUTURES:
        if market_variant == MarketVariant.INVERSE_PERP:
            return "/dapi/v1"  # COIN-M (inverse) perpetuals
        # Default to linear (fapi) for backward compatibility
        return "/fapi/v1"  # USD-M (linear) perpetuals

    # Fallback to spot
    return "/api/v3"


# Market-specific WebSocket URLs
#  - Single stream:   wss://<host>/ws/<stream-name>
#  - Combined stream: wss://<host>/stream?streams=<stream1>/<stream2>/...
WS_SINGLE_URLS = {
    MarketType.SPOT: "wss://stream.binance.com:9443/ws",
    MarketType.FUTURES: "wss://fstream.binance.com/ws",  # Default to linear (backward compatibility)
}

WS_COMBINED_URLS = {
    MarketType.SPOT: "wss://stream.binance.com:9443/stream",
    MarketType.FUTURES: "wss://fstream.binance.com/stream",  # Default to linear (backward compatibility)
}


def get_ws_base_url(market_type: MarketType, market_variant: MarketVariant | None = None) -> str:
    """Get Binance WebSocket base URL based on market type and variant.

    Args:
        market_type: Market type (spot or futures)
        market_variant: Optional market variant (for FUTURES: linear_perp or inverse_perp)

    Returns:
        WebSocket base URL string

    Examples:
        >>> get_ws_base_url(MarketType.SPOT)
        'wss://stream.binance.com:9443/ws'
        >>> get_ws_base_url(MarketType.FUTURES, MarketVariant.LINEAR_PERP)
        'wss://fstream.binance.com/ws'
        >>> get_ws_base_url(MarketType.FUTURES, MarketVariant.INVERSE_PERP)
        'wss://dstream.binance.com/ws'
    """
    if market_type == MarketType.SPOT:
        return WS_SINGLE_URLS[MarketType.SPOT]

    # For FUTURES, check variant
    if market_type == MarketType.FUTURES:
        if market_variant == MarketVariant.INVERSE_PERP:
            return "wss://dstream.binance.com/ws"  # COIN-M (inverse) perpetuals
        # Default to linear (fstream) for backward compatibility
        return "wss://fstream.binance.com/ws"  # USD-M (linear) perpetuals

    # Fallback to default
    return WS_SINGLE_URLS.get(market_type, WS_SINGLE_URLS[MarketType.SPOT])


# Binance interval mapping
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

# Open Interest period mapping - reuse the same interval map since it's the same exchange
OI_PERIOD_MAP = {
    v: v
    for v in INTERVAL_MAP.values()
    if v in ["5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"]
}
