"""Response adapters for Kraken REST endpoints."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from ....core import MarketType
from ....core.exceptions import DataError
from ....io import ResponseAdapter
from ....models import OHLCV, Bar, FundingRate, OpenInterest, OrderBook, SeriesMeta, Symbol, Trade
from ..constants import normalize_symbol_from_kraken


def _extract_result(response: Any, market_type: MarketType) -> Any:
    """Extract result from Kraken's response wrapper.

    Kraken API responses vary:
    - Spot: {error: [], result: {...}}
    - Futures: May have different wrapper or direct result
    """
    if not isinstance(response, dict):
        raise DataError(f"Invalid response format: expected dict, got {type(response)}")

    # Check for errors in Kraken Spot format
    errors = response.get("error", [])
    if errors and len(errors) > 0:
        error_msg = errors[0] if isinstance(errors, list) else str(errors)
        raise DataError(f"Kraken API error: {error_msg}")

    # Kraken Spot wraps in "result" field
    if "result" in response:
        result_value = response["result"]
        # For Futures, if result is "ok", return the full response (data is in other fields)
        if result_value == "ok" and market_type == MarketType.FUTURES:
            return response
        return result_value

    # Kraken Futures may return direct result or wrapped
    # Check for common error indicators
    if "error" in response and response["error"]:
        raise DataError(f"Kraken API error: {response.get('error', 'Unknown error')}")

    # Return response itself if no wrapper
    return response


class CandlesResponseAdapter(ResponseAdapter):
    """Adapter for OHLCV/Candles responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> OHLCV:
        market_type: MarketType = params["market_type"]
        symbol = params["symbol"].upper()
        interval = params["interval"]

        result = _extract_result(response, market_type)

        if market_type == MarketType.FUTURES:
            # Kraken Futures format: {result: "ok", candles: [{time, open, high, low, close, volume}, ...]}
            candles_data = result.get("candles", []) if isinstance(result, dict) else result

            if not isinstance(candles_data, list):
                raise DataError(
                    f"Invalid candles response format: expected list, got {type(candles_data)}"
                )

            meta = SeriesMeta(symbol=symbol, timeframe=interval.value)
            bars = []
            for row in candles_data:
                if not isinstance(row, dict):
                    continue
                try:
                    # Kraken Futures format: {time, open, high, low, close, volume}
                    time_ms = row.get("time", 0)
                    open_price = row.get("open")
                    high_price = row.get("high")
                    low_price = row.get("low")
                    close_price = row.get("close")
                    volume = row.get("volume")

                    if not all([time_ms, open_price, high_price, low_price, close_price, volume]):
                        continue

                    bars.append(
                        Bar(
                            timestamp=datetime.fromtimestamp(time_ms / 1000, tz=UTC),
                            open=Decimal(str(open_price)),
                            high=Decimal(str(high_price)),
                            low=Decimal(str(low_price)),
                            close=Decimal(str(close_price)),
                            volume=Decimal(str(volume)),
                            is_closed=True,  # Historical data is always closed
                        )
                    )
                except (ValueError, TypeError, KeyError):
                    continue

            # Sort by timestamp (oldest first)
            bars.sort(key=lambda b: b.timestamp)

        else:
            # Kraken Spot format: {result: {PAIR: [[time, open, high, low, close, vwap, volume, count], ...]}}
            # Find the pair key (may be normalized)
            pair_data = None
            if isinstance(result, dict):
                # Find first key that looks like a pair
                for key in result:
                    pair_data = result[key]
                    break

            if not isinstance(pair_data, list):
                raise DataError(
                    f"Invalid OHLC response format: expected list, got {type(pair_data)}"
                )

            meta = SeriesMeta(symbol=symbol, timeframe=interval.value)
            bars = []
            for row in pair_data:
                if not isinstance(row, list) or len(row) < 7:
                    continue
                try:
                    # Kraken Spot format: [time, open, high, low, close, vwap, volume, count]
                    # Time is in seconds (Unix timestamp)
                    ts = int(row[0])
                    bars.append(
                        Bar(
                            timestamp=datetime.fromtimestamp(ts, tz=UTC),
                            open=Decimal(str(row[1])),
                            high=Decimal(str(row[2])),
                            low=Decimal(str(row[3])),
                            close=Decimal(str(row[4])),
                            volume=Decimal(str(row[6])),  # Volume is at index 6
                            is_closed=True,
                        )
                    )
                except (ValueError, IndexError, TypeError):
                    continue

        return OHLCV(meta=meta, bars=bars)


