"""Core components."""

from ..io import RESTProvider, WSProvider
from .api import DataAPI
from .base import BaseProvider
from .capabilities import (
    EXCHANGE_METADATA,
    CapabilityKey,
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
from .enums import (
    DataFeature,
    InstrumentSpec,
    InstrumentType,
    MarketType,
    Timeframe,
    TransportKind,
)
from .exceptions import (
    CapabilityError,
    DataError,
    InvalidIntervalError,
    InvalidSymbolError,
    ProviderError,
    RateLimitError,
    SymbolResolutionError,
    ValidationError,
)
from .registry import (
    FeatureHandler,
    ProviderRegistry,
    collect_feature_handlers,
    get_provider_registry,
    register_feature_handler,
)
from .router import DataRouter
from .urm import (
    UniversalRepresentationMapper,
    URMRegistry,
    get_urm_registry,
    parse_urm_id,
    spec_to_urm_id,
    validate_urm_id,
)

__all__ = [
    "BaseProvider",
    "Timeframe",
    "MarketType",
    "DataFeature",
    "TransportKind",
    "InstrumentType",
    "InstrumentSpec",
    "DataError",
    "ProviderError",
    "RateLimitError",
    "InvalidSymbolError",
    "InvalidIntervalError",
    "ValidationError",
    "CapabilityError",
    "SymbolResolutionError",
    "RESTProvider",
    "WSProvider",
    # URM API
    "UniversalRepresentationMapper",
    "URMRegistry",
    "get_urm_registry",
    "parse_urm_id",
    "spec_to_urm_id",
    "validate_urm_id",
    # Capabilities API
    "EXCHANGE_METADATA",
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
    # Provider Registry API
    "ProviderRegistry",
    "FeatureHandler",
    "get_provider_registry",
    "register_feature_handler",
    "collect_feature_handlers",
    # DataRouter & DataAPI
    "DataRouter",
    "DataAPI",
]
