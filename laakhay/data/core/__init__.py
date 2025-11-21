"""Core components."""

from typing import Any

from ..io import RESTProvider, WSProvider
from .base import BaseProvider
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

_CAPABILITY_EXPORTS = {
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
}

_PROVIDER_REGISTRY_EXPORTS = {
    "ProviderRegistry",
    "FeatureHandler",
    "get_provider_registry",
    "register_feature_handler",
    "collect_feature_handlers",
}

_RUNTIME_EXPORTS = {"DataRouter"}
_API_EXPORTS = {"DataAPI"}


def __getattr__(name: str) -> Any:
    if name in _CAPABILITY_EXPORTS:
        from .. import capability as _capability

        value = getattr(_capability, name)
    elif name in _PROVIDER_REGISTRY_EXPORTS:
        from ..runtime import provider_registry as _provider_registry

        value = getattr(_provider_registry, name)
    elif name in _RUNTIME_EXPORTS:
        from ..runtime import router as _runtime_router

        value = getattr(_runtime_router, name)
    elif name in _API_EXPORTS:
        from .. import api as _api

        value = getattr(_api, name)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    globals()[name] = value
    return value


def __dir__() -> list[str]:
    dynamic = _CAPABILITY_EXPORTS | _PROVIDER_REGISTRY_EXPORTS | _RUNTIME_EXPORTS | _API_EXPORTS
    return sorted(set(globals().keys()) | dynamic)
