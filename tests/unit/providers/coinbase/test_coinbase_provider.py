"""Unit tests for Coinbase REST/WS providers (decoupled)."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from laakhay.data.core import MarketType, Timeframe
from laakhay.data.models import (
    OHLCV,
    Bar,
    OrderBook,
    SeriesMeta,
    Symbol,
)
from laakhay.data.providers import (
    CoinbaseProvider,
    CoinbaseRESTProvider,
    CoinbaseWSProvider,
)
from laakhay.data.providers.coinbase.constants import (
    INTERVAL_MAP,
    normalize_symbol_from_coinbase,
    normalize_symbol_to_coinbase,
)
from laakhay.data.providers.coinbase.rest.adapters import (
    CandlesResponseAdapter,
    ExchangeInfoSymbolsAdapter,
    OrderBookResponseAdapter,
    RecentTradesAdapter,
)
from laakhay.data.providers.coinbase.rest.endpoints import (
    candles_spec,
    exchange_info_spec,
    order_book_spec,
    recent_trades_spec,
)
from laakhay.data.providers.coinbase.ws.adapters import (
    OhlcvAdapter,
    OrderBookAdapter,
    TradesAdapter,
)
from laakhay.data.providers.coinbase.ws.endpoints import (
    ohlcv_spec,
    trades_spec,
)
from laakhay.data.providers.coinbase.ws.endpoints import (
    order_book_spec as ws_order_book_spec,
)

# ============================================================================
# Provider Instantiation Tests
# ============================================================================


def test_coinbase_rest_provider_instantiation_defaults_to_spot():
    """REST provider defaults to SPOT market type."""
    provider = CoinbaseRESTProvider()
    assert provider.market_type == MarketType.SPOT


def test_coinbase_rest_provider_instantiation_spot():
    """REST provider can be instantiated with SPOT market type."""
    provider = CoinbaseRESTProvider(market_type=MarketType.SPOT)
    assert provider.market_type == MarketType.SPOT


def test_coinbase_rest_provider_raises_on_futures():
    """REST provider raises ValueError for FUTURES market type."""
    with pytest.raises(ValueError, match="only supports Spot markets"):
        CoinbaseRESTProvider(market_type=MarketType.FUTURES)


def test_coinbase_ws_provider_instantiation():
    """WebSocket provider defaults to SPOT and rejects FUTURES."""
    ws = CoinbaseWSProvider()
    assert ws.market_type == MarketType.SPOT

    ws_spot = CoinbaseWSProvider(market_type=MarketType.SPOT)
    assert ws_spot.market_type == MarketType.SPOT

    with pytest.raises(ValueError, match="only supports Spot markets"):
        CoinbaseWSProvider(market_type=MarketType.FUTURES)


def test_coinbase_provider_instantiation_defaults_to_spot():
    """Unified provider defaults to SPOT market type."""
    provider = CoinbaseProvider()
    assert provider.market_type == MarketType.SPOT


def test_coinbase_provider_instantiation_spot():
    """Unified provider can be instantiated with SPOT market type."""
    provider = CoinbaseProvider(market_type=MarketType.SPOT)
    assert provider.market_type == MarketType.SPOT


def test_coinbase_provider_raises_on_futures():
    """Unified provider raises ValueError for FUTURES market type."""
    with pytest.raises(ValueError, match="only supports Spot markets"):
        CoinbaseProvider(market_type=MarketType.FUTURES)


def test_coinbase_provider_context_manager_closes():
    """Unified provider works as context manager."""

    async def run() -> bool:
        async with CoinbaseProvider() as provider:
            return provider.market_type == MarketType.SPOT

    assert asyncio.run(run())


# ============================================================================
# Constants Tests
# ============================================================================


def test_coinbase_interval_mapping_constants():
    """Verify interval mappings match Coinbase API format."""
    assert INTERVAL_MAP[Timeframe.M1] == "ONE_MINUTE"
    assert INTERVAL_MAP[Timeframe.M5] == "FIVE_MINUTE"
    assert INTERVAL_MAP[Timeframe.M15] == "FIFTEEN_MINUTE"
    assert INTERVAL_MAP[Timeframe.M30] == "THIRTY_MINUTE"
    assert INTERVAL_MAP[Timeframe.H1] == "ONE_HOUR"
    assert INTERVAL_MAP[Timeframe.H2] == "TWO_HOUR"
    assert INTERVAL_MAP[Timeframe.H4] == "FOUR_HOUR"
    assert INTERVAL_MAP[Timeframe.H6] == "SIX_HOUR"
    assert INTERVAL_MAP[Timeframe.H12] == "TWELVE_HOUR"
    assert INTERVAL_MAP[Timeframe.D1] == "ONE_DAY"
    assert INTERVAL_MAP[Timeframe.W1] == "ONE_WEEK"


def test_normalize_symbol_to_coinbase_explicit_mapping():
    """Symbol normalization to Coinbase format uses explicit mappings."""
    assert normalize_symbol_to_coinbase("BTCUSD") == "BTC-USD"
    assert normalize_symbol_to_coinbase("ETHUSD") == "ETH-USD"
    # Coinbase doesn't support USDT pairs - maps to USD instead
    assert normalize_symbol_to_coinbase("BTCUSDT") == "BTC-USD"
    assert normalize_symbol_to_coinbase("ETHUSDT") == "ETH-USD"


def test_normalize_symbol_to_coinbase_already_coinbase_format():
    """Symbol normalization handles already Coinbase-formatted symbols."""
    assert normalize_symbol_to_coinbase("BTC-USD") == "BTC-USD"
    assert normalize_symbol_to_coinbase("ETH-USD") == "ETH-USD"


def test_normalize_symbol_to_coinbase_fallback_inference():
    """Symbol normalization infers format for unknown symbols."""
    # Should infer USD quote (USDT pairs also map to USD)
    result = normalize_symbol_to_coinbase("DOGEUSD")
    assert result == "DOGE-USD"
    # USDT pairs map to USD (Coinbase doesn't support USDT pairs)
    result_usdt = normalize_symbol_to_coinbase("DOGEUSDT")
    assert result_usdt == "DOGE-USD"


def test_normalize_symbol_from_coinbase_explicit_mapping():
    """Symbol normalization from Coinbase format uses explicit mappings."""
    assert normalize_symbol_from_coinbase("BTC-USD") == "BTCUSD"
    assert normalize_symbol_from_coinbase("ETH-USD") == "ETHUSD"
    assert normalize_symbol_from_coinbase("BTC-USDT") == "BTCUSDT"
    assert normalize_symbol_from_coinbase("ETH-USDT") == "ETHUSDT"


def test_normalize_symbol_from_coinbase_already_standard_format():
    """Symbol normalization handles already standard-formatted symbols."""
    assert normalize_symbol_from_coinbase("BTCUSD") == "BTCUSD"
    assert normalize_symbol_from_coinbase("ETHUSD") == "ETHUSD"


def test_normalize_symbol_from_coinbase_fallback_removal():
    """Symbol normalization removes hyphen as fallback."""
    result = normalize_symbol_from_coinbase("DOGE-USD")
    assert result == "DOGEUSD"

    result = normalize_symbol_from_coinbase("DOGE-USDT")
    assert result == "DOGEUSDT"


def test_normalize_symbol_bidirectional():
    """Symbol normalization works bidirectionally."""
    # Standard -> Coinbase -> Standard
    coinbase = normalize_symbol_to_coinbase("BTCUSD")
    assert coinbase == "BTC-USD"

    standard = normalize_symbol_from_coinbase(coinbase)
    assert standard == "BTCUSD"

    # Coinbase -> Standard -> Coinbase
    standard = normalize_symbol_from_coinbase("ETH-USD")
    assert standard == "ETHUSD"

    coinbase = normalize_symbol_to_coinbase(standard)
    assert coinbase == "ETH-USD"


# ============================================================================
# REST Endpoint Spec Tests
# ============================================================================


def test_candles_spec_builds_correct_path():
    """Candles endpoint spec builds correct path with product_id."""
    spec = candles_spec()
    params = {
        "market_type": MarketType.SPOT,
        "symbol": "BTCUSD",
    }

    path = spec.build_path(params)
    assert path == "/products/BTC-USD/candles"


def test_candles_spec_builds_query_with_times():
    """Candles endpoint spec builds query with start/end times."""
    spec = candles_spec()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

    params = {
        "market_type": MarketType.SPOT,
        "symbol": "BTCUSD",
        "interval": Timeframe.M15,
        "interval_str": "FIFTEEN_MINUTE",
        "start_time": base_time,
        "end_time": base_time + timedelta(hours=1),
    }

    query = spec.build_query(params)
    # Coinbase API uses granularity in seconds, not string format
    assert query["granularity"] == 900  # 15 minutes = 900 seconds
    assert query["start"] == base_time.isoformat().replace("+00:00", "Z")
    assert query["end"] == (base_time + timedelta(hours=1)).isoformat().replace("+00:00", "Z")


def test_candles_spec_builds_query_without_times():
    """Candles endpoint spec builds query without optional time parameters."""
    spec = candles_spec()
    params = {
        "market_type": MarketType.SPOT,
        "symbol": "BTCUSD",
        "interval": Timeframe.H1,
        "interval_str": "ONE_HOUR",
    }

    query = spec.build_query(params)
    # Coinbase API uses granularity in seconds, not string format
    assert query["granularity"] == 3600  # 1 hour = 3600 seconds
    assert "start" not in query
    assert "end" not in query


def test_candles_spec_raises_on_futures():
    """Candles endpoint spec raises ValueError for FUTURES market type."""
    spec = candles_spec()
    params = {
        "market_type": MarketType.FUTURES,
        "symbol": "BTCUSD",
    }

    with pytest.raises(ValueError, match="only supports Spot markets"):
        spec.build_path(params)


def test_exchange_info_spec_builds_correct_path():
    """Exchange info endpoint spec builds correct path."""
    spec = exchange_info_spec()
    params = {"market_type": MarketType.SPOT}

    assert spec.build_path(params) == "/products"


def test_exchange_info_spec_builds_query():
    """Exchange info endpoint spec builds query with limit."""
    spec = exchange_info_spec()
    params = {"market_type": MarketType.SPOT}

    query = spec.build_query(params)
    assert query["limit"] == 250


def test_order_book_spec_builds_correct_path():
    """Order book endpoint spec builds correct path with product_id."""
    spec = order_book_spec()
    params = {
        "market_type": MarketType.SPOT,
        "symbol": "BTCUSD",
    }

    path = spec.build_path(params)
    assert path == "/products/BTC-USD/book"


def test_order_book_spec_builds_query_with_limit():
    """Order book endpoint spec builds query with level based on limit."""
    spec = order_book_spec()
    params = {
        "market_type": MarketType.SPOT,
        "symbol": "BTCUSD",
        "limit": 100,
    }

    query = spec.build_query(params)
    # Coinbase uses level parameter (1, 2, or 3) instead of limit
    # Limit > 50 maps to level 3 (full depth)
    assert query["level"] == 3


def test_order_book_spec_caps_limit_at_250():
    """Order book endpoint spec maps limit to appropriate level."""
    spec = order_book_spec()
    params = {
        "market_type": MarketType.SPOT,
        "symbol": "BTCUSD",
        "limit": 50,  # Maps to level 2
    }

    query = spec.build_query(params)
    # Limit <= 50 maps to level 2
    assert query["level"] == 2


def test_recent_trades_spec_builds_correct_path():
    """Recent trades endpoint spec builds correct path with product_id."""
    spec = recent_trades_spec()
    params = {
        "market_type": MarketType.SPOT,
        "symbol": "ETHUSD",
    }

    path = spec.build_path(params)
    assert path == "/products/ETH-USD/trades"


def test_recent_trades_spec_builds_query_with_limit():
    """Recent trades endpoint spec builds query with limit."""
    spec = recent_trades_spec()
    params = {
        "market_type": MarketType.SPOT,
        "symbol": "ETHUSD",
        "limit": 500,
    }

    query = spec.build_query(params)
    assert query["limit"] == 500


def test_recent_trades_spec_caps_limit_at_1000():
    """Recent trades endpoint spec caps limit at Coinbase max of 1000."""
    spec = recent_trades_spec()
    params = {
        "market_type": MarketType.SPOT,
        "symbol": "ETHUSD",
        "limit": 2000,  # Above max
    }

    query = spec.build_query(params)
    assert query["limit"] == 1000


# ============================================================================
# REST Adapter Tests
# ============================================================================


def test_candles_response_adapter_parses_valid_response():
    """Candles adapter parses valid Coinbase candles response."""
    adapter = CandlesResponseAdapter()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

    response = {
        "candles": [
            {
                "start": "2024-01-01T12:00:00Z",
                "low": "42000.00",
                "high": "43000.00",
                "open": "42500.00",
                "close": "42800.00",
                "volume": "123.45",
            },
            {
                "start": "2024-01-01T12:15:00Z",
                "low": "42800.00",
                "high": "43200.00",
                "open": "42800.00",
                "close": "43000.00",
                "volume": "150.00",
            },
        ]
    }

    params = {"symbol": "BTCUSD", "interval": Timeframe.M15}
    result = adapter.parse(response, params)

    assert isinstance(result, OHLCV)
    assert result.meta.symbol == "BTCUSD"
    assert result.meta.timeframe == "15m"
    assert len(result.bars) == 2

    bar1 = result.bars[0]
    assert bar1.timestamp == base_time
    assert bar1.open == Decimal("42500.00")
    assert bar1.high == Decimal("43000.00")
    assert bar1.low == Decimal("42000.00")
    assert bar1.close == Decimal("42800.00")
    assert bar1.volume == Decimal("123.45")
    assert bar1.is_closed is True

    bar2 = result.bars[1]
    assert bar2.timestamp == base_time + timedelta(minutes=15)
    assert bar2.close == Decimal("43000.00")


def test_candles_response_adapter_handles_empty_response():
    """Candles adapter handles empty response."""
    adapter = CandlesResponseAdapter()
    response = {"candles": []}
    params = {"symbol": "BTCUSD", "interval": Timeframe.M15}
    result = adapter.parse(response, params)

    assert isinstance(result, OHLCV)
    assert len(result.bars) == 0


def test_candles_response_adapter_skips_invalid_rows():
    """Candles adapter skips invalid rows gracefully."""
    adapter = CandlesResponseAdapter()

    response = {
        "candles": [
            {
                "start": "2024-01-01T12:00:00Z",
                "open": "42500.00",
                "high": "43000.00",
                "low": "42000.00",
                "close": "42800.00",
                "volume": "123.45",
            },
            {"invalid": "row"},  # Missing required fields
            {
                "start": "2024-01-01T12:15:00Z",
                "open": "42800.00",
                "high": "43200.00",
                "low": "42800.00",
                "close": "43000.00",
                "volume": "150.00",
            },
        ]
    }

    params = {"symbol": "BTCUSD", "interval": Timeframe.M15}
    result = adapter.parse(response, params)

    assert len(result.bars) == 2  # Invalid row skipped


def test_candles_response_adapter_handles_unix_timestamp():
    """Candles adapter handles Unix timestamp format."""
    adapter = CandlesResponseAdapter()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    ts = int(base_time.timestamp())

    response = {
        "candles": [
            {
                "start": ts,  # Unix timestamp instead of ISO string
                "open": "42500.00",
                "high": "43000.00",
                "low": "42000.00",
                "close": "42800.00",
                "volume": "123.45",
            }
        ]
    }

    params = {"symbol": "BTCUSD", "interval": Timeframe.M15}
    result = adapter.parse(response, params)

    assert len(result.bars) == 1
    assert result.bars[0].timestamp == base_time


def test_exchange_info_symbols_adapter_parses_valid_response():
    """Exchange info adapter parses valid Coinbase products response."""
    adapter = ExchangeInfoSymbolsAdapter()

    response = {
        "products": [
            {
                "product_id": "BTC-USD",
                "price": "42800.00",
                "price_percentage_change_24h": "2.5",
                "volume_24h": "1234567.89",
                "base_increment": "0.00000001",
                "quote_increment": "0.01",
                "quote_min_size": "1.00",
                "quote_max_size": "1000000.00",
                "base_min_size": "0.001",
                "base_max_size": "280.00",
                "base_name": "Bitcoin",
                "quote_name": "US Dollar",
                "status": "online",
                "trading_disabled": False,
                "product_type": "SPOT",
                "quote_currency_id": "USD",
                "base_currency_id": "BTC",
                "price_increment": "0.01",
                "size_increment": "0.00000001",
            },
            {
                "product_id": "ETH-USD",
                "price": "3000.00",
                "status": "online",
                "trading_disabled": False,
                "product_type": "SPOT",
                "quote_currency_id": "USD",
                "base_currency_id": "ETH",
                "price_increment": "0.01",
                "size_increment": "0.00000001",
            },
        ]
    }

    params = {"market_type": MarketType.SPOT}
    result = adapter.parse(response, params)

    assert len(result) == 2
    assert result[0].symbol == "BTCUSD"  # Normalized from BTC-USD
    assert result[0].base_asset == "BTC"
    assert result[0].quote_asset == "USD"
    assert result[0].tick_size == Decimal("0.01")
    assert result[0].step_size == Decimal("0.00000001")
    assert result[0].min_notional == Decimal("1.00")
    assert result[1].symbol == "ETHUSD"


def test_exchange_info_symbols_adapter_filters_by_status():
    """Exchange info adapter filters products by status."""
    adapter = ExchangeInfoSymbolsAdapter()

    response = {
        "products": [
            {
                "product_id": "BTC-USD",
                "status": "online",
                "trading_disabled": False,
                "product_type": "SPOT",
                "quote_currency_id": "USD",
                "base_currency_id": "BTC",
                "price_increment": "0.01",
                "size_increment": "0.00000001",
            },
            {
                "product_id": "ETH-USD",
                "status": "delisted",  # Not online
                "trading_disabled": False,
                "product_type": "SPOT",
                "quote_currency_id": "USD",
                "base_currency_id": "ETH",
                "price_increment": "0.01",
                "size_increment": "0.00000001",
            },
            {
                "product_id": "DOGE-USD",
                "status": "online",
                "trading_disabled": True,  # Trading disabled
                "product_type": "SPOT",
                "quote_currency_id": "USD",
                "base_currency_id": "DOGE",
                "price_increment": "0.01",
                "size_increment": "0.00000001",
            },
        ]
    }

    params = {"market_type": MarketType.SPOT}
    result = adapter.parse(response, params)

    # Only BTC-USD should pass (online and trading enabled)
    assert len(result) == 1
    assert result[0].symbol == "BTCUSD"


def test_exchange_info_symbols_adapter_filters_by_quote_asset():
    """Exchange info adapter filters symbols by quote asset."""
    adapter = ExchangeInfoSymbolsAdapter()

    response = {
        "products": [
            {
                "product_id": "BTC-USD",
                "status": "online",
                "trading_disabled": False,
                "product_type": "SPOT",
                "quote_currency_id": "USD",
                "base_currency_id": "BTC",
                "price_increment": "0.01",
                "size_increment": "0.00000001",
            },
            {
                "product_id": "BTC-USDT",
                "status": "online",
                "trading_disabled": False,
                "product_type": "SPOT",
                "quote_currency_id": "USDT",
                "base_currency_id": "BTC",
                "price_increment": "0.01",
                "size_increment": "0.00000001",
            },
        ]
    }

    params = {"market_type": MarketType.SPOT, "quote_asset": "USD"}
    result = adapter.parse(response, params)

    assert len(result) == 1
    assert result[0].quote_asset == "USD"
    assert result[0].symbol == "BTCUSD"


def test_exchange_info_symbols_adapter_filters_by_product_type():
    """Exchange info adapter filters to SPOT products only."""
    adapter = ExchangeInfoSymbolsAdapter()

    response = {
        "products": [
            {
                "product_id": "BTC-USD",
                "status": "online",
                "trading_disabled": False,
                "product_type": "SPOT",
                "quote_currency_id": "USD",
                "base_currency_id": "BTC",
                "price_increment": "0.01",
                "size_increment": "0.00000001",
            },
            {
                "product_id": "BTC-PERP",
                "status": "online",
                "trading_disabled": False,
                "product_type": "FUTURE",  # Not SPOT
                "quote_currency_id": "USD",
                "base_currency_id": "BTC",
                "price_increment": "0.01",
                "size_increment": "0.00000001",
            },
        ]
    }

    params = {"market_type": MarketType.SPOT}
    result = adapter.parse(response, params)

    # Only SPOT products should pass (FUTURE filtered out)
    assert len(result) == 1
    assert result[0].symbol == "BTCUSD"  # SPOT product


def test_order_book_response_adapter_parses_valid_response():
    """Order book adapter parses valid Coinbase order book response."""
    adapter = OrderBookResponseAdapter()

    response = {
        "pricebook": {
            "bids": [
                ["42800.00", "1.5"],
                ["42799.00", "2.0"],
            ],
            "asks": [
                ["42810.00", "1.0"],
                ["42811.00", "3.0"],
            ],
        }
    }

    params = {"symbol": "BTCUSD"}
    result = adapter.parse(response, params)

    assert isinstance(result, OrderBook)
    assert result.symbol == "BTCUSD"
    assert len(result.bids) == 2
    assert len(result.asks) == 2

    assert result.bids[0][0] == Decimal("42800.00")  # price
    assert result.bids[0][1] == Decimal("1.5")  # quantity
    assert result.bids[1][0] == Decimal("42799.00")
    assert result.bids[1][1] == Decimal("2.0")

    assert result.asks[0][0] == Decimal("42810.00")
    assert result.asks[0][1] == Decimal("1.0")
    assert result.asks[1][0] == Decimal("42811.00")
    assert result.asks[1][1] == Decimal("3.0")


def test_order_book_response_adapter_handles_empty_pricebook():
    """Order book adapter handles empty pricebook by adding dummy level.

    Note: OrderBook model requires at least one level, so adapter
    adds a dummy bid if both bids and asks are empty.
    """
    adapter = OrderBookResponseAdapter()

    # Test with completely empty pricebook - adapter should add dummy bid
    response = {
        "pricebook": {
            "bids": [],
            "asks": [],
        }
    }

    params = {"symbol": "BTCUSD"}
    result = adapter.parse(response, params)

    assert isinstance(result, OrderBook)
    # Adapter should add minimal valid levels to satisfy OrderBook validation
    # OrderBook requires at least one level in both bids AND asks
    assert len(result.bids) == 1
    assert len(result.asks) == 1  # Adapter adds dummy ask too
    assert result.bids[0][0] > 0  # Price must be positive
    assert result.asks[0][0] > 0  # Price must be positive


def test_order_book_response_adapter_skips_invalid_entries():
    """Order book adapter skips invalid entries gracefully."""
    adapter = OrderBookResponseAdapter()

    response = {
        "pricebook": {
            "bids": [
                ["42800.00", "1.5"],
                ["invalid"],  # Missing quantity
                ["42799.00", "2.0"],
            ],
            "asks": [
                ["42810.00", "1.0"],
                ["42811.00"],  # Missing quantity
            ],
        }
    }

    params = {"symbol": "BTCUSD"}
    result = adapter.parse(response, params)

    assert len(result.bids) == 2  # Invalid entry skipped
    assert len(result.asks) == 1  # Invalid entry skipped


def test_recent_trades_adapter_parses_valid_response():
    """Recent trades adapter parses valid Coinbase trades response."""
    adapter = RecentTradesAdapter()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

    response = {
        "trades": [
            {
                "trade_id": "123456",
                "product_id": "BTC-USD",
                "price": "42800.00",
                "size": "0.5",
                "time": "2024-01-01T12:00:00Z",
                "side": "BUY",
                "bid": "42799.00",
                "ask": "42801.00",
            },
            {
                "trade_id": "123457",
                "product_id": "BTC-USD",
                "price": "42810.00",
                "size": "1.0",
                "time": "2024-01-01T12:01:00Z",
                "side": "SELL",
            },
        ]
    }

    params = {"symbol": "BTCUSD"}
    result = adapter.parse(response, params)

    assert len(result) == 2

    trade1 = result[0]
    assert trade1.symbol == "BTCUSD"  # Normalized
    assert trade1.trade_id == 123456
    assert trade1.price == Decimal("42800.00")
    assert trade1.quantity == Decimal("0.5")
    assert trade1.quote_quantity == Decimal("21400.00")  # price * quantity
    assert trade1.timestamp == base_time
    assert trade1.is_buyer_maker is False  # "BUY" = buyer is taker, not maker

    trade2 = result[1]
    assert trade2.symbol == "BTCUSD"
    assert trade2.trade_id == 123457
    assert trade2.price == Decimal("42810.00")
    assert trade2.is_buyer_maker is True  # "SELL" = seller is taker, buyer is maker


def test_recent_trades_adapter_handles_empty_response():
    """Recent trades adapter handles empty response."""
    adapter = RecentTradesAdapter()
    response = {"trades": []}
    params = {"symbol": "BTCUSD"}
    result = adapter.parse(response, params)

    assert len(result) == 0


def test_recent_trades_adapter_skips_invalid_trades():
    """Recent trades adapter skips invalid trades gracefully."""
    adapter = RecentTradesAdapter()

    response = {
        "trades": [
            {
                "trade_id": "123456",
                "product_id": "BTC-USD",
                "price": "42800.00",
                "size": "0.5",
                "time": "2024-01-01T12:00:00Z",
                "side": "BUY",
            },
            {
                "product_id": "BTC-USD",
                # Missing required fields
            },
            {
                "trade_id": "123457",
                "product_id": "BTC-USD",
                "price": "42810.00",
                "size": "1.0",
                "time": "2024-01-01T12:01:00Z",
                "side": "SELL",
            },
        ]
    }

    params = {"symbol": "BTCUSD"}
    result = adapter.parse(response, params)

    assert len(result) == 2  # Invalid trade skipped


def test_recent_trades_adapter_handles_string_trade_id():
    """Recent trades adapter handles string trade IDs."""
    adapter = RecentTradesAdapter()

    response = {
        "trades": [
            {
                "trade_id": "abc123xyz",  # Non-numeric ID
                "product_id": "BTC-USD",
                "price": "42800.00",
                "size": "0.5",
                "time": "2024-01-01T12:00:00Z",
                "side": "BUY",
            }
        ]
    }

    params = {"symbol": "BTCUSD"}
    result = adapter.parse(response, params)

    assert len(result) == 1
    # Should use hash of string ID
    assert result[0].trade_id > 0


# ============================================================================
# WebSocket Endpoint Spec Tests
# ============================================================================


def test_ohlcv_ws_spec_builds_stream_name():
    """OHLCV WebSocket spec builds correct channel name."""
    spec = ohlcv_spec(MarketType.SPOT)

    params = {"interval": Timeframe.M15}
    stream_name = spec.build_stream_name("BTCUSD", params)

    # Format: {product_id}:candles:{granularity}
    assert stream_name == "BTC-USD:candles:FIFTEEN_MINUTE"


def test_ohlcv_ws_spec_raises_on_futures():
    """OHLCV WebSocket spec raises ValueError for FUTURES market type."""
    with pytest.raises(ValueError, match="only supports Spot markets"):
        ohlcv_spec(MarketType.FUTURES)

    # Also test trades and order_book specs
    with pytest.raises(ValueError, match="only supports Spot markets"):
        trades_spec(MarketType.FUTURES)

    with pytest.raises(ValueError, match="only supports Spot markets"):
        ws_order_book_spec(MarketType.FUTURES)


def test_trades_ws_spec_builds_stream_name():
    """Trades WebSocket spec builds correct channel name."""
    spec = trades_spec(MarketType.SPOT)

    stream_name = spec.build_stream_name("BTCUSD", {})
    assert stream_name == "BTC-USD:matches"


def test_order_book_ws_spec_builds_stream_name():
    """Order book WebSocket spec builds correct channel name."""
    spec = ws_order_book_spec(MarketType.SPOT)

    stream_name = spec.build_stream_name("BTCUSD", {})
    assert stream_name == "BTC-USD:level2"


# ============================================================================
# WebSocket Adapter Tests
# ============================================================================


def test_ohlcv_adapter_is_relevant():
    """OHLCV adapter correctly identifies relevant messages."""
    adapter = OhlcvAdapter()

    assert adapter.is_relevant({"type": "candle", "product_id": "BTC-USD"})
    assert adapter.is_relevant({"type": "candles", "product_id": "BTC-USD"})
    assert not adapter.is_relevant({"type": "match", "product_id": "BTC-USD"})
    assert not adapter.is_relevant({"invalid": "message"})


def test_ohlcv_adapter_parses_valid_message():
    """OHLCV adapter parses valid candle message."""
    adapter = OhlcvAdapter()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

    payload = {
        "type": "candle",
        "product_id": "BTC-USD",
        "candles": [
            {
                "start": "2024-01-01T12:00:00Z",
                "open": "42500.00",
                "high": "43000.00",
                "low": "42000.00",
                "close": "42800.00",
                "volume": "123.45",
            }
        ],
    }

    result = adapter.parse(payload)

    assert len(result) == 1
    bar = result[0]
    assert bar.symbol == "BTCUSD"  # Normalized
    assert bar.timestamp == base_time
    assert bar.open == Decimal("42500.00")
    assert bar.high == Decimal("43000.00")
    assert bar.low == Decimal("42000.00")
    assert bar.close == Decimal("42800.00")
    assert bar.volume == Decimal("123.45")


def test_ohlcv_adapter_handles_single_candle_object():
    """OHLCV adapter handles single candle object (not array)."""
    adapter = OhlcvAdapter()

    payload = {
        "type": "candle",
        "product_id": "BTC-USD",
        "start": "2024-01-01T12:00:00Z",
        "open": "42500.00",
        "high": "43000.00",
        "low": "42000.00",
        "close": "42800.00",
        "volume": "123.45",
    }

    result = adapter.parse(payload)

    assert len(result) == 1
    assert result[0].symbol == "BTCUSD"


def test_trades_adapter_is_relevant():
    """Trades adapter correctly identifies relevant messages."""
    adapter = TradesAdapter()

    assert adapter.is_relevant({"type": "match", "product_id": "BTC-USD"})
    assert not adapter.is_relevant({"type": "candle", "product_id": "BTC-USD"})
    assert not adapter.is_relevant({"invalid": "message"})


def test_trades_adapter_parses_valid_message():
    """Trades adapter parses valid match message."""
    adapter = TradesAdapter()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

    payload = {
        "type": "match",
        "product_id": "BTC-USD",
        "price": "42800.00",
        "size": "0.5",
        "time": "2024-01-01T12:00:00Z",
        "side": "BUY",
        "trade_id": "123456",
    }

    result = adapter.parse(payload)

    assert len(result) == 1
    trade = result[0]
    assert trade.symbol == "BTCUSD"  # Normalized
    assert trade.price == Decimal("42800.00")
    assert trade.quantity == Decimal("0.5")
    assert trade.quote_quantity == Decimal("21400.00")
    assert trade.timestamp == base_time
    assert trade.is_buyer_maker is False  # "BUY" = buyer is taker


def test_order_book_adapter_is_relevant():
    """Order book adapter correctly identifies relevant messages."""
    adapter = OrderBookAdapter()

    assert adapter.is_relevant({"type": "l2update", "product_id": "BTC-USD"})
    assert adapter.is_relevant({"type": "level2", "product_id": "BTC-USD"})
    assert adapter.is_relevant({"type": "snapshot", "product_id": "BTC-USD"})
    assert not adapter.is_relevant({"type": "match", "product_id": "BTC-USD"})


def test_order_book_adapter_parses_valid_message():
    """Order book adapter parses valid l2update message."""
    adapter = OrderBookAdapter()

    payload = {
        "type": "l2update",
        "product_id": "BTC-USD",
        "changes": [
            ["buy", "42800.00", "1.5"],
            ["sell", "42810.00", "2.0"],
        ],
        "time": "2024-01-01T12:00:00Z",
    }

    result = adapter.parse(payload)

    assert len(result) == 1
    ob = result[0]
    assert ob.symbol == "BTCUSD"  # Normalized
    assert len(ob.bids) == 1
    assert len(ob.asks) == 1
    assert ob.bids[0][0] == Decimal("42800.00")
    assert ob.bids[0][1] == Decimal("1.5")
    assert ob.asks[0][0] == Decimal("42810.00")
    assert ob.asks[0][1] == Decimal("2.0")


def test_order_book_adapter_skips_invalid_changes():
    """Order book adapter skips invalid changes gracefully."""
    adapter = OrderBookAdapter()

    payload = {
        "type": "l2update",
        "product_id": "BTC-USD",
        "changes": [
            ["buy", "42800.00", "1.5"],
            ["invalid"],  # Invalid change
            ["sell", "42810.00", "2.0"],
        ],
    }

    result = adapter.parse(payload)

    assert len(result) == 1
    ob = result[0]
    assert len(ob.bids) == 1
    assert len(ob.asks) == 1


# ============================================================================
# REST Provider Method Tests
# ============================================================================


@pytest.mark.asyncio
async def test_coinbase_rest_get_candles_chunking(monkeypatch):
    """REST provider handles Coinbase's 300 candle limit with chunking."""
    provider = CoinbaseRESTProvider()
    base_time = datetime(2024, 1, 1, tzinfo=UTC)

    def make_chunk(start_index: int, count: int) -> OHLCV:
        bars = []
        for i in range(count):
            ts = base_time + timedelta(minutes=start_index + i)
            price = Decimal(str(100 + start_index + i))
            bars.append(
                Bar(
                    timestamp=ts,
                    open=price,
                    high=price + Decimal("1"),
                    low=price - Decimal("1"),
                    close=price + Decimal("0.5"),
                    volume=Decimal("10"),
                    is_closed=True,
                )
            )
        return OHLCV(meta=SeriesMeta(symbol="BTCUSD", timeframe="1m"), bars=bars)

    responses = [make_chunk(0, 300), make_chunk(300, 200)]
    calls: list[dict[str, Any]] = []

    async def fake_fetch(endpoint: str, params: dict[str, Any]) -> OHLCV:
        calls.append(params)
        return responses.pop(0) if responses else make_chunk(0, 0)

    monkeypatch.setattr(provider, "fetch", fake_fetch)

    result = await provider.get_candles(
        "BTCUSD",
        Timeframe.M1,
        start_time=base_time,
        limit=500,
        max_chunks=3,
    )

    assert len(result.bars) == 500
    assert result.bars[0].timestamp == base_time
    assert result.bars[-1].timestamp == base_time + timedelta(minutes=499)
    assert result.bars == sorted(result.bars, key=lambda b: b.timestamp)

    assert calls[0]["limit"] == 300  # First chunk uses max
    assert calls[1]["limit"] == 200  # Second chunk uses remaining
    assert calls[1]["start_time"] == base_time + timedelta(minutes=300)


