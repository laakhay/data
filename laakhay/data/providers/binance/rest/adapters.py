"""Response adapters for Binance REST endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from ....io.rest_runner import ResponseAdapter
from ....models import OHLCV, Bar, OrderBook, SeriesMeta, Symbol


class CandlesResponseAdapter(ResponseAdapter):
    def parse(self, response: Any, params: dict[str, Any]) -> OHLCV:
        symbol = params["symbol"].upper()
        interval = params["interval"]
        meta = SeriesMeta(symbol=symbol, timeframe=interval.value)
        bars = [
            Bar(
                timestamp=datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc),
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
            timestamp=datetime.now(timezone.utc),
        )
