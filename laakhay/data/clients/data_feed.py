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
from typing import Any

from ..core import Timeframe
from ..models import (
    OHLCV,
    Bar,
    ConnectionEvent,
    ConnectionStatus,
    DataEvent,
    DataEventType,
    SeriesMeta,
    StreamingBar,
)

Callback = Callable[[StreamingBar], Awaitable[None]] | Callable[[StreamingBar], None]
EventCallback = Callable[[DataEvent], Awaitable[None]] | Callable[[DataEvent], None]


@dataclass(frozen=True)
class _Sub:
    callback: Callback
    symbols: set[str] | None  # None means "all effective symbols"
    interval: Timeframe
    only_closed: bool


@dataclass(frozen=True)
class _EventSub:
    """Enhanced subscription for event system."""

    callback: EventCallback
    event_types: set[DataEventType] | None  # None means all event types
    symbols: set[str] | None  # None means all symbols
    interval: Timeframe
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
        enable_connection_events: bool = True,
        max_bar_history: int = 10,
    ) -> None:
        self._provider = provider
        self._stale_threshold = stale_threshold_seconds
        self._throttle_ms = throttle_ms
        self._dedupe = dedupe_same_candle
        self._override_streams_per_conn = max_streams_per_connection
        self._enable_connection_events = enable_connection_events
        self._max_bar_history = max_bar_history

        # Streaming state
        # Currently active stream symbol set (effective set)
        self._symbols: list[str] = []
        # Requested symbols via start/set/add/remove (global intent)
        self._requested_symbols: set[str] = set()
        self._interval: Timeframe | None = None
        self._only_closed: bool = True
        self._stream_task: asyncio.Task | None = None
        self._running = False

        # Cache: latest, previous-closed, and bar history per (symbol, interval)
        self._latest: dict[tuple[str, Timeframe], Bar] = {}
        self._prev_closed: dict[tuple[str, Timeframe], Bar] = {}
        self._bar_history: dict[tuple[str, Timeframe], list[Bar]] = {}

        # Legacy subscriptions (backward compatibility)
        self._subs: dict[str, _Sub] = {}

        # Enhanced event subscriptions
        self._event_subs: dict[str, _EventSub] = {}

        # Connection event subscriptions
        self._connection_callbacks: list[EventCallback] = []

        # Health tracking (derived by chunk id)
        self._chunk_last_msg: dict[int, float] = {}
        self._symbol_chunk_id: dict[str, int] = {}
        self._connection_status: dict[int, ConnectionStatus] = {}

        # Lock for updates
        self._lock = asyncio.Lock()

    # ----------------------
    # Lifecycle
    # ----------------------
    async def start(
        self,
        *,
        symbols: Iterable[str],
        interval: Timeframe = Timeframe.M1,
        only_closed: bool = True,
        # Warm-up behavior: 0 = disabled, >0 = fetch up to this many historical candles
        # per symbol via provider.get_candles before starting streams. Best-effort and
        # non-fatal if provider doesn't support it or returns errors.
        warm_up: int = 0,
    ) -> None:
        """Start streaming for a static symbol set.

        Args:
            symbols: Iterable of symbols to stream (e.g., ["BTCUSDT", ...])
            interval: Bar interval (default 1m)
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

            # Initialize candle history tracking
            for symbol in self._symbols:
                key = (symbol.upper(), interval)
                self._bar_history[key] = []

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
        interval: Timeframe | None = None,
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
    # Enhanced Event Subscriptions
    # ----------------------
    def subscribe_events(
        self,
        callback: EventCallback,
        *,
        event_types: list[DataEventType] | None = None,
        symbols: list[str] | None = None,
        interval: Timeframe | None = None,
        only_closed: bool | None = None,
    ) -> str:
        """Subscribe to structured data events.

        Args:
            callback: Function to call when events are received
            event_types: List of event types to subscribe to (None = all types)
            symbols: List of symbols to subscribe to (None = all symbols)
            interval: Bar interval (None = use feed's current interval)
            only_closed: Only emit closed candle events (None = use feed's setting)

        Returns:
            Subscription ID for later unsubscription
        """
        if interval is None:
            if self._interval is None:
                raise RuntimeError("DataFeed not started: interval unknown")
            interval = self._interval
        if only_closed is None:
            only_closed = self._only_closed

        event_types_set: set[DataEventType] | None = None
        if event_types is not None:
            event_types_set = set(event_types)

        symbols_set: set[str] | None = None
        if symbols is not None:
            symbols_set = {s.upper() for s in symbols}

        sub = _EventSub(
            callback=callback,
            event_types=event_types_set,
            symbols=symbols_set,
            interval=interval,
            only_closed=only_closed,
        )
        sub_id = uuid.uuid4().hex
        self._event_subs[sub_id] = sub

        # If subscriber requested additional symbols, fold into effective set
        if symbols_set:

            async def _maybe_update():
                async with self._lock:
                    self._requested_symbols |= symbols_set
                    eff = self._compute_effective_symbols()
                    if eff != self._symbols:
                        self._symbols = eff
                        self._assign_chunk_ids(self._symbols)
                        # Initialize new symbols' candle history
                        for symbol in symbols_set:
                            key = (symbol.upper(), interval)
                            if key not in self._bar_history:
                                self._bar_history[key] = []
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
                loop.create_task(_maybe_update())
            except RuntimeError:
                pass
        return sub_id

    def unsubscribe_events(self, subscription_id: str) -> None:
        """Unsubscribe from event notifications."""
        self._event_subs.pop(subscription_id, None)

        # Recompute effective set and rebuild if shrunk
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

    def subscribe_connection_events(self, callback: EventCallback) -> None:
        """Subscribe to connection status events."""
        self._connection_callbacks.append(callback)

    def unsubscribe_connection_events(self, callback: EventCallback) -> None:
        """Unsubscribe from connection status events."""
        if callback in self._connection_callbacks:
            self._connection_callbacks.remove(callback)

    # ----------------------
    # Cache access
    # ----------------------
    def get_latest_bar(self, symbol: str, *, interval: Timeframe | None = None) -> Bar | None:
        """Get the latest bar from cache (O(1), non-blocking)."""
        if interval is None:
            interval = self._interval or Timeframe.M1
        return self._latest.get((symbol.upper(), interval))

    def get_previous_closed(self, symbol: str, *, interval: Timeframe | None = None) -> Bar | None:
        """Get the previous closed bar from cache."""
        if interval is None:
            interval = self._interval or Timeframe.M1
        return self._prev_closed.get((symbol.upper(), interval))

    def snapshot(
        self, symbols: Iterable[str] | None = None, *, interval: Timeframe | None = None
    ) -> dict[str, Bar | None]:
        """Return a dict of latest bars for given symbols (or all effective)."""
        if interval is None:
            interval = self._interval or Timeframe.M1
        if symbols is None:
            symbols = list(self._symbols)
        out: dict[str, Bar | None] = {}
        for s in symbols:
            out[s] = self._latest.get((s.upper(), interval))
        return out

    def get_bar_history(
        self, symbol: str, *, interval: Timeframe | None = None, count: int | None = None
    ) -> list[Bar]:
        """Get the last N closed bars for technical analysis."""
        if interval is None:
            interval = self._interval or Timeframe.M1
        key = (symbol.upper(), interval)
        history = self._bar_history.get(key, [])
        if count is not None:
            return history[-count:] if count > 0 else []
        return history.copy()

    def get_ohlcv(
        self, symbol: str, *, interval: Timeframe | None = None, count: int | None = None
    ) -> OHLCV:
        """Get OHLCV series for a symbol."""
        if interval is None:
            interval = self._interval or Timeframe.M1

        bars = self.get_bar_history(symbol, interval=interval, count=count)
        meta = SeriesMeta(symbol=symbol.upper(), timeframe=interval.value)

        return OHLCV(meta=meta, bars=bars)

    # Sugar alias for subscribe
    def on_bar(
        self,
        callback: Callback,
        *,
        symbols: Iterable[str] | None = None,
        interval: Timeframe | None = None,
        only_closed: bool | None = None,
    ) -> str:
        return self.subscribe(callback, symbols=symbols, interval=interval, only_closed=only_closed)

    # Sugar alias for enhanced subscribe_events
    def on_events(
        self,
        callback: EventCallback,
        *,
        event_types: list[DataEventType] | None = None,
        symbols: list[str] | None = None,
        interval: Timeframe | None = None,
        only_closed: bool | None = None,
    ) -> str:
        return self.subscribe_events(
            callback,
            event_types=event_types,
            symbols=symbols,
            interval=interval,
            only_closed=only_closed,
        )

    # ----------------------
    # Health
    # ----------------------
    def get_connection_status(self) -> dict[str, Any]:
        """Enhanced connection health status with connection status tracking."""
        now = time.time()
        stale_ids: list[str] = []
        healthy = 0

        for cid, ts in self._chunk_last_msg.items():
            if now - ts <= self._stale_threshold:
                healthy += 1
            else:
                stale_ids.append(f"connection_{cid}")
                if self._enable_connection_events:
                    # Mark connection as stale
                    self._connection_status[cid] = ConnectionStatus.STALE

        return {
            "active_connections": len(self._chunk_last_msg),
            "healthy_connections": healthy,
            "stale_connections": stale_ids,
            "connection_status": {
                f"connection_{cid}": status.value for cid, status in self._connection_status.items()
            },
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
            async for streaming_bar in self._provider.stream_candles_multi(
                self._symbols,
                self._interval,
                only_closed=self._only_closed,
                throttle_ms=self._throttle_ms,
                dedupe_same_candle=self._dedupe,
            ):
                # Update cache and history
                symbol = streaming_bar.symbol
                key = (symbol.upper(), self._interval)
                closed = bool(streaming_bar.is_closed)

                if closed:
                    # Store previous closed bar
                    prev = self._latest.get(key)
                    if prev is not None and prev.is_closed:
                        self._prev_closed[key] = prev

                    # Add to bar history
                    if key not in self._bar_history:
                        self._bar_history[key] = []
                    self._bar_history[key].append(streaming_bar)
                    # Keep only last N bars to prevent memory growth
                    if len(self._bar_history[key]) > self._max_bar_history:
                        self._bar_history[key] = self._bar_history[key][-self._max_bar_history :]

                self._latest[key] = streaming_bar

                # Update health tracking
                cid = self._symbol_chunk_id.get(symbol.upper())
                if cid is not None:
                    self._chunk_last_msg[cid] = time.time()
                    # Update connection status
                    if self._enable_connection_events:
                        self._connection_status[cid] = ConnectionStatus.CONNECTED

                # Dispatch to enhanced event subscribers
                if self._event_subs:
                    await self._dispatch_events(streaming_bar, cid)

                # Dispatch to subscribers
                if self._subs:
                    await self._dispatch(streaming_bar)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Keep task quiet on exceptions; next start() will recreate
            pass

    async def _dispatch(self, streaming_bar: StreamingBar) -> None:
        to_call: list[tuple[Callback, StreamingBar]] = []
        for sub in self._subs.values():
            if sub.interval != self._interval:
                continue
            if sub.symbols is None or streaming_bar.symbol.upper() in sub.symbols:
                to_call.append((sub.callback, streaming_bar))
        # Fire callbacks (don't block stream)
        for cb, streaming_bar in to_call:
            if asyncio.iscoroutinefunction(cb):
                asyncio.create_task(cb(streaming_bar))
            else:
                # run sync cb in default loop executor to avoid blocking
                loop = asyncio.get_running_loop()
                loop.run_in_executor(None, cb, streaming_bar)

    async def _dispatch_events(
        self, streaming_bar: StreamingBar, connection_id: int | None
    ) -> None:
        """Dispatch events to enhanced event subscribers."""
        connection_id_str = f"connection_{connection_id}" if connection_id is not None else None

        # Create bar event
        bar_event = DataEvent.bar_update(
            bar=streaming_bar.bar,
            symbol=streaming_bar.symbol,
            connection_id=connection_id_str,
            metadata={"chunk_id": connection_id},
        )

        to_call: list[tuple[EventCallback, DataEvent]] = []

        for sub in self._event_subs.values():
            if sub.interval != self._interval:
                continue

            # Filter by event type
            if sub.event_types is not None and bar_event.event_type not in sub.event_types:
                continue

            # Filter by symbol
            if sub.symbols is not None and streaming_bar.symbol.upper() not in sub.symbols:
                continue

            # Filter by closed status
            if sub.only_closed and not streaming_bar.bar.is_closed:
                continue

            to_call.append((sub.callback, bar_event))

        # Fire callbacks
        for cb, event in to_call:
            if asyncio.iscoroutinefunction(cb):
                asyncio.create_task(cb(event))
            else:
                loop = asyncio.get_running_loop()
                loop.run_in_executor(None, cb, event)

    async def _emit_connection_event(self, event: ConnectionEvent) -> None:
        """Emit connection status events."""
        if not self._enable_connection_events:
            return

        data_event = DataEvent.connection_status(event)

        for callback in self._connection_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data_event)
                else:
                    loop = asyncio.get_running_loop()
                    loop.run_in_executor(None, callback, data_event)
            except Exception as e:
                # Log error but don't crash
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Error in connection event callback: {e}")

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
        self._connection_status.clear()

        for idx, chunk in enumerate(chunks):
            for s in chunk:
                self._symbol_chunk_id[s.upper()] = idx
            self._chunk_last_msg[idx] = 0.0
            self._connection_status[idx] = ConnectionStatus.DISCONNECTED

    async def _prefill_from_historical(
        self, symbols: list[str], interval: Timeframe, limit: int | None
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
            # res is a list[Bar]; prefer the most recent (last) as latest
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

        # Legacy subscribers
        for sub in self._subs.values():
            if sub.symbols:
                subs_union |= sub.symbols

        # Enhanced event subscribers
        for sub in self._event_subs.values():
            if sub.symbols:
                subs_union |= sub.symbols

        return sorted(self._requested_symbols | subs_union)