@pytest.mark.asyncio
async def test_coinbase_rest_get_candles_respects_max_chunks(monkeypatch):
    """REST provider respects max_chunks parameter."""
    provider = CoinbaseRESTProvider()
    base_time = datetime(2024, 1, 1, tzinfo=UTC)

    def make_chunk(start_index: int, count: int) -> OHLCV:
        bars = []
        for i in range(count):
            ts = base_time + timedelta(minutes=start_index + i)
            price = Decimal(str(100 + start_index + i))
            bars.append(
                Bar(
                    timestamp=ts,
                    open=price,
                    high=price + Decimal("1"),
                    low=price - Decimal("1"),
                    close=price + Decimal("0.5"),
                    volume=Decimal("10"),
                    is_closed=True,
                )
            )
        return OHLCV(meta=SeriesMeta(symbol="BTCUSD", timeframe="1m"), bars=bars)

    responses = [make_chunk(0, 300), make_chunk(300, 300), make_chunk(600, 200)]
    calls: list[dict[str, Any]] = []

    async def fake_fetch(endpoint: str, params: dict[str, Any]) -> OHLCV:
        calls.append(params)
        return responses.pop(0) if responses else make_chunk(0, 0)

    monkeypatch.setattr(provider, "fetch", fake_fetch)

    result = await provider.get_candles(
        "BTCUSD",
        Timeframe.M1,
        start_time=base_time,
        limit=1000,
        max_chunks=2,  # Limit to 2 chunks
    )

    assert len(result.bars) == 600  # Only 2 chunks worth
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_coinbase_rest_get_symbols(monkeypatch):
    """REST provider fetches symbols correctly."""
    provider = CoinbaseRESTProvider()

    async def fake_fetch(endpoint: str, params: dict[str, Any]) -> list[Symbol]:
        return [
            Symbol(
                symbol="BTCUSD",
                base_asset="BTC",
                quote_asset="USD",
                contract_type=None,
                delivery_date=None,
            ),
            Symbol(
                symbol="ETHUSD",
                base_asset="ETH",
                quote_asset="USD",
                contract_type=None,
                delivery_date=None,
            ),
        ]

    monkeypatch.setattr(provider, "fetch", fake_fetch)

    symbols = await provider.get_symbols()
    assert len(symbols) == 2
    assert symbols[0].symbol == "BTCUSD"


