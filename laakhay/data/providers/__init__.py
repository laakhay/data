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
from laakhay.data.providers.binance import (
    BinanceProvider,
    BinanceRESTProvider,
    BinanceURM,
    BinanceWSProvider,
)
from laakhay.data.providers.bybit import BybitProvider
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
from laakhay.data.providers.okx import OKXProvider, OKXRESTProvider, OKXURM, OKXWSProvider


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


def register_okx(registry: ProviderRegistry | None = None) -> None:
    """Register OKX provider with the registry.

    Args:
        registry: Optional registry instance (defaults to global singleton)
    """
    if registry is None:
        registry = get_provider_registry()

    feature_handlers = {
        # REST handlers
        (DataFeature.OHLCV, TransportKind.REST): FeatureHandler(
            method_name="get_candles",
            method=OKXProvider.get_candles,
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
        ),
        (DataFeature.ORDER_BOOK, TransportKind.REST): FeatureHandler(
            method_name="get_order_book",
            method=OKXProvider.get_order_book,
            feature=DataFeature.ORDER_BOOK,
            transport=TransportKind.REST,
        ),
        (DataFeature.TRADES, TransportKind.REST): FeatureHandler(
            method_name="get_recent_trades",
            method=OKXProvider.get_recent_trades,
            feature=DataFeature.TRADES,
            transport=TransportKind.REST,
        ),
        (DataFeature.FUNDING_RATE, TransportKind.REST): FeatureHandler(
            method_name="get_funding_rate",
            method=OKXProvider.get_funding_rate,
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.REST,
        ),
        (DataFeature.OPEN_INTEREST, TransportKind.REST): FeatureHandler(
            method_name="get_open_interest",
            method=OKXProvider.get_open_interest,
            feature=DataFeature.OPEN_INTEREST,
            transport=TransportKind.REST,
        ),
        (DataFeature.SYMBOL_METADATA, TransportKind.REST): FeatureHandler(
            method_name="get_symbols",
            method=OKXProvider.get_symbols,
            feature=DataFeature.SYMBOL_METADATA,
            transport=TransportKind.REST,
        ),
        # WebSocket handlers
        (DataFeature.OHLCV, TransportKind.WS): FeatureHandler(
            method_name="stream_ohlcv",
            method=OKXProvider.stream_ohlcv,
            feature=DataFeature.OHLCV,
            transport=TransportKind.WS,
        ),
        (DataFeature.ORDER_BOOK, TransportKind.WS): FeatureHandler(
            method_name="stream_order_book",
            method=OKXProvider.stream_order_book,
            feature=DataFeature.ORDER_BOOK,
            transport=TransportKind.WS,
        ),
        (DataFeature.TRADES, TransportKind.WS): FeatureHandler(
            method_name="stream_trades",
            method=OKXProvider.stream_trades,
            feature=DataFeature.TRADES,
            transport=TransportKind.WS,
        ),
        (DataFeature.LIQUIDATIONS, TransportKind.WS): FeatureHandler(
            method_name="stream_liquidations",
            method=OKXProvider.stream_liquidations,
            feature=DataFeature.LIQUIDATIONS,
            transport=TransportKind.WS,
        ),
        (DataFeature.OPEN_INTEREST, TransportKind.WS): FeatureHandler(
            method_name="stream_open_interest",
            method=OKXProvider.stream_open_interest,
            feature=DataFeature.OPEN_INTEREST,
            transport=TransportKind.WS,
        ),
        (DataFeature.FUNDING_RATE, TransportKind.WS): FeatureHandler(
            method_name="stream_funding_rate",
            method=OKXProvider.stream_funding_rate,
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.WS,
        ),
        (DataFeature.MARK_PRICE, TransportKind.WS): FeatureHandler(
            method_name="stream_mark_price",
            method=OKXProvider.stream_mark_price,
            feature=DataFeature.MARK_PRICE,
            transport=TransportKind.WS,
        ),
    }

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

    feature_handlers = {
        # REST handlers
        (DataFeature.OHLCV, TransportKind.REST): FeatureHandler(
            method_name="get_candles",
            method=KrakenProvider.get_candles,
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
        ),
        (DataFeature.ORDER_BOOK, TransportKind.REST): FeatureHandler(
            method_name="get_order_book",
            method=KrakenProvider.get_order_book,
            feature=DataFeature.ORDER_BOOK,
            transport=TransportKind.REST,
        ),
        (DataFeature.TRADES, TransportKind.REST): FeatureHandler(
            method_name="get_recent_trades",
            method=KrakenProvider.get_recent_trades,
            feature=DataFeature.TRADES,
            transport=TransportKind.REST,
        ),
        (DataFeature.FUNDING_RATE, TransportKind.REST): FeatureHandler(
            method_name="get_funding_rate",
            method=KrakenProvider.get_funding_rate,
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.REST,
        ),
        (DataFeature.OPEN_INTEREST, TransportKind.REST): FeatureHandler(
            method_name="get_open_interest",
            method=KrakenProvider.get_open_interest,
            feature=DataFeature.OPEN_INTEREST,
            transport=TransportKind.REST,
        ),
        (DataFeature.SYMBOL_METADATA, TransportKind.REST): FeatureHandler(
            method_name="get_symbols",
            method=KrakenProvider.get_symbols,
            feature=DataFeature.SYMBOL_METADATA,
            transport=TransportKind.REST,
        ),
        # WebSocket handlers
        (DataFeature.OHLCV, TransportKind.WS): FeatureHandler(
            method_name="stream_ohlcv",
            method=KrakenProvider.stream_ohlcv,
            feature=DataFeature.OHLCV,
            transport=TransportKind.WS,
        ),
        (DataFeature.ORDER_BOOK, TransportKind.WS): FeatureHandler(
            method_name="stream_order_book",
            method=KrakenProvider.stream_order_book,
            feature=DataFeature.ORDER_BOOK,
            transport=TransportKind.WS,
        ),
        (DataFeature.TRADES, TransportKind.WS): FeatureHandler(
            method_name="stream_trades",
            method=KrakenProvider.stream_trades,
            feature=DataFeature.TRADES,
            transport=TransportKind.WS,
        ),
        (DataFeature.LIQUIDATIONS, TransportKind.WS): FeatureHandler(
            method_name="stream_liquidations",
            method=KrakenProvider.stream_liquidations,
            feature=DataFeature.LIQUIDATIONS,
            transport=TransportKind.WS,
        ),
        (DataFeature.OPEN_INTEREST, TransportKind.WS): FeatureHandler(
            method_name="stream_open_interest",
            method=KrakenProvider.stream_open_interest,
            feature=DataFeature.OPEN_INTEREST,
            transport=TransportKind.WS,
        ),
        (DataFeature.FUNDING_RATE, TransportKind.WS): FeatureHandler(
            method_name="stream_funding_rate",
            method=KrakenProvider.stream_funding_rate,
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.WS,
        ),
        (DataFeature.MARK_PRICE, TransportKind.WS): FeatureHandler(
            method_name="stream_mark_price",
            method=KrakenProvider.stream_mark_price,
            feature=DataFeature.MARK_PRICE,
            transport=TransportKind.WS,
        ),
    }

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

    feature_handlers = {
        # REST handlers
        (DataFeature.OHLCV, TransportKind.REST): FeatureHandler(
            method_name="get_candles",
            method=HyperliquidProvider.get_candles,
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
        ),
        (DataFeature.ORDER_BOOK, TransportKind.REST): FeatureHandler(
            method_name="get_order_book",
            method=HyperliquidProvider.get_order_book,
            feature=DataFeature.ORDER_BOOK,
            transport=TransportKind.REST,
        ),
        (DataFeature.TRADES, TransportKind.REST): FeatureHandler(
            method_name="get_recent_trades",
            method=HyperliquidProvider.get_recent_trades,
            feature=DataFeature.TRADES,
            transport=TransportKind.REST,
        ),
        (DataFeature.FUNDING_RATE, TransportKind.REST): FeatureHandler(
            method_name="get_funding_rate",
            method=HyperliquidProvider.get_funding_rate,
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.REST,
        ),
        (DataFeature.OPEN_INTEREST, TransportKind.REST): FeatureHandler(
            method_name="get_open_interest",
            method=HyperliquidProvider.get_open_interest,
            feature=DataFeature.OPEN_INTEREST,
            transport=TransportKind.REST,
        ),
        (DataFeature.SYMBOL_METADATA, TransportKind.REST): FeatureHandler(
            method_name="get_symbols",
            method=HyperliquidProvider.get_symbols,
            feature=DataFeature.SYMBOL_METADATA,
            transport=TransportKind.REST,
        ),
        # WebSocket handlers
        (DataFeature.OHLCV, TransportKind.WS): FeatureHandler(
            method_name="stream_ohlcv",
            method=HyperliquidProvider.stream_ohlcv,
            feature=DataFeature.OHLCV,
            transport=TransportKind.WS,
        ),
        (DataFeature.ORDER_BOOK, TransportKind.WS): FeatureHandler(
            method_name="stream_order_book",
            method=HyperliquidProvider.stream_order_book,
            feature=DataFeature.ORDER_BOOK,
            transport=TransportKind.WS,
        ),
        (DataFeature.TRADES, TransportKind.WS): FeatureHandler(
            method_name="stream_trades",
            method=HyperliquidProvider.stream_trades,
            feature=DataFeature.TRADES,
            transport=TransportKind.WS,
        ),
        (DataFeature.LIQUIDATIONS, TransportKind.WS): FeatureHandler(
            method_name="stream_liquidations",
            method=HyperliquidProvider.stream_liquidations,
            feature=DataFeature.LIQUIDATIONS,
            transport=TransportKind.WS,
        ),
        (DataFeature.OPEN_INTEREST, TransportKind.WS): FeatureHandler(
            method_name="stream_open_interest",
            method=HyperliquidProvider.stream_open_interest,
            feature=DataFeature.OPEN_INTEREST,
            transport=TransportKind.WS,
        ),
        (DataFeature.FUNDING_RATE, TransportKind.WS): FeatureHandler(
            method_name="stream_funding_rate",
            method=HyperliquidProvider.stream_funding_rate,
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.WS,
        ),
        (DataFeature.MARK_PRICE, TransportKind.WS): FeatureHandler(
            method_name="stream_mark_price",
            method=HyperliquidProvider.stream_mark_price,
            feature=DataFeature.MARK_PRICE,
            transport=TransportKind.WS,
        ),
    }

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

    feature_handlers = {
        # REST handlers
        (DataFeature.OHLCV, TransportKind.REST): FeatureHandler(
            method_name="get_candles",
            method=CoinbaseProvider.get_candles,
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
        ),
        (DataFeature.ORDER_BOOK, TransportKind.REST): FeatureHandler(
            method_name="get_order_book",
            method=CoinbaseProvider.get_order_book,
            feature=DataFeature.ORDER_BOOK,
            transport=TransportKind.REST,
        ),
        (DataFeature.TRADES, TransportKind.REST): FeatureHandler(
            method_name="get_recent_trades",
            method=CoinbaseProvider.get_recent_trades,
            feature=DataFeature.TRADES,
            transport=TransportKind.REST,
        ),
        (DataFeature.SYMBOL_METADATA, TransportKind.REST): FeatureHandler(
            method_name="get_symbols",
            method=CoinbaseProvider.get_symbols,
            feature=DataFeature.SYMBOL_METADATA,
            transport=TransportKind.REST,
        ),
        # WebSocket handlers
        (DataFeature.OHLCV, TransportKind.WS): FeatureHandler(
            method_name="stream_ohlcv",
            method=CoinbaseProvider.stream_ohlcv,
            feature=DataFeature.OHLCV,
            transport=TransportKind.WS,
        ),
        (DataFeature.ORDER_BOOK, TransportKind.WS): FeatureHandler(
            method_name="stream_order_book",
            method=CoinbaseProvider.stream_order_book,
            feature=DataFeature.ORDER_BOOK,
            transport=TransportKind.WS,
        ),
        (DataFeature.TRADES, TransportKind.WS): FeatureHandler(
            method_name="stream_trades",
            method=CoinbaseProvider.stream_trades,
            feature=DataFeature.TRADES,
            transport=TransportKind.WS,
        ),
        (DataFeature.OPEN_INTEREST, TransportKind.WS): FeatureHandler(
            method_name="stream_open_interest",
            method=CoinbaseProvider.stream_open_interest,
            feature=DataFeature.OPEN_INTEREST,
            transport=TransportKind.WS,
        ),
        (DataFeature.FUNDING_RATE, TransportKind.WS): FeatureHandler(
            method_name="stream_funding_rate",
            method=CoinbaseProvider.stream_funding_rate,
            feature=DataFeature.FUNDING_RATE,
            transport=TransportKind.WS,
        ),
        (DataFeature.MARK_PRICE, TransportKind.WS): FeatureHandler(
            method_name="stream_mark_price",
            method=CoinbaseProvider.stream_mark_price,
            feature=DataFeature.MARK_PRICE,
            transport=TransportKind.WS,
        ),
        (DataFeature.LIQUIDATIONS, TransportKind.WS): FeatureHandler(
            method_name="stream_liquidations",
            method=CoinbaseProvider.stream_liquidations,
            feature=DataFeature.LIQUIDATIONS,
            transport=TransportKind.WS,
        ),
    }

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
