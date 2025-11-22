"""Binance REST API raw response schemas.

This module defines Pydantic models for raw Binance API responses.
These models represent the exact structure returned by Binance before
conversion to domain models.

All models use the exact field names and types as returned by Binance API.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BinanceKline(BaseModel):
    """Raw Binance kline/OHLCV response item.

    Binance returns klines as arrays. This model represents a single kline item.
    Array structure (same for spot/linear/inverse):
    """

    open_time: int
    open: str
    high: str
    low: str
    close: str
    volume: str
    close_time: int
    quote_volume: str
    trades: int
    taker_buy_base_volume: str
    taker_buy_quote_volume: str

    @classmethod
    def from_array(cls, row: list[Any]) -> BinanceKline:
        """Create BinanceKline from array response.

        Args:
            row: Array response from Binance klines endpoint (11 or 12 elements)

        Returns:
            BinanceKline instance

        """
        return cls(
            open_time=int(row[0]),
            open=str(row[1]),
            high=str(row[2]),
            low=str(row[3]),
            close=str(row[4]),
            volume=str(row[5]),
            close_time=int(row[6]),
            quote_volume=str(row[7]),
            trades=int(row[8]),
            taker_buy_base_volume=str(row[9]),
            taker_buy_quote_volume=str(row[10]),
        )


class BinanceTrade(BaseModel):
    """Raw Binance trade response item."""

    id: int = Field(..., description="Trade ID")
    price: str = Field(..., description="Price")
    qty: str = Field(..., description="Quantity")
    quote_qty: str | None = Field(None, alias="quoteQty", description="Quote quantity")
    time: int = Field(..., description="Trade time in milliseconds")
    is_buyer_maker: bool = Field(..., alias="isBuyerMaker", description="Is buyer maker")
    is_best_match: bool | None = Field(None, alias="isBestMatch", description="Is best match")

    model_config = {"populate_by_name": True}


class BinanceSymbolFilter(BaseModel):
    """Raw Binance symbol filter (from exchangeInfo)."""

    filter_type: str = Field(..., alias="filterType", description="Filter type")
    tick_size: str | None = Field(None, alias="tickSize", description="Tick size for PRICE_FILTER")
    step_size: str | None = Field(None, alias="stepSize", description="Step size for LOT_SIZE")
    min_notional: str | None = Field(
        None,
        alias="minNotional",
        description="Min notional for MIN_NOTIONAL",
    )

    model_config = {"populate_by_name": True}


class BinanceSymbolInfo(BaseModel):
    """Raw Binance symbol information (from exchangeInfo)."""

    symbol: str = Field(..., description="Symbol")
    status: str = Field(..., description="Status")
    base_asset: str = Field(..., alias="baseAsset", description="Base asset")
    quote_asset: str = Field(..., alias="quoteAsset", description="Quote asset")
    filters: list[BinanceSymbolFilter] = Field(default_factory=list, description="Filters")
    contract_type: str | None = Field(
        None,
        alias="contractType",
        description="Contract type (FUTURES only)",
    )
    delivery_date: int | None = Field(
        None,
        alias="deliveryDate",
        description="Delivery date (FUTURES only)",
    )

    model_config = {"populate_by_name": True}


class BinanceExchangeInfo(BaseModel):
    """Raw Binance exchangeInfo response."""

    symbols: list[BinanceSymbolInfo] = Field(default_factory=list, description="Symbols list")


class BinanceDepthItem(BaseModel):
    """Raw Binance depth/order book price level."""

    price: str = Field(..., description="Price")
    quantity: str = Field(..., description="Quantity")

    @classmethod
    def from_array(cls, level: list[Any]) -> BinanceDepthItem:
        """Create from array [price, quantity]."""
        return cls(price=str(level[0]), quantity=str(level[1]))


class BinanceOrderBook(BaseModel):
    """Raw Binance order book/depth response."""

    last_update_id: int = Field(..., alias="lastUpdateId", description="Last update ID")
    bids: list[list[str]] = Field(default_factory=list, description="Bids [[price, qty], ...]")
    asks: list[list[str]] = Field(default_factory=list, description="Asks [[price, qty], ...]")

    model_config = {"populate_by_name": True}


class BinanceFundingRate(BaseModel):
    """Raw Binance funding rate response item."""

    symbol: str = Field(..., description="Symbol")
    funding_time: int = Field(..., alias="fundingTime", description="Funding time in milliseconds")
    funding_rate: str = Field(..., alias="fundingRate", description="Funding rate")
    mark_price: str | None = Field(None, alias="markPrice", description="Mark price")

    model_config = {"populate_by_name": True}


class BinanceOpenInterest(BaseModel):
    """Raw Binance open interest response (current)."""

    open_interest: str = Field(..., alias="openInterest", description="Open interest")
    symbol: str = Field(..., description="Symbol")
    time: int = Field(..., description="Time in milliseconds")

    model_config = {"populate_by_name": True}


class BinanceOpenInterestHist(BaseModel):
    """Raw Binance open interest historical response item."""

    symbol: str = Field(..., description="Symbol")
    sum_open_interest: str = Field(..., alias="sumOpenInterest", description="Sum open interest")
    sum_open_interest_value: str = Field(
        ...,
        alias="sumOpenInterestValue",
        description="Sum open interest value",
    )
    timestamp: int = Field(..., description="Timestamp in milliseconds")

    model_config = {"populate_by_name": True}


__all__ = [
    "BinanceDepthItem",
    "BinanceExchangeInfo",
    "BinanceFundingRate",
    "BinanceKline",
    "BinanceOpenInterest",
    "BinanceOpenInterestHist",
    "BinanceOrderBook",
    "BinanceSymbolFilter",
    "BinanceSymbolInfo",
    "BinanceTrade",
]