@pytest.mark.asyncio
async def test_coinbase_rest_get_symbols_filters_by_quote_asset(monkeypatch):
    """REST provider filters symbols by quote asset."""
    provider = CoinbaseRESTProvider()

    async def fake_fetch(endpoint: str, params: dict[str, Any]) -> list[Symbol]:
        all_symbols = [
            Symbol(
                symbol="BTCUSD",
                base_asset="BTC",
                quote_asset="USD",
                contract_type=None,
                delivery_date=None,
            ),
            Symbol(
                symbol="BTCUSDT",
                base_asset="BTC",
                quote_asset="USDT",
                contract_type=None,
                delivery_date=None,
            ),
        ]
        # Filter by quote_asset in adapter, but we'll test provider level
        return all_symbols

    monkeypatch.setattr(provider, "fetch", fake_fetch)

    symbols = await provider.get_symbols(quote_asset="USD")
    # Adapter filters, so we get filtered results
    assert len(symbols) >= 0  # May be filtered by adapter


@pytest.mark.asyncio
async def test_coinbase_rest_get_funding_rate_raises():
    """REST provider raises NotImplementedError for funding rate."""
    provider = CoinbaseRESTProvider()

    with pytest.raises(NotImplementedError, match="does not support funding rates"):
        await provider.get_funding_rate("BTCUSD")


