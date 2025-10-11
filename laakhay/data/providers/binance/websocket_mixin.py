"""WebSocket streaming mixin for Binance provider.

Separation of concerns: robust connection management, backoff with jitter,
graceful cancellation, and optional throttling for high-frequency updates.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from dataclasses import dataclass
from typing import AsyncIterator, Dict, List, Optional
import random
import time

import websockets

from ...core import TimeInterval, MarketType
from ...models import Candle, Liquidation, OpenInterest
from .constants import WS_SINGLE_URLS, WS_COMBINED_URLS, INTERVAL_MAP, OI_PERIOD_MAP

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConfig:
    ping_interval: int = 30
    ping_timeout: int = 10
    base_reconnect_delay: float = 1.0
    max_reconnect_delay: float = 30.0
    jitter: float = 0.2  # +/-20% jitter to avoid thundering herds
    max_size: Optional[int] = None  # bytes; None = websockets default
    max_queue: Optional[int] = 1024  # number of messages queued; None = unlimited
    close_timeout: int = 10


class BinanceWebSocketMixin:
    market_type: MarketType
    # Hint for DataFeed chunking; Spot allows more, Futures is lower.
    max_streams_per_connection: Optional[int] = None

    # Allow providers to override ws_config; fall back to defaults
    @property
    def _ws_conf(self) -> WebSocketConfig:
        """Return active WebSocketConfig (provider override or defaults)."""
        return getattr(self, "ws_config", WebSocketConfig())

    def _next_delay(self, delay: float) -> float:
        """Exponential backoff with jitter, capped to max_reconnect_delay."""
        conf = self._ws_conf
        delay = min(delay * 2, conf.max_reconnect_delay)
        # Apply jitter
        factor = random.uniform(1 - conf.jitter, 1 + conf.jitter)
        return max(0.5, delay * factor)

    def _ws_connect(self, url: str):
        """Create a websockets.connect context with our config (timeouts, sizing)."""
        conf = self._ws_conf
        kwargs = {
            "ping_interval": conf.ping_interval,
            "ping_timeout": conf.ping_timeout,
            "close_timeout": conf.close_timeout,
        }
        # Only include size/queue if not None to keep library defaults
        if conf.max_size is not None:
            kwargs["max_size"] = conf.max_size
        if conf.max_queue is not None:
            kwargs["max_queue"] = conf.max_queue
        return websockets.connect(url, **kwargs)

    async def stream_candles(
        self,
        symbol: str,
        interval: TimeInterval,
        only_closed: bool = False,
        throttle_ms: Optional[int] = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[Candle]:
        """Yield Candle updates for one symbol.

        - Builds single-stream URL and connects with keepalive.
        - Reconnects with backoff on disconnect/errors.
        - Filters only_closed if requested, and supports throttle/dedupe.
        """
        ws_url = WS_SINGLE_URLS.get(self.market_type)
        if not ws_url:
            raise ValueError(f"WebSocket not supported for market type: {self.market_type}")

        stream_name = f"{symbol.lower()}@kline_{INTERVAL_MAP[interval]}"
        full_url = f"{ws_url}/{stream_name}"

        reconnect_delay = self._ws_conf.base_reconnect_delay
        last_emit: Optional[float] = None
        last_close_for_candle: Optional[str] = None
        last_candle_ts: Optional[int] = None

        while True:  # reconnect loop
            try:
                # Connect with configured timeouts
                async with self._ws_connect(full_url) as websocket:
                    reconnect_delay = self._ws_conf.base_reconnect_delay
                    async for message in websocket:  # message loop
                        try:
                            data = json.loads(message)
                            if "k" not in data:  # expect kline payload
                                continue
                            k = data["k"]
                            if only_closed and not k.get("x", False):
                                continue
                            # Optional dedupe: if same candle and close unchanged, skip
                            if dedupe_same_candle and not only_closed:
                                open_ts = int(k["t"])  # ms
                                close_str = str(k["c"])  # string is consistent
                                if last_candle_ts == open_ts and last_close_for_candle == close_str:
                                    continue
                                last_candle_ts = open_ts
                                last_close_for_candle = close_str
                            if throttle_ms and not only_closed:  # soft rate limit
                                now = time.time()
                                if last_emit is not None and (now - last_emit) < (throttle_ms / 1000.0):
                                    continue
                                last_emit = now
                            # Map kline -> Candle
                            yield Candle(
                                symbol=symbol.upper(),
                                timestamp=datetime.fromtimestamp(k["t"] / 1000),
                                open=Decimal(str(k["o"])),
                                high=Decimal(str(k["h"])),
                                low=Decimal(str(k["l"])),
                                close=Decimal(str(k["c"])),
                                volume=Decimal(str(k["v"]))
                            )
                        except Exception as e:  # noqa: BLE001
                            logger.error(f"stream_candles parse error: {e}")
            except asyncio.CancelledError:
                raise
            except websockets.exceptions.ConnectionClosed:
                # Graceful reconnect with backoff
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)
            except Exception as e:  # noqa: BLE001
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)

    async def stream_candles_multi(
        self,
        symbols: List[str],
        interval: TimeInterval,
        only_closed: bool = False,
        throttle_ms: Optional[int] = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[Candle]:
        """Yield Candle updates for multiple symbols using combined streams.

        - Splits symbols to respect per-connection stream limits.
        - For single chunk, yield directly; otherwise fan-in via queue.
        - Supports throttle/dedupe per symbol.
        """
        if not symbols:
            return

        # Chunking per market rules
        max_per_connection = 200 if self.market_type == MarketType.FUTURES else 1024
        # publish hint for callers
        try:
            # set attribute on instance for DataFeed to read
            object.__setattr__(self, "max_streams_per_connection", max_per_connection)
        except Exception:
            # ignore if instance is frozen or does not allow setattr
            pass
        chunks = [symbols[i:i + max_per_connection] for i in range(0, len(symbols), max_per_connection)]

        if len(chunks) == 1:
            # Apply optional throttling here for single-chunk path
            last_emit: Dict[str, float] = {}
            last_close: Dict[tuple, str] = {}
            async for c in self._stream_chunk(chunks[0], interval, only_closed):
                if throttle_ms and not only_closed:
                    now = time.time()
                    last = last_emit.get(c.symbol)
                    if last is not None and (now - last) < (throttle_ms / 1000.0):
                        continue
                    last_emit[c.symbol] = now
                if dedupe_same_candle and not only_closed:
                    key = (c.symbol, int(c.timestamp.timestamp() * 1000))
                    close_s = str(c.close)
                    if last_close.get(key) == close_s:
                        continue
                    last_close[key] = close_s
                yield c
            return

        queue: asyncio.Queue = asyncio.Queue()  # fan-in buffer from chunk tasks

        async def pump(chunk_syms: List[str]):
            """Push chunk stream candles into fan-in queue (auto-reconnect inside)."""
            async for c in self._stream_chunk(chunk_syms, interval, only_closed):
                await queue.put(c)

        tasks = [asyncio.create_task(pump(chunk)) for chunk in chunks]
        last_emit: Dict[str, float] = {}
        last_close: Dict[tuple, str] = {}
        try:
            while True:
                c = await queue.get()  # backpressure: waits if queue empty
                if throttle_ms and not only_closed:
                    now = time.time()
                    last = last_emit.get(c.symbol)
                    if last is not None and (now - last) < (throttle_ms / 1000.0):
                        continue
                    last_emit[c.symbol] = now
                if dedupe_same_candle and not only_closed:
                    key = (c.symbol, int(c.timestamp.timestamp() * 1000))
                    close_s = str(c.close)
                    if last_close.get(key) == close_s:
                        continue
                    last_close[key] = close_s
                yield c
        finally:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _stream_chunk(
        self,
        symbols: List[str],
        interval: TimeInterval,
        only_closed: bool,
    ) -> AsyncIterator[Candle]:
        """Yield candles for one combined-stream connection (one socket)."""
        names = [f"{s.lower()}@kline_{INTERVAL_MAP[interval]}" for s in symbols]
        ws_base = WS_COMBINED_URLS.get(self.market_type)
        if not ws_base:
            raise ValueError(f"WebSocket not supported for market type: {self.market_type}")
        url = f"{ws_base}?streams={'/'.join(names)}"

        reconnect_delay = self._ws_conf.base_reconnect_delay
        while True:  # reconnect loop
            try:
                # Connect to combined stream
                async with self._ws_connect(url) as websocket:
                    reconnect_delay = self._ws_conf.base_reconnect_delay
                    async for message in websocket:  # message loop
                        try:
                            data = json.loads(message)
                            if "data" not in data:  # combined payload has "data"
                                continue
                            k = data["data"].get("k")
                            if not k:
                                continue
                            if only_closed and not k.get("x", False):
                                continue
                            # Map kline -> Candle
                            yield Candle(
                                symbol=k["s"],
                                timestamp=datetime.fromtimestamp(k["t"] / 1000),
                                open=Decimal(str(k["o"])),
                                high=Decimal(str(k["h"])),
                                low=Decimal(str(k["l"])),
                                close=Decimal(str(k["c"])),
                                volume=Decimal(str(k["v"]))
                            )
                        except Exception as e:  # noqa: BLE001
                            logger.error(f"_stream_chunk parse error: {e}")
            except asyncio.CancelledError:
                raise
            except websockets.exceptions.ConnectionClosed:
                # Graceful reconnect with backoff
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Combined WS error: {e}")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)

    async def stream_trades(self, symbol: str) -> AsyncIterator[Dict]:
        """Yield trade prints for a symbol (price, qty, ts, is_buyer_maker)."""
        ws_url = WS_SINGLE_URLS.get(self.market_type)
        if not ws_url:
            raise ValueError(f"WebSocket not supported for market type: {self.market_type}")
        url = f"{ws_url}/{symbol.lower()}@trade"

        reconnect_delay = self._ws_conf.base_reconnect_delay
        while True:  # reconnect loop
            try:
                # Connect to trade stream
                async with self._ws_connect(url) as websocket:
                    reconnect_delay = self._ws_conf.base_reconnect_delay
                    async for message in websocket:  # message loop
                        try:
                            data = json.loads(message)
                            if "p" not in data:
                                continue
                            yield {
                                "symbol": symbol.upper(),
                                "price": Decimal(str(data["p"])),
                                "quantity": Decimal(str(data["q"])),
                                "timestamp": datetime.fromtimestamp(data["T"] / 1000),
                                "is_buyer_maker": data["m"],
                            }
                        except Exception as e:  # noqa: BLE001
                            logger.error(f"stream_trades parse error: {e}")
            except asyncio.CancelledError:
                raise
            except websockets.exceptions.ConnectionClosed:
                # Graceful reconnect with backoff
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Trades WS error: {e}")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)

    async def stream_open_interest(
        self,
        symbols: List[str],
        period: str = "5m",
    ) -> AsyncIterator[OpenInterest]:
        """Yield Open Interest updates using the <symbol>@openInterest@<period> stream.

        Combined-stream payloads are wrapped as {"stream": ..., "data": {...}}; single
        payloads deliver the event directly. The event type is "openInterest" with fields:
        - s: symbol, E or t: event time (ms), oi: open interest (string)

        Args:
            symbols: List of symbols (e.g., ["BTCUSDT"]).
            period: One of OI_PERIOD_MAP keys (e.g., "5m", "15m", "1h", "1d").
        """
        if self.market_type != MarketType.FUTURES:
            raise ValueError("Open Interest streaming is only available for Futures market")

        if period not in OI_PERIOD_MAP:
            raise ValueError(f"Invalid period: {period}. Valid: {sorted(OI_PERIOD_MAP.keys())}")

        ws_base = WS_COMBINED_URLS.get(self.market_type)
        if not ws_base:
            raise ValueError(f"WebSocket not supported for market type: {self.market_type}")

        stream_names = [f"{s.lower()}@openInterest@{period}" for s in symbols]
        url = f"{ws_base}?streams={'/'.join(stream_names)}"

        reconnect_delay = self._ws_conf.base_reconnect_delay

        while True:  # reconnect loop
            try:
                async with self._ws_connect(url) as websocket:
                    reconnect_delay = self._ws_conf.base_reconnect_delay
                    async for message in websocket:
                        try:
                            outer = json.loads(message)
                            payload = outer.get("data", outer)
                            if not isinstance(payload, dict):
                                continue
                            if payload.get("e") and payload.get("e") != "openInterest":
                                continue

                            symbol = payload.get("s") or payload.get("symbol")
                            event_time_ms = payload.get("E") or payload.get("t") or payload.get("eventTime")
                            oi_str = payload.get("oi") or payload.get("o") or payload.get("openInterest")
                            if not symbol or oi_str is None or event_time_ms is None:
                                continue

                            yield OpenInterest(
                                symbol=symbol,
                                timestamp=datetime.fromtimestamp(int(event_time_ms) / 1000, tz=timezone.utc),
                                open_interest=Decimal(str(oi_str)),
                                open_interest_value=None,
                            )
                        except Exception as e:  # noqa: BLE001
                            logger.error(f"stream_open_interest parse error: {e}")
            except asyncio.CancelledError:
                raise
            except websockets.exceptions.ConnectionClosed:
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Open Interest WS error: {e}")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)

    async def stream_liquidations(self) -> AsyncIterator[Liquidation]:
        """Yield liquidation orders for all symbols using forceOrder stream.
        
        This stream provides real-time liquidation data across all futures symbols.
        The stream name is '!forceOrder@arr' which means it receives all liquidations.
        
        Yields:
            Liquidation: Real-time liquidation events
            
        Note:
            This endpoint is only available for Futures market type.
            The stream provides liquidation data for all symbols simultaneously.
        """
        if self.market_type != MarketType.FUTURES:
            raise ValueError("Liquidation streaming is only available for Futures market")

        ws_base = WS_SINGLE_URLS.get(self.market_type)
        if not ws_base:
            raise ValueError(f"WebSocket not supported for market type: {self.market_type}")

        # Force order stream for all symbols
        url = f"{ws_base}/!forceOrder@arr"

        reconnect_delay = self._ws_conf.base_reconnect_delay

        while True:
            try:
                async with self._ws_connect(url) as websocket:
                    reconnect_delay = self._ws_conf.base_reconnect_delay
                    async for message in websocket:
                        try:
                            outer = json.loads(message)
                            payload = outer.get("data", outer)

                            # Expect forceOrder event with nested order object "o"
                            if payload.get("e") != "forceOrder" or "o" not in payload:
                                continue

                            o = payload["o"]
                            event_time_ms = payload.get("E") or o.get("T")
                            if event_time_ms is None:
                                continue

                            liquidation = Liquidation(
                                symbol=o["s"],
                                timestamp=datetime.fromtimestamp(int(event_time_ms) / 1000, tz=timezone.utc),
                                side=o["S"],
                                order_type=o["o"],
                                time_in_force=o["f"],
                                original_quantity=Decimal(str(o["q"])),
                                price=Decimal(str(o["p"])),
                                average_price=Decimal(str(o["ap"])),
                                order_status=o["X"],
                                last_filled_quantity=Decimal(str(o["l"])),
                                accumulated_quantity=Decimal(str(o["z"])),
                                commission=None,
                                commission_asset=None,
                                trade_id=None,
                            )

                            yield liquidation

                        except Exception as e:  # noqa: BLE001
                            logger.error(f"stream_liquidations parse error: {e}")
                            
            except asyncio.CancelledError:
                raise
            except websockets.exceptions.ConnectionClosed:
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)
            except Exception as e:
                logger.error(f"Liquidations WS error: {e}")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)
