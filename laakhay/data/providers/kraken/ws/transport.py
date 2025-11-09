"""Kraken-specific WebSocket transport with subscription support."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import websockets

logger = logging.getLogger(__name__)


class KrakenWebSocketTransport:
    """WebSocket transport for Kraken that handles subscription messages.

    Kraken WebSocket API v2 uses a subscription-based model:
    - Subscribe: {"method": "subscribe", "params": {"channel": "channel_name", "symbol": "symbol"}}
    - Messages: {"channel": "channel_name", "data": {...}}
    """

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

    async def stream(self, channels: list[str]) -> AsyncIterator[Any]:
        """Stream messages from Kraken WebSocket with auto-reconnect.

        Args:
            channels: List of channel names to subscribe to (e.g., ["ohlc-PI_XBTUSD-1", "trade-PI_XBTUSD"])
        """
        while True:
            try:
                async with websockets.connect(
                    self.url,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout,
                ) as websocket:
                    self._reconnect_delay = 1.0

                    # Kraken WebSocket v2 subscription format
                    # For each channel, send subscription message
                    for channel in channels:
                        # Parse channel name to extract channel type and symbol
                        # Format: {channel_type}-{symbol}-{optional_params}
                        parts = channel.split("-")
                        if len(parts) < 2:
                            logger.warning(f"Invalid channel format: {channel}")
                            continue

                        channel_type = parts[0]  # e.g., "ohlc", "trade", "book"
                        symbol = "-".join(parts[1:])  # Rest is symbol (may contain dashes)

                        subscribe_msg: dict[str, Any] = {
                            "method": "subscribe",
                            "params": {
                                "channel": channel_type,
                                "symbol": symbol,
                            },
                        }

                        # Add interval for OHLC channels
                        if channel_type == "ohlc" and len(parts) > 2:
                            params = subscribe_msg["params"]
                            if isinstance(params, dict):
                                params["interval"] = parts[-1]

                        await websocket.send(json.dumps(subscribe_msg))
                        logger.debug(f"Subscribed to channel: {channel}")

                    # Wait for subscription confirmations
                    try:
                        for _ in range(len(channels)):
                            confirm = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            confirm_data = json.loads(confirm)
                            if confirm_data.get("error"):
                                logger.error(f"Subscription failed: {confirm_data}")
                            else:
                                logger.debug(f"Subscription confirmed: {confirm_data}")
                    except TimeoutError:
                        logger.warning("No subscription confirmation received")

                    # Stream messages
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            # Skip subscription confirmations and pings
                            if isinstance(data, dict):
                                # Skip subscription responses
                                if (
                                    data.get("method") == "subscribe"
                                    or data.get("event") == "subscriptionStatus"
                                ):
                                    continue
                                # Skip pings
                                if data.get("event") == "ping" or data.get("event") == "pong":
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