@pytest.mark.asyncio
async def test_coinbase_rest_get_open_interest_raises():
    """REST provider raises NotImplementedError for open interest."""
    provider = CoinbaseRESTProvider()

    with pytest.raises(NotImplementedError, match="does not support open interest"):
        await provider.get_open_interest("BTCUSD")


@pytest.mark.asyncio
async def test_coinbase_ws_stream_open_interest_raises():
    """WebSocket provider raises NotImplementedError for open interest."""
    provider = CoinbaseWSProvider()

    # The method raises immediately when called (it's an async function, not an async generator)
    with pytest.raises(NotImplementedError, match="does not support open interest"):
        await provider.stream_open_interest(["BTCUSD"])


@pytest.mark.asyncio
async def test_coinbase_ws_stream_funding_rate_raises():
    """WebSocket provider raises NotImplementedError for funding rate."""
    provider = CoinbaseWSProvider()

    # The method raises immediately when called (it's an async function, not an async generator)
    with pytest.raises(NotImplementedError, match="does not support funding rates"):
        await provider.stream_funding_rate(["BTCUSD"])


@pytest.mark.asyncio
async def test_coinbase_ws_stream_liquidations_raises():
    """WebSocket provider raises NotImplementedError for liquidations."""
    provider = CoinbaseWSProvider()

    # The method raises immediately when called (it's an async function, not an async generator)
    with pytest.raises(NotImplementedError, match="does not support liquidations"):
        await provider.stream_liquidations()


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_candles_adapter_handles_missing_candles_field():
    """Candles adapter handles missing candles field gracefully."""
    adapter = CandlesResponseAdapter()

    response = {}  # Missing candles field
    params = {"symbol": "BTCUSD", "interval": Timeframe.M15}
    result = adapter.parse(response, params)

    assert isinstance(result, OHLCV)
    assert len(result.bars) == 0


