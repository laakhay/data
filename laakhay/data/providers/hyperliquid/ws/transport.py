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
                            sub_type = parts[0]  # "candle", "trades", "l2Book", "activeAssetCtx", etc.
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

                    # Wait for subscription confirmations
                    # Hyperliquid sends {"channel": "subscriptionResponse", "data": {...}}
                    # Collect confirmations but don't block indefinitely
                    confirmations_received = 0
                    pending_messages = []
                    try:
                        # Try to receive confirmations with timeout
                        while confirmations_received < len(topics):
                            try:
                                confirm = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                                confirm_data = json.loads(confirm)
                                if confirm_data.get("channel") == "subscriptionResponse":
                                    confirmations_received += 1
                                    logger.debug(f"Subscription confirmed ({confirmations_received}/{len(topics)}): {confirm_data.get('data')}")
                                else:
                                    # Non-confirmation message - queue it for later
                                    pending_messages.append(confirm_data)
                            except asyncio.TimeoutError:
                                # Timeout waiting for confirmation - continue anyway
                                logger.warning(f"Timeout waiting for subscription confirmations ({confirmations_received}/{len(topics)})")
                                break
                    except Exception as e:
                        logger.warning(f"Error receiving subscription confirmations: {e}")
                    
                    # Yield any pending messages that came before confirmations
                    for msg in pending_messages:
                        yield msg

                    # Stream messages
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            # Skip subscription confirmations
                            if isinstance(data, dict):
                                if data.get("channel") == "subscriptionResponse":
                                    continue
                            yield data
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse message: {message}")
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

