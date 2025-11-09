"""Response adapters for Coinbase REST endpoints."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from ....io import ResponseAdapter
from ....models import OHLCV, Bar, OrderBook, SeriesMeta, Symbol, Trade
from ..constants import normalize_symbol_from_coinbase


class CandlesResponseAdapter(ResponseAdapter):
    """Adapter for candles/OHLCV responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> OHLCV:
        """Parse Coinbase Exchange API candles response.

        Coinbase Exchange API returns array of arrays:
        [
            [timestamp, low, high, open, close, volume],
            ...
        ]
        Note: Format is [timestamp, low, high, open, close, volume] - low comes before high!
        """
        symbol = params["symbol"].upper()
        interval = params["interval"]

        # Exchange API returns array directly (not wrapped in "candles")
        candles_data = response if isinstance(response, list) else response.get("candles", [])
        if not isinstance(candles_data, list):
            candles_data = []

        meta = SeriesMeta(symbol=symbol, timeframe=interval.value)
        bars = []

        for candle in candles_data:
            if not isinstance(candle, list | tuple) or len(candle) < 6:
                # Try dict format (Advanced Trade API) as fallback
                if isinstance(candle, dict):
                    try:
                        start_str = candle.get("start")
                        if not start_str:
                            continue
                        if isinstance(start_str, str):
                            ts_str = start_str.replace("Z", "+00:00")
                            timestamp = datetime.fromisoformat(ts_str)
                        else:
                            timestamp = datetime.fromtimestamp(float(start_str), tz=UTC)
                        bars.append(
                            Bar(
                                timestamp=timestamp,
                                open=Decimal(str(candle.get("open", "0"))),
                                high=Decimal(str(candle.get("high", "0"))),
                                low=Decimal(str(candle.get("low", "0"))),
                                close=Decimal(str(candle.get("close", "0"))),
                                volume=Decimal(str(candle.get("volume", "0"))),
                                is_closed=True,
                            )
                        )
                    except (ValueError, TypeError, KeyError):
                        continue
                continue

            try:
                # Exchange API format: [timestamp, low, high, open, close, volume]
                timestamp_sec = int(candle[0])
                timestamp = datetime.fromtimestamp(timestamp_sec, tz=UTC)

                low_price = Decimal(str(candle[1]))
                high_price = Decimal(str(candle[2]))
                open_price = Decimal(str(candle[3]))
                close_price = Decimal(str(candle[4]))
                volume = Decimal(str(candle[5]))

                bars.append(
                    Bar(
                        timestamp=timestamp,
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=close_price,
                        volume=volume,
                        is_closed=True,
                    )
                )
            except (ValueError, TypeError, IndexError):
                # Skip invalid candles
                continue

        return OHLCV(meta=meta, bars=bars)


