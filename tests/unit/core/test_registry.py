"""Unit tests for ProviderRegistry."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from laakhay.data.core import (
    BaseProvider,
    DataFeature,
    MarketType,
    ProviderError,
    ProviderRegistry,
    TransportKind,
)
from laakhay.data.core.registry import FeatureHandler, collect_feature_handlers


class MockProvider(BaseProvider):
    """Mock provider for testing."""

    def __init__(
        self,
        *,
        market_type: MarketType = MarketType.SPOT,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        super().__init__(name="mock")
        self.market_type = market_type
        self._closed = False
        self.api_key = api_key
        self.api_secret = api_secret

    async def get_candles(self, symbol: str, interval, start_time=None, end_time=None, limit=None):
        """Mock get_candles."""
        return {"symbol": symbol, "interval": interval}

    async def get_symbols(self):
        """Mock get_symbols."""
        return [{"symbol": "BTCUSDT"}]

    async def close(self) -> None:
        """Mock close."""
        self._closed = True

    async def __aenter__(self):
        """Async context entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context exit."""
        await self.close()


@pytest.mark.asyncio
async def test_registry_register():
    """Test registering a provider."""
    registry = ProviderRegistry()

    registry.register(
        "test_exchange",
        MockProvider,
        market_types=[MarketType.SPOT, MarketType.FUTURES],
    )

    assert registry.is_registered("test_exchange")
    assert "test_exchange" in registry.list_exchanges()


@pytest.mark.asyncio
async def test_registry_register_duplicate():
    """Test registering duplicate exchange raises error."""
    registry = ProviderRegistry()

    registry.register("test_exchange", MockProvider, market_types=[MarketType.SPOT])

    with pytest.raises(ProviderError, match="already registered"):
        registry.register("test_exchange", MockProvider, market_types=[MarketType.SPOT])


@pytest.mark.asyncio
async def test_registry_get_provider():
    """Test getting a provider instance."""
    registry = ProviderRegistry()

    registry.register("test_exchange", MockProvider, market_types=[MarketType.SPOT])

    provider = await registry.get_provider("test_exchange", MarketType.SPOT)

    assert isinstance(provider, MockProvider)
    assert provider.market_type == MarketType.SPOT


@pytest.mark.asyncio
async def test_registry_get_provider_pooling():
    """Test that provider instances are pooled."""
    registry = ProviderRegistry()

    registry.register("test_exchange", MockProvider, market_types=[MarketType.SPOT])

    provider1 = await registry.get_provider("test_exchange", MarketType.SPOT)
    provider2 = await registry.get_provider("test_exchange", MarketType.SPOT)

    # Should return the same instance
    assert provider1 is provider2


@pytest.mark.asyncio
async def test_registry_get_provider_different_market_types():
    """Test that different market types get different instances."""
    registry = ProviderRegistry()

    registry.register(
        "test_exchange", MockProvider, market_types=[MarketType.SPOT, MarketType.FUTURES]
    )

    spot_provider = await registry.get_provider("test_exchange", MarketType.SPOT)
    futures_provider = await registry.get_provider("test_exchange", MarketType.FUTURES)

    # Should be different instances
    assert spot_provider is not futures_provider
    assert spot_provider.market_type == MarketType.SPOT
    assert futures_provider.market_type == MarketType.FUTURES


@pytest.mark.asyncio
async def test_registry_get_provider_not_registered():
    """Test getting unregistered provider raises error."""
    registry = ProviderRegistry()

    with pytest.raises(ProviderError, match="not registered"):
        await registry.get_provider("unknown", MarketType.SPOT)


@pytest.mark.asyncio
async def test_registry_get_provider_unsupported_market_type():
    """Test getting provider with unsupported market type raises error."""
    registry = ProviderRegistry()

    registry.register("test_exchange", MockProvider, market_types=[MarketType.SPOT])

    with pytest.raises(ProviderError, match="not supported"):
        await registry.get_provider("test_exchange", MarketType.FUTURES)


@pytest.mark.asyncio
async def test_registry_unregister():
    """Test unregistering a provider."""
    registry = ProviderRegistry()

    registry.register("test_exchange", MockProvider, market_types=[MarketType.SPOT])
    await registry.get_provider("test_exchange", MarketType.SPOT)

    registry.unregister("test_exchange")

    assert not registry.is_registered("test_exchange")
    with pytest.raises(ProviderError, match="not registered"):
        await registry.get_provider("test_exchange", MarketType.SPOT)


@pytest.mark.asyncio
async def test_registry_unregister_not_registered():
    """Test unregistering non-existent provider raises error."""
    registry = ProviderRegistry()

    with pytest.raises(ProviderError, match="not registered"):
        registry.unregister("unknown")


@pytest.mark.asyncio
async def test_registry_close_all():
    """Test closing all providers."""
    registry = ProviderRegistry()

    registry.register("test1", MockProvider, market_types=[MarketType.SPOT])
    registry.register("test2", MockProvider, market_types=[MarketType.SPOT])

    provider1 = await registry.get_provider("test1", MarketType.SPOT)
    provider2 = await registry.get_provider("test2", MarketType.SPOT)

    await registry.close_all()

    assert provider1._closed
    assert provider2._closed
    assert len(registry._provider_pools) == 0


@pytest.mark.asyncio
async def test_registry_feature_handler():
    """Test getting feature handler."""
    registry = ProviderRegistry()

    handler = FeatureHandler(
        method_name="get_candles",
        method=lambda: None,
        feature=DataFeature.OHLCV,
        transport=TransportKind.REST,
    )

    registry.register(
        "test_exchange",
        MockProvider,
        market_types=[MarketType.SPOT],
        feature_handlers={(DataFeature.OHLCV, TransportKind.REST): handler},
    )

    retrieved = registry.get_feature_handler("test_exchange", DataFeature.OHLCV, TransportKind.REST)
    assert retrieved is handler
    assert retrieved.feature == DataFeature.OHLCV
    assert retrieved.transport == TransportKind.REST


@pytest.mark.asyncio
async def test_registry_feature_handler_not_found():
    """Test getting non-existent feature handler returns None."""
    registry = ProviderRegistry()

    registry.register("test_exchange", MockProvider, market_types=[MarketType.SPOT])

    handler = registry.get_feature_handler("test_exchange", DataFeature.OHLCV, TransportKind.REST)
    assert handler is None


@pytest.mark.asyncio
async def test_registry_context_manager():
    """Test registry as async context manager."""
    async with ProviderRegistry() as registry:
        registry.register("test_exchange", MockProvider, market_types=[MarketType.SPOT])
        provider = await registry.get_provider("test_exchange", MarketType.SPOT)
        assert provider is not None

    # After context exit, providers should be closed
    assert provider._closed


@pytest.mark.asyncio
async def test_registry_get_provider_after_close():
    """Test getting provider after registry is closed raises error."""
    registry = ProviderRegistry()

    registry.register("test_exchange", MockProvider, market_types=[MarketType.SPOT])
    await registry.close_all()

    with pytest.raises(ProviderError, match="closed"):
        await registry.get_provider("test_exchange", MarketType.SPOT)

