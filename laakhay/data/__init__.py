"""Laakhay Data - Multi-exchange market data aggregation library."""

from .capability import (
    CapabilityKey,
    CapabilityService,
    CapabilityStatus,
    FallbackOption,
    describe_exchange,
    get_all_capabilities,
    get_all_exchanges,
    get_all_supported_market_types,
    get_exchange_capability,
    get_supported_data_types,
    get_supported_market_types,
    get_supported_timeframes,
    is_exchange_supported,
    list_features,
    supports,
    supports_data_type,
    supports_market_type,
)
from .clients.ohlcv_feed import OHLCVFeed
from .core import (
    BaseProvider,
    CapabilityError,
    DataError,
    DataFeature,
    InstrumentSpec,
    InstrumentType,
    InvalidIntervalError,
    InvalidSymbolError,
    MarketType,
    ProviderError,
    RateLimitError,
    Timeframe,
    TransportKind,
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
from .providers.coinbase import (
    CoinbaseProvider,
    CoinbaseRESTProvider,
    CoinbaseWSProvider,
)
from .providers.hyperliquid import (
    HyperliquidProvider,
    HyperliquidRESTProvider,
    HyperliquidWSProvider,
)
from .providers.kraken import (
    KrakenURM,
)

# Note: KrakenProvider, KrakenRESTProvider, KrakenWSProvider will be available
# once the connector implementation is complete
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
    "DataFeature",
    "TransportKind",
    "InstrumentType",
    "InstrumentSpec",
    # Providers
    "BaseProvider",
    "BinanceProvider",
    "BinanceRESTProvider",
    "BinanceWSProvider",
    "BybitProvider",
    "BybitRESTProvider",
    "BybitWSProvider",
    "CoinbaseProvider",
    "CoinbaseRESTProvider",
    "CoinbaseWSProvider",
    "HyperliquidProvider",
    "HyperliquidRESTProvider",
    "HyperliquidWSProvider",
    "KrakenURM",
    # Note: KrakenProvider, KrakenRESTProvider, KrakenWSProvider will be available
    # once the connector implementation is complete
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
    "CapabilityError",
    "CapabilityService",
    # Capabilities API
    "CapabilityKey",
    "CapabilityStatus",
    "FallbackOption",
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
    "supports",
    "describe_exchange",
    "list_features",
]
