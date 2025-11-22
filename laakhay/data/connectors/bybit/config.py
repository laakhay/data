"""Shared Bybit connector constants.

This module centralizes URLs and interval mappings used by the REST and
WebSocket connectors so the main provider can stay small and focused.
"""

from __future__ import annotations

from typing import Any

from laakhay.data.core import MarketType, MarketVariant, Timeframe

# Market-specific REST base URLs
# Bybit uses unified API v5 with category parameter
BASE_URLS = {
    MarketType.SPOT: "https://api.bybit.com",
    MarketType.FUTURES: "https://api.bybit.com",  # Same base, different category
}

# Market-specific WebSocket URLs
# Bybit v5 public WebSocket endpoints
WS_SINGLE_URLS = {
    MarketType.SPOT: "wss://stream.bybit.com/v5/public/spot",
    MarketType.FUTURES: "wss://stream.bybit.com/v5/public/linear",  # USDT perpetuals
}

WS_COMBINED_URLS = {
    MarketType.SPOT: "wss://stream.bybit.com/v5/public/spot",
    MarketType.FUTURES: "wss://stream.bybit.com/v5/public/linear",
}


# Category mapping for Bybit API v5
# Bybit uses 'category' parameter to distinguish market types:
# - "spot": Spot trading
# - "linear": USDT perpetuals (linear)
# - "inverse": COIN-M perpetuals (inverse)
def get_category_from_variant(market_variant: MarketVariant) -> str:
    """Get Bybit category parameter from MarketVariant.

    Args:
        market_variant: The market variant to get category for

    Returns:
        Bybit category string: "spot", "linear", or "inverse"

    Raises:
        ValueError: If variant is not supported by Bybit
    """
    if market_variant == MarketVariant.SPOT:
        return "spot"
    if market_variant == MarketVariant.LINEAR_PERP:
        return "linear"
    if market_variant == MarketVariant.INVERSE_PERP:
        return "inverse"
    # For now, only support spot, linear, and inverse perpetuals
    # Future variants (delivery, options, etc.) can be added as needed
    raise ValueError(f"Unsupported market variant for Bybit: {market_variant}")


def get_category(params: dict[str, Any]) -> str:
    """Get Bybit category parameter from params dict.

    Supports both old-style (market_type only) and new-style (market_variant)
    parameter passing for backward compatibility.

    Args:
        params: Parameters dict containing either:
               - market_variant: MarketVariant (preferred)
               - market_type: MarketType (fallback for backward compatibility)

    Returns:
        Bybit category string: "spot", "linear", or "inverse"
    """
    # Prefer market_variant if provided
    if "market_variant" in params:
        market_variant = params["market_variant"]
        if isinstance(market_variant, str):
            market_variant = MarketVariant(market_variant)
        return get_category_from_variant(market_variant)

    # Fallback to market_type for backward compatibility
    if "market_type" in params:
        market_type = params["market_type"]
        if isinstance(market_type, str):
            market_type = MarketType(market_type)
        # Derive variant from type
        market_variant = MarketVariant.from_market_type(market_type)
        return get_category_from_variant(market_variant)

    raise ValueError("Either 'market_variant' or 'market_type' must be provided in params")


# Legacy mapping for backwards compatibility
# Use get_category() or get_category_from_variant() for new code
CATEGORY_MAP = {
    MarketType.SPOT: "spot",
    MarketType.FUTURES: "linear",  # Default to linear for backwards compatibility
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
