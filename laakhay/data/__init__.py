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

# All exchanges moved to connectors
from .connectors.binance import (
    BinanceProvider,
    BinanceRESTConnector,
    BinanceWSConnector,
)
from .connectors.bybit import (
    BybitProvider,
    BybitRESTConnector,
    BybitWSConnector,
)
from .connectors.coinbase import (
    CoinbaseProvider,
    CoinbaseRESTConnector,
    CoinbaseWSConnector,
)
from .connectors.hyperliquid import (
    HyperliquidProvider,
    HyperliquidRESTProvider,
    HyperliquidWSProvider,
)
from .connectors.kraken import (
    KrakenProvider,
    KrakenRESTConnector,
    KrakenWSConnector,
)
from .connectors.okx import (
    OKXProvider,
    OKXRESTConnector,
    OKXWSConnector,
)
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
    "BinanceRESTConnector",
    "BinanceWSConnector",
    "BybitProvider",
    "BybitRESTConnector",
    "BybitWSConnector",
    "CoinbaseProvider",
    "CoinbaseRESTConnector",
    "CoinbaseWSConnector",
    "HyperliquidProvider",
    "HyperliquidRESTProvider",
    "HyperliquidWSProvider",
    "KrakenProvider",
    "KrakenRESTConnector",
    "KrakenWSConnector",
    "OKXProvider",
    "OKXRESTConnector",
    "OKXWSConnector",
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
