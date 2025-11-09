"""High-level OHLCV feed built on top of SymbolStreamFeed."""

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
    ConnectionEvent,
    ConnectionStatus,
    DataEvent,
    DataEventType,
    SeriesMeta,
    StreamingBar,
)
from .base_feed import SymbolStreamFeed

Callback = Callable[[StreamingBar], Awaitable[None]] | Callable[[StreamingBar], None]
EventCallback = Callable[[DataEvent], Awaitable[None]] | Callable[[DataEvent], None]


@dataclass(frozen=True)
class _Sub:
    callback: Callback
    symbols: set[str] | None
    interval: Timeframe
    only_closed: bool


@dataclass(frozen=True)
class _EventSub:
    callback: EventCallback
    event_types: set[DataEventType] | None
    symbols: set[str] | None
    interval: Timeframe
    only_closed: bool


class OHLCVFeed(SymbolStreamFeed[StreamingBar]):
    """Real-time OHLCV feed with cache, history, and subscription support."""

    def __init__(
        self,
        ws_provider: Any,
        *,
        rest_provider: Any | None = None,
        stale_threshold_seconds: int = 900,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
        max_streams_per_connection: int | None = None,
        enable_connection_events: bool = True,
        max_bar_history: int = 10,
    ) -> None:
        super().__init__(
            ws_provider,
            key_selector=lambda bar: bar.symbol.upper(),
            stale_threshold_seconds=stale_threshold_seconds,
        )
        self._ws = ws_provider
        self._rest = rest_provider
        self._throttle_ms = throttle_ms
        self._dedupe = dedupe_same_candle
        self._override_streams_per_conn = max_streams_per_connection
        self._enable_connection_events = enable_connection_events
        self._max_bar_history = max_bar_history

        self._interval: Timeframe | None = None
        self._only_closed: bool = True
        self._pending_warm_up: int = 0

        self._latest: dict[tuple[str, Timeframe], StreamingBar] = {}  # type: ignore[assignment]
        self._prev_closed: dict[tuple[str, Timeframe], StreamingBar] = {}
        self._bar_history: dict[tuple[str, Timeframe], list[StreamingBar]] = {}

        self._bar_subs: dict[str, _Sub] = {}
        self._event_subs: dict[str, _EventSub] = {}
        self._connection_callbacks: list[EventCallback] = []

        self._chunk_last_msg: dict[int, float] = {}
        self._symbol_chunk_id: dict[str, int] = {}
        self._connection_status: dict[int, ConnectionStatus] = {}

    async def start(  # type: ignore[override]
        self,
        *,
        symbols: Iterable[str],
        interval: Timeframe = Timeframe.M1,
        only_closed: bool = True,
        warm_up: int = 0,
    ) -> None:
        self._pending_warm_up = max(0, warm_up)
        self._interval = interval
        self._only_closed = only_closed
        await super().start(
            symbols=symbols,
            interval=interval,
            only_closed=only_closed,
        )

    async def stop(self) -> None:
        await super().stop()

    async def set_symbols(self, symbols: Iterable[str]) -> None:
        await super().set_symbols(symbols)

    async def add_symbols(self, symbols: Iterable[str]) -> None:
        await super().add_symbols(symbols)

    async def remove_symbols(self, symbols: Iterable[str]) -> None:
        await super().remove_symbols(symbols)

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------
    def subscribe(  # type: ignore[override]
        self,
        callback: Callback,
        *,
        symbols: Iterable[str] | None = None,
        interval: Timeframe | None = None,
        only_closed: bool | None = None,
    ) -> str:
        if interval is None:
            if self._interval is None:
                raise RuntimeError("OHLCVFeed not started: interval unknown")
            interval = self._interval
        if only_closed is None:
            only_closed = self._only_closed

        symbols_set = {s.upper() for s in symbols} if symbols else None
        sub_id = super().subscribe(callback, keys=symbols_set)
        self._bar_subs[sub_id] = _Sub(
            callback=callback,
            symbols=symbols_set,
            interval=interval,
            only_closed=only_closed,
        )
        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        super().unsubscribe(subscription_id)
        self._bar_subs.pop(subscription_id, None)

    # ------------------------------------------------------------------
    # Event subscriptions
    # ------------------------------------------------------------------
    def subscribe_events(
        self,
        callback: EventCallback,
        *,
        event_types: list[DataEventType] | None = None,
        symbols: list[str] | None = None,
        interval: Timeframe | None = None,
        only_closed: bool | None = None,
    ) -> str:
        if interval is None:
            if self._interval is None:
                raise RuntimeError("OHLCVFeed not started: interval unknown")
            interval = self._interval
        if only_closed is None:
            only_closed = self._only_closed

        event_type_set = set(event_types) if event_types else None
        symbols_set = {s.upper() for s in symbols} if symbols else None

        sub = _EventSub(
            callback=callback,
            event_types=event_type_set,
            symbols=symbols_set,
            interval=interval,
            only_closed=only_closed,
        )
        sub_id = uuid.uuid4().hex
        self._event_subs[sub_id] = sub
        if symbols_set:
            for symbol in symbols_set:
                key = (symbol.upper(), interval)
                self._bar_history.setdefault(key, [])
        self._schedule_update()
        return sub_id

    def unsubscribe_events(self, subscription_id: str) -> None:
        self._event_subs.pop(subscription_id, None)
        self._schedule_update()

    def on_bar(
        self,
        callback: Callback,
        *,
        symbols: Iterable[str] | None = None,
        interval: Timeframe | None = None,
        only_closed: bool | None = None,
    ) -> str:
        return self.subscribe(callback, symbols=symbols, interval=interval, only_closed=only_closed)

    def on_event(
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

    def on_events(
        self,
        callback: EventCallback,
        *,
        event_types: list[DataEventType] | None = None,
        symbols: list[str] | None = None,
        interval: Timeframe | None = None,
        only_closed: bool | None = None,
    ) -> str:
        """Backward-compatible alias for on_event."""
        return self.on_event(
            callback,
            event_types=event_types,
            symbols=symbols,
            interval=interval,
            only_closed=only_closed,
        )

    def add_connection_callback(self, callback: EventCallback) -> None:
        self._connection_callbacks.append(callback)

    def remove_connection_callback(self, callback: EventCallback) -> None:
        if callback in self._connection_callbacks:
            self._connection_callbacks.remove(callback)

    def subscribe_connection_events(self, callback: EventCallback) -> None:
        """Compatibility alias for adding connection callbacks."""
        self.add_connection_callback(callback)

    def unsubscribe_connection_events(self, callback: EventCallback) -> None:
        """Compatibility alias for removing connection callbacks."""
        self.remove_connection_callback(callback)

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------
    def get_latest_bar(
        self, symbol: str, *, interval: Timeframe | None = None
    ) -> StreamingBar | None:
        if interval is None:
            interval = self._interval or Timeframe.M1
        return self._latest.get((symbol.upper(), interval))

    def get_previous_closed(
        self, symbol: str, *, interval: Timeframe | None = None
    ) -> StreamingBar | None:
        if interval is None:
            interval = self._interval or Timeframe.M1
        return self._prev_closed.get((symbol.upper(), interval))

    def snapshot(
        self, symbols: Iterable[str] | None = None, *, interval: Timeframe | None = None
    ) -> dict[str, StreamingBar | None]:
        if interval is None:
            interval = self._interval or Timeframe.M1
        if symbols is None:
            symbols = self._symbols
        out: dict[str, StreamingBar | None] = {}
        for s in symbols:
            out[s] = self._latest.get((s.upper(), interval))
        return out

    def get_bar_history(
        self, symbol: str, *, interval: Timeframe | None = None, count: int | None = None
    ) -> list[StreamingBar]:
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
        if interval is None:
            interval = self._interval or Timeframe.M1
        bars = self.get_bar_history(symbol, interval=interval, count=count)
        meta = SeriesMeta(symbol=symbol.upper(), timeframe=interval.value)
        return OHLCV(meta=meta, bars=list(bars))

    def get_connection_status(self) -> dict[str, Any]:
        now = time.time()
        healthy: list[str] = []
        stale_ids: list[str] = []

        for cid, last_ts in self._chunk_last_msg.items():
            connection_id = f"connection_{cid}"
            age = now - last_ts if last_ts else float("inf")
            status = self._connection_status.get(cid, ConnectionStatus.DISCONNECTED)
            if age <= self._stale_threshold:
                healthy.append(connection_id)
            else:
                stale_ids.append(connection_id)
                if status != ConnectionStatus.STALE and self._enable_connection_events:
                    self._connection_status[cid] = ConnectionStatus.STALE

        return {
            "active_connections": len(self._chunk_last_msg),
            "healthy_connections": len(healthy),
            "stale_connections": stale_ids,
            "connection_status": {
                f"connection_{cid}": status.value for cid, status in self._connection_status.items()
            },
            "last_message_time": {
                f"connection_{cid}": ts for cid, ts in self._chunk_last_msg.items()
            },
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    async def _stream_iterator(self):
        assert self._interval is not None
        stream_multi = getattr(self._ws, "stream_ohlcv_multi", None) or getattr(
            self._ws, "stream_candles_multi", None
        )
        async for streaming_bar in stream_multi(
            self._symbols,
            self._interval,
            only_closed=self._only_closed,
            throttle_ms=self._throttle_ms,
            dedupe_same_candle=self._dedupe,
        ):
            yield streaming_bar

    async def _on_item(self, streaming_bar: StreamingBar, key: str | None) -> None:
        assert self._interval is not None
        symbol = streaming_bar.symbol.upper()
        key_tuple = (symbol, self._interval)
        closed = bool(streaming_bar.is_closed)

        if closed:
            prev = self._latest.get(key_tuple)
            if prev is not None and prev.is_closed:
                self._prev_closed[key_tuple] = prev
            history = self._bar_history.setdefault(key_tuple, [])
            history.append(streaming_bar)
            if len(history) > self._max_bar_history:
                del history[: -self._max_bar_history]

        self._latest[key_tuple] = streaming_bar
        now = time.time()
        self._last_msg_time = now

        cid = self._symbol_chunk_id.get(symbol)
        if cid is not None:
            self._chunk_last_msg[cid] = now
            if self._enable_connection_events:
                self._connection_status[cid] = ConnectionStatus.CONNECTED

    def _should_dispatch(self, streaming_bar: StreamingBar, key: str | None) -> bool:
        _ = key
        return bool(self._bar_subs or self._event_subs)

    async def _dispatch_item(self, streaming_bar: StreamingBar, key: str | None) -> None:
        cid = self._symbol_chunk_id.get(streaming_bar.symbol.upper())
        if self._event_subs:
            await self._dispatch_events(streaming_bar, cid)
        if self._bar_subs:
            await self._dispatch(streaming_bar)

    async def _dispatch(self, streaming_bar: StreamingBar) -> None:
        to_call: list[Callback] = []
        for sub in self._bar_subs.values():
            if sub.interval != self._interval:
                continue
            if sub.only_closed and not streaming_bar.is_closed:
                continue
            if sub.symbols is None or streaming_bar.symbol.upper() in sub.symbols:
                to_call.append(sub.callback)
        if not to_call:
            return
        loop = asyncio.get_running_loop()
        for cb in to_call:
            if asyncio.iscoroutinefunction(cb):
                loop.create_task(cb(streaming_bar))
            else:
                loop.run_in_executor(None, cb, streaming_bar)

    async def _dispatch_events(
        self, streaming_bar: StreamingBar, connection_id: int | None
    ) -> None:
        connection_id_str = f"connection_{connection_id}" if connection_id is not None else None

        bar_event = DataEvent.bar_update(
            bar=streaming_bar,
            symbol=streaming_bar.symbol,
            connection_id=connection_id_str,
            metadata={"chunk_id": connection_id},
        )

        to_call: list[tuple[EventCallback, DataEvent]] = []
        for sub in self._event_subs.values():
            if sub.interval != self._interval:
                continue
            if sub.event_types is not None and bar_event.event_type not in sub.event_types:
                continue
            if sub.symbols is not None and streaming_bar.symbol.upper() not in sub.symbols:
                continue
            if sub.only_closed and not streaming_bar.is_closed:
                continue
            to_call.append((sub.callback, bar_event))

        loop = asyncio.get_running_loop()
        for cb, event in to_call:
            if asyncio.iscoroutinefunction(cb):
                loop.create_task(cb(event))
            else:
                loop.run_in_executor(None, cb, event)

    async def _emit_connection_event(self, event: ConnectionEvent) -> None:
        if not self._enable_connection_events:
            return

        data_event = DataEvent.connection_status(event)
        loop = asyncio.get_running_loop()
        for callback in self._connection_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data_event)
                else:
                    loop.run_in_executor(None, callback, data_event)
            except Exception:
                import logging

                logger = logging.getLogger(__name__)
                logger.error("Error in connection event callback", exc_info=True)

    def _prepare_stream_args(self, args: dict[str, Any]) -> dict[str, Any]:
        args = dict(args)
        interval = args.get("interval", self._interval or Timeframe.M1)
        only_closed = args.get("only_closed", self._only_closed)
        args["interval"] = interval
        args["only_closed"] = only_closed
        prepared = super()._prepare_stream_args(args)
        self._interval = interval
        self._only_closed = only_closed
        self._assign_chunk_ids(self._symbols)
        for symbol in self._symbols:
            key = (symbol.upper(), interval)
            self._bar_history.setdefault(key, [])
        return prepared

    async def _before_start(self, *, is_restart: bool) -> None:
        await super()._before_start(is_restart=is_restart)
        if (
            not is_restart
            and self._pending_warm_up
            and self._interval is not None
            and self._symbols
        ):
            try:
                await self._prefill_from_historical(
                    self._symbols, self._interval, self._pending_warm_up
                )
            except Exception:
                pass
            finally:
                self._pending_warm_up = 0

    def _assign_chunk_ids(self, symbols: list[str]) -> None:
        max_per_conn = (
            self._override_streams_per_conn
            or getattr(self._ws, "max_streams_per_connection", None)
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
        rest_obj = self._rest
        if rest_obj is None or not hasattr(rest_obj, "get_candles"):
            return

        async def _fetch(symbol: str):
            try:
                return await rest_obj.get_candles(symbol, interval, limit=limit)
            except Exception:
                return None

        tasks = [_fetch(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        for sym, res in zip(symbols, results, strict=False):
            if not res:
                continue
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
        symbols = set(super()._compute_effective_symbols())
        for sub in self._event_subs.values():
            if sub.symbols:
                symbols |= sub.symbols
        return sorted(symbols)