class ExchangeInfoSymbolsAdapter(ResponseAdapter):
    """Adapter for instruments-info/symbols responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Symbol]:
        market_type: MarketType = params["market_type"]
        quote_asset_filter = params.get("quote_asset")

        result = _extract_result(response, market_type)

        out: list[Symbol] = []

        if market_type == MarketType.FUTURES:
            # Kraken Futures format: {result: "ok", instruments: [{symbol, type, underlying, ...}, ...]}
            instruments = result.get("instruments", []) if isinstance(result, dict) else result
            if not isinstance(instruments, list):
                instruments = []

            for inst in instruments:
                if not isinstance(inst, dict):
                    continue

                # Filter by status if available
                status = inst.get("status", "open")
                if status != "open":
                    continue

                symbol_str = inst.get("symbol", "")
                if not symbol_str:
                    continue

                # Normalize symbol from Kraken format
                normalized_symbol = normalize_symbol_from_kraken(symbol_str, market_type)

                # Extract base and quote assets
                # Kraken Futures: PI_XBTUSD -> base: XBT, quote: USD
                # We'll try to extract from symbol or use defaults
                base_asset = inst.get("underlying", "").replace("XBT", "BTC")
                quote_asset = inst.get("quoteCurrency", "USD")

                # Filter by quote asset if specified
                if quote_asset_filter and quote_asset.upper() != quote_asset_filter.upper():
                    continue

                # Extract tick size and step size
                tick_size = None
                step_size = None
                min_notional = None

                tick_size_str = inst.get("tickSize")
                if tick_size_str:
                    with contextlib.suppress(ValueError, TypeError):
                        tick_size = Decimal(str(tick_size_str))

                step_size_str = inst.get("contractSize") or inst.get("lotSize")
                if step_size_str:
                    with contextlib.suppress(ValueError, TypeError):
                        step_size = Decimal(str(step_size_str))

                contract_type = inst.get("type", "perpetual")
                delivery_date = inst.get("expiry") or inst.get("expiryDate")

                out.append(
                    Symbol(
                        symbol=normalized_symbol,
                        base_asset=base_asset or normalized_symbol[:3],
                        quote_asset=quote_asset or normalized_symbol[-3:],
                        tick_size=tick_size,
                        step_size=step_size,
                        min_notional=min_notional,
                        contract_type=contract_type,
                        delivery_date=delivery_date,
                    )
                )

        else:
            # Kraken Spot format: {result: {PAIR: {altname, wsname, ...}, ...}}
            if not isinstance(result, dict):
                return out

            for pair_key, pair_info in result.items():
                if not isinstance(pair_info, dict):
                    continue

                # Filter by status
                status = pair_info.get("status", "")
                if status and status != "online":
                    continue

                # Normalize symbol
                normalized_symbol = normalize_symbol_from_kraken(pair_key, market_type)

                # Extract base and quote assets
                base_asset = pair_info.get("base", "")
                quote_asset = pair_info.get("quote", "")

                # Convert XBT to BTC
                if base_asset == "XBT":
                    base_asset = "BTC"

                # Filter by quote asset if specified
                if quote_asset_filter and quote_asset.upper() != quote_asset_filter.upper():
                    continue

                # Extract tick size and step size
                tick_size = None
                step_size = None
                min_notional = None

                tick_size_str = pair_info.get("tick_size")
                if tick_size_str:
                    with contextlib.suppress(ValueError, TypeError):
                        tick_size = Decimal(str(tick_size_str))

                step_size_str = pair_info.get("lot_decimals")
                if step_size_str is not None:
                    with contextlib.suppress(ValueError, TypeError):
                        # lot_decimals is number of decimals, calculate step size
                        step_size = Decimal("1") / (Decimal("10") ** int(step_size_str))

                min_notional_str = pair_info.get("ordermin")
                if min_notional_str:
                    with contextlib.suppress(ValueError, TypeError):
                        min_notional = Decimal(str(min_notional_str))

                out.append(
                    Symbol(
                        symbol=normalized_symbol,
                        base_asset=base_asset or normalized_symbol[:3],
                        quote_asset=quote_asset or normalized_symbol[-3:],
                        tick_size=tick_size,
                        step_size=step_size,
                        min_notional=min_notional,
                        contract_type=None,
                        delivery_date=None,
                    )
                )

        return out


class OrderBookResponseAdapter(ResponseAdapter):
    """Adapter for orderbook responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> OrderBook:
        market_type: MarketType = params["market_type"]
        symbol = params["symbol"].upper()

        result = _extract_result(response, market_type)

        bids = []
        asks = []

        if market_type == MarketType.FUTURES:
            # Kraken Futures format: {result: "ok", orderBook: {bids: [[price, qty], ...], asks: [[price, qty], ...]}}
            orderbook_data = result.get("orderBook", result) if isinstance(result, dict) else result

            bids_data = orderbook_data.get("bids", []) if isinstance(orderbook_data, dict) else []
            asks_data = orderbook_data.get("asks", []) if isinstance(orderbook_data, dict) else []

            if isinstance(bids_data, list):
                bids = [
                    (Decimal(str(p)), Decimal(str(q))) for p, q in bids_data if len([p, q]) >= 2
                ]

            if isinstance(asks_data, list):
                asks = [
                    (Decimal(str(p)), Decimal(str(q))) for p, q in asks_data if len([p, q]) >= 2
                ]

            timestamp_ms = (
                orderbook_data.get("serverTime", 0) if isinstance(orderbook_data, dict) else 0
            )
            last_update_id = (
                orderbook_data.get("sequenceNumber", 0) if isinstance(orderbook_data, dict) else 0
            )

        else:
            # Kraken Spot format: {result: {PAIR: {bids: [[price, volume, timestamp], ...], asks: [[price, volume, timestamp], ...]}}}
            pair_data = None
            if isinstance(result, dict):
                # Find first key that looks like a pair
                for key in result:
                    pair_data = result[key]
                    break

            if isinstance(pair_data, dict):
                bids_data = pair_data.get("bids", [])
                asks_data = pair_data.get("asks", [])

                if isinstance(bids_data, list):
                    # Kraken Spot: [price, volume, timestamp]
                    bids = [
                        (Decimal(str(row[0])), Decimal(str(row[1])))
                        for row in bids_data
                        if len(row) >= 2
                    ]

                if isinstance(asks_data, list):
                    asks = [
                        (Decimal(str(row[0])), Decimal(str(row[1])))
                        for row in asks_data
                        if len(row) >= 2
                    ]

                timestamp_ms = 0
                last_update_id = 0

        timestamp = (
            datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
            if timestamp_ms
            else datetime.now(UTC)
        )

        # OrderBook requires at least one level - use default if empty
        if not bids and not asks:
            bids = [(Decimal("0"), Decimal("0"))]
            asks = [(Decimal("0"), Decimal("0"))]
        elif not bids:
            bids = [(Decimal("0"), Decimal("0"))]
        elif not asks:
            asks = [(Decimal("0"), Decimal("0"))]

        return OrderBook(
            symbol=symbol,
            last_update_id=last_update_id,
            bids=bids,
            asks=asks,
            timestamp=timestamp,
        )