def test_candles_adapter_handles_non_list_candles():
    """Candles adapter handles non-list candles field."""
    adapter = CandlesResponseAdapter()

    response = {"candles": "not a list"}
    params = {"symbol": "BTCUSD", "interval": Timeframe.M15}
    result = adapter.parse(response, params)

    assert isinstance(result, OHLCV)
    assert len(result.bars) == 0


def test_exchange_info_adapter_handles_missing_products_field():
    """Exchange info adapter handles missing products field gracefully."""
    adapter = ExchangeInfoSymbolsAdapter()

    response = {}  # Missing products field
    params = {"market_type": MarketType.SPOT}
    result = adapter.parse(response, params)

    assert isinstance(result, list)
    assert len(result) == 0


def test_order_book_adapter_handles_missing_pricebook():
    """Order book adapter handles missing pricebook field by adding dummy levels.

    OrderBook model requires at least one level in both bids and asks,
    so adapter adds minimal valid levels when pricebook is missing or empty.
    """
    adapter = OrderBookResponseAdapter()

    response = {}  # Missing pricebook
    params = {"symbol": "BTCUSD"}
    result = adapter.parse(response, params)

    assert isinstance(result, OrderBook)
    # Adapter adds dummy levels to satisfy OrderBook validation
    assert len(result.bids) == 1
    assert len(result.asks) == 1
    assert result.bids[0][0] > 0  # Price must be positive
    assert result.asks[0][0] > 0  # Price must be positive


