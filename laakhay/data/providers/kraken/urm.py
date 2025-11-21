"""Kraken URM mapper (shim for backward compatibility).

This module is a shim that imports from connectors. The actual implementation
has been moved to connectors/kraken/urm.py.

Handles Kraken-specific symbol formats and aliases:
- Spot: XBT/USD, ETH/USD (with separator, XBT = BTC)
- Futures: PI_XBTUSD, PI_ETHUSD (PI_ prefix for perpetuals, XBT = BTC)
"""

# Import from connector for backward compatibility
from laakhay.data.connectors.kraken.urm import KrakenURM

__all__ = ["KrakenURM"]
