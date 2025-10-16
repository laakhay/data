"""WebSocket streaming mixin for Binance provider.

Separation of concerns: robust connection management, backoff with jitter,
graceful cancellation, and optional throttling for high-frequency updates.
"""

import asyncio
import json
import logging
import random
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

import websockets

from ...core import MarketType, Timeframe
from ...models import FundingRate, Liquidation, MarkPrice, OpenInterest, OrderBook, Trade
from ...models.streaming_bar import StreamingBar
from .constants import INTERVAL_MAP, OI_PERIOD_MAP, WS_COMBINED_URLS, WS_SINGLE_URLS

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConfig:
    ping_interval: int = 30
    ping_timeout: int = 10
    base_reconnect_delay: float = 1.0
    max_reconnect_delay: float = 30.0
    jitter: float = 0.2  # +/-20% jitter to avoid thundering herds
    max_size: int | None = None  # bytes; None = websockets default
    max_queue: int | None = 1024  # number of messages queued; None = unlimited
    close_timeout: int = 10


class BinanceWebSocketMixin:
    market_type: MarketType
    # Hint for DataFeed chunking; Spot allows more, Futures is lower.
    max_streams_per_connection: int | None = None

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
        interval: Timeframe,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        """Yield StreamingBar updates for one symbol.

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
        last_emit: float | None = None
        last_close_for_candle: str | None = None
        last_candle_ts: int | None = None

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
                                if last_emit is not None and (now - last_emit) < (
                                    throttle_ms / 1000.0
                                ):
                                    continue
                                last_emit = now
                            # Map kline -> StreamingBar
                            yield StreamingBar(
                                symbol=symbol.upper(),
                                timestamp=datetime.fromtimestamp(k["t"] / 1000, tz=timezone.utc),
                                open=Decimal(str(k["o"])),
                                high=Decimal(str(k["h"])),
                                low=Decimal(str(k["l"])),
                                close=Decimal(str(k["c"])),
                                volume=Decimal(str(k["v"])),
                                is_closed=bool(k.get("x", False)),
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
        symbols: list[str],
        interval: Timeframe,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        """Yield StreamingBar updates for multiple symbols using combined streams.

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
        chunks = [
            symbols[i : i + max_per_connection] for i in range(0, len(symbols), max_per_connection)
        ]

        if len(chunks) == 1:
            # Apply optional throttling here for single-chunk path
            last_emit: dict[str, float] = {}
            last_close: dict[tuple, str] = {}
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

        async def pump(chunk_syms: list[str]):
            """Push chunk stream candles into fan-in queue (auto-reconnect inside)."""
            async for c in self._stream_chunk(chunk_syms, interval, only_closed):
                await queue.put(c)

        tasks = [asyncio.create_task(pump(chunk)) for chunk in chunks]
        last_emit: dict[str, float] = {}
        last_close: dict[tuple, str] = {}
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
        symbols: list[str],
        interval: Timeframe,
        only_closed: bool,
    ) -> AsyncIterator[StreamingBar]:
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
                            # Map kline -> StreamingBar
                            yield StreamingBar(
                                symbol=k["s"],
                                timestamp=datetime.fromtimestamp(k["t"] / 1000, tz=timezone.utc),
                                open=Decimal(str(k["o"])),
                                high=Decimal(str(k["h"])),
                                low=Decimal(str(k["l"])),
                                close=Decimal(str(k["c"])),
                                volume=Decimal(str(k["v"])),
                                is_closed=bool(k.get("x", False)),
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

    async def stream_trades(self, symbol: str) -> AsyncIterator[dict]:
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
        symbols: list[str],
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
                            event_time_ms = (
                                payload.get("E") or payload.get("t") or payload.get("eventTime")
                            )
                            oi_str = (
                                payload.get("oi") or payload.get("o") or payload.get("openInterest")
                            )
                            if not symbol or oi_str is None or event_time_ms is None:
                                continue

                            yield OpenInterest(
                                symbol=symbol,
                                timestamp=datetime.fromtimestamp(
                                    int(event_time_ms) / 1000, tz=timezone.utc
                                ),
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
                                timestamp=datetime.fromtimestamp(
                                    int(event_time_ms) / 1000, tz=timezone.utc
                                ),
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

    async def stream_funding_rate(
        self,
        symbols: list[str],
        update_speed: str = "1s",
    ) -> AsyncIterator[FundingRate]:
        """Yield predicted/next funding rate updates for multiple symbols using markPrice stream.

        The @markPrice stream includes the PREDICTED funding rate in the 'r' field.
        This is the rate that WILL BE applied at the next funding time (00:00, 08:00, 16:00 UTC).

        IMPORTANT: This rate changes continuously in real-time as market conditions change.
        It represents the time-weighted average of the Premium Index and shows where
        funding is trending. The actual applied rate is fixed when funding settles.

        Args:
            symbols: List of symbols to monitor (e.g., ["BTCUSDT", "ETHUSDT"])
            update_speed: Update frequency ("1s" or "3s")

        Yields:
            FundingRate: Predicted funding rate updates (changes every second)

        Note:
            - This is the PREDICTED/NEXT funding rate (changes continuously)
            - Actual funding is APPLIED every 8 hours (00:00, 08:00, 16:00 UTC)
            - Use this to monitor funding trends and anticipate costs
            - For historical APPLIED rates, use get_funding_rate() REST method
        """
        if self.market_type != MarketType.FUTURES:
            raise ValueError("Funding rate streaming is only available for Futures market")

        if update_speed not in ["1s", "3s"]:
            raise ValueError("update_speed must be '1s' or '3s'")

        ws_base = WS_COMBINED_URLS.get(self.market_type)
        if not ws_base:
            raise ValueError(f"WebSocket not supported for market type: {self.market_type}")

        # Create stream names for mark price (includes funding rate)
        stream_names = [f"{s.lower()}@markPrice@{update_speed}" for s in symbols]
        url = f"{ws_base}?streams={'/'.join(stream_names)}"

        reconnect_delay = self._ws_conf.base_reconnect_delay

        while True:
            try:
                async with self._ws_connect(url) as websocket:
                    reconnect_delay = self._ws_conf.base_reconnect_delay
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            if "data" not in data:
                                continue

                            mark_data = data["data"]

                            # Verify this is a mark price update with funding rate
                            if not mark_data or "r" not in mark_data or "T" not in mark_data:
                                continue

                            # Parse funding rate data
                            funding_rate = FundingRate(
                                symbol=mark_data["s"],
                                funding_time=datetime.fromtimestamp(
                                    mark_data["T"] / 1000, tz=timezone.utc
                                ),
                                funding_rate=Decimal(str(mark_data["r"])),
                                mark_price=(
                                    Decimal(str(mark_data["p"])) if "p" in mark_data else None
                                ),
                            )

                            yield funding_rate

                        except Exception as e:  # noqa: BLE001
                            logger.error(f"stream_funding_rate parse error: {e}")

            except asyncio.CancelledError:
                raise
            except websockets.exceptions.ConnectionClosed:
                # Graceful reconnect with backoff
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Funding rate WS error: {e}")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)

    async def stream_mark_price(
        self,
        symbols: list[str],
        update_speed: str = "1s",
    ) -> AsyncIterator[MarkPrice]:
        """Yield mark price and index price updates for multiple symbols.

        The @markPrice stream provides comprehensive pricing data including:
        - Mark Price: Used for liquidations and unrealized PnL
        - Index Price: Weighted average spot price from multiple exchanges
        - Funding Rate: Current predicted funding rate
        - Next Funding Time: When funding will be applied

        This stream is essential for:
        - Monitoring mark/index price divergence (dislocation alerts)
        - Detecting venue anomalies (index vs exchange spot)
        - Preventing unfair liquidations
        - Fair PnL calculations

        Args:
            symbols: List of symbols to monitor (e.g., ["BTCUSDT", "ETHUSDT"])
            update_speed: Update frequency ("1s" or "3s")

        Yields:
            MarkPrice: Mark price updates with index price and funding data

        Example:
            >>> async for mp in provider.stream_mark_price(["BTCUSDT"]):
            >>>     if mp.is_high_spread:
            >>>         print(f"Alert: Mark/Index spread {mp.mark_index_spread_bps} bps")

        Note:
            - Updates every 1 second (or 3 seconds)
            - Only available for Futures market
            - Contains both mark and index prices for comparison
        """
        if self.market_type != MarketType.FUTURES:
            raise ValueError("Mark price streaming is only available for Futures market")

        if update_speed not in ["1s", "3s"]:
            raise ValueError("update_speed must be '1s' or '3s'")

        ws_base = WS_COMBINED_URLS.get(self.market_type)
        if not ws_base:
            raise ValueError(f"WebSocket not supported for market type: {self.market_type}")

        # Create stream names for mark price
        stream_names = [f"{s.lower()}@markPrice@{update_speed}" for s in symbols]
        url = f"{ws_base}?streams={'/'.join(stream_names)}"

        reconnect_delay = self._ws_conf.base_reconnect_delay

        while True:
            try:
                async with self._ws_connect(url) as websocket:
                    reconnect_delay = self._ws_conf.base_reconnect_delay
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            if "data" not in data:
                                continue

                            mark_data = data["data"]

                            # Verify this is a mark price update
                            if not mark_data or mark_data.get("e") != "markPriceUpdate":
                                continue

                            # Parse mark price data
                            # Fields: s=symbol, p=mark, i=index, P=settle, r=funding, T=next funding time, E=event time
                            mark_price = MarkPrice(
                                symbol=mark_data["s"],
                                mark_price=Decimal(str(mark_data["p"])),
                                index_price=(
                                    Decimal(str(mark_data["i"])) if "i" in mark_data else None
                                ),
                                estimated_settle_price=(
                                    Decimal(str(mark_data["P"])) if "P" in mark_data else None
                                ),
                                last_funding_rate=(
                                    Decimal(str(mark_data["r"])) if "r" in mark_data else None
                                ),
                                next_funding_time=(
                                    datetime.fromtimestamp(mark_data["T"] / 1000, tz=timezone.utc)
                                    if "T" in mark_data
                                    else None
                                ),
                                timestamp=datetime.fromtimestamp(
                                    mark_data["E"] / 1000, tz=timezone.utc
                                ),
                            )

                            yield mark_price

                        except Exception as e:  # noqa: BLE001
                            logger.error(f"stream_mark_price parse error: {e}")

            except asyncio.CancelledError:
                raise
            except websockets.exceptions.ConnectionClosed:
                # Graceful reconnect with backoff
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Mark price WS error: {e}")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)

    async def stream_order_book(
        self,
        symbol: str,
        update_speed: str = "100ms",
    ) -> AsyncIterator[OrderBook]:
        """Yield order book updates for a symbol using depth stream.

        The @depth stream provides real-time order book updates (partial book).
        For full order book maintenance, use get_order_book() REST then apply deltas.

        Args:
            symbol: Symbol to monitor (e.g., "BTCUSDT")
            update_speed: Update frequency ("100ms" or "1000ms")

        Yields:
            OrderBook: Order book snapshots/updates

        Note:
            - This streams UPDATES (deltas), not full snapshots
            - Use get_order_book() first for initial snapshot
            - Updates every 100ms or 1000ms
            - Available for both SPOT and FUTURES
        """
        if update_speed not in ["100ms", "1000ms"]:
            raise ValueError("update_speed must be '100ms' or '1000ms'")

        ws_base = WS_SINGLE_URLS.get(self.market_type)
        if not ws_base:
            raise ValueError(f"WebSocket not supported for market type: {self.market_type}")

        # Depth stream URL
        stream_suffix = f"@depth@{update_speed}"
        url = f"{ws_base}/{symbol.lower()}{stream_suffix}"

        reconnect_delay = self._ws_conf.base_reconnect_delay

        while True:
            try:
                async with self._ws_connect(url) as websocket:
                    reconnect_delay = self._ws_conf.base_reconnect_delay
                    async for message in websocket:
                        try:
                            data = json.loads(message)

                            # Verify this is a depth update
                            if data.get("e") != "depthUpdate":
                                continue

                            # Parse bids and asks
                            bids = [
                                (Decimal(str(price)), Decimal(str(qty)))
                                for price, qty in data.get("b", [])
                            ]
                            asks = [
                                (Decimal(str(price)), Decimal(str(qty)))
                                for price, qty in data.get("a", [])
                            ]

                            # Skip empty updates
                            if not bids and not asks:
                                continue

                            # Create OrderBook with updates
                            # Note: This is a delta, not full book
                            order_book = OrderBook(
                                symbol=data["s"],
                                last_update_id=data["u"],
                                bids=(
                                    bids if bids else [(Decimal("0"), Decimal("0"))]
                                ),  # At least one level
                                asks=asks if asks else [(Decimal("0"), Decimal("0"))],
                                timestamp=datetime.fromtimestamp(data["E"] / 1000, tz=timezone.utc),
                            )

                            yield order_book

                        except Exception as e:  # noqa: BLE001
                            logger.error(f"stream_order_book parse error: {e}")

            except asyncio.CancelledError:
                raise
            except websockets.exceptions.ConnectionClosed:
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Order book WS error: {e}")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)

    async def stream_trades_multi(
        self,
        symbols: list[str],
    ) -> AsyncIterator[Trade]:
        """Yield real-time trades for multiple symbols.

        The @trade stream provides individual trade executions as they occur.

        Args:
            symbols: List of symbols to monitor (e.g., ["BTCUSDT", "ETHUSDT"])

        Yields:
            Trade: Individual trade executions

        Note:
            - Streams EVERY trade execution in real-time
            - High frequency for popular pairs
            - Available for both SPOT and FUTURES
        """
        ws_base = WS_COMBINED_URLS.get(self.market_type)
        if not ws_base:
            raise ValueError(f"WebSocket not supported for market type: {self.market_type}")

        # Create stream names for trades
        stream_names = [f"{s.lower()}@trade" for s in symbols]
        url = f"{ws_base}?streams={'/'.join(stream_names)}"

        reconnect_delay = self._ws_conf.base_reconnect_delay

        while True:
            try:
                async with self._ws_connect(url) as websocket:
                    reconnect_delay = self._ws_conf.base_reconnect_delay
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            if "data" not in data:
                                continue

                            trade_data = data["data"]

                            # Verify this is a trade event
                            if not trade_data or trade_data.get("e") != "trade":
                                continue

                            # Parse trade
                            # Fields: s=symbol, t=trade id, p=price, q=quantity, T=time, m=is buyer maker
                            trade = Trade(
                                symbol=trade_data["s"],
                                trade_id=trade_data["t"],
                                price=Decimal(str(trade_data["p"])),
                                quantity=Decimal(str(trade_data["q"])),
                                quote_quantity=Decimal(str(trade_data.get("q", "0")))
                                * Decimal(str(trade_data["p"])),
                                timestamp=datetime.fromtimestamp(
                                    trade_data["T"] / 1000, tz=timezone.utc
                                ),
                                is_buyer_maker=trade_data["m"],
                                is_best_match=trade_data.get("M"),
                            )

                            yield trade

                        except Exception as e:  # noqa: BLE001
                            logger.error(f"stream_trades_multi parse error: {e}")

            except asyncio.CancelledError:
                raise
            except websockets.exceptions.ConnectionClosed:
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Trades WS error: {e}")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = self._next_delay(reconnect_delay)
