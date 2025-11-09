"""Laakhay Data - Multi-exchange market data aggregation library."""

from .clients.ohlcv_feed import OHLCVFeed
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
    BinanceProvider,
    BinanceRESTProvider,
    BinanceWSProvider,
)
from .providers.bybit import (
    BybitProvider,
    BybitRESTProvider,
    BybitWSProvider,
)
from .providers.okx import (
    OKXProvider,
    OKXRESTProvider,
    OKXWSProvider,
)

__version__ = "0.1.0"

__all__ = [
    # Core enums
    "Timeframe",
    "MarketType",
    # Providers
    "BaseProvider",
    "BinanceProvider",
    "BinanceRESTProvider",
    "BinanceWSProvider",
    "BybitProvider",
    "BybitRESTProvider",
    "BybitWSProvider",
    "OKXProvider",
    "OKXRESTProvider",
    "OKXWSProvider",
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
    "OHLCVFeed",
    # Exceptions
    "DataError",
    "ProviderError",
    "RateLimitError",
    "InvalidSymbolError",
    "InvalidIntervalError",
    "ValidationError",
]
