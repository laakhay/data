"""Provider registration utilities.

This module provides utilities for registering providers with the global
ProviderRegistry. All exchanges are now in connectors/.
"""

from __future__ import annotations

from laakhay.data.connectors.binance import BinanceProvider
from laakhay.data.connectors.binance.urm import BinanceURM
from laakhay.data.connectors.bybit import BybitProvider
from laakhay.data.connectors.bybit.urm import BybitURM
from laakhay.data.connectors.coinbase import CoinbaseProvider
from laakhay.data.connectors.coinbase.urm import CoinbaseURM
from laakhay.data.connectors.hyperliquid import HyperliquidProvider
from laakhay.data.connectors.hyperliquid.urm import HyperliquidURM
from laakhay.data.connectors.kraken import KrakenProvider
from laakhay.data.connectors.kraken.urm import KrakenURM
from laakhay.data.connectors.okx import OKXProvider
from laakhay.data.connectors.okx.urm import OKXURM
from laakhay.data.core import MarketType
from laakhay.data.runtime.provider_registry import (
    ProviderRegistry,
    collect_feature_handlers,
    get_provider_registry,
)

__all__ = [
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

    feature_handlers = collect_feature_handlers(BinanceProvider)

    registry.register(
        "binance",
        BinanceProvider,
        market_types=[MarketType.SPOT, MarketType.FUTURES],
        urm_mapper=BinanceURM(),
        feature_handlers=feature_handlers,
    )


def register_bybit(registry: ProviderRegistry | None = None) -> None:
    """Register Bybit provider with the registry.

    Args:
        registry: Optional registry instance (defaults to global singleton)
    """
    if registry is None:
        registry = get_provider_registry()

    feature_handlers = collect_feature_handlers(BybitProvider)

    registry.register(
        "bybit",
        BybitProvider,
        market_types=[MarketType.SPOT, MarketType.FUTURES],
        urm_mapper=BybitURM(),
        feature_handlers=feature_handlers,
    )


def register_okx(registry: ProviderRegistry | None = None) -> None:
    """Register OKX provider with the registry.

    Args:
        registry: Optional registry instance (defaults to global singleton)
    """
    if registry is None:
        registry = get_provider_registry()

    feature_handlers = collect_feature_handlers(OKXProvider)

    registry.register(
        "okx",
        OKXProvider,
        market_types=[MarketType.SPOT, MarketType.FUTURES],
        urm_mapper=OKXURM(),
        feature_handlers=feature_handlers,
    )


def register_kraken(registry: ProviderRegistry | None = None) -> None:
    """Register Kraken provider with the registry.

    Args:
        registry: Optional registry instance (defaults to global singleton)
    """
    if registry is None:
        registry = get_provider_registry()

    feature_handlers = collect_feature_handlers(KrakenProvider)

    registry.register(
        "kraken",
        KrakenProvider,
        market_types=[MarketType.SPOT, MarketType.FUTURES],
        urm_mapper=KrakenURM(),
        feature_handlers=feature_handlers,
    )


def register_hyperliquid(registry: ProviderRegistry | None = None) -> None:
    """Register Hyperliquid provider with the registry.

    Args:
        registry: Optional registry instance (defaults to global singleton)
    """
    if registry is None:
        registry = get_provider_registry()

    feature_handlers = collect_feature_handlers(HyperliquidProvider)

    registry.register(
        "hyperliquid",
        HyperliquidProvider,
        market_types=[MarketType.SPOT, MarketType.FUTURES],
        urm_mapper=HyperliquidURM(),
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

    feature_handlers = collect_feature_handlers(CoinbaseProvider)

    registry.register(
        "coinbase",
        CoinbaseProvider,
        market_types=[MarketType.SPOT],  # Coinbase only supports spot
        urm_mapper=CoinbaseURM(),
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
