"""Unit tests for DataRouter."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from laakhay.data.core.capability_service import CapabilityService
from laakhay.data.core.enums import (
    DataFeature,
    InstrumentType,
    MarketType,
    Timeframe,
    TransportKind,
)
from laakhay.data.core.exceptions import CapabilityError, ProviderError
from laakhay.data.core.registry import FeatureHandler, ProviderRegistry
from laakhay.data.core.request import DataRequest
from laakhay.data.core.router import DataRouter


class MockProvider:
    """Mock provider for testing."""

    def __init__(self) -> None:
        """Initialize mock provider."""
        self.name = "mock"
        self.market_type = MarketType.SPOT

    async def get_candles(
        self,
        symbol: str,
        timeframe: str | Timeframe,
        start_time=None,
        end_time=None,
        limit=None,
    ):
        """Mock get_candles method."""
        return {"symbol": symbol, "timeframe": timeframe, "limit": limit}

    async def stream_trades(self, symbol: str) -> AsyncIterator[dict]:
        """Mock stream_trades method."""
        yield {"symbol": symbol, "price": 50000}
        yield {"symbol": symbol, "price": 50001}


@pytest.fixture
def mock_provider_registry():
    """Create a mock provider registry."""
    registry = MagicMock(spec=ProviderRegistry)
    registry.get_provider = AsyncMock(return_value=MockProvider())
    registry.get_feature_handler = MagicMock(
        return_value=FeatureHandler(
            method_name="get_candles",
            method=MockProvider.get_candles,
            feature=DataFeature.OHLCV,
            transport=TransportKind.REST,
        )
    )
    registry.get_urm_mapper = MagicMock(return_value=None)  # No URM mapper for simple tests
    return registry


@pytest.fixture
def mock_capability_service():
    """Create a mock capability service."""
    service = MagicMock(spec=CapabilityService)
    service.validate_request = MagicMock()  # No-op by default (assumes valid)
    return service


@pytest.fixture
def router(mock_provider_registry, mock_capability_service):
    """Create a DataRouter with mocked dependencies."""
    return DataRouter(
        provider_registry=mock_provider_registry,
        capability_service=mock_capability_service,
    )


@pytest.mark.asyncio
async def test_route_valid_request(router, mock_provider_registry):
    """Test routing a valid request."""
    request = DataRequest(
        feature=DataFeature.OHLCV,
        transport=TransportKind.REST,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        limit=100,
    )

    result = await router.route(request)

    # Verify capability was checked
    router._capability_service.validate_request.assert_called_once_with(request)

    # Verify provider was retrieved
    mock_provider_registry.get_provider.assert_called_once_with("binance", MarketType.SPOT)

    # Verify result
    assert result["symbol"] == "BTCUSDT"
    assert result["timeframe"] == Timeframe.H1  # Returns enum, not string
    assert result["limit"] == 100


@pytest.mark.asyncio
async def test_route_capability_error(router, mock_capability_service):
    """Test that CapabilityError is raised when capability is unsupported."""
    request = DataRequest(
        feature=DataFeature.OHLCV,
        transport=TransportKind.REST,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
    )

    # Make capability service raise error
    mock_capability_service.validate_request.side_effect = CapabilityError(
        "Capability not supported", key=None, status=None
    )

    with pytest.raises(CapabilityError):
        await router.route(request)


@pytest.mark.asyncio
async def test_route_no_handler(router, mock_provider_registry):
    """Test that ProviderError is raised when no handler is found."""
    request = DataRequest(
        feature=DataFeature.OHLCV,
        transport=TransportKind.REST,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
    )

    # Make registry return None for handler
    mock_provider_registry.get_feature_handler.return_value = None

    with pytest.raises(ProviderError, match="No handler found"):
        await router.route(request)


@pytest.mark.asyncio
async def test_route_stream(router, mock_provider_registry):
    """Test routing a streaming request."""
    request = DataRequest(
        feature=DataFeature.TRADES,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
    )

    # Setup handler for streaming
    mock_provider_registry.get_feature_handler.return_value = FeatureHandler(
        method_name="stream_trades",
        method=MockProvider.stream_trades,
        feature=DataFeature.TRADES,
        transport=TransportKind.WS,
    )

    results = []
    async for item in router.route_stream(request):
        results.append(item)

    assert len(results) == 2
    assert results[0]["symbol"] == "BTCUSDT"
    assert results[0]["price"] == 50000


@pytest.mark.asyncio
async def test_route_stream_requires_ws(router):
    """Test that route_stream requires WS transport."""
    request = DataRequest(
        feature=DataFeature.OHLCV,
        transport=TransportKind.REST,  # Wrong transport
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
    )

    with pytest.raises(ValueError, match="requires transport=TransportKind.WS"):
        async for _ in router.route_stream(request):
            pass


@pytest.mark.asyncio
async def test_resolve_symbols_with_urm(router, mock_provider_registry):
    """Test symbol resolution with URM mapper."""
    # Create a mock URM mapper
    mock_mapper = MagicMock()
    mock_mapper.to_spec = MagicMock(
        return_value=MagicMock(base="BTC", quote="USDT", instrument_type=InstrumentType.SPOT)
    )
    mock_mapper.to_exchange_symbol = MagicMock(return_value="BTCUSDT")

    mock_provider_registry.get_urm_mapper.return_value = mock_mapper

    request = DataRequest(
        feature=DataFeature.OHLCV,
        transport=TransportKind.REST,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",  # This will be normalized
        timeframe=Timeframe.H1,
    )

    exchange_symbol = router._resolve_symbols(request)
    assert exchange_symbol == "BTCUSDT"
    mock_mapper.to_spec.assert_called_once_with("BTCUSDT", market_type=MarketType.SPOT)
    mock_mapper.to_exchange_symbol.assert_called_once()


@pytest.mark.asyncio
async def test_resolve_symbols_no_urm(router, mock_provider_registry):
    """Test symbol resolution without URM mapper (passes through)."""
    mock_provider_registry.get_urm_mapper.return_value = None

    request = DataRequest(
        feature=DataFeature.OHLCV,
        transport=TransportKind.REST,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
    )

    exchange_symbol = router._resolve_symbols(request)
    assert exchange_symbol == "BTCUSDT"  # Passes through unchanged


@pytest.mark.asyncio
async def test_resolve_multiple_symbols(router, mock_provider_registry):
    """Test resolving multiple symbols."""
    mock_mapper = MagicMock()
    mock_mapper.to_spec = MagicMock(
        return_value=MagicMock(base="BTC", quote="USDT", instrument_type=InstrumentType.SPOT)
    )
    mock_mapper.to_exchange_symbol = MagicMock(side_effect=["BTCUSDT", "ETHUSDT"])

    mock_provider_registry.get_urm_mapper.return_value = mock_mapper

    request = DataRequest(
        feature=DataFeature.OHLCV,
        transport=TransportKind.REST,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe=Timeframe.H1,
    )

    exchange_symbols = router._resolve_symbols(request)
    assert exchange_symbols == ["BTCUSDT", "ETHUSDT"]
    assert mock_mapper.to_spec.call_count == 2
    assert mock_mapper.to_exchange_symbol.call_count == 2


@pytest.mark.asyncio
async def test_build_method_args(router):
    """Test building method arguments from request."""
    request = DataRequest(
        feature=DataFeature.OHLCV,
        transport=TransportKind.REST,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        start_time=None,
        end_time=None,
        limit=100,
    )

    args = router._build_method_args(request, "BTCUSDT")

    assert args["symbol"] == "BTCUSDT"
    assert args["timeframe"] == Timeframe.H1
    assert args["limit"] == 100


@pytest.mark.asyncio
async def test_build_method_args_order_book(router):
    """Test building method arguments for order book (depth -> limit)."""
    request = DataRequest(
        feature=DataFeature.ORDER_BOOK,
        transport=TransportKind.REST,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
        depth=50,
    )

    args = router._build_method_args(request, "BTCUSDT")

    assert args["symbol"] == "BTCUSDT"
    assert args["limit"] == 50  # depth maps to limit for order book


@pytest.mark.asyncio
async def test_build_method_args_streaming(router):
    """Test building method arguments for streaming requests."""
    request = DataRequest(
        feature=DataFeature.OHLCV,
        transport=TransportKind.WS,
        exchange="binance",
        market_type=MarketType.SPOT,
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        only_closed=True,
        throttle_ms=100,
        dedupe_same_candle=True,
    )

    args = router._build_method_args(request, "BTCUSDT")

    assert args["symbol"] == "BTCUSDT"
    assert args["timeframe"] == Timeframe.H1
    assert args["only_closed"] is True
    assert args["throttle_ms"] == 100
    assert args["dedupe_same_candle"] is True
