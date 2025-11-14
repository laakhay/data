"""Provider registration and initialization.

This module provides utilities for registering providers with the global
ProviderRegistry and setting up feature handlers.
"""

from __future__ import annotations

from laakhay.data.core import (
    DataFeature,
    FeatureHandler,
    MarketType,
    ProviderRegistry,
    TransportKind,
    get_provider_registry,
)
from laakhay.data.providers.binance import BinanceProvider, BinanceURM
from laakhay.data.providers.bybit import BybitProvider
from laakhay.data.providers.bybit.urm import BybitURM


def register_binance(registry: ProviderRegistry | None = None) -> None:
    """Register Binance provider with the registry.

    Args:
        registry: Optional registry instance (defaults to global singleton)
    """
    if registry is None:
        registry = get_provider_registry()

    # Map feature handlers manually (decorators can be added later)
    feature_handlers = {
        # REST handlers
        (DataFeature.OHLCV, TransportKind.REST): FeatureHandler(
            method_name="get_candles",
            method=BinanceProvider.get_candles,
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
        ),
        (DataFeature.ORDER_BOOK, TransportKind.REST): FeatureHandler(
            method_name="get_order_book",
            method=BinanceProvider.get_order_book,
            feature=DataFeature.ORDER_BOOK,
            transport=TransportKind.REST,
        ),
        (DataFeature.TRADES, TransportKind.REST): FeatureHandler(
            method_name="get_recent_trades",
            method=BinanceProvider.get_recent_trades,
            feature=DataFeature.TRADES,
            transport=TransportKind.REST,
        ),
        (DataFeature.FUNDING_RATE, TransportKind.REST): FeatureHandler(
            method_name="get_funding_rate",
            method=BinanceProvider.get_funding_rate,
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.REST,
        ),
        (DataFeature.OPEN_INTEREST, TransportKind.REST): FeatureHandler(
            method_name="get_open_interest",
            method=BinanceProvider.get_open_interest,
            feature=DataFeature.OPEN_INTEREST,
            transport=TransportKind.REST,
        ),
        (DataFeature.SYMBOL_METADATA, TransportKind.REST): FeatureHandler(
            method_name="get_symbols",
            method=BinanceProvider.get_symbols,
            feature=DataFeature.SYMBOL_METADATA,
            transport=TransportKind.REST,
        ),
        # WebSocket handlers
        (DataFeature.OHLCV, TransportKind.WS): FeatureHandler(
            method_name="stream_ohlcv",
            method=BinanceProvider.stream_ohlcv,
            feature=DataFeature.OHLCV,
            transport=TransportKind.WS,
        ),
        (DataFeature.ORDER_BOOK, TransportKind.WS): FeatureHandler(
            method_name="stream_order_book",
            method=BinanceProvider.stream_order_book,
            feature=DataFeature.ORDER_BOOK,
            transport=TransportKind.WS,
        ),
        (DataFeature.TRADES, TransportKind.WS): FeatureHandler(
            method_name="stream_trades",
            method=BinanceProvider.stream_trades,
            feature=DataFeature.TRADES,
            transport=TransportKind.WS,
        ),
        (DataFeature.LIQUIDATIONS, TransportKind.WS): FeatureHandler(
            method_name="stream_liquidations",
            method=BinanceProvider.stream_liquidations,
            feature=DataFeature.LIQUIDATIONS,
            transport=TransportKind.WS,
        ),
        (DataFeature.OPEN_INTEREST, TransportKind.WS): FeatureHandler(
            method_name="stream_open_interest",
            method=BinanceProvider.stream_open_interest,
            feature=DataFeature.OPEN_INTEREST,
            transport=TransportKind.WS,
        ),
        (DataFeature.FUNDING_RATE, TransportKind.WS): FeatureHandler(
            method_name="stream_funding_rate",
            method=BinanceProvider.stream_funding_rate,
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.WS,
        ),
        (DataFeature.MARK_PRICE, TransportKind.WS): FeatureHandler(
            method_name="stream_mark_price",
            method=BinanceProvider.stream_mark_price,
            feature=DataFeature.MARK_PRICE,
            transport=TransportKind.WS,
        ),
    }

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

    # Map feature handlers manually
    feature_handlers = {
        # REST handlers
        (DataFeature.OHLCV, TransportKind.REST): FeatureHandler(
            method_name="get_candles",
            method=BybitProvider.get_candles,
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
        ),
        (DataFeature.ORDER_BOOK, TransportKind.REST): FeatureHandler(
            method_name="get_order_book",
            method=BybitProvider.get_order_book,
            feature=DataFeature.ORDER_BOOK,
            transport=TransportKind.REST,
        ),
        (DataFeature.TRADES, TransportKind.REST): FeatureHandler(
            method_name="get_recent_trades",
            method=BybitProvider.get_recent_trades,
            feature=DataFeature.TRADES,
            transport=TransportKind.REST,
        ),
        (DataFeature.FUNDING_RATE, TransportKind.REST): FeatureHandler(
            method_name="get_funding_rate",
            method=BybitProvider.get_funding_rate,
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.REST,
        ),
        (DataFeature.OPEN_INTEREST, TransportKind.REST): FeatureHandler(
            method_name="get_open_interest",
            method=BybitProvider.get_open_interest,
            feature=DataFeature.OPEN_INTEREST,
            transport=TransportKind.REST,
        ),
        (DataFeature.SYMBOL_METADATA, TransportKind.REST): FeatureHandler(
            method_name="get_symbols",
            method=BybitProvider.get_symbols,
            feature=DataFeature.SYMBOL_METADATA,
            transport=TransportKind.REST,
        ),
        # WebSocket handlers
        (DataFeature.OHLCV, TransportKind.WS): FeatureHandler(
            method_name="stream_ohlcv",
            method=BybitProvider.stream_ohlcv,
            feature=DataFeature.OHLCV,
            transport=TransportKind.WS,
        ),
        (DataFeature.ORDER_BOOK, TransportKind.WS): FeatureHandler(
            method_name="stream_order_book",
            method=BybitProvider.stream_order_book,
            feature=DataFeature.ORDER_BOOK,
            transport=TransportKind.WS,
        ),
        (DataFeature.TRADES, TransportKind.WS): FeatureHandler(
            method_name="stream_trades",
            method=BybitProvider.stream_trades,
            feature=DataFeature.TRADES,
            transport=TransportKind.WS,
        ),
        (DataFeature.LIQUIDATIONS, TransportKind.WS): FeatureHandler(
            method_name="stream_liquidations",
            method=BybitProvider.stream_liquidations,
            feature=DataFeature.LIQUIDATIONS,
            transport=TransportKind.WS,
        ),
        (DataFeature.OPEN_INTEREST, TransportKind.WS): FeatureHandler(
            method_name="stream_open_interest",
            method=BybitProvider.stream_open_interest,
            feature=DataFeature.OPEN_INTEREST,
            transport=TransportKind.WS,
        ),
        (DataFeature.FUNDING_RATE, TransportKind.WS): FeatureHandler(
            method_name="stream_funding_rate",
            method=BybitProvider.stream_funding_rate,
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.WS,
        ),
        (DataFeature.MARK_PRICE, TransportKind.WS): FeatureHandler(
            method_name="stream_mark_price",
            method=BybitProvider.stream_mark_price,
            feature=DataFeature.MARK_PRICE,
            transport=TransportKind.WS,
        ),
    }

    registry.register(
        "bybit",
        BybitProvider,
        market_types=[MarketType.SPOT, MarketType.FUTURES],
        urm_mapper=BybitURM(),
        feature_handlers=feature_handlers,
    )


def register_all(registry: ProviderRegistry | None = None) -> None:
    """Register all available providers.

    Args:
        registry: Optional registry instance (defaults to global singleton)
    """
    register_binance(registry)
    register_bybit(registry)
