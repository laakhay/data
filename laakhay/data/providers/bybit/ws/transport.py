"""Bybit-specific WebSocket transport with subscription support."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import websockets

logger = logging.getLogger(__name__)


class BybitWebSocketTransport:
    """WebSocket transport for Bybit that handles subscription messages."""

    def __init__(
        self,
        url: str,
        ping_interval: float = 20.0,
        ping_timeout: float = 10.0,
        max_reconnect_delay: float = 30.0,
    ) -> None:
        self.url = url
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.max_reconnect_delay = max_reconnect_delay
        self._reconnect_delay = 1.0

    async def stream(self, topics: list[str]) -> AsyncIterator[Any]:
        """Stream messages from Bybit WebSocket with auto-reconnect.

        Args:
            topics: List of topic names to subscribe to (e.g., ["kline.1.BTCUSDT"])
        """
        while True:
            try:
                async with websockets.connect(
                    self.url,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout,
                ) as websocket:
                    self._reconnect_delay = 1.0

                    # Send subscription message
                    subscribe_msg = {
                        "op": "subscribe",
                        "args": topics,
                    }
                    await websocket.send(json.dumps(subscribe_msg))
                    logger.debug(f"Subscribed to {len(topics)} topics on Bybit WebSocket")

                    # Wait for subscription confirmation
                    try:
                        confirm = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        confirm_data = json.loads(confirm)
                        if confirm_data.get("success") is False:
                            logger.error(f"Subscription failed: {confirm_data}")
                    except TimeoutError:
                        logger.warning("No subscription confirmation received")

                    # Stream messages
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            # Skip subscription confirmations and pings
                            if isinstance(data, dict) and (
                                data.get("op") == "subscribe" or data.get("topic") == ""
                            ):
                                continue
                            yield data
                        except json.JSONDecodeError:
                            msg_str = (
                                message.decode("utf-8", errors="replace")
                                if isinstance(message, bytes)
                                else str(message)
                            )
                            logger.warning(f"Failed to parse message: {msg_str}")
                            continue

            except asyncio.CancelledError:
                raise
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, self.max_reconnect_delay)
            except Exception as e:  # noqa: BLE001
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, self.max_reconnect_delay)
