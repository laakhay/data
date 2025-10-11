"""Unit tests for WebSocket client."""

import pytest
from unittest.mock import MagicMock

from laakhay.data.utils import WebSocketClient, ConnectionState


def test_websocket_client_initialization():
    """Test WebSocket client can be instantiated."""
    on_message = MagicMock()
    client = WebSocketClient(
        url="wss://example.com/ws",
        on_message=on_message
    )
    
    assert client.url == "wss://example.com/ws"
    assert client.on_message == on_message
    assert client.state == ConnectionState.DISCONNECTED
    assert not client.is_connected
    assert client.ping_interval == 30.0
    assert client.ping_timeout == 10.0
    assert client.max_reconnect_delay == 30.0


def test_websocket_client_custom_parameters():
    """Test WebSocket client with custom parameters."""
    on_message = MagicMock()
    client = WebSocketClient(
        url="wss://example.com/ws",
        on_message=on_message,
        ping_interval=20.0,
        ping_timeout=5.0,
        max_reconnect_delay=60.0
    )
    
    assert client.ping_interval == 20.0
    assert client.ping_timeout == 5.0
    assert client.max_reconnect_delay == 60.0


@pytest.mark.asyncio
async def test_websocket_client_connection_state():
    """Test connection state transitions."""
    on_message = MagicMock()
    client = WebSocketClient(
        url="wss://example.com/ws",
        on_message=on_message
    )
    
    # Initially disconnected
    assert client.state == ConnectionState.DISCONNECTED
    assert not client.is_connected


@pytest.mark.asyncio
async def test_websocket_client_send_when_not_connected():
    """Test sending message when not connected raises error."""
    on_message = MagicMock()
    client = WebSocketClient(
        url="wss://example.com/ws",
        on_message=on_message
    )
    
    with pytest.raises(RuntimeError, match="not connected"):
        await client.send({"type": "ping"})


@pytest.mark.asyncio
async def test_websocket_client_disconnect_when_not_connected():
    """Test disconnecting when not connected doesn't error."""
    on_message = MagicMock()
    client = WebSocketClient(
        url="wss://example.com/ws",
        on_message=on_message
    )
    
    # Should not raise
    await client.disconnect()
    assert client.state == ConnectionState.CLOSED
