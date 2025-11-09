"""Message adapters for Bybit WebSocket streams."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from ....io import MessageAdapter
from ....models import FundingRate, Liquidation, MarkPrice, OpenInterest, OrderBook, Trade
from ....models.streaming_bar import StreamingBar


class OhlcvAdapter(MessageAdapter):
    """Adapter for kline/OHLCV WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        topic = payload.get("topic", "")
        return bool(isinstance(topic, str) and topic.startswith("kline."))

    def parse(self, payload: Any) -> list[StreamingBar]:
        out: list[StreamingBar] = []
        if not isinstance(payload, dict):
            return out

        topic = payload.get("topic", "")
        data_list = payload.get("data", [])

        if not isinstance(data_list, list):
            return out

        # Extract symbol from topic: kline.{interval}.{symbol}
        parts = topic.split(".")
        if len(parts) < 3:
            return out
        symbol = parts[2].upper()

        for item in data_list:
            if not isinstance(item, dict):
                continue

            try:
                # Bybit kline format: {start, end, interval, open, close, high, low, volume, turnover, confirm}
                start_ms = item.get("start", item.get("t", 0))
                open_price = item.get("open")
                high_price = item.get("high")
                low_price = item.get("low")
                close_price = item.get("close")
                volume = item.get("volume")
                confirm = item.get("confirm", False)  # Whether candle is closed

                if not all([start_ms, open_price, high_price, low_price, close_price, volume]):
                    continue

                if start_ms is None:
                    continue

                out.append(
                    StreamingBar(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(int(start_ms) / 1000, tz=UTC),
                        open=Decimal(str(open_price)),
                        high=Decimal(str(high_price)),
                        low=Decimal(str(low_price)),
                        close=Decimal(str(close_price)),
                        volume=Decimal(str(volume)),
                        is_closed=bool(confirm),
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue

        return out


class TradesAdapter(MessageAdapter):
    """Adapter for trade WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        topic = payload.get("topic", "")
        return bool(isinstance(topic, str) and topic.startswith("publicTrade."))

    def parse(self, payload: Any) -> list[Trade]:
        out: list[Trade] = []
        if not isinstance(payload, dict):
            return out

        topic = payload.get("topic", "")
        data_list = payload.get("data", [])

        if not isinstance(data_list, list):
            return out

        # Extract symbol from topic: publicTrade.{symbol}
        parts = topic.split(".")
        if len(parts) < 2:
            return out
        symbol = parts[1].upper()

        for item in data_list:
            if not isinstance(item, dict):
                continue

            try:
                # Bybit trade format: {T, s, S, v, p, L, i, BT}
                # T: timestamp, s: symbol, S: side (Buy/Sell), v: volume, p: price, L: lastTickDirection, i: tradeId, BT: blockTrade
                time_ms = item.get("T", 0)
                price_str = item.get("p")
                qty_str = item.get("v")
                side = item.get("S", "")
                trade_id = item.get("i", "")

                if not all([time_ms, price_str, qty_str]):
                    continue

                price = Decimal(str(price_str))
                quantity = Decimal(str(qty_str))
                quote_quantity = price * quantity

                # Bybit side: "Buy" means buyer is maker, "Sell" means seller is maker
                is_buyer_maker = side == "Buy"

                out.append(
                    Trade(
                        symbol=symbol,
                        trade_id=int(hash(trade_id)) if trade_id else 0,
                        price=price,
                        quantity=quantity,
                        quote_quantity=quote_quantity,
                        timestamp=datetime.fromtimestamp(int(time_ms) / 1000, tz=UTC),
                        is_buyer_maker=is_buyer_maker,
                        is_best_match=None,
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue

        return out


class OrderBookAdapter(MessageAdapter):
    """Adapter for orderbook WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        topic = payload.get("topic", "")
        return bool(isinstance(topic, str) and topic.startswith("orderbook."))

    def parse(self, payload: Any) -> list[OrderBook]:
        out: list[OrderBook] = []
        if not isinstance(payload, dict):
            return out

        topic = payload.get("topic", "")
        data = payload.get("data", {})
        ts_ms = payload.get("ts", 0)

        if not isinstance(data, dict):
            return out

        # Extract symbol from topic: orderbook.{depth}.{symbol}
        parts = topic.split(".")
        if len(parts) < 3:
            return out
        symbol = parts[2].upper()

        try:
            # Bybit orderbook format: {s, b, a, ts, u}
            # s: symbol, b: bids, a: asks, ts: timestamp, u: updateId
            bids_data = data.get("b", [])
            asks_data = data.get("a", [])

            bids = []
            asks = []

            if isinstance(bids_data, list) and len(bids_data) > 0:
                bids = [
                    (Decimal(str(p)), Decimal(str(q)))
                    for item in bids_data
                    if isinstance(item, list) and len(item) >= 2
                    for p, q in [item[:2]]
                ]

            if isinstance(asks_data, list) and len(asks_data) > 0:
                asks = [
                    (Decimal(str(p)), Decimal(str(q)))
                    for item in asks_data
                    if isinstance(item, list) and len(item) >= 2
                    for p, q in [item[:2]]
                ]

            # Handle both snapshot and delta types
            # Bybit uses "u" for update ID or "seq" for sequence number
            last_update_id_raw = data.get("u") or data.get("seq") or 0
            last_update_id = int(last_update_id_raw) if last_update_id_raw is not None else 0

            timestamp = datetime.fromtimestamp(ts_ms / 1000, tz=UTC) if ts_ms else datetime.now(UTC)

            out.append(
                OrderBook(
                    symbol=symbol,
                    last_update_id=last_update_id,
                    bids=bids if bids else [(Decimal("0"), Decimal("0"))],
                    asks=asks if asks else [(Decimal("0"), Decimal("0"))],
                    timestamp=timestamp,
                )
            )
        except (ValueError, TypeError, KeyError, IndexError):
            return []

        return out


class OpenInterestAdapter(MessageAdapter):
    """Adapter for open interest WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        topic = payload.get("topic", "")
        return bool(isinstance(topic, str) and topic.startswith("openInterest."))

    def parse(self, payload: Any) -> list[OpenInterest]:
        out: list[OpenInterest] = []
        if not isinstance(payload, dict):
            return out

        topic = payload.get("topic", "")
        data = payload.get("data", {})
        ts_ms = payload.get("ts", 0)

        if not isinstance(data, dict):
            return out

        # Extract symbol from topic: openInterest.{symbol}
        parts = topic.split(".")
        if len(parts) < 2:
            return out
        symbol = parts[1].upper()

        try:
            # Bybit open interest format: {openInterest, openInterestValue, timestamp}
            oi_str = data.get("openInterest")
            oi_value_str = data.get("openInterestValue")
            timestamp_ms = data.get("timestamp", ts_ms)

            if oi_str is None:
                return []

            timestamp = (
                datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=UTC)
                if timestamp_ms
                else datetime.now(UTC)
            )

            out.append(
                OpenInterest(
                    symbol=symbol,
                    timestamp=timestamp,
                    open_interest=Decimal(str(oi_str)),
                    open_interest_value=Decimal(str(oi_value_str)) if oi_value_str else None,
                )
            )
        except (ValueError, TypeError, KeyError):
            return []

        return out


class FundingRateAdapter(MessageAdapter):
    """Adapter for funding rate WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        topic = payload.get("topic", "")
        return bool(isinstance(topic, str) and topic.startswith("funding."))

    def parse(self, payload: Any) -> list[FundingRate]:
        out: list[FundingRate] = []
        if not isinstance(payload, dict):
            return out

        topic = payload.get("topic", "")
        data = payload.get("data", {})

        if not isinstance(data, dict):
            return out

        # Extract symbol from topic: funding.{symbol}
        parts = topic.split(".")
        if len(parts) < 2:
            return out
        symbol = parts[1].upper()

        try:
            # Bybit funding rate format: {fundingRate, fundingRateTimestamp, symbol, markPrice}
            fr_str = data.get("fundingRate")
            ts_ms = data.get("fundingRateTimestamp", data.get("fundingTime", 0))
            mark_price_str = data.get("markPrice")

            if fr_str is None or ts_ms is None:
                return []

            out.append(
                FundingRate(
                    symbol=symbol,
                    funding_time=datetime.fromtimestamp(int(ts_ms) / 1000, tz=UTC),
                    funding_rate=Decimal(str(fr_str)),
                    mark_price=Decimal(str(mark_price_str)) if mark_price_str else None,
                )
            )
        except (ValueError, TypeError, KeyError):
            return []

        return out


class MarkPriceAdapter(MessageAdapter):
    """Adapter for mark price WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        topic = payload.get("topic", "")
        return bool(isinstance(topic, str) and topic.startswith("markPrice."))

    def parse(self, payload: Any) -> list[MarkPrice]:
        out: list[MarkPrice] = []
        if not isinstance(payload, dict):
            return out

        topic = payload.get("topic", "")
        data = payload.get("data", {})
        ts_ms = payload.get("ts", 0)

        if not isinstance(data, dict):
            return out

        # Extract symbol from topic: markPrice.{symbol}
        parts = topic.split(".")
        if len(parts) < 2:
            return out
        symbol = parts[1].upper()

        try:
            # Bybit mark price format: {symbol, markPrice, indexPrice, fundingRate, nextFundingTime}
            mark_price_str = data.get("markPrice")
            index_price_str = data.get("indexPrice")
            funding_rate_str = data.get("fundingRate")
            next_funding_time_ms = data.get("nextFundingTime")

            if mark_price_str is None:
                return []

            timestamp = (
                datetime.fromtimestamp(int(ts_ms) / 1000, tz=UTC) if ts_ms else datetime.now(UTC)
            )

            next_funding_time = (
                datetime.fromtimestamp(int(next_funding_time_ms) / 1000, tz=UTC)
                if next_funding_time_ms
                else None
            )

            out.append(
                MarkPrice(
                    symbol=symbol,
                    mark_price=Decimal(str(mark_price_str)),
                    index_price=Decimal(str(index_price_str)) if index_price_str else None,
                    estimated_settle_price=None,
                    last_funding_rate=Decimal(str(funding_rate_str)) if funding_rate_str else None,
                    next_funding_time=next_funding_time,
                    timestamp=timestamp,
                )
            )
        except (ValueError, TypeError, KeyError):
            return []

        return out


class LiquidationsAdapter(MessageAdapter):
    """Adapter for liquidation WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        topic = payload.get("topic", "")
        return bool(isinstance(topic, str) and topic.startswith("liquidation."))

    def parse(self, payload: Any) -> list[Liquidation]:
        out: list[Liquidation] = []
        if not isinstance(payload, dict):
            return out

        topic = payload.get("topic", "")
        data = payload.get("data")
        ts_ms = payload.get("ts", 0)

        # Extract symbol from topic: liquidation.{symbol}
        parts = topic.split(".")
        if len(parts) < 2:
            return out
        symbol = parts[1].upper()

        # Bybit can send data as dict or list
        data_items = []
        if isinstance(data, dict):
            data_items = [data]
        elif isinstance(data, list):
            data_items = data
        else:
            return out

        for item in data_items:
            if not isinstance(item, dict):
                continue

            try:
                # Bybit liquidation format: {symbol, side, size, price, time}
                side = item.get("side", "")
                size_str = item.get("size")
                price_str = item.get("price")
                time_ms = item.get("time", ts_ms)

                if not all([side, size_str, price_str]):
                    continue

                side_upper = side.upper()
                if side_upper not in ["BUY", "SELL"]:
                    continue

                timestamp = (
                    datetime.fromtimestamp(int(time_ms) / 1000, tz=UTC)
                    if time_ms
                    else datetime.now(UTC)
                )

                out.append(
                    Liquidation(
                        symbol=symbol,
                        timestamp=timestamp,
                        side=side_upper,
                        order_type="LIQUIDATION",
                        time_in_force="IOC",
                        original_quantity=Decimal(str(size_str)),
                        price=Decimal(str(price_str)),
                        average_price=Decimal(str(price_str)),  # Use same as price if not available
                        order_status="FILLED",
                        last_filled_quantity=Decimal(str(size_str)),
                        accumulated_quantity=Decimal(str(size_str)),
                        commission=None,
                        commission_asset=None,
                        trade_id=None,
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue

        return out
