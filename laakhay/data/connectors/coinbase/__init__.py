"""Coinbase connector package."""

from .provider import CoinbaseProvider
from .rest.provider import CoinbaseRESTConnector
from .urm import CoinbaseURM
from .ws.provider import CoinbaseWSConnector

# Alias for compatibility with providers API
CoinbaseRESTProvider = CoinbaseRESTConnector
CoinbaseWSProvider = CoinbaseWSConnector

__all__ = [
    "CoinbaseProvider",
    "CoinbaseRESTProvider",
    "CoinbaseWSProvider",
    "CoinbaseRESTConnector",
    "CoinbaseWSConnector",
    "CoinbaseURM",
]
