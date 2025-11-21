"""Tests for provider registration."""

import pytest

from laakhay.data.core import DataFeature, MarketType, TransportKind
from laakhay.data.providers import (
    register_all,
    register_binance,
    register_bybit,
    register_coinbase,
    register_hyperliquid,
    register_kraken,
)
from laakhay.data.runtime.provider_registry import ProviderRegistry


@pytest.mark.asyncio
async def test_register_binance():
    """Test registering Binance provider."""
    registry = ProviderRegistry()  # Use fresh instance to avoid conflicts

    register_binance(registry)

    assert registry.is_registered("binance")
    assert "binance" in registry.list_exchanges()

    # Check URM mapper
    urm = registry.get_urm_mapper("binance")
    assert urm is not None

    # Check feature handlers
    ohlcv_rest = registry.get_feature_handler("binance", DataFeature.OHLCV, TransportKind.REST)
    assert ohlcv_rest is not None
    assert ohlcv_rest.method_name == "fetch_ohlcv"

    hist_rest = registry.get_feature_handler(
        "binance", DataFeature.HISTORICAL_TRADES, TransportKind.REST
    )
    assert hist_rest is not None
    assert hist_rest.method_name == "fetch_historical_trades"

    health_rest = registry.get_feature_handler("binance", DataFeature.HEALTH, TransportKind.REST)
    assert health_rest is not None
    assert health_rest.method_name == "fetch_health"

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
    registry = ProviderRegistry()  # Use fresh instance to avoid conflicts

    register_bybit(registry)

    assert registry.is_registered("bybit")
    assert "bybit" in registry.list_exchanges()

    # Check URM mapper
    urm = registry.get_urm_mapper("bybit")
    assert urm is not None

    # Check feature handlers
    ohlcv_rest = registry.get_feature_handler("bybit", DataFeature.OHLCV, TransportKind.REST)
    assert ohlcv_rest is not None
    assert ohlcv_rest.method_name == "fetch_ohlcv"

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
    binance_ohlcv_rest = registry.get_feature_handler(
        "binance", DataFeature.OHLCV, TransportKind.REST
    )
    bybit_ohlcv_rest = registry.get_feature_handler("bybit", DataFeature.OHLCV, TransportKind.REST)

    assert binance_ohlcv_rest is not None
    assert bybit_ohlcv_rest is not None
    # Both should map to fetch_ohlcv
    assert binance_ohlcv_rest.method_name == "fetch_ohlcv"
    assert bybit_ohlcv_rest.method_name == "fetch_ohlcv"

    # Test WS handlers
    binance_trades_ws = registry.get_feature_handler(
        "binance", DataFeature.TRADES, TransportKind.WS
    )
    bybit_trades_ws = registry.get_feature_handler("bybit", DataFeature.TRADES, TransportKind.WS)

    assert binance_trades_ws is not None
    assert bybit_trades_ws is not None
    # Both should map to stream_trades
    assert binance_trades_ws.method_name == "stream_trades"
    assert bybit_trades_ws.method_name == "stream_trades"


@pytest.mark.asyncio
async def test_register_all_exchanges():
    """Test registering all exchanges."""
    registry = ProviderRegistry()

    register_all(registry)

    expected_exchanges = ["binance", "bybit", "kraken", "hyperliquid", "coinbase", "okx"]
    assert set(registry.list_exchanges()) == set(expected_exchanges)

    # Verify all have URM mappers
    for exchange in expected_exchanges:
        urm = registry.get_urm_mapper(exchange)
        assert urm is not None, f"{exchange} should have URM mapper"


@pytest.mark.asyncio
async def test_register_kraken():
    """Test registering Kraken provider."""
    registry = ProviderRegistry()

    register_kraken(registry)

    assert registry.is_registered("kraken")
    urm = registry.get_urm_mapper("kraken")
    assert urm is not None

    # Test provider retrieval
    spot_provider = await registry.get_provider("kraken", MarketType.SPOT)
    assert spot_provider.name == "kraken"
    assert spot_provider.market_type == MarketType.SPOT


@pytest.mark.asyncio
async def test_register_hyperliquid():
    """Test registering Hyperliquid provider."""
    registry = ProviderRegistry()

    register_hyperliquid(registry)

    assert registry.is_registered("hyperliquid")
    urm = registry.get_urm_mapper("hyperliquid")
    assert urm is not None

    # Test provider retrieval
    spot_provider = await registry.get_provider("hyperliquid", MarketType.SPOT)
    assert spot_provider.name == "hyperliquid"
    assert spot_provider.market_type == MarketType.SPOT


@pytest.mark.asyncio
async def test_register_coinbase():
    """Test registering Coinbase provider (spot only)."""
    registry = ProviderRegistry()

    register_coinbase(registry)

    assert registry.is_registered("coinbase")
    urm = registry.get_urm_mapper("coinbase")
    assert urm is not None

    # Test provider retrieval (spot only)
    spot_provider = await registry.get_provider("coinbase", MarketType.SPOT)
    assert spot_provider.name == "coinbase"
    assert spot_provider.market_type == MarketType.SPOT

    # Coinbase should not support futures
    with pytest.raises(Exception):  # ProviderError from registry
        await registry.get_provider("coinbase", MarketType.FUTURES)