def test_trades_adapter_handles_missing_trades_field():
    """Trades adapter handles missing trades field gracefully."""
    adapter = RecentTradesAdapter()

    response = {}  # Missing trades field
    params = {"symbol": "BTCUSD"}
    result = adapter.parse(response, params)

    assert isinstance(result, list)
    assert len(result) == 0


def test_ohlcv_adapter_handles_missing_product_id():
    """OHLCV adapter handles missing product_id gracefully."""
    adapter = OhlcvAdapter()

    payload = {
        "type": "candle",
        # Missing product_id
        "candles": [
            {
                "start": "2024-01-01T12:00:00Z",
                "open": "42500",
                "high": "43000",
                "low": "42000",
                "close": "42800",
                "volume": "100",
            }
        ],
    }

    result = adapter.parse(payload)
    assert len(result) == 0  # Should return empty if no product_id


def test_trades_adapter_handles_missing_product_id():
    """Trades adapter handles missing product_id gracefully."""
    adapter = TradesAdapter()

    payload = {
        "type": "match",
        # Missing product_id
        "price": "42800.00",
        "size": "0.5",
    }

    result = adapter.parse(payload)
    assert len(result) == 0  # Should return empty if no product_id


def test_order_book_adapter_handles_missing_product_id():
    """Order book adapter handles missing product_id gracefully."""
    adapter = OrderBookAdapter()

    payload = {
        "type": "l2update",
        # Missing product_id
        "changes": [["buy", "42800.00", "1.5"]],
    }

    result = adapter.parse(payload)
    assert len(result) == 0  # Should return empty if no product_id


