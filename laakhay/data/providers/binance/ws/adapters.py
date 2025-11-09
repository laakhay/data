"""Message adapters for Binance WS streams."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from ....io import MessageAdapter
from ....models import FundingRate, Liquidation, MarkPrice, OpenInterest, OrderBook, Trade
from ....models.streaming_bar import StreamingBar


class OhlcvAdapter(MessageAdapter):
    def is_relevant(self, payload: Any) -> bool:
        if isinstance(payload, dict):
            if "data" in payload:
                return isinstance(payload.get("data"), dict) and "k" in payload.get("data", {})
            return "k" in payload
        return False

    def parse(self, payload: Any) -> list[StreamingBar]:
        out: list[StreamingBar] = []
        if not isinstance(payload, dict):
            return out
        data = payload.get("data", payload)
        k = data.get("k") if isinstance(data, dict) else None
        if not isinstance(k, dict):
            return out
        try:
            out.append(
                StreamingBar(
                    symbol=str(k.get("s") or data.get("s")),
                    timestamp=datetime.fromtimestamp(int(k["t"]) / 1000, tz=UTC),
                    open=Decimal(str(k["o"])),
                    high=Decimal(str(k["h"])),
                    low=Decimal(str(k["l"])),
                    close=Decimal(str(k["c"])),
                    volume=Decimal(str(k["v"])),
                    is_closed=bool(k.get("x", False)),
                )
            )
        except Exception:
            return []
        return out


class TradesAdapter(MessageAdapter):
    def is_relevant(self, payload: Any) -> bool:
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            return isinstance(data, dict) and data.get("e") == "trade"
        return False

    def parse(self, payload: Any) -> list[Trade]:
        out: list[Trade] = []
        if not isinstance(payload, dict):
            return out
        d = payload.get("data", payload)
        try:
            out.append(
                Trade(
                    symbol=str(d["s"]),
                    trade_id=int(d["t"]),
                    price=Decimal(str(d["p"])),
                    quantity=Decimal(str(d["q"])),
                    quote_quantity=Decimal(str(d.get("q", "0"))) * Decimal(str(d["p"])),
                    timestamp=datetime.fromtimestamp(int(d["T"]) / 1000, tz=UTC),
                    is_buyer_maker=bool(d["m"]),
                    is_best_match=d.get("M"),
                )
            )
        except Exception:
            return []
        return out


class OpenInterestAdapter(MessageAdapter):
    def is_relevant(self, payload: Any) -> bool:
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            if not isinstance(data, dict):
                return False
            evt = data.get("e")
            return (evt is None) or evt == "openInterest"
        return False

    def parse(self, payload: Any) -> list[OpenInterest]:
        out: list[OpenInterest] = []
        if not isinstance(payload, dict):
            return out
        d = payload.get("data", payload)
        try:
            symbol = str(d.get("s") or d.get("symbol"))
            event_time_ms = int(d.get("E") or d.get("t") or d.get("eventTime"))
            oi_str = d.get("oi") or d.get("o") or d.get("openInterest")
            if symbol and oi_str is not None and event_time_ms is not None:
                out.append(
                    OpenInterest(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(event_time_ms / 1000, tz=UTC),
                        open_interest=Decimal(str(oi_str)),
                        open_interest_value=None,
                    )
                )
        except Exception:
            return []
        return out


class FundingRateAdapter(MessageAdapter):
    def is_relevant(self, payload: Any) -> bool:
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            return isinstance(data, dict) and ("r" in data and "T" in data)
        return False

    def parse(self, payload: Any) -> list[FundingRate]:
        out: list[FundingRate] = []
        if not isinstance(payload, dict):
            return out
        d = payload.get("data", payload)
        try:
            out.append(
                FundingRate(
                    symbol=str(d["s"]),
                    funding_time=datetime.fromtimestamp(int(d["T"]) / 1000, tz=UTC),
                    funding_rate=Decimal(str(d["r"])),
                    mark_price=Decimal(str(d["p"])) if "p" in d else None,
                )
            )
        except Exception:
            return []
        return out


class MarkPriceAdapter(MessageAdapter):
    def is_relevant(self, payload: Any) -> bool:
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            return isinstance(data, dict) and data.get("e") == "markPriceUpdate"
        return False

    def parse(self, payload: Any) -> list[MarkPrice]:
        out: list[MarkPrice] = []
        if not isinstance(payload, dict):
            return out
        d = payload.get("data", payload)
        try:
            out.append(
                MarkPrice(
                    symbol=str(d["s"]),
                    mark_price=Decimal(str(d["p"])),
                    index_price=Decimal(str(d["i"])) if "i" in d else None,
                    estimated_settle_price=Decimal(str(d["P"])) if "P" in d else None,
                    last_funding_rate=Decimal(str(d["r"])) if "r" in d else None,
                    next_funding_time=(
                        datetime.fromtimestamp(int(d["T"]) / 1000, tz=UTC) if "T" in d else None
                    ),
                    timestamp=datetime.fromtimestamp(int(d["E"]) / 1000, tz=UTC),
                )
            )
        except Exception:
            return []
        return out


class OrderBookAdapter(MessageAdapter):
    def is_relevant(self, payload: Any) -> bool:
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            return isinstance(data, dict) and data.get("e") == "depthUpdate"
        return False

    def parse(self, payload: Any) -> list[OrderBook]:
        out: list[OrderBook] = []
        if not isinstance(payload, dict):
            return out
        d = payload.get("data", payload)
        try:
            bids = [(Decimal(str(price)), Decimal(str(qty))) for price, qty in d.get("b", [])]
            asks = [(Decimal(str(price)), Decimal(str(qty))) for price, qty in d.get("a", [])]
            out.append(
                OrderBook(
                    symbol=str(d["s"]),
                    last_update_id=int(d["u"]),
                    bids=bids if bids else [(Decimal("0"), Decimal("0"))],
                    asks=asks if asks else [(Decimal("0"), Decimal("0"))],
                    timestamp=datetime.fromtimestamp(int(d["E"]) / 1000, tz=UTC),
                )
            )
        except Exception:
            return []
        return out


class LiquidationsAdapter(MessageAdapter):
    def is_relevant(self, payload: Any) -> bool:
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            return isinstance(data, dict) and data.get("e") == "forceOrder" and "o" in data
        return False

    def parse(self, payload: Any) -> list[Liquidation]:
        out: list[Liquidation] = []
        if not isinstance(payload, dict):
            return out
        d = payload.get("data", payload)
        try:
            o = d["o"]
            event_time_ms = int(d.get("E") or o.get("T"))
            out.append(
                Liquidation(
                    symbol=str(o["s"]),
                    timestamp=datetime.fromtimestamp(event_time_ms / 1000, tz=UTC),
                    side=o["S"],
                    order_type=o["o"],
                    time_in_force=o["f"],
                    original_quantity=Decimal(str(o["q"])),
                    price=Decimal(str(o["p"])),
                    average_price=Decimal(str(o.get("ap", "0"))),
                    order_status=o["X"],
                    last_filled_quantity=Decimal(str(o.get("l", "0"))),
                    accumulated_quantity=Decimal(str(o.get("z", "0"))),
                    commission=None,
                    commission_asset=None,
                    trade_id=None,
                )
            )
        except Exception:
            return []
        return out
