"""WebSocket client for real-time data streaming."""

import asyncio
import contextlib
import logging
from collections.abc import Callable
from enum import Enum
from typing import Any

import websockets

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """WebSocket connection state."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSED = "closed"


class WebSocketClient:
    """Async WebSocket client with auto-reconnect.

    Features:
    - Automatic reconnection with exponential backoff
    - Ping/pong keepalive
    - Message handler callback
    - Graceful shutdown
    """

    def __init__(
        self,
        url: str,
        on_message: Callable[[dict], Any],
        ping_interval: float = 30.0,
        ping_timeout: float = 10.0,
        max_reconnect_delay: float = 30.0,
    ) -> None:
        """Initialize WebSocket client.

        Args:
            url: WebSocket URL to connect to
            on_message: Callback function for incoming messages
            ping_interval: Interval between ping frames (seconds)
            ping_timeout: Timeout for pong response (seconds)
            max_reconnect_delay: Maximum delay between reconnection attempts
        """
        self.url = url
        self.on_message = on_message
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.max_reconnect_delay = max_reconnect_delay

        self._ws: Any | None = None
        self._state = ConnectionState.DISCONNECTED
        self._reconnect_delay = 1.0
        self._should_reconnect = True
        self._receive_task: asyncio.Task | None = None

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._state == ConnectionState.CONNECTED and self._ws is not None

    async def connect(self) -> None:
        """Connect to WebSocket server.

        Raises:
            ConnectionError: If connection fails
        """
        if self._state in (ConnectionState.CONNECTING, ConnectionState.CONNECTED):
            logger.warning(f"Already {self._state.value}, skipping connect")
            return

        self._state = ConnectionState.CONNECTING
        logger.info(f"Connecting to {self.url}")

        try:
            self._ws = await websockets.connect(
                self.url,
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout,
            )
            self._state = ConnectionState.CONNECTED
            self._reconnect_delay = 1.0  # Reset delay on successful connection
            logger.info("WebSocket connected successfully")

            # Start receiving messages
            self._receive_task = asyncio.create_task(self._receive_loop())

        except Exception as e:
            self._state = ConnectionState.DISCONNECTED
            logger.error(f"Connection failed: {e}")
            raise ConnectionError(f"Failed to connect to {self.url}: {e}") from e

    async def _receive_loop(self) -> None:
        """Receive messages from WebSocket."""
        if self._ws is None:
            return
        try:
            async for message in self._ws:
                try:
                    # Parse JSON message
                    import json

                    data = json.loads(message)

                    # Call user callback
                    if asyncio.iscoroutinefunction(self.on_message):
                        await self.on_message(data)
                    else:
                        self.on_message(data)

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self._state = ConnectionState.DISCONNECTED

            # Auto-reconnect if enabled
            if self._should_reconnect:
                await self._reconnect()

        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
            self._state = ConnectionState.DISCONNECTED

    async def _reconnect(self) -> None:
        """Reconnect with exponential backoff."""
        self._state = ConnectionState.RECONNECTING

        while self._should_reconnect:
            logger.info(f"Reconnecting in {self._reconnect_delay}s...")
            await asyncio.sleep(self._reconnect_delay)

            try:
                await self.connect()
                logger.info("Reconnected successfully")
                break
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
                # Exponential backoff with max delay
                self._reconnect_delay = min(self._reconnect_delay * 2, self.max_reconnect_delay)

    async def disconnect(self) -> None:
        """Gracefully disconnect from WebSocket."""
        logger.info("Disconnecting WebSocket")
        self._should_reconnect = False
        self._state = ConnectionState.CLOSED

        # Cancel receive task
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._receive_task

        # Close WebSocket connection
        if self._ws and not self._ws.closed:
            await self._ws.close()

        self._ws = None
        logger.info("WebSocket disconnected")

    async def send(self, data: dict) -> None:
        """Send message to WebSocket.

        Args:
            data: Dictionary to send as JSON

        Raises:
            RuntimeError: If not connected
        """
        if not self.is_connected or self._ws is None:
            raise RuntimeError("WebSocket not connected")

        import json

        message = json.dumps(data)
        await self._ws.send(message)

    async def __aenter__(self) -> "WebSocketClient":
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.disconnect()
