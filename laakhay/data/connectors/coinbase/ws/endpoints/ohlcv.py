"""Coinbase OHLCV WebSocket endpoint specification and adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.coinbase.config import INTERVAL_MAP, WS_PUBLIC_URLS, normalize_symbol_from_coinbase, normalize_symbol_to_coinbase
from laakhay.data.core import MarketType, Timeframe
from laakhay.data.models.streaming_bar import StreamingBar
from laakhay.data.runtime.ws.runner import MessageAdapter, WSEndpointSpec


def build_spec(market_type: MarketType) -> WSEndpointSpec:
    """Build OHLCV WebSocket endpoint specification.

    Args:
        market_type: Market type (only SPOT supported for Coinbase)

    Returns:
        WSEndpointSpec for OHLCV streaming
    """
    if market_type != MarketType.SPOT:
        raise ValueError("Coinbase Advanced Trade API only supports Spot markets")

    ws_url = WS_PUBLIC_URLS.get(market_type)
    if not ws_url:
        raise ValueError(f"WebSocket not supported for market type: {market_type}")

    def build_stream_name(symbol: str, params: dict[str, Any]) -> str:
        """Build channel name for OHLCV subscription.

        Coinbase format: candles channel with product_id
        Note: Actual subscription uses JSON message, this is for identification
        """
        product_id = normalize_symbol_to_coinbase(symbol)
        interval: Timeframe = params["interval"]
        interval_str = INTERVAL_MAP[interval]
        # Format: {product_id}:{channel}:{granularity}
        return f"{product_id}:candles:{interval_str}"

    def build_combined_url(names: list[str]) -> str:
        """Build WebSocket URL for combined subscriptions.

        Coinbase uses single URL, subscriptions sent via JSON messages.
        """
        return ws_url

    def build_single_url(name: str) -> str:
        """Build WebSocket URL for single subscription."""
        return ws_url

    # Coinbase supports multiple subscriptions per connection
    # Exact limit TBD - using conservative estimate
    max_streams = 50
    return WSEndpointSpec(
        id="ohlcv",
        combined_supported=True,  # Coinbase supports multiple channels in one subscription
        max_streams_per_connection=max_streams,
        build_stream_name=build_stream_name,
        build_combined_url=build_combined_url,
        build_single_url=build_single_url,
    )


class Adapter(MessageAdapter):
    """Adapter for parsing Coinbase OHLCV WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if message is a candles update."""
        if isinstance(payload, dict):
            # Coinbase format: {"type": "candle", "product_id": "...", ...}
            msg_type = payload.get("type", "")
            return msg_type in ("candle", "candles")
        return False

    def parse(self, payload: Any) -> list[StreamingBar]:
        """Parse candles message to StreamingBar."""
        out: list[StreamingBar] = []
        if not isinstance(payload, dict):
            return out

        try:
            # Extract product_id and normalize to standard symbol format
            product_id = payload.get("product_id", "")
            if not product_id:
                return out

            symbol = normalize_symbol_from_coinbase(product_id)

            # Coinbase candle format (expected):
            # {
            #   "type": "candle",
            #   "product_id": "BTC-USD",
            #   "candles": [
            #     {
            #       "start": "2024-01-01T00:00:00Z",
            #       "low": "42000.00",
            #       "high": "43000.00",
            #       "open": "42500.00",
            #       "close": "42800.00",
            #       "volume": "123.45"
            #     }
            #   ]
            # }
            # OR single candle object:
            # {
            #   "type": "candle",
            #   "product_id": "BTC-USD",
            #   "start": "2024-01-01T00:00:00Z",
            #   "open": "42500.00",
            #   ...
            # }

            candles = payload.get("candles")
            if candles is None or not isinstance(candles, list):
                # Check if payload itself is a candle object (has "open" field)
                # This handles cases where candles field is missing or payload is single candle
                candles = [payload] if payload.get("open") is not None else []

            for candle in candles:
                if not isinstance(candle, dict):
                    continue

                # Parse timestamp
                start_str = candle.get("start", "")
                if not start_str:
                    continue

                if isinstance(start_str, str):
                    ts_str = start_str.replace("Z", "+00:00")
                    timestamp = datetime.fromisoformat(ts_str)
                else:
                    timestamp = datetime.fromtimestamp(float(start_str), tz=UTC)

                # Parse OHLCV
                open_price = Decimal(str(candle.get("open", "0")))
                high_price = Decimal(str(candle.get("high", "0")))
                low_price = Decimal(str(candle.get("low", "0")))
                close_price = Decimal(str(candle.get("close", "0")))
                volume = Decimal(str(candle.get("volume", "0")))

                # Determine if candle is closed (typically if it's a historical update)
                is_closed = candle.get("is_closed", True)

                out.append(
                    StreamingBar(
                        symbol=symbol,
                        timestamp=timestamp,
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=close_price,
                        volume=volume,
                        is_closed=is_closed,
                    )
                )
        except Exception:
            return []

        return out

