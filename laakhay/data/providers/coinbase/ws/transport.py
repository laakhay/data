"""Coinbase-specific WebSocket transport with subscription support.

Coinbase Advanced Trade API requires sending subscription messages after connecting.
Format: {"type": "subscribe", "product_ids": ["BTC-USD"], "channel": "matches"}
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import websockets

logger = logging.getLogger(__name__)


class CoinbaseWebSocketTransport:
    """WebSocket transport for Coinbase Exchange API that handles subscription messages.

    Coinbase Exchange API WebSocket format:
    - Connect to wss://ws-feed.exchange.coinbase.com
    - Send subscription message: {"type": "subscribe", "product_ids": ["BTC-USD"], "channels": ["matches"]}
    - Note: Exchange API uses "channels" (plural, array), not "channel" (singular)
    - Available channels: "matches", "level2", "ticker", "heartbeat"
    - Exchange API does NOT support candles via WebSocket (REST only)
    """

    def __init__(
        self,
        url: str,
        ping_interval: float = 30.0,
        ping_timeout: float = 10.0,
        max_reconnect_delay: float = 30.0,
    ) -> None:
        self.url = url
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.max_reconnect_delay = max_reconnect_delay
        self._reconnect_delay = 1.0

    async def stream(self, topics: list[str]) -> AsyncIterator[Any]:
        """Stream messages from Coinbase WebSocket with auto-reconnect.

        Args:
            topics: List of topic names in format "BTC-USD:matches" or "BTC-USD:candles:ONE_MINUTE"
        """
        while True:
            try:
                async with websockets.connect(
                    self.url,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout,
                ) as websocket:
                    self._reconnect_delay = 1.0

                    # Parse topics and group by channel
                    # Topics format: "BTC-USD:matches", "BTC-USD:level2"
                    # Note: Exchange API doesn't support candles via WebSocket
                    all_product_ids: set[str] = set()
                    all_channels: set[str] = set()

                    for topic in topics:
                        parts = topic.split(":")
                        if len(parts) >= 2:
                            product_id = parts[0]  # "BTC-USD"
                            channel = parts[1]  # "matches", "level2"

                            # Skip candles - Exchange API doesn't support WebSocket candles
                            if channel == "candles":
                                logger.warning(
                                    f"Skipping candles channel for {product_id} - Exchange API doesn't support WebSocket candles"
                                )
                                continue

                            # Skip level2 - Exchange API requires authentication for level2/level3/full channels
                            # Only "matches" (trades) and "ticker" are available without auth
                            if channel == "level2":
                                logger.warning(
                                    f"Skipping level2 channel for {product_id} - Exchange API requires authentication for level2"
                                )
                                continue

                            all_product_ids.add(product_id)
                            all_channels.add(channel)

                    # Exchange API format: single subscription with all product_ids and channels
                    # Format: {"type": "subscribe", "product_ids": [...], "channels": [...]}
                    if all_product_ids and all_channels:
                        subscribe_msg: dict[str, Any] = {
                            "type": "subscribe",
                            "product_ids": sorted(all_product_ids),  # Sort for consistency
                            "channels": sorted(
                                all_channels
                            ),  # Exchange API uses "channels" (plural, array)
                        }
                        subscribe_json = json.dumps(subscribe_msg)
                        logger.debug(f"Sending subscription: {subscribe_json}")
                        await websocket.send(subscribe_json)
                        logger.info(
                            f"Sent subscription for {len(all_product_ids)} products ({', '.join(sorted(all_product_ids))}), {len(all_channels)} channels ({', '.join(sorted(all_channels))}) on Coinbase Exchange WebSocket"
                        )
                    else:
                        logger.warning(f"No valid subscriptions after parsing {len(topics)} topics")
                        # If no valid subscriptions, wait a bit before reconnecting
                        await asyncio.sleep(5)
                        continue

                    # Stream messages
                    async for message in websocket:
                        try:
                            data = json.loads(message)

                            # Skip subscription confirmations and control messages
                            if isinstance(data, dict):
                                msg_type = data.get("type", "")

                                # Handle subscription responses
                                if msg_type == "subscriptions" or msg_type == "subscribe":
                                    logger.info(f"Subscription confirmation received: {data}")
                                    # Check for errors in subscription response
                                    if (
                                        "error" in str(data).lower()
                                        or "reject" in str(data).lower()
                                    ):
                                        logger.error(f"Subscription rejected: {data}")
                                        # If subscription rejected, break to reconnect
                                        break
                                    continue

                                # Handle l2update snapshot (level2 initial snapshot)
                                if msg_type == "snapshot":
                                    # Level2 snapshot - yield it for order book initialization
                                    yield data
                                    continue

                                # Skip heartbeat/ping messages (Exchange API sends heartbeat)
                                if (
                                    msg_type == "heartbeat"
                                    or msg_type == "pong"
                                    or msg_type == "ping"
                                ):
                                    continue

                                # Handle error messages
                                if msg_type == "error":
                                    error_msg = data.get("message", str(data))
                                    logger.error(f"Coinbase WebSocket error: {error_msg}")
                                    # Don't yield errors, but don't break connection either
                                    continue

                            # Yield actual data messages (match, l2update, ticker, etc.)
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
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(
                    f"Coinbase WebSocket connection closed (code: {e.code}, reason: {e.reason}), reconnecting..."
                )
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, self.max_reconnect_delay)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Coinbase WebSocket error: {e}")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, self.max_reconnect_delay)