class RecentTradesAdapter(ResponseAdapter):
    """Adapter for recent trades responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Trade]:
        market_type: MarketType = params["market_type"]
        symbol = params["symbol"].upper()

        result = _extract_result(response, market_type)

        out: list[Trade] = []

        if market_type == MarketType.FUTURES:
            # Kraken Futures format: {result: "ok", history: [{time, trade_id, price, size, side}, ...]}
            trades_list = result.get("history", []) if isinstance(result, dict) else result
            if not isinstance(trades_list, list):
                return out

            for row in trades_list:
                if not isinstance(row, dict):
                    continue

                try:
                    time_ms = row.get("time", 0)
                    price_str = row.get("price")
                    qty_str = row.get("size")
                    side = row.get("side", "")  # "buy" or "sell"
                    trade_id = row.get("trade_id", "")

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
                            timestamp=datetime.fromtimestamp(time_ms / 1000, tz=UTC)
                            if time_ms
                            else datetime.now(UTC),
                            is_buyer_maker=is_buyer_maker,
                            is_best_match=None,
                        )
                    )
                except (ValueError, TypeError, KeyError):
                    continue

        else:
            # Kraken Spot format: {result: {PAIR: [[price, volume, time, buy/sell, market/limit, misc], ...]}}
            pair_data = None
            if isinstance(result, dict):
                for key in result:
                    pair_data = result[key]
                    break

            if not isinstance(pair_data, list):
                return out

            for row in pair_data:
                if not isinstance(row, list) or len(row) < 4:
                    continue

                try:
                    # Kraken Spot: [price, volume, time, buy/sell, market/limit, misc]
                    price_str = row[0]
                    qty_str = row[1]
                    time_float = float(row[2])
                    side_str = row[3] if len(row) > 3 else ""

                    price = Decimal(str(price_str))
                    quantity = Decimal(str(qty_str))
                    quote_quantity = price * quantity

                    # Kraken side: "b" means buy, "s" means sell
                    is_buyer_maker = side_str.lower() == "b"

                    out.append(
                        Trade(
                            symbol=symbol,
                            trade_id=int(hash(f"{time_float}{price_str}{qty_str}")),
                            price=price,
                            quantity=quantity,
                            quote_quantity=quote_quantity,
                            timestamp=datetime.fromtimestamp(time_float, tz=UTC),
                            is_buyer_maker=is_buyer_maker,
                            is_best_match=None,
                        )
                    )
                except (ValueError, TypeError, IndexError):
                    continue

        return out


class FundingRateAdapter(ResponseAdapter):
    """Adapter for funding rate history responses (Futures only)."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[FundingRate]:
        market_type: MarketType = params["market_type"]
        if market_type != MarketType.FUTURES:
            return []

        symbol = params["symbol"].upper()
        result = _extract_result(response, market_type)

        # Kraken Futures format: {result: "ok", fundingRates: [{time, fundingRate, markPrice}, ...]}
        rates_list = result.get("fundingRates", []) if isinstance(result, dict) else result
        if not isinstance(rates_list, list):
            return []

        out: list[FundingRate] = []
        for row in rates_list:
            if not isinstance(row, dict):
                continue

            try:
                fr_str = row.get("fundingRate")
                ts_ms = row.get("time", 0)
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


