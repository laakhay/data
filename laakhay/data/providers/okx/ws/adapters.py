"""Message adapters for OKX WebSocket streams."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from ....io import MessageAdapter
from ....models import FundingRate, Liquidation, MarkPrice, OpenInterest, OrderBook, Trade
from ....models.streaming_bar import StreamingBar
from ..constants import from_okx_symbol


class OhlcvAdapter(MessageAdapter):
    """Adapter for candles/OHLCV WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        arg = payload.get("arg", {})
        if not isinstance(arg, dict):
            return False
        channel = arg.get("channel", "")
        return bool(isinstance(channel, str) and channel.startswith("candles."))

    def parse(self, payload: Any) -> list[StreamingBar]:
        out: list[StreamingBar] = []
        if not isinstance(payload, dict):
            return out

        arg = payload.get("arg", {})
        data_list = payload.get("data", [])

        if not isinstance(arg, dict) or not isinstance(data_list, list):
            return out

        # Extract symbol from arg: {channel: "candles.1m.BTC-USDT", instId: "BTC-USDT"}
        inst_id = arg.get("instId", "")
        symbol = from_okx_symbol(inst_id)  # Convert BTC-USDT to BTCUSDT

        for item in data_list:
            if not isinstance(item, list) or len(item) < 6:
                continue

            try:
                # OKX kline format: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
                ts_str = str(item[0])
                if "T" in ts_str:
                    ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    ts_ms = int(ts_dt.timestamp() * 1000)
                else:
                    ts_ms = int(ts_str)

                open_price = item[1]
                high_price = item[2]
                low_price = item[3]
                close_price = item[4]
                volume = item[5]
                confirm = item[8] if len(item) > 8 else True  # Whether candle is closed

                if not all([ts_ms, open_price, high_price, low_price, close_price, volume]):
                    continue

                out.append(
                    StreamingBar(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                        open=Decimal(str(open_price)),
                        high=Decimal(str(high_price)),
                        low=Decimal(str(low_price)),
                        close=Decimal(str(close_price)),
                        volume=Decimal(str(volume)),
                        is_closed=bool(confirm),
                    )
                )
            except (ValueError, TypeError, KeyError, IndexError):
                continue

        return out


