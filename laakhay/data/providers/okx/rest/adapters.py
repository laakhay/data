"""Response adapters for OKX REST endpoints."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from ....core.exceptions import DataError
from ....io import ResponseAdapter
from ....models import OHLCV, Bar, FundingRate, OpenInterest, OrderBook, SeriesMeta, Symbol, Trade


def _extract_result(response: Any) -> Any:
    """Extract result from OKX's response wrapper.

    OKX API v5 returns: {code: "0", msg: "", data: [...]}
    """
    if not isinstance(response, dict):
        raise DataError(f"Invalid response format: expected dict, got {type(response)}")

    code = response.get("code", "-1")
    msg = response.get("msg", "Unknown error")

    if code != "0":
        raise DataError(f"OKX API error: {msg} (code: {code})")

    data = response.get("data")
    if data is None:
        raise DataError("OKX API response missing 'data' field")

    return data


class CandlesResponseAdapter(ResponseAdapter):
    """Adapter for candles/OHLCV responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> OHLCV:
        data = _extract_result(response)
        symbol = params["symbol"].upper()
        interval = params["interval"]

        # OKX returns list of candle arrays: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
        if not isinstance(data, list):
            raise DataError(f"Invalid candles response format: expected list, got {type(data)}")

        meta = SeriesMeta(symbol=symbol, timeframe=interval.value)
        bars = []
        for row in data:
            if not isinstance(row, list) or len(row) < 6:
                continue
            try:
                # OKX format: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
                # Timestamp is in milliseconds (ISO format string)
                ts_str = str(row[0])
                # OKX returns ISO timestamp string, convert to ms
                if "T" in ts_str:
                    # ISO format: "2024-01-01T00:00:00.000Z"
                    ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    ts_ms = int(ts_dt.timestamp() * 1000)
                else:
                    ts_ms = int(ts_str)

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

        # OKX returns newest first, reverse to get chronological order
        bars.reverse()

        return OHLCV(meta=meta, bars=bars)


class ExchangeInfoSymbolsAdapter(ResponseAdapter):
    """Adapter for instruments/symbols responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Symbol]:
        data = _extract_result(response)
        market_type = params["market_type"]
        quote_asset_filter = params.get("quote_asset")

        if not isinstance(data, list):
            data = []

        out: list[Symbol] = []
        for inst in data:
            if not isinstance(inst, dict):
                continue

            # Filter by state - OKX uses "live" state for active trading
            state = inst.get("state", "")
            if state != "live":
                continue

            # Filter by quote asset if specified
            quote_asset = inst.get("quoteCcy", "")
            if quote_asset_filter and quote_asset != quote_asset_filter:
                continue

            # For futures, filter to SWAP only (perpetuals)
            if market_type.name == "FUTURES":
                inst_type = inst.get("instType", "")
                if inst_type != "SWAP":
                    continue

            # Extract tick size and step size from lotSz and tickSz
            tick_size = None
            step_size = None
            min_notional = None

            tick_size_str = inst.get("tickSz")
            if tick_size_str:
                with contextlib.suppress(ValueError, TypeError):
                    tick_size = Decimal(str(tick_size_str))

            lot_size_str = inst.get("lotSz")
            if lot_size_str:
                with contextlib.suppress(ValueError, TypeError):
                    step_size = Decimal(str(lot_size_str))

            min_notional_str = inst.get("minSz")
            if min_notional_str:
                with contextlib.suppress(ValueError, TypeError):
                    min_notional = Decimal(str(min_notional_str))

            symbol_str = inst.get("instId", "")
            base_asset = inst.get("baseCcy", "")
            quote_asset = inst.get("quoteCcy", "")

            if not symbol_str or not base_asset or not quote_asset:
                continue

            contract_type = inst.get("instType")
            delivery_date = inst.get("expTime")  # OKX uses expTime for delivery

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
        data = _extract_result(response)
        symbol = params["symbol"].upper()

        # OKX returns list with single orderbook object
        if not isinstance(data, list) or len(data) == 0:
            raise DataError("OKX orderbook response missing data")

        ob_data = data[0]
        if not isinstance(ob_data, dict):
            raise DataError("Invalid orderbook data format")

        bids = []
        asks = []

        # Extract bids and asks
        bids_data = ob_data.get("bids", [])
        asks_data = ob_data.get("asks", [])

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

        # OKX uses "ts" for timestamp
        timestamp_ms = ob_data.get("ts", 0)

        timestamp = (
            datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=UTC)
            if timestamp_ms
            else datetime.now(UTC)
        )

        return OrderBook(
            symbol=symbol,
            last_update_id=0,  # OKX doesn't provide update ID
            bids=bids,
            asks=asks,
            timestamp=timestamp,
        )


class OpenInterestCurrentAdapter(ResponseAdapter):
    """Adapter for current open interest responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        data = _extract_result(response)
        symbol = params["symbol"].upper()

        # OKX returns list with single OI object
        if not isinstance(data, list) or len(data) == 0:
            return []

        oi_data = data[0]
        if not isinstance(oi_data, dict):
            return []

        oi_str = oi_data.get("oi")
        oi_value_str = oi_data.get("oiCcy")
        timestamp_ms = oi_data.get("ts", 0)

        if oi_str is None:
            return []

        try:
            return [
                OpenInterest(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=UTC)
                    if timestamp_ms
                    else datetime.now(UTC),
                    open_interest=Decimal(str(oi_str)),
                    open_interest_value=Decimal(str(oi_value_str)) if oi_value_str else None,
                )
            ]
        except (ValueError, TypeError):
            return []


