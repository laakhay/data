"""Message adapters for Hyperliquid WebSocket streams.

Based on official API documentation:
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions

Message format: {"channel": "candle", "data": [...]} or {"channel": "trades", "data": [...]}
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from ....io import MessageAdapter
from ....models import FundingRate, Liquidation, MarkPrice, OpenInterest, OrderBook, Trade
from ....models.streaming_bar import StreamingBar


class OhlcvAdapter(MessageAdapter):
    """Adapter for candle/OHLCV WebSocket messages.

    Hyperliquid format: {"channel": "candle", "data": [{"t": open_ms, "T": close_ms, "s": coin, "i": interval, "o": open, "c": close, "h": high, "l": low, "v": volume, "n": trades}, ...]}
    """

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        channel = payload.get("channel", "")
        return bool(channel == "candle")

    def parse(self, payload: Any) -> list[StreamingBar]:
        out: list[StreamingBar] = []
        if not isinstance(payload, dict):
            return out

        # Extract data array
        data = payload.get("data", [])
        if not isinstance(data, list):
            return out

        for item in data:
            if not isinstance(item, dict):
                continue

            try:
                # Hyperliquid format: {"t": open_ms, "T": close_ms, "s": coin, "i": interval, "o": open, "c": close, "h": high, "l": low, "v": volume, "n": trades}
                open_ms = int(item.get("t", 0))  # Open time
                close_ms = int(item.get("T", 0))  # Close time
                symbol = item.get("s", "").upper()  # Coin symbol
                open_price = item.get("o")
                high_price = item.get("h")
                low_price = item.get("l")
                close_price = item.get("c")
                volume = item.get("v")

                if not all(
                    [open_ms, symbol, open_price, high_price, low_price, close_price, volume]
                ):
                    continue

                # Candle is closed if close_ms exists and is different from open_ms
                is_closed = close_ms > open_ms if close_ms else True

                out.append(
                    StreamingBar(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(open_ms / 1000, tz=UTC),
                        open=Decimal(str(open_price)),
                        high=Decimal(str(high_price)),
                        low=Decimal(str(low_price)),
                        close=Decimal(str(close_price)),
                        volume=Decimal(str(volume)),
                        is_closed=is_closed,
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue

        return out


class TradesAdapter(MessageAdapter):
    """Adapter for trade WebSocket messages.

    Hyperliquid format: {"channel": "trades", "data": [{"coin": "BTC", "side": "A"/"B", "px": price, "sz": size, "hash": hash, "time": ms, "tid": trade_id, "users": [buyer, seller]}, ...]}
    """

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        channel = payload.get("channel", "")
        return bool(channel == "trades")

    def parse(self, payload: Any) -> list[Trade]:
        out: list[Trade] = []
        if not isinstance(payload, dict):
            return out

        # Extract data array
        data = payload.get("data", [])
        if not isinstance(data, list):
            return out

        for item in data:
            if not isinstance(item, dict):
                continue

            try:
                # Hyperliquid format: {"coin": "BTC", "side": "A"/"B", "px": price, "sz": size, "hash": hash, "time": ms, "tid": trade_id, "users": [buyer, seller]}
                symbol = item.get("coin", "").upper()
                side = item.get("side", "")  # "A" = ask (sell), "B" = bid (buy)
                price_str = item.get("px")
                qty_str = item.get("sz")
                time_ms = item.get("time", 0)
                trade_id = item.get("tid", 0)

                if not all([symbol, side, price_str, qty_str, time_ms]):
                    continue

                price = Decimal(str(price_str))
                quantity = Decimal(str(qty_str))
                quote_quantity = price * quantity

                # Hyperliquid side: "A" = ask (seller is maker), "B" = bid (buyer is maker)
                is_buyer_maker = side == "A"

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
    """Adapter for orderbook WebSocket messages.

    Hyperliquid format: {"channel": "l2Book", "data": {"coin": "BTC", "time": ms, "levels": [[bids...], [asks...]]}}
    Where levels[0] = bids, levels[1] = asks
    Each level: {"px": price, "sz": size, "n": number of orders}
    """

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        channel = payload.get("channel", "")
        return bool(channel == "l2Book")

    def parse(self, payload: Any) -> list[OrderBook]:
        out: list[OrderBook] = []
        if not isinstance(payload, dict):
            return out

        # Extract data object
        data = payload.get("data", {})
        if not isinstance(data, dict):
            return out

        symbol = data.get("coin", "").upper()
        if not symbol:
            return out

        # Extract levels array: [bids_array, asks_array]
        levels = data.get("levels", [])
        if not isinstance(levels, list) or len(levels) < 2:
            return out

        bids_data = levels[0] if isinstance(levels[0], list) else []
        asks_data = levels[1] if isinstance(levels[1], list) else []

        bids = []
        asks = []

        # Parse bids: Hyperliquid format can be either:
        # 1. Array format: [[price, size], [price, size], ...]
        # 2. Dict format: [{"px": price, "sz": size, "n": orders}, ...]
        for item in bids_data:
            try:
                if isinstance(item, dict):
                    # Dictionary format: {"px": price, "sz": size, "n": orders}
                    px_str = item.get("px")
                    sz_str = item.get("sz")
                    if px_str is not None and sz_str is not None:
                        price = Decimal(str(px_str))
                        size = Decimal(str(sz_str))
                        if price > 0 and size >= 0:
                            bids.append((price, size))
                elif isinstance(item, list) and len(item) >= 2:
                    # Array format: [price, size]
                    px_str = item[0]
                    sz_str = item[1]
                    price = Decimal(str(px_str))
                    size = Decimal(str(sz_str))
                    if price > 0 and size >= 0:
                        bids.append((price, size))
            except (ValueError, TypeError, IndexError, KeyError):
                continue

        # Parse asks: same format as bids
        for item in asks_data:
            try:
                if isinstance(item, dict):
                    # Dictionary format: {"px": price, "sz": size, "n": orders}
                    px_str = item.get("px")
                    sz_str = item.get("sz")
                    if px_str is not None and sz_str is not None:
                        price = Decimal(str(px_str))
                        size = Decimal(str(sz_str))
                        if price > 0 and size >= 0:
                            asks.append((price, size))
                elif isinstance(item, list) and len(item) >= 2:
                    # Array format: [price, size]
                    px_str = item[0]
                    sz_str = item[1]
                    price = Decimal(str(px_str))
                    size = Decimal(str(sz_str))
                    if price > 0 and size >= 0:
                        asks.append((price, size))
            except (ValueError, TypeError, IndexError, KeyError):
                continue

        # OrderBook requires at least one level in both bids and asks
        if not bids or not asks:
            return out

        # Extract timestamp
        timestamp_ms = data.get("time", 0)
        timestamp = (
            datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=UTC)
            if timestamp_ms
            else datetime.now(UTC)
        )

        out.append(
            OrderBook(
                symbol=symbol,
                last_update_id=0,  # Hyperliquid doesn't use update IDs
                bids=bids,
                asks=asks,
                timestamp=timestamp,
            )
        )

        return out


class OpenInterestAdapter(MessageAdapter):
    """Adapter for open interest WebSocket messages.

    Hyperliquid format: {"channel": "activeAssetCtx", "data": {"coin": "BTC", "ctx": {"openInterest": value, ...}}}
    Open interest is part of activeAssetCtx context data.
    """

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        channel = payload.get("channel", "")
        return bool(channel == "activeAssetCtx")

    def parse(self, payload: Any) -> list[OpenInterest]:
        out: list[OpenInterest] = []
        if not isinstance(payload, dict):
            return out

        # Extract data object
        data = payload.get("data", {})
        if not isinstance(data, dict):
            return out

        symbol = data.get("coin", "").upper()
        ctx = data.get("ctx", {})

        if not symbol or not isinstance(ctx, dict):
            return out

        # Extract open interest from context
        # Hyperliquid uses "oi" field, not "openInterest"
        oi_value = ctx.get("oi") or ctx.get("openInterest")
        if oi_value is None:
            return out

        try:
            timestamp_ms = data.get("time", 0)
            out.append(
                OpenInterest(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=UTC)
                    if timestamp_ms
                    else datetime.now(UTC),
                    open_interest=Decimal(str(oi_value)),
                    open_interest_value=None,
                )
            )
        except (ValueError, TypeError):
            pass

        return out


class FundingRateAdapter(MessageAdapter):
    """Adapter for funding rate WebSocket messages.

    Hyperliquid format: {"channel": "activeAssetCtx", "data": {"coin": "BTC", "ctx": {"funding": rate, ...}}}
    Funding rate is part of activeAssetCtx context data.
    """

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        channel = payload.get("channel", "")
        return bool(channel == "activeAssetCtx")

    def parse(self, payload: Any) -> list[FundingRate]:
        out: list[FundingRate] = []
        if not isinstance(payload, dict):
            return out

        # Extract data object
        data = payload.get("data", {})
        if not isinstance(data, dict):
            return out

        symbol = data.get("coin", "").upper()
        ctx = data.get("ctx", {})

        if not symbol or not isinstance(ctx, dict):
            return out

        # Extract funding rate from context
        funding_rate = ctx.get("funding")
        mark_price = ctx.get("markPx")

        if funding_rate is None:
            return out

        try:
            timestamp_ms = data.get("time", 0)
            out.append(
                FundingRate(
                    symbol=symbol,
                    funding_time=datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=UTC)
                    if timestamp_ms
                    else datetime.now(UTC),
                    funding_rate=Decimal(str(funding_rate)),
                    mark_price=Decimal(str(mark_price)) if mark_price is not None else None,
                )
            )
        except (ValueError, TypeError):
            pass

        return out


class MarkPriceAdapter(MessageAdapter):
    """Adapter for mark price WebSocket messages.

    Hyperliquid format: {"channel": "activeAssetCtx", "data": {"coin": "BTC", "ctx": {"markPx": price, ...}}}
    Mark price is part of activeAssetCtx context data.
    """

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        channel = payload.get("channel", "")
        return bool(channel == "activeAssetCtx")

    def parse(self, payload: Any) -> list[MarkPrice]:
        out: list[MarkPrice] = []
        if not isinstance(payload, dict):
            return out

        # Extract data object
        data = payload.get("data", {})
        if not isinstance(data, dict):
            return out

        symbol = data.get("coin", "").upper()
        ctx = data.get("ctx", {})

        if not symbol or not isinstance(ctx, dict):
            return out

        # Extract mark price from context
        mark_price = ctx.get("markPx")
        if mark_price is None:
            return out

        try:
            timestamp_ms = data.get("time", 0)
            out.append(
                MarkPrice(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=UTC)
                    if timestamp_ms
                    else datetime.now(UTC),
                    mark_price=Decimal(str(mark_price)),
                )
            )
        except (ValueError, TypeError):
            pass

        return out


class LiquidationsAdapter(MessageAdapter):
    """Adapter for liquidation WebSocket messages.

    Hyperliquid format: {"channel": "userEvents", "data": {"liquidation": {"lid": id, "liquidator": addr, "liquidated_user": addr, "liquidated_ntl_pos": pos, "liquidated_account_value": value}}}
    Note: Liquidations are only available via userEvents subscription (requires user address).
    Public liquidations are not directly available.
    """

    def is_relevant(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        channel = payload.get("channel", "")
        if channel != "userEvents":
            return False
        # Check if data contains liquidation event
        data = payload.get("data", {})
        return bool(isinstance(data, dict) and "liquidation" in data)

    def parse(self, payload: Any) -> list[Liquidation]:
        out: list[Liquidation] = []
        if not isinstance(payload, dict):
            return out

        # Extract data object
        data = payload.get("data", {})
        if not isinstance(data, dict):
            return out

        # Extract liquidation event
        liquidation_data = data.get("liquidation")
        if not isinstance(liquidation_data, dict):
            return out

        from contextlib import suppress

        with suppress(ValueError, TypeError, KeyError):
            # Hyperliquid format: {"lid": id, "liquidator": addr, "liquidated_user": addr, "liquidated_ntl_pos": pos, "liquidated_account_value": value}
            # Note: This doesn't include symbol, price, size directly - may need additional API call
            # For now, return minimal liquidation info
            # Symbol not available in liquidation event - would need to query user positions
            # For now, use placeholder or skip
            # This is a limitation of Hyperliquid's API - liquidations require user context

            # Skip for now - liquidations need user address and position data
            # This would require additional API calls to get full liquidation details
            pass

        return out
