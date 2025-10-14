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
    TimeInterval,
    ValidationError,
)
from .models import (
    Candle,
    ConnectionEvent,
    ConnectionStatus,
    DataEvent,
    DataEventType,
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
    "TimeInterval",
    "MarketType",
    # Providers
    "BaseProvider",
    "BinanceProvider",
    "BinanceFuturesProvider",
    "BinanceSpotProvider",
    # Models
    "Candle",
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
