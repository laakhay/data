"""Message adapters for Coinbase WebSocket streams."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from ....io import MessageAdapter
from ....models import OrderBook, Trade
from ....models.streaming_bar import StreamingBar
from ..constants import normalize_symbol_from_coinbase


class OhlcvAdapter(MessageAdapter):
    """Adapter for OHLCV/candles WebSocket messages."""

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


class TradesAdapter(MessageAdapter):
    """Adapter for trades/matches WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if message is a trade update."""
        if isinstance(payload, dict):
            # Exchange API uses "match" for new trades and "last_match" for the last trade before subscription
            msg_type = payload.get("type", "")
            return msg_type in ("match", "last_match")
        return False

    def parse(self, payload: Any) -> list[Trade]:
        """Parse trade message to Trade."""
        out: list[Trade] = []
        if not isinstance(payload, dict):
            return out

        try:
            # Extract product_id and normalize
            product_id = payload.get("product_id", "")
            if not product_id:
                return out

            symbol = normalize_symbol_from_coinbase(product_id)

            # Coinbase match format (expected):
            # {
            #   "type": "match",
            #   "product_id": "BTC-USD",
            #   "price": "42800.00",
            #   "size": "0.5",
            #   "time": "2024-01-01T12:00:00Z",
            #   "side": "BUY",
            #   "trade_id": "123456"
            # }

            price_str = payload.get("price")
            size_str = payload.get("size")

            if not price_str or not size_str:
                return out

            price = Decimal(str(price_str))
            quantity = Decimal(str(size_str))
            quote_quantity = price * quantity

            # Parse timestamp
            time_str = payload.get("time", "")
            if time_str:
                if isinstance(time_str, str):
                    ts_str = time_str.replace("Z", "+00:00")
                    timestamp = datetime.fromisoformat(ts_str)
                else:
                    timestamp = datetime.fromtimestamp(float(time_str), tz=UTC)
            else:
                timestamp = datetime.now(UTC)

            # Extract trade ID
            trade_id_str = payload.get("trade_id", "")
            trade_id = 0
            if trade_id_str:
                try:
                    trade_id = int(trade_id_str)
                except (ValueError, TypeError):
                    trade_id = abs(hash(trade_id_str)) % (10**10)

            # Extract side - Exchange API uses lowercase "buy"/"sell"
            side = payload.get("side", "").upper()
            # "BUY" means buyer is taker, "SELL" means seller is taker
            is_buyer_maker = side == "SELL"

            out.append(
                Trade(
                    symbol=symbol,
                    trade_id=trade_id,
                    price=price,
                    quantity=quantity,
                    quote_quantity=quote_quantity,
                    timestamp=timestamp,
                    is_buyer_maker=is_buyer_maker,
                    is_best_match=None,  # Coinbase doesn't provide this
                )
            )
        except Exception:
            return []

        return out


class OrderBookAdapter(MessageAdapter):
    """Adapter for order book/level2 WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        """Check if message is an order book update."""
        if isinstance(payload, dict):
            # Coinbase format: {"type": "l2update", "product_id": "...", ...}
            msg_type = payload.get("type", "")
            return msg_type in ("l2update", "level2", "snapshot")
        return False

    def parse(self, payload: Any) -> list[OrderBook]:
        """Parse order book message to OrderBook."""
        out: list[OrderBook] = []
        if not isinstance(payload, dict):
            return out

        try:
            # Extract product_id and normalize
            product_id = payload.get("product_id", "")
            if not product_id:
                return out

            symbol = normalize_symbol_from_coinbase(product_id)

            # Coinbase level2 format (expected):
            # {
            #   "type": "l2update",
            #   "product_id": "BTC-USD",
            #   "changes": [
            #     ["buy", "42800.00", "1.5"],
            #     ["sell", "42810.00", "2.0"]
            #   ],
            #   "time": "2024-01-01T12:00:00Z"
            # }

            # For order book updates, we need to maintain state
            # This adapter returns the update, but the provider should maintain full book
            changes = payload.get("changes", [])
            if not isinstance(changes, list):
                return out

            bids = []
            asks = []

            for change in changes:
                if not isinstance(change, list) or len(change) < 3:
                    continue

                side = change[0]  # "buy" or "sell"
                price_str = change[1]
                size_str = change[2]

                try:
                    price = Decimal(str(price_str))
                    quantity = Decimal(str(size_str))

                    if side == "buy":
                        bids.append((price, quantity))
                    elif side == "sell":
                        asks.append((price, quantity))
                except (ValueError, TypeError):
                    continue

            # Parse timestamp
            time_str = payload.get("time", "")
            if time_str:
                if isinstance(time_str, str):
                    ts_str = time_str.replace("Z", "+00:00")
                    timestamp = datetime.fromisoformat(ts_str)
                else:
                    timestamp = datetime.fromtimestamp(float(time_str), tz=UTC)
            else:
                timestamp = datetime.now(UTC)

            # Note: This returns only the changes, not full book
            # Provider should maintain full order book state
            out.append(
                OrderBook(
                    symbol=symbol,
                    last_update_id=0,  # Coinbase doesn't provide sequence numbers
                    bids=bids,
                    asks=asks,
                    timestamp=timestamp,
                )
            )
        except Exception:
            return []

        return out
