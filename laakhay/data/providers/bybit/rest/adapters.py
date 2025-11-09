"""Response adapters for Bybit REST endpoints."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from ....core.exceptions import DataError
from ....io import ResponseAdapter
from ....models import OHLCV, Bar, FundingRate, OpenInterest, OrderBook, SeriesMeta, Symbol, Trade


def _extract_result(response: Any) -> Any:
    """Extract result from Bybit's response wrapper.

    Bybit API v5 returns: {retCode: 0, retMsg: "OK", result: {...}}
    """
    if not isinstance(response, dict):
        raise DataError(f"Invalid response format: expected dict, got {type(response)}")

    ret_code = response.get("retCode", -1)
    ret_msg = response.get("retMsg", "Unknown error")

    if ret_code != 0:
        raise DataError(f"Bybit API error: {ret_msg} (code: {ret_code})")

    result = response.get("result")
    if result is None:
        raise DataError("Bybit API response missing 'result' field")

    return result


class CandlesResponseAdapter(ResponseAdapter):
    """Adapter for kline/OHLCV responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> OHLCV:
        result = _extract_result(response)
        symbol = params["symbol"].upper()
        interval = params["interval"]

        # Bybit returns list of kline arrays: [timestamp, open, high, low, close, volume, turnover]
        # Or wrapped in "list" field
        klines = result.get("list", result) if isinstance(result, dict) else result

        if not isinstance(klines, list):
            raise DataError(f"Invalid kline response format: expected list, got {type(klines)}")

        meta = SeriesMeta(symbol=symbol, timeframe=interval.value)
        bars = []
        for row in klines:
            if not isinstance(row, list) or len(row) < 6:
                continue
            try:
                # Bybit format: [timestamp, open, high, low, close, volume, turnover]
                # Timestamp is in milliseconds
                ts_ms = int(row[0])
                bars.append(
                    Bar(
                        timestamp=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                        open=Decimal(str(row[1])),
                        high=Decimal(str(row[2])),
                        low=Decimal(str(row[3])),
                        close=Decimal(str(row[4])),
                        volume=Decimal(str(row[5])),
                        is_closed=True,  # Historical data is always closed
                    )
                )
            except (ValueError, IndexError, TypeError):
                # Skip invalid rows
                continue

        # Bybit returns newest first, reverse to get chronological order
        bars.reverse()

        return OHLCV(meta=meta, bars=bars)


class ExchangeInfoSymbolsAdapter(ResponseAdapter):
    """Adapter for instruments-info/symbols responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Symbol]:
        result = _extract_result(response)
        market_type = params["market_type"]
        quote_asset_filter = params.get("quote_asset")

        # Bybit returns list in "list" field
        instruments = result.get("list", []) if isinstance(result, dict) else result
        if not isinstance(instruments, list):
            instruments = []

        out: list[Symbol] = []
        for inst in instruments:
            if not isinstance(inst, dict):
                continue

            # Filter by status - Bybit uses "Trading" status
            status = inst.get("status", "")
            if status != "Trading":
                continue

            # Filter by quote asset if specified
            quote_asset = inst.get("quoteCoin", "")
            if quote_asset_filter and quote_asset != quote_asset_filter:
                continue

            # For futures, filter to perpetuals only
            if market_type.name == "FUTURES":
                contract_type = inst.get("contractType", "")
                if contract_type != "Perpetual":
                    continue

            # Extract tick size and step size from lotSizeFilter and priceFilter
            tick_size = None
            step_size = None
            min_notional = None

            # Price filter
            price_filter = inst.get("priceFilter", {})
            if isinstance(price_filter, dict):
                tick_size_str = price_filter.get("tickSize")
                if tick_size_str:
                    with contextlib.suppress(ValueError, TypeError):
                        tick_size = Decimal(str(tick_size_str))

            # Lot size filter
            lot_size_filter = inst.get("lotSizeFilter", {})
            if isinstance(lot_size_filter, dict):
                step_size_str = lot_size_filter.get("qtyStep")
                if step_size_str:
                    with contextlib.suppress(ValueError, TypeError):
                        step_size = Decimal(str(step_size_str))

            # Min notional filter
            min_notional_filter = inst.get("minNotionalFilter", {})
            if isinstance(min_notional_filter, dict):
                min_notional_str = min_notional_filter.get("notional")
                if min_notional_str:
                    with contextlib.suppress(ValueError, TypeError):
                        min_notional = Decimal(str(min_notional_str))

            symbol_str = inst.get("symbol", "")
            base_asset = inst.get("baseCoin", "")
            quote_asset = inst.get("quoteCoin", "")

            if not symbol_str or not base_asset or not quote_asset:
                continue

            contract_type = inst.get("contractType")
            delivery_date = inst.get("deliveryDate")

            out.append(
                Symbol(
                    symbol=symbol_str,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    tick_size=tick_size,
                    step_size=step_size,
                    min_notional=min_notional,
                    contract_type=contract_type,
                    delivery_date=delivery_date,
                )
            )

        return out


class OrderBookResponseAdapter(ResponseAdapter):
    """Adapter for orderbook responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> OrderBook:
        result = _extract_result(response)
        symbol = params["symbol"].upper()

        # Bybit returns orderbook in result
        bids = []
        asks = []

        # Extract bids and asks
        bids_data = result.get("b", [])
        asks_data = result.get("a", [])

        if isinstance(bids_data, list):
            bids = [(Decimal(str(p)), Decimal(str(q))) for p, q in bids_data if len([p, q]) >= 2]

        if isinstance(asks_data, list):
            asks = [(Decimal(str(p)), Decimal(str(q))) for p, q in asks_data if len([p, q]) >= 2]

        # Bybit uses "ts" for timestamp, "u" for update ID
        timestamp_ms = result.get("ts", 0)
        last_update_id = result.get("u", 0)

        timestamp = (
            datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
            if timestamp_ms
            else datetime.now(UTC)
        )

        return OrderBook(
            symbol=symbol,
            last_update_id=last_update_id,
            bids=bids,
            asks=asks,
            timestamp=timestamp,
        )


