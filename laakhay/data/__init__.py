"""Laakhay Data - Multi-exchange market data aggregation library."""

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
from .models import Candle, Symbol
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
    # Exceptions
    "DataError",
    "ProviderError",
    "RateLimitError",
    "InvalidSymbolError",
    "InvalidIntervalError",
    "ValidationError",
]
