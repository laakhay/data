"""Binance connector implementation."""

from .provider import BinanceProvider
from .rest.provider import BinanceRESTConnector
from .urm import BinanceURM
from .ws.provider import BinanceWSConnector

# Alias for compatibility with providers API
BinanceRESTProvider = BinanceRESTConnector
BinanceWSProvider = BinanceWSConnector

__all__ = [
    "BinanceProvider",
    "BinanceRESTProvider",
    "BinanceWSProvider",
    "BinanceRESTConnector",
    "BinanceWSConnector",
    "BinanceURM",
]
