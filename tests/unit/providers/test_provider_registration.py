"""Tests for provider registration."""

import pytest

from laakhay.data.core import (
    DataFeature,
    MarketType,
    ProviderRegistry,
    TransportKind,
    get_provider_registry,
)
from laakhay.data.providers import register_binance, register_bybit


@pytest.mark.asyncio
async def test_register_binance():
    """Test registering Binance provider."""
    registry = get_provider_registry()

    register_binance(registry)

    assert registry.is_registered("binance")
    assert "binance" in registry.list_exchanges()

    # Check URM mapper
    urm = registry.get_urm_mapper("binance")
    assert urm is not None

    # Check feature handlers
    ohlcv_rest = registry.get_feature_handler("binance", DataFeature.OHLCV, TransportKind.REST)
    assert ohlcv_rest is not None
    assert ohlcv_rest.method_name == "get_candles"

    ohlcv_ws = registry.get_feature_handler("binance", DataFeature.OHLCV, TransportKind.WS)
    assert ohlcv_ws is not None
    assert ohlcv_ws.method_name == "stream_ohlcv"

    liquidations_ws = registry.get_feature_handler(
        "binance", DataFeature.LIQUIDATIONS, TransportKind.WS
    )
    assert liquidations_ws is not None
    assert liquidations_ws.method_name == "stream_liquidations"


@pytest.mark.asyncio
async def test_register_bybit():
    """Test registering Bybit provider."""
    registry = get_provider_registry()

    register_bybit(registry)

    assert registry.is_registered("bybit")
    assert "bybit" in registry.list_exchanges()

    # Check URM mapper
    urm = registry.get_urm_mapper("bybit")
    assert urm is not None

    # Check feature handlers
    ohlcv_rest = registry.get_feature_handler("bybit", DataFeature.OHLCV, TransportKind.REST)
    assert ohlcv_rest is not None
    assert ohlcv_rest.method_name == "get_candles"

    mark_price_ws = registry.get_feature_handler("bybit", DataFeature.MARK_PRICE, TransportKind.WS)
    assert mark_price_ws is not None
    assert mark_price_ws.method_name == "stream_mark_price"


@pytest.mark.asyncio
async def test_get_provider_binance():
    """Test getting Binance provider instance."""
    registry = ProviderRegistry()

    register_binance(registry)

    # Test spot provider
    spot_provider = await registry.get_provider("binance", MarketType.SPOT)
    assert spot_provider.name == "binance"
    assert spot_provider.market_type == MarketType.SPOT

    # Test futures provider
    futures_provider = await registry.get_provider("binance", MarketType.FUTURES)
    assert futures_provider.name == "binance"
    assert futures_provider.market_type == MarketType.FUTURES

    # Should be different instances
    assert spot_provider is not futures_provider


@pytest.mark.asyncio
async def test_get_provider_bybit():
    """Test getting Bybit provider instance."""
    registry = ProviderRegistry()

    register_bybit(registry)

    # Test spot provider
    spot_provider = await registry.get_provider("bybit", MarketType.SPOT)
    assert spot_provider.name == "bybit"
    assert spot_provider.market_type == MarketType.SPOT

    # Test futures provider
    futures_provider = await registry.get_provider("bybit", MarketType.FUTURES)
    assert futures_provider.name == "bybit"
    assert futures_provider.market_type == MarketType.FUTURES


@pytest.mark.asyncio
async def test_provider_pooling():
    """Test that provider instances are pooled correctly."""
    registry = ProviderRegistry()

    register_binance(registry)
    register_bybit(registry)

    # Get providers
    binance_spot1 = await registry.get_provider("binance", MarketType.SPOT)
    binance_spot2 = await registry.get_provider("binance", MarketType.SPOT)
    bybit_spot = await registry.get_provider("bybit", MarketType.SPOT)

    # Same exchange + market_type should return same instance
    assert binance_spot1 is binance_spot2

    # Different exchanges should return different instances
    assert binance_spot1 is not bybit_spot


@pytest.mark.asyncio
async def test_feature_handler_mapping():
    """Test that feature handlers are correctly mapped."""
    registry = ProviderRegistry()

    register_binance(registry)
    register_bybit(registry)

    # Test REST handlers
    binance_ohlcv_rest = registry.get_feature_handler("binance", DataFeature.OHLCV, TransportKind.REST)
    bybit_ohlcv_rest = registry.get_feature_handler("bybit", DataFeature.OHLCV, TransportKind.REST)

    assert binance_ohlcv_rest is not None
    assert bybit_ohlcv_rest is not None
    # Both should map to get_candles
    assert binance_ohlcv_rest.method_name == "get_candles"
    assert bybit_ohlcv_rest.method_name == "get_candles"

    # Test WS handlers
    binance_trades_ws = registry.get_feature_handler("binance", DataFeature.TRADES, TransportKind.WS)
    bybit_trades_ws = registry.get_feature_handler("bybit", DataFeature.TRADES, TransportKind.WS)

    assert binance_trades_ws is not None
    assert bybit_trades_ws is not None
    # Both should map to stream_trades
    assert binance_trades_ws.method_name == "stream_trades"
    assert bybit_trades_ws.method_name == "stream_trades"

