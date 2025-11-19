"""Data models for market data types.

Architecture:
    This module exports all Pydantic v2 data models used throughout the library.
    All models are immutable (frozen=True) to ensure data integrity and prevent
    accidental modification during processing.

Design Decisions:
    - Pydantic v2: Type validation, serialization, and immutable models
    - Frozen models: Immutability prevents accidental data corruption
    - Decimal for prices: Precision for financial calculations
    - Computed properties: Derived metrics (spreads, imbalances, etc.)

Model Categories:
    - Market Data: Bar, OHLCV, OrderBook, Trade
    - Derivatives: Liquidation, OpenInterest, FundingRate, MarkPrice
    - Metadata: Symbol, SeriesMeta
    - Events: DataEvent, ConnectionEvent
    - Streaming: StreamingBar

See Also:
    - Pydantic documentation: https://docs.pydantic.dev/
    - Core enums: InstrumentSpec, Timeframe, MarketType
"""

from .bar import Bar
from .events import ConnectionEvent, ConnectionStatus, DataEvent, DataEventType
from .funding_rate import FundingRate
from .liquidation import Liquidation
from .mark_price import MarkPrice
from .ohlcv import OHLCV
from .open_interest import OpenInterest
from .order_book import OrderBook
from .series_meta import SeriesMeta
from .streaming_bar import StreamingBar
from .symbol import Symbol
from .trade import Trade

__all__ = [
    "Bar",
    "ConnectionEvent",
    "ConnectionStatus",
    "DataEvent",
    "DataEventType",
    "FundingRate",
    "Liquidation",
    "MarkPrice",
    "OHLCV",
    "OpenInterest",
    "OrderBook",
    "SeriesMeta",
    "StreamingBar",
    "Symbol",
    "Trade",
]
