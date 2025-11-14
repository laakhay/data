"""Provider registration and initialization.

This module provides utilities for registering providers with the global
ProviderRegistry and setting up feature handlers.
"""

from __future__ import annotations

from laakhay.data.core import (
    MarketType,
    ProviderRegistry,
    collect_feature_handlers,
    get_provider_registry,
)

# Explicitly import and re-export all public classes from provider modules
from laakhay.data.providers.binance import (
    BinanceProvider,
    BinanceRESTProvider,
    BinanceURM,
    BinanceWSProvider,
)
from laakhay.data.providers.bybit import (
    BybitProvider,
    BybitRESTProvider,
    BybitWSProvider,
)
from laakhay.data.providers.bybit.urm import BybitURM
from laakhay.data.providers.coinbase import (
    CoinbaseProvider,
    CoinbaseRESTProvider,
    CoinbaseURM,
    CoinbaseWSProvider,
)
from laakhay.data.providers.hyperliquid import (
    HyperliquidProvider,
    HyperliquidRESTProvider,
    HyperliquidURM,
    HyperliquidWSProvider,
)
from laakhay.data.providers.kraken import (
    KrakenProvider,
    KrakenRESTProvider,
    KrakenURM,
    KrakenWSProvider,
)
from laakhay.data.providers.okx import (
    OKXURM,
    OKXProvider,
    OKXRESTProvider,
    OKXWSProvider,
)

# Explicit re-exports to satisfy ruff (these are exported via __all__)
__all__ = [
    # Binance
    "BinanceProvider",
    "BinanceRESTProvider",
    "BinanceURM",
    "BinanceWSProvider",
    # Bybit
    "BybitProvider",
    "BybitRESTProvider",
    "BybitURM",
    "BybitWSProvider",
    # Coinbase
    "CoinbaseProvider",
    "CoinbaseRESTProvider",
    "CoinbaseURM",
    "CoinbaseWSProvider",
    # Hyperliquid
    "HyperliquidProvider",
    "HyperliquidRESTProvider",
    "HyperliquidURM",
    "HyperliquidWSProvider",
    # Kraken
    "KrakenProvider",
    "KrakenRESTProvider",
    "KrakenURM",
    "KrakenWSProvider",
    # OKX
    "OKXProvider",
    "OKXRESTProvider",
    "OKXURM",
    "OKXWSProvider",
    # Registration functions
    "register_binance",
    "register_bybit",
    "register_coinbase",
    "register_hyperliquid",
    "register_kraken",
    "register_okx",
    "register_all",
]


def register_binance(registry: ProviderRegistry | None = None) -> None:
    """Register Binance provider with the registry.

    Args:
        registry: Optional registry instance (defaults to global singleton)
    """
    if registry is None:
        registry = get_provider_registry()

    # Collect feature handlers from decorators
    feature_handlers = collect_feature_handlers(BinanceProvider)  # noqa: F405

    registry.register(
        "binance",
        BinanceProvider,  # noqa: F405
        market_types=[MarketType.SPOT, MarketType.FUTURES],
        urm_mapper=BinanceURM(),  # noqa: F405
        feature_handlers=feature_handlers,
    )


def register_bybit(registry: ProviderRegistry | None = None) -> None:
    """Register Bybit provider with the registry.

    Args:
        registry: Optional registry instance (defaults to global singleton)
    """
    if registry is None:
        registry = get_provider_registry()

    # Collect feature handlers from decorators
    feature_handlers = collect_feature_handlers(BybitProvider)  # noqa: F405

    registry.register(
        "bybit",
        BybitProvider,  # noqa: F405
        market_types=[MarketType.SPOT, MarketType.FUTURES],
        urm_mapper=BybitURM(),  # noqa: F405
        feature_handlers=feature_handlers,
    )


def register_okx(registry: ProviderRegistry | None = None) -> None:
    """Register OKX provider with the registry.

    Args:
        registry: Optional registry instance (defaults to global singleton)
    """
    if registry is None:
        registry = get_provider_registry()

    # Collect feature handlers from decorators
    feature_handlers = collect_feature_handlers(OKXProvider)  # noqa: F405

    registry.register(
        "okx",
        OKXProvider,  # noqa: F405
        market_types=[MarketType.SPOT, MarketType.FUTURES],
        urm_mapper=OKXURM(),  # noqa: F405
        feature_handlers=feature_handlers,
    )


def register_kraken(registry: ProviderRegistry | None = None) -> None:
    """Register Kraken provider with the registry.

    Args:
        registry: Optional registry instance (defaults to global singleton)
    """
    if registry is None:
        registry = get_provider_registry()

    # Collect feature handlers from decorators
    feature_handlers = collect_feature_handlers(KrakenProvider)  # noqa: F405

    registry.register(
        "kraken",
        KrakenProvider,  # noqa: F405
        market_types=[MarketType.SPOT, MarketType.FUTURES],
        urm_mapper=KrakenURM(),  # noqa: F405
        feature_handlers=feature_handlers,
    )


def register_hyperliquid(registry: ProviderRegistry | None = None) -> None:
    """Register Hyperliquid provider with the registry.

    Args:
        registry: Optional registry instance (defaults to global singleton)
    """
    if registry is None:
        registry = get_provider_registry()

    # Collect feature handlers from decorators
    feature_handlers = collect_feature_handlers(HyperliquidProvider)  # noqa: F405

    registry.register(
        "hyperliquid",
        HyperliquidProvider,  # noqa: F405
        market_types=[MarketType.SPOT, MarketType.FUTURES],
        urm_mapper=HyperliquidURM(),  # noqa: F405
        feature_handlers=feature_handlers,
    )


def register_coinbase(registry: ProviderRegistry | None = None) -> None:
    """Register Coinbase provider with the registry.

    Note: Coinbase only supports Spot markets.

    Args:
        registry: Optional registry instance (defaults to global singleton)
    """
    if registry is None:
        registry = get_provider_registry()

    # Collect feature handlers from decorators
    feature_handlers = collect_feature_handlers(CoinbaseProvider)  # noqa: F405

    registry.register(
        "coinbase",
        CoinbaseProvider,  # noqa: F405
        market_types=[MarketType.SPOT],  # Coinbase only supports spot
        urm_mapper=CoinbaseURM(),  # noqa: F405
        feature_handlers=feature_handlers,
    )


def register_all(registry: ProviderRegistry | None = None) -> None:
    """Register all available providers.

    Args:
        registry: Optional registry instance (defaults to global singleton)
    """
    register_binance(registry)
    register_bybit(registry)
    register_okx(registry)
    register_kraken(registry)
    register_hyperliquid(registry)
    register_coinbase(registry)