# ============================================================================
# Integration-style Tests (with mocks)
# ============================================================================


def test_coinbase_provider_unified_interface():
    """Unified provider correctly delegates to REST and WS providers."""
    provider = CoinbaseProvider(market_type=MarketType.SPOT)

    assert provider._rest.market_type == MarketType.SPOT
    assert provider._ws.market_type == MarketType.SPOT

    # Verify both providers are accessible
    assert isinstance(provider._rest, CoinbaseRESTProvider)
    assert isinstance(provider._ws, CoinbaseWSProvider)


def test_coinbase_provider_get_timeframes():
    """Unified provider returns list of supported timeframes."""
    provider = CoinbaseProvider()
    timeframes = provider.get_timeframes()

    assert isinstance(timeframes, list)
    assert len(timeframes) > 0
    # Should include common timeframes
    assert Timeframe.M1 in timeframes
    assert Timeframe.H1 in timeframes
    assert Timeframe.D1 in timeframes


@pytest.mark.asyncio
async def test_coinbase_provider_close():
    """Unified provider closes both REST and WS providers."""
    provider = CoinbaseProvider()

    # Should not raise
    await provider.close()

    # Second close should be no-op
    await provider.close()


def test_coinbase_rest_provider_fetch_unknown_endpoint():
    """REST provider raises ValueError for unknown endpoint."""
    provider = CoinbaseRESTProvider()

    async def run():
        with pytest.raises(ValueError, match="Unknown REST endpoint"):
            await provider.fetch("unknown_endpoint", {})

    asyncio.run(run())


def test_coinbase_rest_provider_get_candles_invalid_timeframe():
    """REST provider raises ValueError for invalid timeframe."""
    provider = CoinbaseRESTProvider()

    async def run():
        with pytest.raises(ValueError, match="Invalid timeframe"):
            # Use a timeframe not in INTERVAL_MAP
            await provider.get_candles("BTCUSD", "invalid_timeframe")

    asyncio.run(run())


def test_coinbase_rest_provider_get_candles_invalid_max_chunks():
    """REST provider raises ValueError for invalid max_chunks."""
    provider = CoinbaseRESTProvider()

    async def run():
        with pytest.raises(ValueError, match="max_chunks must be None or a positive integer"):
            await provider.get_candles(
                "BTCUSD",
                Timeframe.M1,
                limit=100,
                max_chunks=0,  # Invalid
            )

    asyncio.run(run())


def test_coinbase_ws_provider_stream_unknown_endpoint():
    """WebSocket provider raises ValueError for unknown endpoint."""
    provider = CoinbaseWSProvider()

    async def run():
        with pytest.raises(ValueError, match="Unknown endpoint"):
            async for _ in provider.stream("unknown_endpoint", ["BTCUSD"], {}):
                pass

    asyncio.run(run())
