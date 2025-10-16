"""Laakhay Data - Multi-exchange market data aggregation library."""

from .clients.data_feed import DataFeed
from .core import (
    BaseProvider,
    DataError,
    InvalidIntervalError,
    InvalidSymbolError,
    MarketType,
    ProviderError,
    RateLimitError,
    Timeframe,
    ValidationError,
)
from .models import (
    OHLCV,
    Bar,
    ConnectionEvent,
    ConnectionStatus,
    DataEvent,
    DataEventType,
    SeriesMeta,
    StreamingBar,
    Symbol,
)
from .providers.binance import (
    BinanceFuturesProvider,
    BinanceProvider,
    BinanceSpotProvider,
)

__version__ = "0.1.0"

__all__ = [
    # Core enums
    "Timeframe",
    "MarketType",
    # Providers
    "BaseProvider",
    "BinanceProvider",
    "BinanceFuturesProvider",
    "BinanceSpotProvider",
    # Models
    "Bar",
    "OHLCV",
    "SeriesMeta",
    "StreamingBar",
    "Symbol",
    "ConnectionEvent",
    "ConnectionStatus",
    "DataEvent",
    "DataEventType",
    # Clients
    "DataFeed",
    # Exceptions
    "DataError",
    "ProviderError",
    "RateLimitError",
    "InvalidSymbolError",
    "InvalidIntervalError",
    "ValidationError",
]
