"""Reusable WebSocket transport with reconnect, timeouts, and backpressure.

This module is exchange-agnostic and is responsible only for I/O:
- Connect to a WebSocket URL with configured timeouts/sizing
- Reconnect with exponential backoff and jitter
- Yield raw messages (JSON-decoded if possible, else raw string)
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import websockets

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TransportConfig:
    ping_interval: int = 30
    ping_timeout: int = 10
    close_timeout: int = 10
    base_reconnect_delay: float = 1.0
    max_reconnect_delay: float = 30.0
    jitter: float = 0.2
    max_size: int | None = None
    max_queue: int | None = 1024


class WebSocketTransport:
    """Low-level WebSocket client with robust reconnect loop."""

    def __init__(self, config: TransportConfig | None = None) -> None:
        self._conf = config or TransportConfig()

    def _next_delay(self, delay: float) -> float:
        delay = min(delay * 2, self._conf.max_reconnect_delay)
        factor = random.uniform(1 - self._conf.jitter, 1 + self._conf.jitter)
        return max(0.5, delay * factor)

    def _connect_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "ping_interval": self._conf.ping_interval,
            "ping_timeout": self._conf.ping_timeout,
            "close_timeout": self._conf.close_timeout,
        }
        if self._conf.max_size is not None:
            kwargs["max_size"] = self._conf.max_size
        if self._conf.max_queue is not None:
            kwargs["max_queue"] = self._conf.max_queue
        return kwargs

    async def stream(self, url: str) -> AsyncIterator[Any]:
        """Yield messages from a WebSocket URL with auto-reconnect."""
        delay = self._conf.base_reconnect_delay
        while True:
            try:
                async with websockets.connect(url, **self._connect_kwargs()) as websocket:
                    delay = self._conf.base_reconnect_delay
                    async for message in websocket:
                        try:
                            yield json.loads(message)
                        except Exception:
                            yield message
            except asyncio.CancelledError:
                raise
            except websockets.exceptions.ConnectionClosed:
                await asyncio.sleep(delay)
                delay = self._next_delay(delay)
            except Exception as e:  # noqa: BLE001
                logger.error(f"WS transport error: {e}")
                await asyncio.sleep(delay)
                delay = self._next_delay(delay)
