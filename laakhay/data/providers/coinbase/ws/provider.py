"""Coinbase WebSocket-only provider.

Implements the WSProvider interface for Coinbase Advanced Trade API.
Coinbase Advanced Trade API only supports Spot markets.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Any

from ....core import MarketType, Timeframe
from ....io import MessageAdapter, WSProvider
from ....models.streaming_bar import StreamingBar
from ..constants import WS_PUBLIC_URLS
from .adapters import OhlcvAdapter, OrderBookAdapter, TradesAdapter
from .endpoints import ohlcv_spec, order_book_spec, trades_spec
from .transport import CoinbaseWebSocketTransport

if TYPE_CHECKING:
    from ....models import OrderBook, Trade


class CoinbaseWSProvider(WSProvider):
    """Streaming-only provider for Coinbase Advanced Trade API (Spot markets only)."""

    def __init__(self, *, market_type: MarketType = MarketType.SPOT) -> None:
        # Coinbase Advanced Trade API only supports Spot markets
        if market_type != MarketType.SPOT:
            raise ValueError(
                "Coinbase Advanced Trade API only supports Spot markets. "
                f"Got market_type={market_type}"
            )

        self.market_type = MarketType.SPOT  # Force to SPOT

        # Endpoint registry: key -> (spec_builder, adapter_class)
        self._ENDPOINTS: dict[str, tuple[Callable[[MarketType], Any], type[MessageAdapter]]] = {
            "ohlcv": (ohlcv_spec, OhlcvAdapter),
            "trades": (trades_spec, TradesAdapter),
            "order_book": (order_book_spec, OrderBookAdapter),
            # Note: Coinbase doesn't support Futures features:
            # - open_interest
            # - funding_rate
            # - mark_price
            # - liquidations
        }

    async def stream_ohlcv(  # type: ignore[override,misc]
        self,
        symbol: str,
        interval: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        """Stream OHLCV candles for a symbol."""
        # Delegate to registry-backed stream()
        async for obj in self.stream(
            "ohlcv",
            [symbol],
            {"interval": interval},
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_key=None,
        ):
            yield obj

    async def stream_ohlcv_multi(  # type: ignore[override,misc]
        self,
        symbols: list[str],
        interval: Timeframe,
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_same_candle: bool = False,
    ) -> AsyncIterator[StreamingBar]:
        """Stream OHLCV candles for multiple symbols."""
        async for obj in self.stream(
            "ohlcv",
            symbols,
            {"interval": interval},
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_key=None,
        ):
            yield obj

    async def close(self) -> None:
        """Close WebSocket connections."""
        # No persistent sockets to close beyond task cancellation handled by callers
        return None

    async def _stream(
        self,
        spec: Any,
        adapter: MessageAdapter,
        symbols: list[str],
        params: dict[str, Any],
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_key: Any | None = None,
    ) -> AsyncIterator[Any]:
        """Internal streaming method using Coinbase-specific transport."""
        import time

        # Get WebSocket URL
        ws_url = WS_PUBLIC_URLS.get(self.market_type)
        if not ws_url:
            raise ValueError(f"WebSocket not supported for market type: {self.market_type}")

        # Build stream names (topics) for Coinbase transport
        # build_stream_name normalizes symbols internally
        topics = [spec.build_stream_name(s, params) for s in symbols]

        # Create Coinbase-specific transport
        transport = CoinbaseWebSocketTransport(ws_url)

        # Track last emit times for throttling
        last_emit: dict[str, float] = {}
        last_close: dict[tuple[str, int], str] = {}

        # Stream messages from Coinbase WebSocket
        async for payload in transport.stream(topics):
            # Parse messages through adapter
            for obj in adapter.parse(payload):
                # Filter closed candles if requested
                if only_closed and getattr(obj, "is_closed", False) is False:
                    continue

                # Apply throttling
                if throttle_ms:
                    now = time.time()
                    sym = getattr(obj, "symbol", "")
                    last = last_emit.get(sym)
                    if last is not None and (now - last) < (throttle_ms / 1000.0):
                        continue
                    last_emit[sym] = now

                # Apply deduplication
                if dedupe_key and not only_closed:
                    sym, ts, close_str = dedupe_key(obj)
                    key = (sym, ts)
                    if last_close.get(key) == close_str:
                        continue
                    last_close[key] = close_str

                yield obj

    async def stream(
        self,
        endpoint: str,
        symbols: list[str],
        params: dict[str, Any],
        *,
        only_closed: bool = False,
        throttle_ms: int | None = None,
        dedupe_key: Any | None = None,
    ) -> AsyncIterator[Any]:
        """Generic stream method."""
        if endpoint not in self._ENDPOINTS:
            raise ValueError(f"Unknown endpoint: {endpoint}")
        spec_fn, adapter_cls = self._ENDPOINTS[endpoint]
        spec = spec_fn(self.market_type)
        adapter = adapter_cls()

        # Apply endpoint-specific defaults
        if endpoint == "ohlcv" and not only_closed and dedupe_key is None:

            def _ohlcv_key(obj) -> tuple[str, int, str]:
                return (obj.symbol, int(obj.timestamp.timestamp() * 1000), str(obj.close))

            dedupe_key = _ohlcv_key

        async for obj in self._stream(
            spec,
            adapter,
            symbols,
            params,
            only_closed=only_closed,
            throttle_ms=throttle_ms,
            dedupe_key=dedupe_key,
        ):
            yield obj

    # --- Trades ---
    async def stream_trades(self, symbol: str) -> AsyncIterator[Trade]:
        """Stream trades for a symbol."""
        async for obj in self.stream("trades", [symbol], {}):
            yield obj

    async def stream_trades_multi(self, symbols: list[str]) -> AsyncIterator[Trade]:
        """Stream trades for multiple symbols."""
        async for obj in self.stream("trades", symbols, {}):
            yield obj

    # --- Order Book ---
    async def stream_order_book(
        self, symbol: str, update_speed: str = "100ms"
    ) -> AsyncIterator[OrderBook]:
        """Stream order book updates for a symbol.

        Note: Coinbase Exchange API requires authentication for level2 WebSocket.
        This method will raise NotImplementedError. Use REST API for order book snapshots instead.
        """
        raise NotImplementedError(
            "Coinbase Exchange API requires authentication for level2 WebSocket. "
            "Use REST API (get_order_book) for order book data, or implement authentication for WebSocket."
        )

    # --- Futures features (NOT SUPPORTED) ---
    async def stream_open_interest(self, symbols: list[str], period: str = "5m") -> AsyncIterator:
        """Stream open interest - NOT SUPPORTED by Coinbase Advanced Trade API."""
        raise NotImplementedError(
            "Coinbase Advanced Trade API does not support open interest "
            "(Futures feature, not available on Spot markets)"
        )

    async def stream_funding_rate(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator:
        """Stream funding rates - NOT SUPPORTED by Coinbase Advanced Trade API."""
        raise NotImplementedError(
            "Coinbase Advanced Trade API does not support funding rates "
            "(Futures feature, not available on Spot markets)"
        )

    async def stream_mark_price(
        self, symbols: list[str], update_speed: str = "1s"
    ) -> AsyncIterator:
        """Stream mark prices - NOT SUPPORTED by Coinbase Advanced Trade API."""
        raise NotImplementedError(
            "Coinbase Advanced Trade API does not support mark prices "
            "(Futures feature, not available on Spot markets)"
        )

    async def stream_liquidations(self) -> AsyncIterator:
        """Stream liquidations - NOT SUPPORTED by Coinbase Advanced Trade API."""
        raise NotImplementedError(
            "Coinbase Advanced Trade API does not support liquidations "
            "(Futures feature, not available on Spot markets)"
        )
