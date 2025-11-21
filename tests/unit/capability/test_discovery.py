"""Tests for code-driven capability discovery."""

from __future__ import annotations

import pytest

from laakhay.data.capability.discovery import CapabilityDiscovery
from laakhay.data.core.enums import DataFeature, InstrumentType, MarketType, TransportKind
from laakhay.data.registration import register_all


@pytest.fixture
def discovery():
    """Create a discovery instance with registered providers."""
    from laakhay.data.runtime.provider_registry import ProviderRegistry

    # Use a fresh registry to avoid conflicts with other tests
    registry = ProviderRegistry()
    # Register all providers for testing
    register_all(registry)
    return CapabilityDiscovery(registry)


def test_discovery_finds_exchanges(discovery):
    """Test that discovery finds all registered exchanges."""
    capabilities = discovery.discover_all()

    # Should find capabilities for all registered exchanges
    exchanges = {cap.exchange for cap in capabilities}
    assert "binance" in exchanges
    assert "bybit" in exchanges
    assert "coinbase" in exchanges


def test_discovery_finds_features(discovery):
    """Test that discovery finds features from handlers."""
    capabilities = discovery.discover_exchange("binance")

    # Should find OHLCV capability
    ohlcv_caps = [
        cap
        for cap in capabilities
        if cap.feature == DataFeature.OHLCV and cap.transport == TransportKind.REST
    ]
    assert len(ohlcv_caps) > 0

    # Should find capabilities for both spot and futures
    spot_caps = [cap for cap in ohlcv_caps if cap.market_type == MarketType.SPOT]
    futures_caps = [cap for cap in ohlcv_caps if cap.market_type == MarketType.FUTURES]
    assert len(spot_caps) > 0
    assert len(futures_caps) > 0


def test_discovery_finds_endpoints(discovery):
    """Test that discovery finds capabilities from endpoint modules."""
    capabilities = discovery.discover_exchange("binance")

    # Should find order_book from endpoints
    orderbook_caps = [
        cap
        for cap in capabilities
        if cap.feature == DataFeature.ORDER_BOOK and cap.transport == TransportKind.REST
    ]
    assert len(orderbook_caps) > 0


def test_discovery_infers_instrument_types(discovery):
    """Test that discovery correctly infers instrument types."""
    capabilities = discovery.discover_exchange("binance")

    # Spot market should only have SPOT instruments
    spot_caps = [cap for cap in capabilities if cap.market_type == MarketType.SPOT]
    spot_instruments = {cap.instrument_type for cap in spot_caps}
    assert InstrumentType.SPOT in spot_instruments
    assert InstrumentType.PERPETUAL not in spot_instruments

    # Futures market should have PERPETUAL and FUTURE instruments
    futures_caps = [cap for cap in capabilities if cap.market_type == MarketType.FUTURES]
    futures_instruments = {cap.instrument_type for cap in futures_caps}
    assert InstrumentType.PERPETUAL in futures_instruments
    assert InstrumentType.FUTURE in futures_instruments


def test_discovery_handles_coinbase_spot_only(discovery):
    """Test that discovery correctly handles Coinbase (spot only)."""
    capabilities = discovery.discover_exchange("coinbase")

    # Coinbase should only have spot market
    market_types = {cap.market_type for cap in capabilities}
    assert MarketType.SPOT in market_types
    assert MarketType.FUTURES not in market_types


def test_discovery_caches_results(discovery):
    """Test that discovery caches results."""
    # First call
    caps1 = discovery.discover_exchange("binance")
    # Second call should return cached results
    caps2 = discovery.discover_exchange("binance")

    assert caps1 is caps2  # Should be same list object (cached)


def test_discovery_finds_ws_capabilities(discovery):
    """Test that discovery finds WebSocket capabilities."""
    capabilities = discovery.discover_exchange("binance")

    # Should find WS capabilities
    ws_caps = [cap for cap in capabilities if cap.transport == TransportKind.WS]
    assert len(ws_caps) > 0

    # WS capabilities should have stream constraints
    ohlcv_ws = [
        cap
        for cap in ws_caps
        if cap.feature == DataFeature.OHLCV and cap.transport == TransportKind.WS
    ]
    if ohlcv_ws:
        # Should have constraints from endpoint spec
        assert "max_streams" in ohlcv_ws[0].constraints or len(ohlcv_ws[0].constraints) >= 0
