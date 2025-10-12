"""Thin feed for Open Interest with cache, pub-sub, and basic health.

Provider contract (duck-typed):
- stream_open_interest(symbols: list[str], period: str) -> AsyncIterator[OpenInterest]

Notes:
- We keep this feed provider-agnostic. The provider validates period values.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any

from ..models import OpenInterest

Callback = Callable[[OpenInterest], Awaitable[None]] | Callable[[OpenInterest], None]


@dataclass(frozen=True)
class _Sub:
    callback: Callback
    symbols: set[str] | None  # None means all


class OpenInterestFeed:
    """Real-time Open Interest feed with cache and subscriptions."""

    def __init__(
        self,
        provider: Any,
        *,
        stale_threshold_seconds: int = 900,
    ) -> None:
        self._provider = provider
        self._stale_threshold = stale_threshold_seconds

        # Streaming state
        self._symbols: list[str] = []
        self._requested_symbols: set[str] = set()
        self._period: str = "5m"
        self._stream_task: asyncio.Task | None = None
        self._running = False

        # Cache: latest OI per symbol
        self._latest: dict[str, OpenInterest] = {}

        # Subscriptions
        self._subs: dict[str, _Sub] = {}

        # Health
        self._last_msg_time: float = 0.0

        # Lock
        self._lock = asyncio.Lock()

    # Lifecycle
    async def start(self, *, symbols: Iterable[str], period: str = "5m") -> None:
        async with self._lock:
            if self._running:
                return
            self._requested_symbols = {s.upper() for s in symbols}
            self._symbols = sorted(self._requested_symbols)
            self._period = period
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

    # Dynamic symbols
    async def set_symbols(self, symbols: Iterable[str]) -> None:
        async with self._lock:
            self._requested_symbols = {s.upper() for s in symbols}
            self._symbols = sorted(self._requested_symbols)
            if self._running:
                if self._stream_task and not self._stream_task.done():
                    self._stream_task.cancel()
                    try:
                        await self._stream_task
                    except asyncio.CancelledError:
                        pass
                self._stream_task = asyncio.create_task(self._stream_loop())

    async def add_symbols(self, symbols: Iterable[str]) -> None:
        to_add = {s.upper() for s in symbols}
        async with self._lock:
            self._requested_symbols |= to_add
            updated = sorted(self._requested_symbols)
        if updated != self._symbols:
            await self.set_symbols(updated)

    async def remove_symbols(self, symbols: Iterable[str]) -> None:
        to_remove = {s.upper() for s in symbols}
        async with self._lock:
            self._requested_symbols -= to_remove
            updated = sorted(self._requested_symbols)
        if updated != self._symbols:
            await self.set_symbols(updated)

    # Subscriptions
    def subscribe(self, callback: Callback, *, symbols: Iterable[str] | None = None) -> str:
        subs_symbols: set[str] | None = None
        if symbols is not None:
            subs_symbols = {s.upper() for s in symbols}
        sub = _Sub(callback=callback, symbols=subs_symbols)
        sub_id = uuid.uuid4().hex
        self._subs[sub_id] = sub

        # Expand streaming set if subscriber asks for more symbols
        if subs_symbols:

            async def _maybe_update():
                async with self._lock:
                    self._requested_symbols |= subs_symbols
                    eff = sorted(self._requested_symbols)
                    if eff != self._symbols:
                        self._symbols = eff
                        if self._running:
                            if self._stream_task and not self._stream_task.done():
                                self._stream_task.cancel()
                                try:
                                    await self._stream_task
                                except asyncio.CancelledError:
                                    pass
                            self._stream_task = asyncio.create_task(self._stream_loop())

            try:
                asyncio.get_running_loop().create_task(_maybe_update())
            except RuntimeError:
                pass
        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        self._subs.pop(subscription_id, None)

        async def _maybe_shrink():
            async with self._lock:
                eff = sorted(self._requested_symbols)
                if eff != self._symbols:
                    self._symbols = eff
                    if self._running:
                        if self._stream_task and not self._stream_task.done():
                            self._stream_task.cancel()
                            try:
                                await self._stream_task
                            except asyncio.CancelledError:
                                pass
                        self._stream_task = asyncio.create_task(self._stream_loop())

        try:
            asyncio.get_running_loop().create_task(_maybe_shrink())
        except RuntimeError:
            pass

    # Cache access
    def get_latest(self, symbol: str) -> OpenInterest | None:
        return self._latest.get(symbol.upper())

    def snapshot(self, symbols: Iterable[str] | None = None) -> dict[str, OpenInterest | None]:
        if symbols is None:
            symbols = list(self._symbols)
        out: dict[str, OpenInterest | None] = {}
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
            async for oi in self._provider.stream_open_interest(self._symbols, period=self._period):
                # Cache and health
                self._latest[oi.symbol.upper()] = oi
                self._last_msg_time = time.time()

                # Dispatch
                if self._subs:
                    await self._dispatch(oi)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Quiet failure; caller can restart
            pass

    async def _dispatch(self, oi: OpenInterest) -> None:
        to_call: list[tuple[Callback, OpenInterest]] = []
        for sub in self._subs.values():
            if sub.symbols is None or oi.symbol.upper() in sub.symbols:
                to_call.append((sub.callback, oi))
        for cb, item in to_call:
            if asyncio.iscoroutinefunction(cb):
                asyncio.create_task(cb(item))
            else:
                loop = asyncio.get_running_loop()
                loop.run_in_executor(None, cb, item)
