"""Core components."""

from ..io import RESTProvider, WSProvider
from .base import BaseProvider
from .capabilities import (
    EXCHANGE_METADATA,
    get_all_capabilities,
    get_all_exchanges,
    get_all_supported_market_types,
    get_exchange_capability,
    get_supported_data_types,
    get_supported_market_types,
    get_supported_timeframes,
    is_exchange_supported,
    supports_data_type,
    supports_market_type,
)
from .enums import MarketType, Timeframe
from .exceptions import (
    DataError,
    InvalidIntervalError,
    InvalidSymbolError,
    ProviderError,
    RateLimitError,
    ValidationError,
)

__all__ = [
    "BaseProvider",
    "Timeframe",
    "MarketType",
    "DataError",
    "ProviderError",
    "RateLimitError",
    "InvalidSymbolError",
    "InvalidIntervalError",
    "ValidationError",
    "RESTProvider",
    "WSProvider",
    # Capabilities API
    "EXCHANGE_METADATA",
    "get_all_exchanges",
    "get_exchange_capability",
    "get_all_capabilities",
    "get_supported_market_types",
    "get_supported_timeframes",
    "get_supported_data_types",
    "get_all_supported_market_types",
    "is_exchange_supported",
    "supports_market_type",
    "supports_data_type",
]
