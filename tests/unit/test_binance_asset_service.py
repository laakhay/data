"""Unit tests for BinanceAssetService adapter."""

from decimal import Decimal

import pytest

from laakhay.data.providers.binance.asset_service import BinanceAssetService, ProductCap


class FakeHTTP:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    async def get(self, url, params=None, headers=None):
        self.calls += 1
        return self.payload

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_asset_service_parse_and_sort():
    payload = {
        "data": [
            {"s": "BTCUSDT", "b": "BTC", "q": "USDT", "c": "60000", "cs": "19500000"},
            {"s": "ETHUSDT", "b": "ETH", "q": "USDT", "c": "3000", "cs": "120000000"},
            {"s": "XYZUSDT", "b": "XYZ", "q": "USDT", "c": "1.5", "cs": "1000000"},
        ]
    }
    svc = BinanceAssetService(http=FakeHTTP(payload))
    items = await svc.get_market_caps(quote="USDT")
    assert len(items) == 3
    # Sorted by market cap desc: BTC > ETH > XYZ
    assert items[0].symbol == "BTCUSDT"
    assert items[1].symbol == "ETHUSDT"
    assert items[2].symbol == "XYZUSDT"
    # MC sanity
    assert items[0].circulating_market_cap > items[1].circulating_market_cap


@pytest.mark.asyncio
async def test_asset_service_filters_and_topn():
    payload = {
        "data": [
            {"s": "AAAUSDT", "b": "AAA", "q": "USDT", "c": "2", "cs": "100"},
            {"s": "BBBUSD", "b": "BBB", "q": "USD", "c": "10", "cs": "100"},
            {"s": "CCCUSDT", "b": "CCC", "q": "USDT", "c": "1", "cs": "10"},
        ]
    }
    svc = BinanceAssetService(http=FakeHTTP(payload))
    items = await svc.get_market_caps(quote="USDT", min_circulating_supply=Decimal("50"))
    # Only AAAUSDT should pass the min CS filter (100), CCC has 10
    assert [x.symbol for x in items] == ["AAAUSDT"]
    top = await svc.get_top_market_caps(n=1, quote="USDT")
    assert len(top) == 1
    assert isinstance(top[0], ProductCap)


@pytest.mark.asyncio
async def test_asset_service_caching():
    payload = {"data": [{"s": "BTCUSDT", "b": "BTC", "q": "USDT", "c": "60000", "cs": "19500000"}]}
    http = FakeHTTP(payload)
    svc = BinanceAssetService(http=http, ttl_seconds=3600)
    # First call fetches
    first = await svc.get_products()
    assert http.calls == 1
    # Second call should use cache
    second = await svc.get_products()
    assert http.calls == 1
    assert first == second
    # Force refresh bypasses cache
    await svc.get_products(force_refresh=True)
    assert http.calls == 2
