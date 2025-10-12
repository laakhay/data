"""High-level DataFeed for real-time candles with cache, pub-sub, and health.

This wraps a provider that supports Binance-style WebSocket streaming and
exposes a developer-friendly API for service layers:

- start/stop lifecycle for streaming a set of symbols at a given interval
- synchronous latest-candle cache reads for fast polling paths
- subscribe/unsubscribe to receive candle callbacks (only_closed by default)
- basic connection health status derived from message recency per chunk

Notes:
- Initial version assumes a static symbol set passed to `start(...)`.
  Subscriptions can be a subset of that set. Dynamic expansion/shrink of the
  underlying stream set can be added later if needed.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any, Union

from ..core import TimeInterval
from ..models import Candle

Callback = Union[Callable[[Candle], Awaitable[None]], Callable[[Candle], None]]

@dataclass(frozen=True)
class _Sub:
    callback: Callback
    symbols: set[str] | None  # None means "all effective symbols"
    interval: TimeInterval
    only_closed: bool


class DataFeed:
    """Real-time data feed with cache and subscriptions."""

    def __init__(
        self,
        provider: Any,
        *,
        stale_threshold_seconds: int = 900,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
        max_streams_per_connection: int | None = None,
    ) -> None:
        self._provider = provider
        self._stale_threshold = stale_threshold_seconds
        self._throttle_ms = throttle_ms
        self._dedupe = dedupe_same_candle
        self._override_streams_per_conn = max_streams_per_connection

        # Streaming state
        # Currently active stream symbol set (effective set)
        self._symbols: list[str] = []
        # Requested symbols via start/set/add/remove (global intent)
        self._requested_symbols: set[str] = set()
        self._interval: TimeInterval | None = None
        self._only_closed: bool = True
        self._stream_task: asyncio.Task | None = None
        self._running = False

        # Cache: latest and previous-closed per (symbol, interval)
        self._latest: dict[tuple[str, TimeInterval], Candle] = {}
        self._prev_closed: dict[tuple[str, TimeInterval], Candle] = {}

        # Subscriptions
        self._subs: dict[str, _Sub] = {}

        # Health tracking (derived by chunk id)
        self._chunk_last_msg: dict[int, float] = {}
        self._symbol_chunk_id: dict[str, int] = {}

        # Lock for updates
        self._lock = asyncio.Lock()

    # ----------------------
    # Lifecycle
    # ----------------------
    async def start(
        self,
        *,
        symbols: Iterable[str],
        interval: TimeInterval = TimeInterval.M1,
        only_closed: bool = True,
        # Warm-up behavior: 0 = disabled, >0 = fetch up to this many historical candles
        # per symbol via provider.get_candles before starting streams. Best-effort and
        # non-fatal if provider doesn't support it or returns errors.
        warm_up: int = 0,
    ) -> None:
        """Start streaming for a static symbol set.

        Args:
            symbols: Iterable of symbols to stream (e.g., ["BTCUSDT", ...])
            interval: Candle interval (default 1m)
            only_closed: Emit only closed candles (recommended)
        """
        async with self._lock:
            if self._running:
                return
            if symbols is not None:
                self._requested_symbols = {s.upper() for s in symbols}
            # Compute effective symbol set = requested ∪ subs' unions
            self._symbols = self._compute_effective_symbols()
            self._interval = interval
            self._only_closed = only_closed
            self._assign_chunk_ids(self._symbols)
            # Optionally prefill cache from provider REST before starting streams.
            # warm_up > 0 indicates the per-symbol limit to request; 0 disables warm-up.
            if warm_up and warm_up > 0:
                try:
                    await self._prefill_from_historical(self._symbols, self._interval, warm_up)
                except Exception:
                    # Prefill best-effort; don't fail start on provider errors
                    pass

            self._running = True
            self._stream_task = asyncio.create_task(self._stream_loop())

    async def stop(self) -> None:
        """Stop streaming and cleanup."""
        async with self._lock:
            self._running = False
            if self._stream_task and not self._stream_task.done():
                self._stream_task.cancel()
                try:
                    await self._stream_task
                except asyncio.CancelledError:
                    pass
            self._stream_task = None

    # ----------------------
    # Dynamic symbol management
    # ----------------------
    async def set_symbols(self, symbols: Iterable[str]) -> None:
        """Replace the current symbol set and restart streaming if running."""
        new_syms = [s.upper() for s in symbols]
        async with self._lock:
            self._requested_symbols = set(new_syms)
            self._symbols = self._compute_effective_symbols()
            self._assign_chunk_ids(self._symbols)
            if self._running:
                # restart stream with new set
                if self._stream_task and not self._stream_task.done():
                    self._stream_task.cancel()
                    try:
                        await self._stream_task
                    except asyncio.CancelledError:
                        pass
                self._stream_task = asyncio.create_task(self._stream_loop())

    async def add_symbols(self, symbols: Iterable[str]) -> None:
        """Add symbols to the current set and restart streaming if changed."""
        to_add = {s.upper() for s in symbols}
        async with self._lock:
            self._requested_symbols |= to_add
            updated = self._compute_effective_symbols()
        if updated != self._symbols:
            await self.set_symbols(updated)

    async def remove_symbols(self, symbols: Iterable[str]) -> None:
        """Remove symbols from the current set and restart streaming if changed."""
        to_remove = {s.upper() for s in symbols}
        async with self._lock:
            self._requested_symbols -= to_remove
            updated = self._compute_effective_symbols()
        if updated != self._symbols:
            await self.set_symbols(updated)

    # ----------------------
    # Subscriptions
    # ----------------------
    def subscribe(
        self,
        callback: Callback,
        *,
        symbols: Iterable[str] | None = None,
        interval: TimeInterval | None = None,
        only_closed: bool | None = None,
    ) -> str:
        """Subscribe to candle updates for given symbols.

        Returns a subscription_id to later unsubscribe.

        If symbols is None, subscriber receives all effective symbols.
        """
        if interval is None:
            if self._interval is None:
                raise RuntimeError("DataFeed not started: interval unknown")
            interval = self._interval
        if only_closed is None:
            only_closed = self._only_closed

        subs_symbols: set[str] | None = None
        if symbols is not None:
            subs_symbols = {s.upper() for s in symbols}
        sub = _Sub(
            callback=callback, symbols=subs_symbols, interval=interval, only_closed=only_closed
        )
        sub_id = uuid.uuid4().hex
        self._subs[sub_id] = sub

        # If subscriber requested additional symbols, fold into effective set
        if subs_symbols:
            # Update requested set minimally to include these symbols
            # so the underlying stream covers them.
            async def _maybe_update():
                async with self._lock:
                    # don't mutate requested_symbols permanently if you want
                    # subs-only symbols to go away after unsubscribe; but for
                    # simplicity, add to requested set to keep stream stable
                    self._requested_symbols |= subs_symbols  # simple, robust
                    eff = self._compute_effective_symbols()
                    if eff != self._symbols:
                        self._symbols = eff
                        self._assign_chunk_ids(self._symbols)
                        if self._running:
                            if self._stream_task and not self._stream_task.done():
                                self._stream_task.cancel()
                                try:
                                    await self._stream_task
                                except asyncio.CancelledError:
                                    pass
                            self._stream_task = asyncio.create_task(self._stream_loop())

            # schedule update but don't block caller
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_maybe_update())
            except RuntimeError:
                # If not in async loop (rare for services), ignore
                pass
        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        self._subs.pop(subscription_id, None)

        # Recompute effective set from requested + subs; rebuild if shrunk
        async def _maybe_shrink():
            async with self._lock:
                eff = self._compute_effective_symbols()
                if eff != self._symbols:
                    self._symbols = eff
                    self._assign_chunk_ids(self._symbols)
                    if self._running:
                        if self._stream_task and not self._stream_task.done():
                            self._stream_task.cancel()
                            try:
                                await self._stream_task
                            except asyncio.CancelledError:
                                pass
                        self._stream_task = asyncio.create_task(self._stream_loop())

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_maybe_shrink())
        except RuntimeError:
            pass

    # ----------------------
    # Cache access
    # ----------------------
    def get_latest_candle(
        self, symbol: str, *, interval: TimeInterval | None = None
    ) -> Candle | None:
        """Get the latest candle from cache (O(1), non-blocking)."""
        if interval is None:
            interval = self._interval or TimeInterval.M1
        return self._latest.get((symbol.upper(), interval))

    def get_previous_closed(
        self, symbol: str, *, interval: TimeInterval | None = None
    ) -> Candle | None:
        if interval is None:
            interval = self._interval or TimeInterval.M1
        return self._prev_closed.get((symbol.upper(), interval))

    def snapshot(
        self, symbols: Iterable[str] | None = None, *, interval: TimeInterval | None = None
    ) -> dict[str, Candle | None]:
        """Return a dict of latest candles for given symbols (or all effective)."""
        if interval is None:
            interval = self._interval or TimeInterval.M1
        if symbols is None:
            symbols = list(self._symbols)
        out: dict[str, Candle | None] = {}
        for s in symbols:
            out[s] = self._latest.get((s.upper(), interval))
        return out

    # Sugar alias for subscribe
    def on_candle(
        self,
        callback: Callback,
        *,
        symbols: Iterable[str] | None = None,
        interval: TimeInterval | None = None,
        only_closed: bool | None = None,
    ) -> str:
        return self.subscribe(callback, symbols=symbols, interval=interval, only_closed=only_closed)

    # ----------------------
    # Health
    # ----------------------
    def get_connection_status(self) -> dict[str, Any]:
        """Summarize connection health derived from per-chunk last message times."""
        now = time.time()
        stale_ids: list[str] = []
        healthy = 0
        for cid, ts in self._chunk_last_msg.items():
            if now - ts <= self._stale_threshold:
                healthy += 1
            else:
                stale_ids.append(f"connection_{cid}")
        return {
            "active_connections": len(self._chunk_last_msg),
            "healthy_connections": healthy,
            "stale_connections": stale_ids,
            "last_message_time": {
                f"connection_{cid}": ts for cid, ts in self._chunk_last_msg.items()
            },
        }

    # ----------------------
    # Internals
    # ----------------------
    async def _stream_loop(self) -> None:
        assert self._interval is not None
        try:
            async for candle in self._provider.stream_candles_multi(
                self._symbols,
                self._interval,
                only_closed=self._only_closed,
                throttle_ms=self._throttle_ms,
                dedupe_same_candle=self._dedupe,
            ):
                # Update cache
                key = (candle.symbol.upper(), self._interval)
                closed = bool(candle.is_closed)
                if closed:
                    prev = self._latest.get(key)
                    if prev is not None:
                        self._prev_closed[key] = prev
                self._latest[key] = candle

                # Update health (by chunk)
                cid = self._symbol_chunk_id.get(candle.symbol.upper())
                if cid is not None:
                    self._chunk_last_msg[cid] = time.time()

                # Dispatch to subscribers
                if self._subs:
                    await self._dispatch(candle)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Keep task quiet on exceptions; next start() will recreate
            pass

    async def _dispatch(self, candle: Candle) -> None:
        to_call: list[tuple[Callback, Candle]] = []
        for sub in self._subs.values():
            if sub.interval != self._interval:
                continue
            if sub.symbols is None or candle.symbol.upper() in sub.symbols:
                to_call.append((sub.callback, candle))
        # Fire callbacks (don't block stream)
        for cb, c in to_call:
            if asyncio.iscoroutinefunction(cb):
                asyncio.create_task(cb(c))
            else:
                # run sync cb in default loop executor to avoid blocking
                loop = asyncio.get_running_loop()
                loop.run_in_executor(None, cb, c)

    def _assign_chunk_ids(self, symbols: list[str]) -> None:
        # Mirror provider's chunking to derive per-connection ids.
        # Prefer explicit override, then provider hint, else conservative default (200).
        max_per_conn = (
            self._override_streams_per_conn
            or getattr(self._provider, "max_streams_per_connection", None)
            or 200
        )
        chunks = [symbols[i : i + max_per_conn] for i in range(0, len(symbols), max_per_conn)]
        self._symbol_chunk_id.clear()
        self._chunk_last_msg.clear()
        for idx, chunk in enumerate(chunks):
            for s in chunk:
                self._symbol_chunk_id[s.upper()] = idx
            # initialize last message times to 0 (unknown)
            self._chunk_last_msg[idx] = 0.0

    async def _prefill_from_historical(
        self, symbols: list[str], interval: TimeInterval, limit: int | None
    ) -> None:
        """Best-effort prefill of latest-candle cache using provider REST method.

        This will call provider.get_candles(symbol, interval, limit=limit) for each
        symbol in parallel if the provider exposes that method. Exceptions per-symbol
        are ignored so warm-up is non-fatal.
        """
        if not hasattr(self._provider, "get_candles"):
            return

        async def _fetch(s: str):
            try:
                return await self._provider.get_candles(s, interval, limit=limit)
            except Exception:
                return None

        # Fire off parallel fetches
        tasks = [_fetch(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        for sym, res in zip(symbols, results, strict=False):
            if not res:
                continue
            # res is a list[Candle]; prefer the most recent (last) as latest
            try:
                last_candle = res[-1]
            except Exception:
                continue
            key = (sym.upper(), interval)
            if self._only_closed:
                prev = self._latest.get(key)
                if prev is not None:
                    self._prev_closed[key] = prev
            self._latest[key] = last_candle

    def _compute_effective_symbols(self) -> list[str]:
        """Union of requested symbols and all subscriber symbols (if any)."""
        subs_union: set[str] = set()
        for sub in self._subs.values():
            if sub.symbols:
                subs_union |= sub.symbols
        eff = sorted(self._requested_symbols | subs_union)
        return eff