class TradesAdapter(MessageAdapter):
    """Adapter for trade WebSocket messages."""

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        arg = payload.get("arg", {})
        if not isinstance(arg, dict):
            return False
        channel = arg.get("channel", "")
        return bool(channel == "trades")

    def parse(self, payload: Any) -> list[Trade]:
        out: list[Trade] = []
        if not isinstance(payload, dict):
            return out

        arg = payload.get("arg", {})
        data_list = payload.get("data", [])

        if not isinstance(arg, dict) or not isinstance(data_list, list):
            return out

        # Extract symbol from arg
        inst_id = arg.get("instId", "")
        symbol = inst_id.replace("-", "").upper()

        for item in data_list:
            if not isinstance(item, dict):
                continue

            try:
                # OKX trade format: {instId, tradeId, px, sz, side, ts, count}
                trade_id = item.get("tradeId", "")
                price_str = item.get("px")
                qty_str = item.get("sz")
                side = item.get("side", "")  # "buy" or "sell"
                time_ms = item.get("ts", 0)

                if not all([time_ms, price_str, qty_str]):
                    continue

                price = Decimal(str(price_str))
                quantity = Decimal(str(qty_str))
                quote_quantity = price * quantity

                # OKX side: "buy" means buyer is taker, "sell" means seller is taker
                is_buyer_maker = side == "sell"

                out.append(
                    Trade(
                        symbol=symbol,
                        trade_id=int(trade_id) if trade_id else 0,
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
        arg = payload.get("arg", {})
        if not isinstance(arg, dict):
            return False
        channel = arg.get("channel", "")
        return bool(isinstance(channel, str) and channel.startswith("books."))

    def parse(self, payload: Any) -> list[OrderBook]:
        out: list[OrderBook] = []
        if not isinstance(payload, dict):
            return out

        arg = payload.get("arg", {})
        data_list = payload.get("data", [])

        if not isinstance(arg, dict) or not isinstance(data_list, list) or len(data_list) == 0:
            return out

        # Extract symbol from arg
        inst_id = arg.get("instId", "")
        symbol = inst_id.replace("-", "").upper()

        # OKX sends list with single orderbook object
        ob_data = data_list[0]
        if not isinstance(ob_data, dict):
            return out

        try:
            # OKX orderbook format: {bids: [[price, size, ...]], asks: [[price, size, ...]], ts, checksum}
            bids_data = ob_data.get("bids", [])
            asks_data = ob_data.get("asks", [])

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

            timestamp_ms = ob_data.get("ts", 0)

            timestamp = (
                datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=UTC)
                if timestamp_ms
                else datetime.now(UTC)
            )

            out.append(
                OrderBook(
                    symbol=symbol,
                    last_update_id=0,  # OKX doesn't provide update ID
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
        arg = payload.get("arg", {})
        if not isinstance(arg, dict):
            return False
        channel = arg.get("channel", "")
        return bool(channel == "open-interest")

    def parse(self, payload: Any) -> list[OpenInterest]:
        out: list[OpenInterest] = []
        if not isinstance(payload, dict):
            return out

        arg = payload.get("arg", {})
        data_list = payload.get("data", [])

        if not isinstance(arg, dict) or not isinstance(data_list, list) or len(data_list) == 0:
            return out

        # Extract symbol from arg
        inst_id = arg.get("instId", "")
        symbol = inst_id.replace("-", "").upper()

        oi_data = data_list[0]
        if not isinstance(oi_data, dict):
            return out

        try:
            # OKX open interest format: {instId, oi, oiCcy, ts}
            oi_str = oi_data.get("oi")
            oi_value_str = oi_data.get("oiCcy")
            timestamp_ms = oi_data.get("ts", 0)

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
        arg = payload.get("arg", {})
        if not isinstance(arg, dict):
            return False
        channel = arg.get("channel", "")
        return bool(channel == "funding-rate")

    def parse(self, payload: Any) -> list[FundingRate]:
        out: list[FundingRate] = []
        if not isinstance(payload, dict):
            return out

        arg = payload.get("arg", {})
        data_list = payload.get("data", [])

        if not isinstance(arg, dict) or not isinstance(data_list, list) or len(data_list) == 0:
            return out

        # Extract symbol from arg
        inst_id = arg.get("instId", "")
        symbol = inst_id.replace("-", "").upper()

        fr_data = data_list[0]
        if not isinstance(fr_data, dict):
            return out

        try:
            # OKX funding rate format: {instId, fundingRate, fundingTime, nextFundingTime, markPx}
            fr_str = fr_data.get("fundingRate")
            ts_str = fr_data.get("fundingTime", "")
            mark_price_str = fr_data.get("markPx")

            if fr_str is None or not ts_str:
                return []

            # Convert timestamp
            if "T" in ts_str:
                ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                ts_ms = int(ts_dt.timestamp() * 1000)
            else:
                ts_ms = int(ts_str)

            out.append(
                FundingRate(
                    symbol=symbol,
                    funding_time=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
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
        arg = payload.get("arg", {})
        if not isinstance(arg, dict):
            return False
        channel = arg.get("channel", "")
        return bool(channel == "mark-price")

    def parse(self, payload: Any) -> list[MarkPrice]:
        out: list[MarkPrice] = []
        if not isinstance(payload, dict):
            return out

        arg = payload.get("arg", {})
        data_list = payload.get("data", [])

        if not isinstance(arg, dict) or not isinstance(data_list, list) or len(data_list) == 0:
            return out

        # Extract symbol from arg
        inst_id = arg.get("instId", "")
        symbol = inst_id.replace("-", "").upper()

        mp_data = data_list[0]
        if not isinstance(mp_data, dict):
            return out

        try:
            # OKX mark price format: {instId, markPx, idxPx, ts, ...}
            mark_price_str = mp_data.get("markPx")
            index_price_str = mp_data.get("idxPx")
            timestamp_ms = mp_data.get("ts", 0)

            if mark_price_str is None:
                return []

            timestamp = (
                datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=UTC)
                if timestamp_ms
                else datetime.now(UTC)
            )

            out.append(
                MarkPrice(
                    symbol=symbol,
                    mark_price=Decimal(str(mark_price_str)),
                    index_price=Decimal(str(index_price_str)) if index_price_str else None,
                    estimated_settle_price=None,
                    last_funding_rate=None,
                    next_funding_time=None,
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
        arg = payload.get("arg", {})
        if not isinstance(arg, dict):
            return False
        channel = arg.get("channel", "")
        return bool(channel == "liquidation")

    def parse(self, payload: Any) -> list[Liquidation]:
        out: list[Liquidation] = []
        if not isinstance(payload, dict):
            return out

        arg = payload.get("arg", {})
        data_list = payload.get("data", [])

        # Extract symbol from arg
        inst_id = arg.get("instId", "")
        symbol = inst_id.replace("-", "").upper()

        if not isinstance(data_list, list):
            return out

        for item in data_list:
            if not isinstance(item, dict):
                continue

            try:
                # OKX liquidation format: {instId, side, sz, px, ts}
                side = item.get("side", "")
                size_str = item.get("sz")
                price_str = item.get("px")
                time_ms = item.get("ts", 0)

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