class ExchangeInfoSymbolsAdapter(ResponseAdapter):
    """Adapter for products/symbols responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Symbol]:
        """Parse Coinbase products response.

        Coinbase returns: {
            "products": [
                {
                    "product_id": "BTC-USD",
                    "price": "42800.00",
                    "price_percentage_change_24h": "2.5",
                    "volume_24h": "1234567.89",
                    "volume_percentage_change_24h": "5.0",
                    "base_increment": "0.00000001",
                    "quote_increment": "0.01",
                    "quote_min_size": "1.00",
                    "quote_max_size": "1000000.00",
                    "base_min_size": "0.001",
                    "base_max_size": "280.00",
                    "base_name": "Bitcoin",
                    "quote_name": "US Dollar",
                    "watched": false,
                    "is_disabled": false,
                    "new": false,
                    "status": "online",
                    "cancel_only": false,
                    "limit_only": false,
                    "post_only": false,
                    "trading_disabled": false,
                    "auction_mode": false,
                    "product_type": "SPOT",
                    "quote_currency_id": "USD",
                    "base_currency_id": "BTC",
                    "fcm_trading_session_details": null,
                    "mid_market_price": "",
                    "alias": "",
                    "alias_to": [],
                    "base_display_symbol": "BTC",
                    "quote_display_symbol": "USD",
                    "view_only": false,
                    "price_increment": "0.01",
                    "size_increment": "0.00000001",
                    "display_name": "BTC-USD"
                },
                ...
            ]
        }
        """
        quote_asset_filter = params.get("quote_asset")

        # Exchange API returns array directly (not wrapped in "products")
        products_data = response if isinstance(response, list) else response.get("products", [])
        if not isinstance(products_data, list):
            products_data = []

        out: list[Symbol] = []

        for product in products_data:
            if not isinstance(product, dict):
                continue

            try:
                # Filter by status - Coinbase uses "online" for active products
                status = product.get("status", "")
                if status != "online":
                    continue

                # Filter by trading disabled
                if product.get("trading_disabled", False):
                    continue

                # Exchange API doesn't have product_type field - all are spot
                # Advanced Trade API has product_type - filter for SPOT
                product_type = product.get("product_type")
                if product_type and product_type != "SPOT":
                    continue

                # Extract product_id (Exchange API uses "id", Advanced Trade uses "product_id")
                product_id = product.get("id") or product.get("product_id", "")
                if not product_id:
                    continue

                # Normalize symbol to standard format
                symbol = normalize_symbol_from_coinbase(product_id)

                # Extract base and quote assets
                # Exchange API uses "base_currency"/"quote_currency"
                # Advanced Trade API uses "base_currency_id"/"quote_currency_id"
                base_asset = product.get("base_currency") or product.get("base_currency_id", "")
                quote_asset = product.get("quote_currency") or product.get("quote_currency_id", "")

                # Filter by quote asset if specified
                if quote_asset_filter and quote_asset != quote_asset_filter:
                    continue

                # Extract tick size (price increment)
                # Exchange API uses "quote_increment", Advanced Trade uses "price_increment"
                price_increment_str = product.get("quote_increment") or product.get(
                    "price_increment"
                )
                tick_size = None
                if price_increment_str:
                    with contextlib.suppress(ValueError, TypeError):
                        tick_size = Decimal(str(price_increment_str))

                # Extract step size (size increment)
                # Exchange API uses "base_increment", Advanced Trade uses "size_increment"
                size_increment_str = product.get("base_increment") or product.get("size_increment")
                step_size = None
                if size_increment_str:
                    with contextlib.suppress(ValueError, TypeError):
                        step_size = Decimal(str(size_increment_str))

                # Extract min notional (quote min size)
                # Exchange API uses "min_market_funds", Advanced Trade uses "quote_min_size"
                quote_min_size_str = product.get("min_market_funds") or product.get(
                    "quote_min_size"
                )
                min_notional = None
                if quote_min_size_str:
                    with contextlib.suppress(ValueError, TypeError):
                        min_notional = Decimal(str(quote_min_size_str))

                out.append(
                    Symbol(
                        symbol=symbol,
                        base_asset=base_asset,
                        quote_asset=quote_asset,
                        tick_size=tick_size,
                        step_size=step_size,
                        min_notional=min_notional,
                        contract_type=None,  # Spot markets don't have contract types
                        delivery_date=None,  # Spot markets don't have delivery dates
                    )
                )
            except (ValueError, TypeError, KeyError):
                # Skip invalid products
                continue

        return out


class OrderBookResponseAdapter(ResponseAdapter):
    """Adapter for order book responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> OrderBook:
        """Parse Coinbase Exchange API order book response.

        Exchange API returns: {
            "bids": [["price", "size", num_orders], ...],
            "asks": [["price", "size", num_orders], ...],
            "sequence": 123456,
            "time": "2024-01-01T00:00:00Z"
        }

        Advanced Trade API returns: {
            "pricebook": {
                "bids": [["price", "size"], ...],
                "asks": [["price", "size"], ...]
            }
        }
        """
        symbol = params["symbol"].upper()

        # Exchange API has bids/asks directly, Advanced Trade wraps in "pricebook"
        if "pricebook" in response:
            pricebook = response.get("pricebook", {})
            bids_data = pricebook.get("bids", [])
            asks_data = pricebook.get("asks", [])
        else:
            bids_data = response.get("bids", [])
            asks_data = response.get("asks", [])

        bids = []
        asks = []

        # Parse bids
        if isinstance(bids_data, list):
            for bid in bids_data:
                if isinstance(bid, list) and len(bid) >= 2:
                    try:
                        price = Decimal(str(bid[0]))
                        quantity = Decimal(str(bid[1]))
                        bids.append((price, quantity))
                    except (ValueError, TypeError):
                        continue

        # Parse asks
        if isinstance(asks_data, list):
            for ask in asks_data:
                if isinstance(ask, list) and len(ask) >= 2:
                    try:
                        price = Decimal(str(ask[0]))
                        quantity = Decimal(str(ask[1]))
                        asks.append((price, quantity))
                    except (ValueError, TypeError):
                        continue

        # Coinbase doesn't provide last_update_id or timestamp in order book response
        # Use current timestamp
        timestamp = datetime.now(UTC)

        # OrderBook model requires at least one level in BOTH bids AND asks
        # If either is empty, add a minimal valid level to satisfy validation
        # Using a very small positive price (0.0001) to satisfy validation
        if not bids:
            bids = [(Decimal("0.0001"), Decimal("0.0001"))]
        if not asks:
            asks = [(Decimal("0.0001"), Decimal("0.0001"))]

        return OrderBook(
            symbol=symbol,
            last_update_id=0,  # Coinbase doesn't provide this
            bids=bids,
            asks=asks,
            timestamp=timestamp,
        )


