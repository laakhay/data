"""Generic stream orchestrator using EndpointSpec + Adapter + Transport.

This runner centralizes chunking, combined stream fan-in, throttling, and
dedupe. Adapters are responsible only for mapping raw messages to models.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any

from .transport import WebSocketTransport


@dataclass(frozen=True)
class WSEndpointSpec:
    id: str
    combined_supported: bool
    max_streams_per_connection: int
    build_stream_name: Callable[[str, dict[str, Any]], str]  # symbol -> stream name
    build_combined_url: Callable[[list[str]], str]
    build_single_url: Callable[[str], str]


class MessageAdapter:
    """Adapter interface: convert raw messages into domain objects."""

    def is_relevant(self, payload: Any) -> bool:
        return True

    def parse(self, payload: Any) -> list[Any]:
        return []


class StreamRunner:
    """Run one logical stream across one or more WS connections."""

    def __init__(
        self,
        *,
        transport: WebSocketTransport | None = None,
    ) -> None:
        self._transport = transport or WebSocketTransport()

    async def run(
        self,
        *,
        spec: WSEndpointSpec,
        adapter: MessageAdapter,
        symbols: list[str],
        params: dict[str, Any] | None = None,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_key: Callable[[Any], tuple[str, int, str]] | None = None,
    ) -> AsyncIterator[Any]:
        if not symbols:
            return
        params = params or {}

        # Chunk symbols
        cap = max(1, spec.max_streams_per_connection)
        chunks = [symbols[i : i + cap] for i in range(0, len(symbols), cap)]

        # Single-chunk fast path
        if len(chunks) == 1:
            last_emit: dict[str, float] = {}
            last_close: dict[tuple[str, int], str] = {}
            async for payload in self._stream_chunk(spec, adapter, chunks[0], params):
                for obj in adapter.parse(payload):
                    if only_closed and getattr(obj, "is_closed", False) is False:
                        continue
                    if throttle_ms:
                        now = time.time()
                        sym = getattr(obj, "symbol", "")
                        last = last_emit.get(sym)
                        if last is not None and (now - last) < (throttle_ms / 1000.0):
                            continue
                        last_emit[sym] = now
                    if dedupe_key and not only_closed:
                        sym, ts, close_str = dedupe_key(obj)
                        key = (sym, ts)
                        if last_close.get(key) == close_str:
                            continue
                        last_close[key] = close_str
                    yield obj
            return

        # Multi-chunk fan-in
        queue: asyncio.Queue = asyncio.Queue()

        async def pump(chunk_syms: list[str]):
            async for payload in self._stream_chunk(spec, adapter, chunk_syms, params):
                await queue.put(payload)

        tasks = [asyncio.create_task(pump(chunk)) for chunk in chunks]
        last_emit: dict[str, float] = {}  # type: ignore[no-redef]
        last_close: dict[tuple[str, int], str] = {}  # type: ignore[no-redef]
        try:
            while True:
                payload = await queue.get()
                for obj in adapter.parse(payload):
                    if only_closed and getattr(obj, "is_closed", False) is False:
                        continue
                    if throttle_ms:
                        now = time.time()
                        sym = getattr(obj, "symbol", "")
                        last = last_emit.get(sym)
                        if last is not None and (now - last) < (throttle_ms / 1000.0):
                            continue
                        last_emit[sym] = now
                    if dedupe_key and not only_closed:
                        sym, ts, close_str = dedupe_key(obj)
                        key = (sym, ts)
                        if last_close.get(key) == close_str:
                            continue
                        last_close[key] = close_str
                    yield obj
        finally:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _stream_chunk(
        self,
        spec: WSEndpointSpec,
        adapter: MessageAdapter,
        symbols: list[str],
        params: dict[str, Any],
    ) -> AsyncIterator[Any]:
        if spec.combined_supported and len(symbols) > 1:
            names = [spec.build_stream_name(s, params) for s in symbols]
            url = spec.build_combined_url(names)
            async for msg in self._transport.stream(url):
                yield msg
        else:
            # Single stream per symbol
            for s in symbols:
                name = spec.build_stream_name(s, params)
                url = spec.build_single_url(name)

                async def single(url: str):
                    async for msg in self._transport.stream(url):
                        yield msg

                async for msg in single(url):
                    yield msg
