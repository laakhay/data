"""I/O layer abstractions (REST and streaming provider interfaces)."""

from .rest.http import HTTPClient
from .rest.provider import RESTProvider

# Re-export REST and WS subpackages
from .rest.runner import ResponseAdapter, RestEndpointSpec, RestRunner
from .rest.transport import RESTTransport
from .ws.client import ConnectionState, WebSocketClient
from .ws.provider import WSProvider
from .ws.runner import MessageAdapter, StreamRunner, WSEndpointSpec
from .ws.transport import TransportConfig, WebSocketTransport

__all__ = [
    "RESTProvider",
    "WSProvider",
    # REST
    "RESTTransport",
    "RestRunner",
    "RestEndpointSpec",
    "ResponseAdapter",
    # WS
    "TransportConfig",
    "WebSocketTransport",
    "WebSocketClient",
    "ConnectionState",
    "WSEndpointSpec",
    "MessageAdapter",
    "StreamRunner",
    # Common HTTP
    "HTTPClient",
]
