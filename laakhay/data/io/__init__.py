"""I/O layer abstractions (REST and streaming provider interfaces)."""

from .rest import RESTProvider
from .stream_runner import WSEndpointSpec, MessageAdapter, StreamRunner
from .ws import WSProvider
from .ws_transport import TransportConfig, WebSocketTransport

__all__ = [
    "RESTProvider",
    "WSProvider",
    "TransportConfig",
    "WebSocketTransport",
    "WSEndpointSpec",
    "MessageAdapter",
    "StreamRunner",
]
