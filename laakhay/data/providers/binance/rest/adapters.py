"""Response adapters for Binance REST endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from ....io import ResponseAdapter
from ....models import OHLCV, Bar, FundingRate, OpenInterest, OrderBook, SeriesMeta, Symbol, Trade


class CandlesResponseAdapter(ResponseAdapter):
    def parse(self, response: Any, params: dict[str, Any]) -> OHLCV:
        symbol = params["symbol"].upper()
        interval = params["interval"]
        meta = SeriesMeta(symbol=symbol, timeframe=interval.value)
        bars = [
            Bar(
                timestamp=datetime.fromtimestamp(row[0] / 1000, tz=UTC),
                open=Decimal(str(row[1])),
                high=Decimal(str(row[2])),
                low=Decimal(str(row[3])),
                close=Decimal(str(row[4])),
                volume=Decimal(str(row[5])),
                is_closed=True,
            )
            for row in response
        ]
        return OHLCV(meta=meta, bars=bars)


class ExchangeInfoSymbolsAdapter(ResponseAdapter):
    def parse(self, response: Any, params: dict[str, Any]) -> list[Symbol]:
        market_type = params["market_type"]
        quote_asset_filter = params.get("quote_asset")
        out: list[Symbol] = []
        for sd in response.get("symbols", []) or []:
            if sd.get("status") != "TRADING":
                continue
            if quote_asset_filter and sd.get("quoteAsset") != quote_asset_filter:
                continue
            if market_type.name == "FUTURES" and sd.get("contractType") != "PERPETUAL":
                continue
            tick_size = None
            step_size = None
            min_notional = None
            for f in sd.get("filters", []) or []:
                t = f.get("filterType")
                if t == "PRICE_FILTER":
                    v = f.get("tickSize")
                    tick_size = Decimal(str(v)) if v is not None else None
                elif t == "LOT_SIZE":
                    v = f.get("stepSize")
                    step_size = Decimal(str(v)) if v is not None else None
                elif t == "MIN_NOTIONAL":
                    v = f.get("minNotional")
                    min_notional = Decimal(str(v)) if v is not None else None
            out.append(
                Symbol(
                    symbol=sd["symbol"],
                    base_asset=sd["baseAsset"],
                    quote_asset=sd["quoteAsset"],
                    tick_size=tick_size,
                    step_size=step_size,
                    min_notional=min_notional,
                    contract_type=sd.get("contractType"),
                    delivery_date=sd.get("deliveryDate"),
                )
            )
        return out


class OrderBookResponseAdapter(ResponseAdapter):
    def parse(self, response: Any, params: dict[str, Any]) -> OrderBook:
        symbol = params["symbol"].upper()
        bids = [(Decimal(str(p)), Decimal(str(q))) for p, q in response.get("bids", [])]
        asks = [(Decimal(str(p)), Decimal(str(q))) for p, q in response.get("asks", [])]
        return OrderBook(
            symbol=symbol,
            last_update_id=response.get("lastUpdateId", 0),
            bids=bids,
            asks=asks,
            timestamp=datetime.now(UTC),
        )


class OpenInterestCurrentAdapter(ResponseAdapter):
    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        symbol = params["symbol"].upper()
        oi_str = response.get("openInterest")
        ts_ms = response.get("time")
        if oi_str is None or ts_ms is None:
            return []
        return [
            OpenInterest(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                open_interest=Decimal(str(oi_str)),
                open_interest_value=None,
            )
        ]


class OpenInterestHistAdapter(ResponseAdapter):
    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        symbol = params["symbol"].upper()
        out: list[OpenInterest] = []
        for row in response or []:
            ts_ms = row.get("timestamp")
            oi_str = row.get("sumOpenInterest")
            if ts_ms is None or oi_str is None:
                continue
            out.append(
                OpenInterest(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                    open_interest=Decimal(str(oi_str)),
                    open_interest_value=None,
                )
            )
        return out


class RecentTradesAdapter(ResponseAdapter):
    def parse(self, response: Any, params: dict[str, Any]) -> list[Trade]:
        symbol = params["symbol"].upper()
        out: list[Trade] = []
        for row in response or []:
            out.append(
                Trade(
                    symbol=symbol,
                    trade_id=int(row.get("id")),
                    price=Decimal(str(row.get("price"))),
                    quantity=Decimal(str(row.get("qty"))),
                    quote_quantity=(
                        Decimal(str(row.get("quoteQty")))
                        if row.get("quoteQty") is not None
                        else None
                    ),
                    timestamp=datetime.fromtimestamp(int(row.get("time", 0)) / 1000, tz=UTC),
                    is_buyer_maker=bool(row.get("isBuyerMaker")),
                    is_best_match=row.get("isBestMatch"),
                )
            )
        return out


class FundingRateAdapter(ResponseAdapter):
    def parse(self, response: Any, params: dict[str, Any]) -> list[FundingRate]:
        symbol = params["symbol"].upper()
        out: list[FundingRate] = []
        for row in response or []:
            fr = Decimal(str(row.get("fundingRate")))
            ts_ms = int(row.get("fundingTime", 0))
            out.append(
                FundingRate(
                    symbol=symbol,
                    funding_time=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                    funding_rate=fr,
                    mark_price=(
                        Decimal(str(row.get("markPrice")))
                        if row.get("markPrice") is not None
                        else None
                    ),
                )
            )
        return out
