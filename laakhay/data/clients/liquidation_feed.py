"""Thin feed for Liquidations with cache, pub-sub, and basic health.

Provider contract (duck-typed):
- stream_liquidations() -> AsyncIterator[Liquidation]
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any, Union

from ..models import Liquidation

Callback = Union[Callable[[Liquidation], Awaitable[None]], Callable[[Liquidation], None]]


@dataclass(frozen=True)
class _Sub:
    callback: Callback
    symbols: set[str] | None  # None means all


class LiquidationFeed:
    """Real-time Liquidations feed with cache and subscriptions."""

    def __init__(
        self,
        provider: Any,
        *,
        stale_threshold_seconds: int = 900,
    ) -> None:
        self._provider = provider
        self._stale_threshold = stale_threshold_seconds

        # Streaming state
        self._stream_task: asyncio.Task | None = None
        self._running = False

        # Cache: latest liquidation per symbol
        self._latest: dict[str, Liquidation] = {}

        # Subscriptions
        self._subs: dict[str, _Sub] = {}

        # Health
        self._last_msg_time: float = 0.0

        # Lock
        self._lock = asyncio.Lock()

    # Lifecycle
    async def start(self) -> None:
        async with self._lock:
            if self._running:
                return
            self._running = True
            self._stream_task = asyncio.create_task(self._stream_loop())

    async def stop(self) -> None:
        async with self._lock:
            self._running = False
            if self._stream_task and not self._stream_task.done():
                self._stream_task.cancel()
                try:
                    await self._stream_task
                except asyncio.CancelledError:
                    pass
            self._stream_task = None

    # Subscriptions
    def subscribe(self, callback: Callback, *, symbols: Iterable[str] | None = None) -> str:
        subs_symbols: set[str] | None = None
        if symbols is not None:
            subs_symbols = {s.upper() for s in symbols}
        sub = _Sub(callback=callback, symbols=subs_symbols)
        sub_id = uuid.uuid4().hex
        self._subs[sub_id] = sub
        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        self._subs.pop(subscription_id, None)

    # Cache access
    def get_latest(self, symbol: str) -> Liquidation | None:
        return self._latest.get(symbol.upper())

    def snapshot(self, symbols: Iterable[str] | None = None) -> dict[str, Liquidation | None]:
        out: dict[str, Liquidation | None] = {}
        if symbols is None:
            symbols = list(self._latest.keys())
        for s in symbols:
            out[s.upper()] = self._latest.get(s.upper())
        return out

    # Health
    def get_connection_status(self) -> dict[str, Any]:
        now = time.time()
        healthy = (
            (now - self._last_msg_time) <= self._stale_threshold if self._last_msg_time else False
        )
        return {
            "active_connections": 1 if self._stream_task and not self._stream_task.done() else 0,
            "healthy_connections": 1 if healthy else 0,
            "stale_connections": [] if healthy else ["connection_0"],
            "last_message_time": {"connection_0": self._last_msg_time},
        }

    # Internals
    async def _stream_loop(self) -> None:
        try:
            async for liq in self._provider.stream_liquidations():
                # Cache and health
                self._latest[liq.symbol.upper()] = liq
                self._last_msg_time = time.time()

                # Dispatch
                if self._subs:
                    await self._dispatch(liq)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Quiet failure; caller can restart
            pass

    async def _dispatch(self, liq: Liquidation) -> None:
        to_call: list[tuple[Callback, Liquidation]] = []
        for sub in self._subs.values():
            if sub.symbols is None or liq.symbol.upper() in sub.symbols:
                to_call.append((sub.callback, liq))
        for cb, item in to_call:
            if asyncio.iscoroutinefunction(cb):
                asyncio.create_task(cb(item))
            else:
                loop = asyncio.get_running_loop()
                loop.run_in_executor(None, cb, item)