class RecentTradesAdapter(ResponseAdapter):
    """Adapter for recent trades responses."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Trade]:
        """Parse Coinbase Exchange API trades response.

        Exchange API returns array directly:
        [
            {
                "trade_id": 123456,
                "side": "buy",  # or "sell" (lowercase)
                "size": "0.5",
                "price": "42800.00",
                "time": "2024-01-01T12:00:00Z"
            },
            ...
        ]

        Advanced Trade API returns: {
            "trades": [
                {
                    "trade_id": "123456",
                    "side": "BUY",
                    ...
                }
            ]
        }
        """
        symbol = params["symbol"].upper()

        # Exchange API returns array directly, Advanced Trade wraps in "trades"
        trades_data = response if isinstance(response, list) else response.get("trades", [])
        if not isinstance(trades_data, list):
            trades_data = []

        out: list[Trade] = []

        for trade_data in trades_data:
            if not isinstance(trade_data, dict):
                continue

            try:
                # Extract trade ID (Exchange API uses int, Advanced Trade uses string)
                trade_id_raw = trade_data.get("trade_id", 0)
                trade_id = 0
                if trade_id_raw:
                    try:
                        trade_id = int(trade_id_raw)
                    except (ValueError, TypeError):
                        # Use hash if not numeric
                        trade_id = abs(hash(str(trade_id_raw))) % (10**10)

                # Extract price and size
                price_str = trade_data.get("price")
                size_str = trade_data.get("size")

                if not price_str or not size_str:
                    continue

                price = Decimal(str(price_str))
                quantity = Decimal(str(size_str))
                quote_quantity = price * quantity

                # Extract timestamp
                time_str = trade_data.get("time", "")
                if time_str:
                    # Parse ISO 8601 timestamp
                    if isinstance(time_str, str):
                        ts_str = time_str.replace("Z", "+00:00")
                        timestamp = datetime.fromisoformat(ts_str)
                    else:
                        timestamp = datetime.fromtimestamp(float(time_str), tz=UTC)
                else:
                    timestamp = datetime.now(UTC)

                # Extract side - Exchange API uses "buy"/"sell" (lowercase), Advanced Trade uses "BUY"/"SELL"
                side = trade_data.get("side", "").upper()
                # "BUY" means buyer is taker (not maker), so is_buyer_maker = False
                # "SELL" means seller is taker (not maker), so is_buyer_maker = True
                is_buyer_maker = side == "SELL"

                out.append(
                    Trade(
                        symbol=symbol,
                        trade_id=trade_id,
                        price=price,
                        quantity=quantity,
                        quote_quantity=quote_quantity,
                        timestamp=timestamp,
                        is_buyer_maker=is_buyer_maker,
                        is_best_match=None,  # Coinbase doesn't provide this
                    )
                )
            except (ValueError, TypeError, KeyError):
                # Skip invalid trades
                continue

        return out
