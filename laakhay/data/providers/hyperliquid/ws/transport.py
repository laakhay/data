"""Hyperliquid-specific WebSocket transport with subscription support.

NOTE: Subscription format is based on common patterns.
This needs to be verified against actual Hyperliquid WebSocket API documentation.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import websockets

logger = logging.getLogger(__name__)


class HyperliquidWebSocketTransport:
    """WebSocket transport for Hyperliquid that handles subscription messages.

    Hyperliquid likely uses subscription messages similar to Bybit.
    Format to be verified.
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

    async def stream(self, topics: list[str]) -> AsyncIterator[Any]:
        """Stream messages from Hyperliquid WebSocket with auto-reconnect.

        Args:
            topics: List of topic names to subscribe to (e.g., ["candle.BTCUSDT.1m"])
        """
        while True:
            try:
                async with websockets.connect(
                    self.url,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout,
                ) as websocket:
                    self._reconnect_delay = 1.0

                    # Send subscription messages
                    # Hyperliquid format: {"method": "subscribe", "subscription": {"type": "candle", "coin": "BTC", "interval": "15m"}}
                    # For multiple subscriptions, send separate messages
                    for topic in topics:
                        # Parse topic format: "candle.BTC.15m" -> {"type": "candle", "coin": "BTC", "interval": "15m"}
                        # Or "activeAssetCtx.BTC" -> {"type": "activeAssetCtx", "coin": "BTC"}
                        parts = topic.split(".")
                        if len(parts) >= 2:
                            sub_type = parts[
                                0
                            ]  # "candle", "trades", "l2Book", "activeAssetCtx", etc.
                            coin = parts[1]  # Symbol
                            subscription: dict[str, Any] = {"type": sub_type, "coin": coin}
                            if sub_type == "candle" and len(parts) >= 3:
                                subscription["interval"] = parts[2]

                            subscribe_msg = {
                                "method": "subscribe",
                                "subscription": subscription,
                            }
                            await websocket.send(json.dumps(subscribe_msg))
                    logger.debug(f"Subscribed to {len(topics)} topics on Hyperliquid WebSocket")

                    # Hyperliquid may send subscription responses or start streaming immediately
                    # Don't block waiting for confirmations - start streaming right away
                    # The server will send data messages or error messages if subscription fails
                    logger.debug(f"Sent {len(topics)} subscription messages, starting to stream")

                    # Stream messages
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            # Skip subscription confirmations and empty messages
                            if isinstance(data, dict):
                                channel = data.get("channel", "")
                                # Skip subscription responses
                                if channel == "subscriptionResponse":
                                    logger.debug(f"Subscription response: {data.get('data')}")
                                    continue
                                # Skip ping/pong messages
                                if channel == "pong" or data.get("method") == "pong":
                                    continue
                            # Yield actual data messages
                            yield data
                        except json.JSONDecodeError as e:
                            msg_str = (
                                message.decode("utf-8", errors="replace")[:100]
                                if isinstance(message, bytes)
                                else str(message)[:100]
                            )
                            logger.warning(f"Failed to parse message: {msg_str}... Error: {e}")
                            continue
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
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