class OpenInterestHistAdapter(ResponseAdapter):
    """Adapter for historical open interest responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        data = _extract_result(response)
        symbol = params["symbol"].upper()

        if not isinstance(data, list):
            return []

        out: list[OpenInterest] = []
        for row in data:
            if not isinstance(row, list) or len(row) < 2:
                continue

            try:
                # OKX format: [ts, oi, oiCcy]
                ts_str = str(row[0])
                if "T" in ts_str:
                    ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    ts_ms = int(ts_dt.timestamp() * 1000)
                else:
                    ts_ms = int(ts_str)

                oi_str = row[1] if len(row) > 1 else None
                oi_value_str = row[2] if len(row) > 2 else None

                if oi_str is None:
                    continue

                out.append(
                    OpenInterest(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                        open_interest=Decimal(str(oi_str)),
                        open_interest_value=Decimal(str(oi_value_str)) if oi_value_str else None,
                    )
                )
            except (ValueError, TypeError, IndexError):
                continue

        return out


class RecentTradesAdapter(ResponseAdapter):
    """Adapter for recent trades responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Trade]:
        data = _extract_result(response)
        symbol = params["symbol"].upper()

        if not isinstance(data, list):
            return []

        out: list[Trade] = []
        for row in data:
            if not isinstance(row, dict):
                continue

            try:
                # OKX format: {instId, tradeId, px, sz, side, ts, count}
                trade_id = row.get("tradeId", "")
                price_str = row.get("px")
                qty_str = row.get("sz")
                side = row.get("side", "")  # "buy" or "sell"
                time_ms = row.get("ts", 0)

                if not price_str or not qty_str:
                    continue

                price = Decimal(str(price_str))
                quantity = Decimal(str(qty_str))
                quote_quantity = price * quantity

                # OKX side: "buy" means buyer is taker, "sell" means seller is taker
                # So "buy" means buyer is NOT maker (is_buyer_maker = False)
                is_buyer_maker = side == "sell"

                out.append(
                    Trade(
                        symbol=symbol,
                        trade_id=int(trade_id) if trade_id else 0,
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


class FundingRateAdapter(ResponseAdapter):
    """Adapter for funding rate history responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[FundingRate]:
        data = _extract_result(response)
        symbol = params["symbol"].upper()

        if not isinstance(data, list):
            return []

        out: list[FundingRate] = []
        for row in data:
            if not isinstance(row, dict):
                continue

            try:
                # OKX format: {instId, fundingRate, fundingTime, nextFundingTime, markPx}
                fr_str = row.get("fundingRate")
                ts_str = row.get("fundingTime", "")
                mark_price_str = row.get("markPx")

                if fr_str is None or not ts_str:
                    continue

                # Convert timestamp
                if "T" in ts_str:
                    ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    ts_ms = int(ts_dt.timestamp() * 1000)
                else:
                    ts_ms = int(ts_str)

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
