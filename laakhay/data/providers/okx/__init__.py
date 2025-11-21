"""OKX providers (REST-only, WS-only, and unified facade)."""

# Import provider classes from connectors (using aliases for backward compatibility)
from laakhay.data.connectors.okx.provider import OKXProvider
from laakhay.data.connectors.okx.rest.provider import OKXRESTConnector as OKXRESTProvider
from laakhay.data.connectors.okx.urm import OKXURM
from laakhay.data.connectors.okx.ws.provider import OKXWSConnector as OKXWSProvider

__all__ = [
    "OKXProvider",
    "OKXRESTProvider",
    "OKXURM",
    "OKXWSProvider",
]
