"""Kraken connector implementation."""

from .provider import KrakenProvider
from .rest.provider import KrakenRESTConnector
from .urm import KrakenURM
from .ws.provider import KrakenWSConnector

# Alias for compatibility with providers API
KrakenRESTProvider = KrakenRESTConnector
KrakenWSProvider = KrakenWSConnector

__all__ = [
    "KrakenProvider",
    "KrakenRESTProvider",
    "KrakenWSProvider",
    "KrakenRESTConnector",
    "KrakenWSConnector",
    "KrakenURM",
]
