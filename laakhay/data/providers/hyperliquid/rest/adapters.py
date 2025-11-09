"""Response adapters for Hyperliquid REST endpoints.

Based on official API documentation:
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from ....core import MarketType
from ....core.exceptions import DataError
from ....io import ResponseAdapter
from ....models import OHLCV, Bar, FundingRate, OpenInterest, OrderBook, SeriesMeta, Symbol, Trade


def _extract_result(response: Any) -> Any:
    """Extract result from Hyperliquid response.
    
    Hyperliquid may return:
    - Direct data: {...}
    - Wrapped: {"status": "ok", "data": {...}}
    - Error: {"error": "..."}
    
    Format to be verified.
    """
    if not isinstance(response, dict):
        raise DataError(f"Invalid response format: expected dict, got {type(response)}")

    # Check for error
    if "error" in response:
        error_msg = response.get("error", "Unknown error")
        raise DataError(f"Hyperliquid API error: {error_msg}")

    # Check for wrapped response
    if "data" in response:
        return response["data"]
    
    # Check for status wrapper
    if "status" in response and response.get("status") != "ok":
        status = response.get("status", "unknown")
        raise DataError(f"Hyperliquid API error: status={status}")

    # Assume direct response
    return response


class CandlesResponseAdapter(ResponseAdapter):
    """Adapter for candle/OHLCV responses.
    
    Hyperliquid returns array of candle objects:
    [{"T": close_ms, "c": close, "h": high, "i": interval, "l": low, "n": trades, "o": open, "s": coin, "t": open_ms, "v": volume}, ...]
    """

    def parse(self, response: Any, params: dict[str, Any]) -> OHLCV:
        # Hyperliquid returns array directly (not wrapped)
        if not isinstance(response, list):
            raise DataError(f"Invalid candle response format: expected list, got {type(response)}")
        
        symbol = params["symbol"].upper()
        interval = params["interval"]

        meta = SeriesMeta(symbol=symbol, timeframe=interval.value)
        bars = []
        
        for row in response:
            if not isinstance(row, dict):
                continue
            
            try:
                # Hyperliquid format: {"T": close_ms, "c": close, "h": high, "i": interval, "l": low, "n": trades, "o": open, "s": coin, "t": open_ms, "v": volume}
                open_ms = int(row.get("t", 0))  # Open time
                close_ms = int(row.get("T", 0))  # Close time
                open_price = Decimal(str(row.get("o", 0)))
                high_price = Decimal(str(row.get("h", 0)))
                low_price = Decimal(str(row.get("l", 0)))
                close_price = Decimal(str(row.get("c", 0)))
                volume = Decimal(str(row.get("v", 0)))
                
                # Use open time for timestamp
                if not open_ms:
                    continue

                bars.append(
                    Bar(
                        timestamp=datetime.fromtimestamp(open_ms / 1000, tz=timezone.utc),
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=close_price,
                        volume=volume,
                        is_closed=True,  # Historical data is always closed
                    )
                )
            except (ValueError, TypeError, KeyError) as e:
                # Skip invalid rows
                continue

        # Hyperliquid returns candles in chronological order (oldest first)
        return OHLCV(meta=meta, bars=bars)


class ExchangeInfoSymbolsAdapter(ResponseAdapter):
    """Adapter for meta/symbols responses.
    
    Expected format: Object with symbols/instruments list
    Format to be verified.
    """

    def parse(self, response: Any, params: dict[str, Any]) -> list[Symbol]:
        result = _extract_result(response)
        market_type = params["market_type"]
        quote_asset_filter = params.get("quote_asset")

        # Hyperliquid supports both Spot and Futures
        # Meta response contains both universe (perps) and spotMeta (spot)

        # Extract symbols list
        # May be in "universe", "symbols", "instruments", "meta" field
        symbols_data = (
            result.get("universe") or
            result.get("symbols") or
            result.get("instruments") or
            result.get("meta") or
            []
        )
        
        if not isinstance(symbols_data, list):
            if isinstance(symbols_data, dict):
                # May be object with list inside
                symbols_data = symbols_data.get("list", [])
            else:
                symbols_data = []

        out: list[Symbol] = []
        for sym_data in symbols_data:
            if not isinstance(sym_data, dict):
                continue

            try:
                # Extract symbol name - field name to be verified
                symbol_str = sym_data.get("name") or sym_data.get("symbol") or sym_data.get("coin") or ""
                if not symbol_str:
                    continue

                # Filter by quote asset if specified
                # Hyperliquid perps are typically quoted in USDC
                quote_asset = sym_data.get("quoteAsset") or sym_data.get("quote") or ("USDC" if market_type == MarketType.FUTURES else "USD")
                if quote_asset_filter and quote_asset != quote_asset_filter:
                    continue

                # Extract base asset
                base_asset = sym_data.get("baseAsset") or sym_data.get("base") or symbol_str.split("-")[0] if "-" in symbol_str else symbol_str.replace("USD", "")

                # Extract tick size and step size
                tick_size = None
                step_size = None
                min_notional = None

                # Try common field names
                if "tickSize" in sym_data:
                    tick_size = Decimal(str(sym_data["tickSize"]))
                elif "szDecimals" in sym_data:
                    # May be number of decimals
                    sz_decimals = sym_data.get("szDecimals", 0)
                    tick_size = Decimal("1") / (10 ** int(sz_decimals))

                if "stepSize" in sym_data:
                    step_size = Decimal(str(sym_data["stepSize"]))
                elif "lotSize" in sym_data:
                    step_size = Decimal(str(sym_data["lotSize"]))

                if "minNotional" in sym_data:
                    min_notional = Decimal(str(sym_data["minNotional"]))
                elif "minOrderSize" in sym_data:
                    min_notional = Decimal(str(sym_data["minOrderSize"]))

                # Determine contract type based on market_type
                contract_type = "PERPETUAL" if market_type == MarketType.FUTURES else "SPOT"
                
                out.append(
                    Symbol(
                        symbol=symbol_str,
                        base_asset=base_asset,
                        quote_asset=quote_asset,
                        tick_size=tick_size,
                        step_size=step_size,
                        min_notional=min_notional,
                        contract_type=contract_type,
                        delivery_date=None,
                    )
                )
            except (ValueError, TypeError, KeyError) as e:
                continue

        return out


class OrderBookResponseAdapter(ResponseAdapter):
    """Adapter for order book responses.
    
    Hyperliquid format: {"coin": "BTC", "time": ms, "levels": [[bids...], [asks...]]}
    Where levels[0] = bids, levels[1] = asks
    Each level: {"px": price, "sz": size, "n": number of orders}
    """

    def parse(self, response: Any, params: dict[str, Any]) -> OrderBook:
        # Hyperliquid returns object directly
        if not isinstance(response, dict):
            raise DataError(f"Invalid order book response format: expected dict, got {type(response)}")
        
        symbol = params["symbol"].upper()

        # Extract levels array: [bids_array, asks_array]
        levels = response.get("levels", [])
        if not isinstance(levels, list) or len(levels) < 2:
            raise DataError("Invalid order book levels format")

        bids_data = levels[0] if isinstance(levels[0], list) else []
        asks_data = levels[1] if isinstance(levels[1], list) else []

        bids = []
        asks = []

        # Parse bids: Hyperliquid format is [[price, size], [price, size], ...]
        for item in bids_data:
            if isinstance(item, list) and len(item) >= 2:
                try:
                    px_str = item[0]
                    sz_str = item[1]
                    bids.append((Decimal(str(px_str)), Decimal(str(sz_str))))
                except (ValueError, TypeError, IndexError):
                    continue

        # Parse asks: same format as bids
        for item in asks_data:
            if isinstance(item, list) and len(item) >= 2:
                try:
                    px_str = item[0]
                    sz_str = item[1]
                    asks.append((Decimal(str(px_str)), Decimal(str(sz_str))))
                except (ValueError, TypeError, IndexError):
                    continue

        # OrderBook requires at least one level
        if not bids and not asks:
            raise DataError("Order book must have at least one level")

        # Extract timestamp
        timestamp_ms = response.get("time", 0)
        timestamp = (
            datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            if timestamp_ms
            else datetime.now(timezone.utc)
        )

        return OrderBook(
            symbol=symbol,
            last_update_id=0,  # Hyperliquid doesn't use update IDs
            bids=bids,
            asks=asks,
            timestamp=timestamp,
        )


class OpenInterestCurrentAdapter(ResponseAdapter):
    """Adapter for current open interest responses.
    
    Expected format: Single OI value or object
    Format to be verified.
    """

    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        result = _extract_result(response)
        symbol = params["symbol"].upper()

        # Hyperliquid may return:
        # - Single value: {"openInterest": 12345}
        # - Object: {"coin": "BTC", "openInterest": 12345, "time": ...}
        
        oi_str = result.get("openInterest") or result.get("oi") or result.get("open_interest")
        timestamp_ms = result.get("time") or result.get("timestamp") or result.get("ts") or 0

        if oi_str is None:
            return []

        try:
            return [
                OpenInterest(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
                    if timestamp_ms
                    else datetime.now(timezone.utc),
                    open_interest=Decimal(str(oi_str)),
                    open_interest_value=None,  # Calculate if price available
                )
            ]
        except (ValueError, TypeError):
            return []


class OpenInterestHistAdapter(ResponseAdapter):
    """Adapter for historical open interest responses.
    
    Expected format: Array of OI data points
    Format to be verified.
    """

    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        result = _extract_result(response)
        symbol = params["symbol"].upper()

        # Extract OI list
        oi_list = result.get("list") or result.get("data") or result.get("history") or result
        if not isinstance(oi_list, list):
            oi_list = []

        out: list[OpenInterest] = []
        for row in oi_list:
            if not isinstance(row, dict):
                continue

            try:
                ts_ms = row.get("timestamp") or row.get("time") or row.get("ts") or 0
                oi_str = row.get("openInterest") or row.get("oi") or row.get("open_interest")

                if ts_ms is None or oi_str is None:
                    continue

                out.append(
                    OpenInterest(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc),
                        open_interest=Decimal(str(oi_str)),
                        open_interest_value=None,
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue

        return out


class RecentTradesAdapter(ResponseAdapter):
    """Adapter for recent trades responses.
    
    Expected format: Array of trade objects
    Format to be verified.
    """

    def parse(self, response: Any, params: dict[str, Any]) -> list[Trade]:
        result = _extract_result(response)
        symbol = params["symbol"].upper()

        # Extract trades list
        trades_list = result.get("trades") or result.get("data") or result.get("list") or result
        if not isinstance(trades_list, list):
            trades_list = []

        out: list[Trade] = []
        for row in trades_list:
            if not isinstance(row, dict):
                continue

            try:
                # Extract trade fields - names to be verified
                trade_id = row.get("id") or row.get("tradeId") or row.get("txid") or ""
                price_str = row.get("price") or row.get("p")
                qty_str = row.get("quantity") or row.get("qty") or row.get("size") or row.get("sz")
                side = row.get("side", "")  # "buy", "sell", "B", "S", etc.
                time_ms = row.get("time") or row.get("timestamp") or row.get("ts") or 0

                if not price_str or not qty_str:
                    continue

                price = Decimal(str(price_str))
                quantity = Decimal(str(qty_str))
                quote_quantity = price * quantity

                # Determine if buyer is maker
                # Hyperliquid format to be verified
                is_buyer_maker = None
                if side:
                    side_upper = side.upper()
                    # Common patterns: "BUY" = buyer taker, "SELL" = seller taker
                    # Or "B" = buy, "S" = sell
                    # Verify actual meaning
                    is_buyer_maker = side_upper in ["SELL", "S"]

                # Generate trade ID if not provided
                trade_id_int = 0
                if trade_id:
                    try:
                        trade_id_int = int(trade_id)
                    except (ValueError, TypeError):
                        trade_id_int = hash(str(trade_id)) % (2**31)  # Convert to int

                out.append(
                    Trade(
                        symbol=symbol,
                        trade_id=trade_id_int,
                        price=price,
                        quantity=quantity,
                        quote_quantity=quote_quantity,
                        timestamp=datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc)
                        if time_ms
                        else datetime.now(timezone.utc),
                        is_buyer_maker=is_buyer_maker,
                        is_best_match=None,
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue

        return out


class FundingRateAdapter(ResponseAdapter):
    """Adapter for funding rate history responses.
    
    Expected format: Array of funding rate objects
    Format to be verified.
    """

    def parse(self, response: Any, params: dict[str, Any]) -> list[FundingRate]:
        result = _extract_result(response)
        symbol = params["symbol"].upper()

        # Extract funding rates list
        rates_list = result.get("fundingRates") or result.get("funding") or result.get("data") or result.get("list") or result
        if not isinstance(rates_list, list):
            rates_list = []

        out: list[FundingRate] = []
        for row in rates_list:
            if not isinstance(row, dict):
                continue

            try:
                # Extract funding rate fields - names to be verified
                fr_str = row.get("fundingRate") or row.get("rate") or row.get("funding_rate")
                ts_ms = row.get("fundingTime") or row.get("time") or row.get("timestamp") or row.get("ts") or 0
                mark_price_str = row.get("markPrice") or row.get("mark_price") or row.get("mark")

                if fr_str is None:
                    continue

                mark_price = None
                if mark_price_str:
                    mark_price = Decimal(str(mark_price_str))

                out.append(
                    FundingRate(
                        symbol=symbol,
                        funding_time=datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
                        if ts_ms
                        else datetime.now(timezone.utc),
                        funding_rate=Decimal(str(fr_str)),
                        mark_price=mark_price,
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue

        return out

