"""Generic streaming feed scaffolding used by higher-level data feeds."""

from __future__ import annotations

import asyncio
import contextlib
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")

Callback = Callable[[T], Awaitable[None]] | Callable[[T], None]

_SINGLETON_KEY = "__single__"


@dataclass(frozen=True)
class _BaseSubscription[T]:
    callback: Callback
    keys: set[str] | None


class BaseStreamFeed[T]:
    """Reusable base for async streaming feeds with cache and subscriptions."""

    def __init__(
        self,
        provider: Any,
        *,
        key_selector: Callable[[T], str] | None = None,
        stale_threshold_seconds: int = 900,
    ) -> None:
        self._provider = provider
        self._key_selector = key_selector
        self._stale_threshold = stale_threshold_seconds

        self._lock = asyncio.Lock()
        self._running = False
        self._stream_task: asyncio.Task | None = None
        self._stream_args: dict[str, Any] = {}

        self._latest: dict[str, T] = {}
        self._subs: dict[str, _BaseSubscription[T]] = {}
        self._last_msg_time: float = 0.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def start(self, **stream_args: Any) -> None:
        """Start streaming with optional provider-specific arguments."""
        async with self._lock:
            if self._running:
                return
            self._stream_args = self._prepare_stream_args(dict(stream_args))
            await self._before_start(is_restart=False)
            self._running = True
            self._stream_task = asyncio.create_task(self._run_stream())

    async def stop(self) -> None:
        """Stop streaming and cancel background tasks."""
        async with self._lock:
            self._running = False
            if self._stream_task and not self._stream_task.done():
                self._stream_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._stream_task
            self._stream_task = None

    async def update_stream(self, **changes: Any) -> None:
        """Merge new stream arguments and restart the stream if running."""
        async with self._lock:
            updated = dict(self._stream_args)
            updated.update(changes)
            self._stream_args = self._prepare_stream_args(updated)
            if self._running:
                await self._restart_stream_locked()

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------
    def subscribe(self, callback: Callback, *, keys: Iterable[str] | None = None) -> str:
        """Subscribe to feed updates. Optionally filter by key (e.g., symbol)."""
        key_set: set[str] | None = None
        if keys is not None:
            key_set = {str(k) for k in keys}
        sub_id = uuid.uuid4().hex
        self._subs[sub_id] = _BaseSubscription(callback=callback, keys=key_set)
        self._schedule_update()
        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        """Remove a subscription by id."""
        if subscription_id in self._subs:
            self._subs.pop(subscription_id, None)
            self._schedule_update()

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------
    def get_latest(self, key: str | None = None) -> T | None:
        """Latest cached item for the given key (or singleton feed if None)."""
        cache_key = key if key is not None else _SINGLETON_KEY
        return self._latest.get(cache_key)

    def snapshot(self, keys: Iterable[str] | None = None) -> dict[str, T | None]:
        """Return a snapshot of the cache for provided keys (or all known keys)."""
        if keys is None:
            keys = list(self._latest.keys())
        out: dict[str, T | None] = {}
        for key in keys:
            out[str(key)] = self._latest.get(str(key))
        return out

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------
    def get_connection_status(self) -> dict[str, Any]:
        """Basic connection status details."""
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

    # ------------------------------------------------------------------
    # Hooks for subclasses
    # ------------------------------------------------------------------
    def _prepare_stream_args(self, args: dict[str, Any]) -> dict[str, Any]:
        """Allow subclasses to normalize/augment stream arguments."""
        return args

    async def _before_start(self, *, is_restart: bool) -> None:
        """Hook before launching or restarting the stream."""
        _ = is_restart

    def _stream_iterator(self) -> AsyncIterator[T]:
        """Return the provider async iterator for the current stream args."""
        raise NotImplementedError

    async def _handle_stream_exception(self, exc: Exception) -> None:
        """Hook for subclasses to handle stream errors."""
        _ = exc

    def _on_symbols_updated(self) -> None:
        """Symbol-specific feeds can override to react to symbol changes."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _run_stream(self) -> None:
        try:
            async for item in self._stream_iterator():
                key = self._select_key(item)
                await self._on_item(item, key)
                if self._should_dispatch(item, key):
                    await self._dispatch_item(item, key)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            await self._handle_stream_exception(exc)

    async def _on_item(self, item: T, key: str | None) -> None:
        """Default cache behavior when an item is received."""
        cache_key = key if key is not None else _SINGLETON_KEY
        self._latest[cache_key] = item
        self._last_msg_time = time.time()

    def _should_dispatch(self, item: T, key: str | None) -> bool:
        """Whether to dispatch to subscribers."""
        _ = (item, key)
        return bool(self._subs)

    async def _dispatch_item(self, item: T, key: str | None) -> None:
        """Dispatch to matching subscribers."""
        if not self._subs:
            return
        to_call: list[Callback] = []
        for sub in self._subs.values():
            if sub.keys is None or key is None or key in sub.keys:
                to_call.append(sub.callback)
        if not to_call:
            return
        loop = asyncio.get_running_loop()
        for cb in to_call:
            if asyncio.iscoroutinefunction(cb):
                loop.create_task(cb(item))
            else:
                loop.run_in_executor(None, cb, item)

    def _select_key(self, item: T) -> str | None:
        if self._key_selector is None:
            return None
        return self._key_selector(item)

    async def _restart_stream_locked(self) -> None:
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._stream_task
        if self._running:
            await self._before_start(is_restart=True)
            self._stream_task = asyncio.create_task(self._run_stream())

    def _schedule_update(self, **changes: Any) -> None:
        """Schedule a background stream update (non-blocking)."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self.update_stream(**changes))

    def _subscription_key_union(self) -> set[str]:
        keys: set[str] = set()
        for sub in self._subs.values():
            if sub.keys:
                keys |= sub.keys
        return keys


