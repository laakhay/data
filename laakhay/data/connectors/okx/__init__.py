"""OKX connector implementation."""

from .provider import OKXProvider
from .rest.provider import OKXRESTConnector
from .urm import OKXURM
from .ws.provider import OKXWSConnector

# Alias for compatibility with providers API
OKXRESTProvider = OKXRESTConnector
OKXWSProvider = OKXWSConnector

__all__ = [
    "OKXProvider",
    "OKXRESTProvider",
    "OKXWSProvider",
    "OKXRESTConnector",
    "OKXWSConnector",
    "OKXURM",
]