class OpenInterestCurrentAdapter(ResponseAdapter):
    """Adapter for current open interest responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        result = _extract_result(response)
        symbol = params["symbol"].upper()

        # Bybit returns single OI value
        oi_str = result.get("openInterest")
        timestamp_ms = result.get("time", result.get("ts", 0))

        if oi_str is None:
            return []

        try:
            return [
                OpenInterest(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
                    if timestamp_ms
                    else datetime.now(UTC),
                    open_interest=Decimal(str(oi_str)),
                    open_interest_value=None,
                )
            ]
        except (ValueError, TypeError):
            return []


class OpenInterestHistAdapter(ResponseAdapter):
    """Adapter for historical open interest responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        result = _extract_result(response)
        symbol = params["symbol"].upper()

        # Bybit returns list in "list" field
        oi_list = result.get("list", []) if isinstance(result, dict) else result
        if not isinstance(oi_list, list):
            return []

        out: list[OpenInterest] = []
        for row in oi_list:
            if not isinstance(row, dict):
                continue

            try:
                # Bybit format: {timestamp, openInterest}
                ts_ms = row.get("timestamp", row.get("time", 0))
                oi_str = row.get("openInterest", row.get("openInterestValue"))

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
            except (ValueError, TypeError, KeyError):
                continue

        return out


class RecentTradesAdapter(ResponseAdapter):
    """Adapter for recent trades responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Trade]:
        result = _extract_result(response)
        symbol = params["symbol"].upper()

        # Bybit returns list in "list" field
        trades_list = result.get("list", []) if isinstance(result, dict) else result
        if not isinstance(trades_list, list):
            return []

        out: list[Trade] = []
        for row in trades_list:
            if not isinstance(row, dict):
                continue

            try:
                # Bybit format: {execId, symbol, price, size, side, time, isBlockTrade}
                trade_id = row.get("execId", row.get("execId", ""))
                price_str = row.get("price")
                qty_str = row.get("size")
                side = row.get("side", "")  # "Buy" or "Sell"
                time_ms = row.get("time", 0)

                if not price_str or not qty_str:
                    continue

                price = Decimal(str(price_str))
                quantity = Decimal(str(qty_str))
                quote_quantity = price * quantity

                # Bybit side: "Buy" means buyer is maker, "Sell" means seller is maker
                is_buyer_maker = side == "Buy"

                out.append(
                    Trade(
                        symbol=symbol,
                        trade_id=int(hash(trade_id)) if trade_id else 0,  # Use hash if not numeric
                        price=price,
                        quantity=quantity,
                        quote_quantity=quote_quantity,
                        timestamp=datetime.fromtimestamp(time_ms / 1000, tz=UTC)
                        if time_ms
                        else datetime.now(UTC),
                        is_buyer_maker=is_buyer_maker,
                        is_best_match=None,
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue

        return out


class FundingRateAdapter(ResponseAdapter):
    """Adapter for funding rate history responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[FundingRate]:
        result = _extract_result(response)
        symbol = params["symbol"].upper()

        # Bybit returns list in "list" field
        rates_list = result.get("list", []) if isinstance(result, dict) else result
        if not isinstance(rates_list, list):
            return []

        out: list[FundingRate] = []
        for row in rates_list:
            if not isinstance(row, dict):
                continue

            try:
                # Bybit format: {symbol, fundingRate, fundingRateTimestamp, markPrice}
                fr_str = row.get("fundingRate")
                ts_ms = row.get("fundingRateTimestamp", row.get("fundingTime", 0))
                mark_price_str = row.get("markPrice")

                if fr_str is None or ts_ms is None:
                    continue

                funding_rate = Decimal(str(fr_str))
                mark_price = Decimal(str(mark_price_str)) if mark_price_str else None

                out.append(
                    FundingRate(
                        symbol=symbol,
                        funding_time=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                        funding_rate=funding_rate,
                        mark_price=mark_price,
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue

        return out