class SymbolStreamFeed(BaseStreamFeed[T]):
    """Feed base for symbol-aware streams with dynamic symbol management."""

    def __init__(
        self,
        provider: Any,
        *,
        key_selector: Callable[[T], str],
        stale_threshold_seconds: int = 900,
    ) -> None:
        super().__init__(
            provider,
            key_selector=key_selector,
            stale_threshold_seconds=stale_threshold_seconds,
        )
        self._requested_symbols: set[str] = set()
        self._symbols: list[str] = []

    async def start(self, *, symbols: Iterable[str], **stream_args: Any) -> None:  # type: ignore[override]
        self._requested_symbols = self._normalize_symbols(symbols)
        await super().start(**stream_args)

    async def set_symbols(self, symbols: Iterable[str]) -> None:
        normalized = self._normalize_symbols(symbols)
        if normalized == self._requested_symbols:
            return
        self._requested_symbols = normalized
        await self.update_stream()

    async def add_symbols(self, symbols: Iterable[str]) -> None:
        addition = self._normalize_symbols(symbols)
        if not addition.difference(self._requested_symbols):
            return
        self._requested_symbols |= addition
        await self.update_stream()

    async def remove_symbols(self, symbols: Iterable[str]) -> None:
        removal = self._normalize_symbols(symbols)
        if not removal.intersection(self._requested_symbols):
            return
        self._requested_symbols -= removal
        await self.update_stream()

    def snapshot(self, symbols: Iterable[str] | None = None) -> dict[str, T | None]:
        if symbols is None:
            symbols = self._symbols
        return super().snapshot(symbols)

    # Hooks ----------------------------------------------------------------
    def _prepare_stream_args(self, args: dict[str, Any]) -> dict[str, Any]:
        args = dict(args)
        effective = self._compute_effective_symbols()
        self._symbols = effective
        args["symbols"] = effective
        prepared = super()._prepare_stream_args(args)
        self._on_symbols_updated()
        return prepared

    def _compute_effective_symbols(self) -> list[str]:
        """Union of requested symbols and subscription-driven symbols."""
        combined = self._requested_symbols | self._subscription_key_union()
        return sorted(combined)

    def _normalize_symbols(self, symbols: Iterable[str]) -> set[str]:
        return {s.upper() for s in symbols}
