"""Unit tests for ProviderRegistry."""

import pytest

from laakhay.data.core import (
    BaseProvider,
    DataFeature,
    MarketType,
    ProviderError,
    ProviderRegistry,
    TransportKind,
)
from laakhay.data.core.registry import FeatureHandler


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


@pytest.mark.asyncio
async def test_registry_get_provider_removes_closed_provider():
    """Test that closed providers are removed from pool and recreated."""
    registry = ProviderRegistry()

    registry.register("test_exchange", MockProvider, market_types=[MarketType.SPOT])

    provider1 = await registry.get_provider("test_exchange", MarketType.SPOT)
    await provider1.close()  # Close the provider

    # Should create a new provider instance
    provider2 = await registry.get_provider("test_exchange", MarketType.SPOT)

    assert provider1 is not provider2
    assert provider1._closed is True  # First one is closed
    assert provider2._closed is False  # New one is open


@pytest.mark.asyncio
async def test_registry_get_provider_with_credentials():
    """Test getting provider with API credentials."""
    registry = ProviderRegistry()

    registry.register("test_exchange", MockProvider, market_types=[MarketType.SPOT])

    provider = await registry.get_provider(
        "test_exchange", MarketType.SPOT, api_key="key123", api_secret="secret456"
    )

    assert provider.api_key == "key123"
    assert provider.api_secret == "secret456"


@pytest.mark.asyncio
async def test_registry_get_feature_handler_unregistered_exchange():
    """Test getting feature handler for unregistered exchange returns None."""
    registry = ProviderRegistry()

    handler = registry.get_feature_handler("unknown", DataFeature.OHLCV, TransportKind.REST)
    assert handler is None


@pytest.mark.asyncio
async def test_registry_get_urm_mapper():
    """Test getting URM mapper."""
    from unittest.mock import MagicMock

    registry = ProviderRegistry()
    mock_mapper = MagicMock()

    registry.register(
        "test_exchange",
        MockProvider,
        market_types=[MarketType.SPOT],
        urm_mapper=mock_mapper,
    )

    mapper = registry.get_urm_mapper("test_exchange")
    assert mapper is mock_mapper


@pytest.mark.asyncio
async def test_registry_get_urm_mapper_unregistered():
    """Test getting URM mapper for unregistered exchange returns None."""
    registry = ProviderRegistry()

    mapper = registry.get_urm_mapper("unknown")
    assert mapper is None


@pytest.mark.asyncio
async def test_registry_close_all_idempotent():
    """Test that close_all can be called multiple times safely."""
    registry = ProviderRegistry()

    registry.register("test_exchange", MockProvider, market_types=[MarketType.SPOT])
    await registry.get_provider("test_exchange", MarketType.SPOT)

    await registry.close_all()
    await registry.close_all()  # Should not raise error

    assert registry._closed


@pytest.mark.asyncio
async def test_get_provider_registry_singleton():
    """Test that get_provider_registry returns singleton."""
    from laakhay.data.core.registry import get_provider_registry

    registry1 = get_provider_registry()
    registry2 = get_provider_registry()

    assert registry1 is registry2


@pytest.mark.asyncio
async def test_register_feature_handler_decorator():
    """Test register_feature_handler decorator."""
    from laakhay.data.core.registry import register_feature_handler

    @register_feature_handler(DataFeature.OHLCV, TransportKind.REST)
    async def test_method(self, symbol: str):
        """Test method."""
        return symbol

    assert hasattr(test_method, "_feature_handlers")
    assert len(test_method._feature_handlers) == 1
    assert test_method._feature_handlers[0]["feature"] == DataFeature.OHLCV
    assert test_method._feature_handlers[0]["transport"] == TransportKind.REST


@pytest.mark.asyncio
async def test_register_feature_handler_with_constraints():
    """Test register_feature_handler with constraints."""
    from laakhay.data.core.registry import register_feature_handler

    @register_feature_handler(
        DataFeature.OHLCV, TransportKind.REST, constraints={"max_limit": 1000}
    )
    async def test_method(self, symbol: str):
        """Test method."""
        return symbol

    assert test_method._feature_handlers[0]["constraints"] == {"max_limit": 1000}


@pytest.mark.asyncio
async def test_collect_feature_handlers():
    """Test collecting feature handlers from provider class."""
    from laakhay.data.core.registry import (
        collect_feature_handlers,
        register_feature_handler,
    )

    class TestProvider(BaseProvider):
        """Test provider with decorated methods."""

        def __init__(self):
            super().__init__(name="test")

        @register_feature_handler(DataFeature.OHLCV, TransportKind.REST)
        async def get_candles(self, symbol: str):
            """Get candles."""
            return symbol

        @register_feature_handler(DataFeature.TRADES, TransportKind.WS)
        async def stream_trades(self, symbol: str):
            """Stream trades."""
            return symbol

        async def regular_method(self):
            """Regular method without decorator."""
            pass

    handlers = collect_feature_handlers(TestProvider)

    assert len(handlers) == 2
    assert (DataFeature.OHLCV, TransportKind.REST) in handlers
    assert (DataFeature.TRADES, TransportKind.WS) in handlers

    ohlcv_handler = handlers[(DataFeature.OHLCV, TransportKind.REST)]
    assert ohlcv_handler.method_name == "get_candles"
    assert ohlcv_handler.feature == DataFeature.OHLCV
    assert ohlcv_handler.transport == TransportKind.REST