class OpenInterestCurrentAdapter(ResponseAdapter):
    """Adapter for current open interest responses (Futures only)."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        market_type: MarketType = params["market_type"]
        if market_type != MarketType.FUTURES:
            return []

        symbol = params["symbol"].upper()
        result = _extract_result(response, market_type)

        # Kraken Futures format: {result: "ok", ticker: {openInterest, openInterestValue, ...}}
        ticker_data = result.get("ticker", result) if isinstance(result, dict) else result

        if not isinstance(ticker_data, dict):
            return []

        oi_str = ticker_data.get("openInterest")
        oi_value_str = ticker_data.get("openInterestValue")
        timestamp_ms = ticker_data.get("serverTime", 0)

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
                    open_interest_value=Decimal(str(oi_value_str)) if oi_value_str else None,
                )
            ]
        except (ValueError, TypeError):
            return []


class OpenInterestHistAdapter(ResponseAdapter):
    """Adapter for historical open interest responses (Futures only)."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        market_type: MarketType = params["market_type"]
        if market_type != MarketType.FUTURES:
            return []

        symbol = params["symbol"].upper()
        result = _extract_result(response, market_type)

        # Kraken Futures format: {result: "ok", openInterest: [{time, openInterest, openInterestValue}, ...]}
        oi_list = result.get("openInterest", []) if isinstance(result, dict) else result
        if not isinstance(oi_list, list):
            return []

        out: list[OpenInterest] = []
        for row in oi_list:
            if not isinstance(row, dict):
                continue

            try:
                ts_ms = row.get("time", 0)
                oi_str = row.get("openInterest")
                oi_value_str = row.get("openInterestValue")

                if ts_ms is None or oi_str is None:
                    continue

                out.append(
                    OpenInterest(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                        open_interest=Decimal(str(oi_str)),
                        open_interest_value=Decimal(str(oi_value_str)) if oi_value_str else None,
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue

        return out
