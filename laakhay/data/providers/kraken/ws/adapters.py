"""Message adapters for Kraken WebSocket streams."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from ....core import MarketType
from ....io import MessageAdapter
from ....models import FundingRate, Liquidation, MarkPrice, OpenInterest, OrderBook, Trade
from ....models.streaming_bar import StreamingBar
from ..constants import normalize_symbol_from_kraken


class OhlcvAdapter(MessageAdapter):
    """Adapter for OHLCV/Candles WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        channel = payload.get("channel", "")
        return channel.startswith("ohlc") or "ohlc" in str(payload.get("event", ""))

    def parse(self, payload: Any) -> list[StreamingBar]:
        out: list[StreamingBar] = []
        if not isinstance(payload, dict):
            return out

        # Kraken format: {channel: "ohlc", symbol: "PI_XBTUSD", data: [{time, open, high, low, close, volume}, ...]}
        symbol_raw = payload.get("symbol", "")
        data_list = payload.get("data", [])

        if not symbol_raw:
            return out

        # Determine market type from symbol format
        market_type = MarketType.FUTURES if symbol_raw.startswith("PI_") else MarketType.SPOT
        symbol = normalize_symbol_from_kraken(symbol_raw, market_type)

        if not isinstance(data_list, list):
            return out

        for item in data_list:
            if not isinstance(item, dict):
                continue

            try:
                # Kraken format: {time, open, high, low, close, volume}
                time_ms = item.get("time", 0)
                open_price = item.get("open")
                high_price = item.get("high")
                low_price = item.get("low")
                close_price = item.get("close")
                volume = item.get("volume")

                if not all([time_ms, open_price, high_price, low_price, close_price, volume]):
                    continue

                # Check if candle is closed (Kraken may indicate this)
                is_closed = item.get("closed", True)  # Default to True for historical data

                out.append(
                    StreamingBar(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(int(time_ms) / 1000, tz=UTC),
                        open=Decimal(str(open_price)),
                        high=Decimal(str(high_price)),
                        low=Decimal(str(low_price)),
                        close=Decimal(str(close_price)),
                        volume=Decimal(str(volume)),
                        is_closed=bool(is_closed),
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
        channel = payload.get("channel", "")
        return channel.startswith("trade") or "trade" in str(payload.get("event", ""))

    def parse(self, payload: Any) -> list[Trade]:
        out: list[Trade] = []
        if not isinstance(payload, dict):
            return out

        # Kraken format: {channel: "trade", symbol: "PI_XBTUSD", data: [{time, price, size, side}, ...]}
        symbol_raw = payload.get("symbol", "")
        data_list = payload.get("data", [])

        if not symbol_raw:
            return out

        # Determine market type from symbol format
        market_type = MarketType.FUTURES if symbol_raw.startswith("PI_") else MarketType.SPOT
        symbol = normalize_symbol_from_kraken(symbol_raw, market_type)

        if not isinstance(data_list, list):
            return out

        for item in data_list:
            if not isinstance(item, dict):
                continue

            try:
                time_ms = item.get("time", 0)
                price_str = item.get("price")
                qty_str = item.get("size") or item.get("volume")
                side = item.get("side", "")  # "buy" or "sell"
                trade_id = item.get("trade_id", "")

                if not all([time_ms, price_str, qty_str]):
                    continue

                price = Decimal(str(price_str))
                quantity = Decimal(str(qty_str))
                quote_quantity = price * quantity

                # Kraken side: "buy" means buyer is maker
                is_buyer_maker = side.lower() == "buy"

                out.append(
                    Trade(
                        symbol=symbol,
                        trade_id=int(trade_id)
                        if trade_id and str(trade_id).isdigit()
                        else int(hash(str(trade_id))),
                        price=price,
                        quantity=quantity,
                        quote_quantity=quote_quantity,
                        timestamp=datetime.fromtimestamp(int(time_ms) / 1000, tz=UTC)
                        if time_ms
                        else datetime.now(UTC),
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
        channel = payload.get("channel", "")
        return channel.startswith("book") or "book" in str(payload.get("event", ""))

    def parse(self, payload: Any) -> list[OrderBook]:
        out: list[OrderBook] = []
        if not isinstance(payload, dict):
            return out

        # Kraken format: {channel: "book", symbol: "PI_XBTUSD", data: {bids: [[price, qty], ...], asks: [[price, qty], ...]}}
        symbol_raw = payload.get("symbol", "")
        data = payload.get("data", {})
        ts_ms = payload.get("time", 0)

        if not symbol_raw:
            return out

        # Determine market type from symbol format
        market_type = MarketType.FUTURES if symbol_raw.startswith("PI_") else MarketType.SPOT
        symbol = normalize_symbol_from_kraken(symbol_raw, market_type)

        if not isinstance(data, dict):
            return out

        try:
            bids_data = data.get("bids", [])
            asks_data = data.get("asks", [])

            bids = []
            asks = []

            if isinstance(bids_data, list):
                bids = [
                    (Decimal(str(p)), Decimal(str(q)))
                    for item in bids_data
                    if isinstance(item, list) and len(item) >= 2
                    for p, q in [item[:2]]
                ]

            if isinstance(asks_data, list):
                asks = [
                    (Decimal(str(p)), Decimal(str(q)))
                    for item in asks_data
                    if isinstance(item, list) and len(item) >= 2
                    for p, q in [item[:2]]
                ]

            # Handle both snapshot and delta types
            last_update_id_raw = data.get("sequenceNumber") or data.get("seq") or 0
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
    """Adapter for open interest WebSocket messages (Futures only)."""

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        channel = payload.get("channel", "")
        return channel.startswith("open_interest") or "open_interest" in str(
            payload.get("event", "")
        )

    def parse(self, payload: Any) -> list[OpenInterest]:
        out: list[OpenInterest] = []
        if not isinstance(payload, dict):
            return out

        # Kraken Futures format: {channel: "open_interest", symbol: "PI_XBTUSD", data: {openInterest, openInterestValue, time}}
        symbol_raw = payload.get("symbol", "")
        data = payload.get("data", {})
        ts_ms = payload.get("time", 0)

        if not symbol_raw or not symbol_raw.startswith("PI_"):
            return out

        symbol = normalize_symbol_from_kraken(symbol_raw, MarketType.FUTURES)

        if not isinstance(data, dict):
            return out

        try:
            oi_str = data.get("openInterest")
            oi_value_str = data.get("openInterestValue")
            timestamp_ms = data.get("time", ts_ms)

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
    """Adapter for funding rate WebSocket messages (Futures only)."""

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        channel = payload.get("channel", "")
        return channel.startswith("funding_rate") or "funding_rate" in str(payload.get("event", ""))

    def parse(self, payload: Any) -> list[FundingRate]:
        out: list[FundingRate] = []
        if not isinstance(payload, dict):
            return out

        # Kraken Futures format: {channel: "funding_rate", symbol: "PI_XBTUSD", data: {fundingRate, markPrice, time}}
        symbol_raw = payload.get("symbol", "")
        data = payload.get("data", {})

        if not symbol_raw or not symbol_raw.startswith("PI_"):
            return out

        symbol = normalize_symbol_from_kraken(symbol_raw, MarketType.FUTURES)

        if not isinstance(data, dict):
            return out

        try:
            fr_str = data.get("fundingRate")
            ts_ms = data.get("time", 0)
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
    """Adapter for mark price WebSocket messages (Futures only)."""

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        channel = payload.get("channel", "")
        return channel.startswith("ticker") or "ticker" in str(payload.get("event", ""))

    def parse(self, payload: Any) -> list[MarkPrice]:
        out: list[MarkPrice] = []
        if not isinstance(payload, dict):
            return out

        # Kraken Futures format: {channel: "ticker", symbol: "PI_XBTUSD", data: {markPrice, indexPrice, fundingRate, nextFundingTime}}
        symbol_raw = payload.get("symbol", "")
        data = payload.get("data", {})
        ts_ms = payload.get("time", 0)

        if not symbol_raw or not symbol_raw.startswith("PI_"):
            return out

        symbol = normalize_symbol_from_kraken(symbol_raw, MarketType.FUTURES)

        if not isinstance(data, dict):
            return out

        try:
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
    """Adapter for liquidation WebSocket messages (Futures only)."""

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        channel = payload.get("channel", "")
        return channel.startswith("liquidation") or "liquidation" in str(payload.get("event", ""))

    def parse(self, payload: Any) -> list[Liquidation]:
        out: list[Liquidation] = []
        if not isinstance(payload, dict):
            return out

        # Kraken Futures format: {channel: "liquidation", symbol: "PI_XBTUSD", data: {side, size, price, time}}
        symbol_raw = payload.get("symbol", "")
        data = payload.get("data", {})
        ts_ms = payload.get("time", 0)

        if not symbol_raw or not symbol_raw.startswith("PI_"):
            return out

        symbol = normalize_symbol_from_kraken(symbol_raw, MarketType.FUTURES)

        # Kraken can send data as dict or list
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
                        average_price=Decimal(str(price_str)),
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
