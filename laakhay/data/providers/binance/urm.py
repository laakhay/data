"""Binance URM mapper (shim for backward compatibility).

This module is a shim that imports from connectors. The actual implementation
has been moved to connectors/binance/urm.py.

Handles Binance-specific symbol formats:
- Spot: BTCUSDT, ETHUSDT (standard format)
- Futures: BTCUSDT (perpetual), BTCUSDT_240329 (dated future with delivery date)
"""

from __future__ import annotations

# Import from connectors for backward compatibility
from laakhay.data.connectors.binance.urm import BinanceURM  # noqa: F401

__all__ = ["BinanceURM"]
