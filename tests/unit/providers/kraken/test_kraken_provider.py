"""Unit tests for Kraken REST/WS providers (decoupled)."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from laakhay.data.core import MarketType, Timeframe
from laakhay.data.core.exceptions import DataError
from laakhay.data.models import (
    OHLCV,
    Bar,
    OrderBook,
    SeriesMeta,
)
from laakhay.data.providers import (
    KrakenProvider,
    KrakenRESTProvider,
    KrakenWSProvider,
)
from laakhay.data.providers.kraken.constants import (
    INTERVAL_MAP,
    normalize_symbol_from_kraken,
    normalize_symbol_to_kraken,
)
from laakhay.data.providers.kraken.rest.adapters import (
    CandlesResponseAdapter,
    ExchangeInfoSymbolsAdapter,
    FundingRateAdapter,
    OpenInterestCurrentAdapter,
    OpenInterestHistAdapter,
    OrderBookResponseAdapter,
    RecentTradesAdapter,
    _extract_result,
)
from laakhay.data.providers.kraken.rest.endpoints import (
    candles_spec,
    exchange_info_spec,
    funding_rate_spec,
    open_interest_current_spec,
    order_book_spec,
    recent_trades_spec,
)
from laakhay.data.providers.kraken.ws.adapters import (
    FundingRateAdapter as WSFundingRateAdapter,
)
from laakhay.data.providers.kraken.ws.adapters import (
    LiquidationsAdapter,
    MarkPriceAdapter,
    OhlcvAdapter,
    OpenInterestAdapter,
    OrderBookAdapter,
    TradesAdapter,
)
from laakhay.data.providers.kraken.ws.endpoints import (
    funding_rate_spec as ws_funding_rate_spec,
)
from laakhay.data.providers.kraken.ws.endpoints import (
    ohlcv_spec,
    open_interest_spec,
    trades_spec,
)
from laakhay.data.providers.kraken.ws.endpoints import (
    order_book_spec as ws_order_book_spec,
)

# ============================================================================
# Provider Instantiation Tests
# ============================================================================


def test_kraken_rest_provider_instantiation_defaults_to_spot():
    """REST provider defaults to SPOT market type."""
    provider = KrakenRESTProvider()
    assert provider.market_type == MarketType.SPOT


def test_kraken_rest_provider_instantiation_futures():
    """REST provider can be instantiated with FUTURES market type."""
    provider = KrakenRESTProvider(market_type=MarketType.FUTURES)
    assert provider.market_type == MarketType.FUTURES


def test_kraken_ws_provider_instantiation():
    """WebSocket provider defaults to SPOT and can be configured."""
    ws = KrakenWSProvider()
    assert ws.market_type == MarketType.SPOT

    ws_fut = KrakenWSProvider(market_type=MarketType.FUTURES)
    assert ws_fut.market_type == MarketType.FUTURES


def test_kraken_provider_instantiation_defaults_to_spot():
    """Unified provider defaults to SPOT market type."""
    provider = KrakenProvider()
    assert provider.market_type == MarketType.SPOT


def test_kraken_provider_instantiation_futures():
    """Unified provider can be instantiated with FUTURES market type."""
    provider = KrakenProvider(market_type=MarketType.FUTURES)
    assert provider.market_type == MarketType.FUTURES


def test_kraken_provider_context_manager_closes():
    """Unified provider works as context manager."""

    async def run() -> bool:
        async with KrakenProvider() as provider:
            return provider.market_type == MarketType.SPOT

    assert asyncio.run(run())


# ============================================================================
# Constants Tests
# ============================================================================


def test_kraken_interval_mapping_constants():
    """Verify interval mappings match Kraken API format."""
    assert INTERVAL_MAP[Timeframe.M1] == "1"
    assert INTERVAL_MAP[Timeframe.M5] == "5"
    assert INTERVAL_MAP[Timeframe.M15] == "15"
    assert INTERVAL_MAP[Timeframe.M30] == "30"
    assert INTERVAL_MAP[Timeframe.H1] == "60"
    assert INTERVAL_MAP[Timeframe.H4] == "240"
    assert INTERVAL_MAP[Timeframe.D1] == "1440"
    assert INTERVAL_MAP[Timeframe.W1] == "10080"


def test_symbol_normalization_to_kraken_spot():
    """Symbol normalization converts standard format to Kraken Spot format."""
    assert normalize_symbol_to_kraken("BTCUSD", MarketType.SPOT) == "XBT/USD"
    assert normalize_symbol_to_kraken("BTCUSDT", MarketType.SPOT) == "XBT/USDT"
    assert normalize_symbol_to_kraken("ETHUSD", MarketType.SPOT) == "ETH/USD"
    assert normalize_symbol_to_kraken("SOLUSDT", MarketType.SPOT) == "SOL/USDT"


def test_symbol_normalization_to_kraken_futures():
    """Symbol normalization converts standard format to Kraken Futures format."""
    assert normalize_symbol_to_kraken("BTCUSD", MarketType.FUTURES) == "PI_XBTUSD"
    assert normalize_symbol_to_kraken("BTCUSDT", MarketType.FUTURES) == "PI_XBTUSD"
    assert normalize_symbol_to_kraken("ETHUSD", MarketType.FUTURES) == "PI_ETHUSD"
    assert normalize_symbol_to_kraken("SOLUSDT", MarketType.FUTURES) == "PI_SOLUSD"


def test_symbol_normalization_from_kraken_spot():
    """Symbol normalization converts Kraken Spot format to standard format."""
    assert normalize_symbol_from_kraken("XBT/USD", MarketType.SPOT) == "BTCUSD"
    assert normalize_symbol_from_kraken("XBT/USDT", MarketType.SPOT) == "BTCUSDT"
    assert normalize_symbol_from_kraken("ETH/USD", MarketType.SPOT) == "ETHUSD"
    assert normalize_symbol_from_kraken("SOL/USDT", MarketType.SPOT) == "SOLUSDT"


def test_symbol_normalization_from_kraken_futures():
    """Symbol normalization converts Kraken Futures format to standard format."""
    assert normalize_symbol_from_kraken("PI_XBTUSD", MarketType.FUTURES) == "BTCUSD"
    assert normalize_symbol_from_kraken("PI_ETHUSD", MarketType.FUTURES) == "ETHUSD"
    assert normalize_symbol_from_kraken("PI_SOLUSD", MarketType.FUTURES) == "SOLUSD"


def test_symbol_normalization_fallback():
    """Symbol normalization handles unknown symbols with fallback."""
    # Unknown symbol should use fallback logic
    result_spot = normalize_symbol_to_kraken("UNKNOWNUSD", MarketType.SPOT)
    assert "USD" in result_spot or result_spot == "UNKNOWNUSD"

    result_futures = normalize_symbol_to_kraken("UNKNOWNUSD", MarketType.FUTURES)
    assert result_futures.startswith("PI_") or result_futures == "PI_UNKNOWNUSD"


# ============================================================================
# REST Endpoint Spec Tests
# ============================================================================


def test_candles_spec_builds_path_spot():
    """Candles endpoint spec builds correct path for Spot."""
    spec = candles_spec()
    params = {
        "market_type": MarketType.SPOT,
        "symbol": "BTCUSD",
    }
    path = spec.build_path(params)
    assert path == "/0/public/OHLCData"


def test_candles_spec_builds_path_futures():
    """Candles endpoint spec builds correct path for Futures."""
    spec = candles_spec()
    params = {
        "market_type": MarketType.FUTURES,
        "symbol": "BTCUSD",
    }
    path = spec.build_path(params)
    assert path == "/instruments/PI_XBTUSD/candles"


def test_candles_spec_builds_query_spot():
    """Candles endpoint spec builds correct query for Spot."""
    spec = candles_spec()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

    params = {
        "market_type": MarketType.SPOT,
        "symbol": "BTCUSD",
        "interval": Timeframe.M15,
        "start_time": base_time,
        "limit": 100,
    }

    query = spec.build_query(params)
    assert query["pair"] == "XBT/USD"
    assert query["interval"] == "15"
    assert query["since"] == int(base_time.timestamp())
    assert query["limit"] == 100


def test_candles_spec_builds_query_futures():
    """Candles endpoint spec builds correct query for Futures."""
    spec = candles_spec()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

    params = {
        "market_type": MarketType.FUTURES,
        "symbol": "BTCUSD",
        "interval": Timeframe.M15,
        "start_time": base_time,
        "end_time": base_time + timedelta(hours=1),
        "limit": 1000,
    }

    query = spec.build_query(params)
    assert query["interval"] == "15"
    assert query["start"] == int(base_time.timestamp() * 1000)
    assert query["end"] == int((base_time + timedelta(hours=1)).timestamp() * 1000)
    assert query["limit"] == 1000


def test_exchange_info_spec_builds_path():
    """Exchange info endpoint spec builds correct path."""
    spec_spot = exchange_info_spec()
    spec_futures = exchange_info_spec()

    params_spot = {"market_type": MarketType.SPOT}
    params_futures = {"market_type": MarketType.FUTURES}

    assert spec_spot.build_path(params_spot) == "/0/public/AssetPairs"
    assert spec_futures.build_path(params_futures) == "/instruments"


def test_order_book_spec_builds_query_spot():
    """Order book endpoint spec builds correct query for Spot."""
    spec = order_book_spec()
    params = {
        "market_type": MarketType.SPOT,
        "symbol": "BTCUSD",
        "limit": 100,
    }

    query = spec.build_query(params)
    assert query["pair"] == "XBT/USD"
    assert query["count"] == 100


def test_order_book_spec_builds_query_futures():
    """Order book endpoint spec builds correct query for Futures."""
    spec = order_book_spec()
    params = {
        "market_type": MarketType.FUTURES,
        "symbol": "BTCUSD",
        "limit": 100,
    }

    query = spec.build_query(params)
    assert query["symbol"] == "PI_XBTUSD"
    assert query["depth"] == 100  # Mapped to nearest supported depth


def test_recent_trades_spec_builds_query():
    """Recent trades endpoint spec builds correct query."""
    spec_spot = recent_trades_spec()
    spec_futures = recent_trades_spec()

    params_spot = {
        "market_type": MarketType.SPOT,
        "symbol": "BTCUSD",
        "limit": 50,
    }
    params_futures = {
        "market_type": MarketType.FUTURES,
        "symbol": "BTCUSD",
        "limit": 50,
    }

    query_spot = spec_spot.build_query(params_spot)
    query_futures = spec_futures.build_query(params_futures)

    assert query_spot["pair"] == "XBT/USD"
    assert query_spot["count"] == 50
    assert query_futures["symbol"] == "PI_XBTUSD"
    assert query_futures["limit"] == 50


def test_funding_rate_spec_raises_for_spot():
    """Funding rate endpoint spec raises ValueError for Spot."""
    spec = funding_rate_spec()
    params = {
        "market_type": MarketType.SPOT,
        "symbol": "BTCUSD",
    }

    with pytest.raises(ValueError, match="Futures-only"):
        spec.build_path(params)


def test_open_interest_spec_raises_for_spot():
    """Open interest endpoint spec raises ValueError for Spot."""
    spec = open_interest_current_spec()
    params = {
        "market_type": MarketType.SPOT,
        "symbol": "BTCUSD",
    }

    with pytest.raises(ValueError, match="Futures-only"):
        spec.build_path(params)


# ============================================================================
# REST Adapter Tests
# ============================================================================


def test_extract_result_handles_spot_response():
    """_extract_result handles Kraken Spot response format."""
    response = {
        "error": [],
        "result": {"XBT/USD": {"a": ["50000"], "b": ["49900"]}},
    }
    result = _extract_result(response, MarketType.SPOT)
    assert "XBT/USD" in result


def test_extract_result_handles_futures_response():
    """_extract_result handles Kraken Futures response format."""
    response = {
        "result": "ok",
        "candles": [
            {
                "time": 1704110400000,
                "open": "50000",
                "high": "50100",
                "low": "49900",
                "close": "50050",
                "volume": "100",
            }
        ],
    }
    result = _extract_result(response, MarketType.FUTURES)
    assert "candles" in result


def test_extract_result_raises_on_error():
    """_extract_result raises DataError on error response."""
    response = {"error": ["EGeneral:Invalid arguments"]}
    with pytest.raises(DataError, match="Kraken API error"):
        _extract_result(response, MarketType.SPOT)


def test_candles_response_adapter_parses_spot_response():
    """Candles adapter parses valid Kraken Spot response."""
    adapter = CandlesResponseAdapter()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    ts = int(base_time.timestamp())

    response = {
        "error": [],
        "result": {
            "XBT/USD": [
                [ts, "50000.5", "50100.0", "49900.0", "50050.0", "100.5", "100.0", 150],
            ],
        },
    }

    params = {
        "market_type": MarketType.SPOT,
        "symbol": "BTCUSD",
        "interval": Timeframe.M15,
    }
    result = adapter.parse(response, params)

    assert isinstance(result, OHLCV)
    assert result.meta.symbol == "BTCUSD"
    assert len(result.bars) == 1

    bar = result.bars[0]
    assert bar.timestamp == base_time
    assert bar.open == Decimal("50000.5")
    assert bar.high == Decimal("50100.0")
    assert bar.low == Decimal("49900.0")
    assert bar.close == Decimal("50050.0")
    assert bar.volume == Decimal("100.0")  # Volume is at index 6


def test_candles_response_adapter_parses_futures_response():
    """Candles adapter parses valid Kraken Futures response."""
    adapter = CandlesResponseAdapter()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    time_ms = int(base_time.timestamp() * 1000)

    response = {
        "result": "ok",
        "candles": [
            {
                "time": time_ms,
                "open": "50000.5",
                "high": "50100.0",
                "low": "49900.0",
                "close": "50050.0",
                "volume": "100.5",
            },
        ],
    }

    params = {
        "market_type": MarketType.FUTURES,
        "symbol": "BTCUSD",
        "interval": Timeframe.M15,
    }
    result = adapter.parse(response, params)

    assert isinstance(result, OHLCV)
    assert len(result.bars) == 1
    assert result.bars[0].timestamp == base_time


def test_exchange_info_symbols_adapter_parses_spot():
    """Exchange info adapter parses Spot symbols."""
    adapter = ExchangeInfoSymbolsAdapter()

    response = {
        "error": [],
        "result": {
            "XBT/USD": {
                "altname": "XBTUSD",
                "wsname": "XBT/USD",
                "base": "XBT",
                "quote": "USD",
                "status": "online",
                "tick_size": "0.1",
                "lot_decimals": 8,
                "ordermin": "1",
            },
        },
    }

    params = {"market_type": MarketType.SPOT}
    result = adapter.parse(response, params)

    assert len(result) == 1
    assert result[0].symbol == "BTCUSD"  # Normalized
    assert result[0].base_asset == "BTC"  # XBT converted to BTC
    assert result[0].quote_asset == "USD"


def test_exchange_info_symbols_adapter_parses_futures():
    """Exchange info adapter parses Futures symbols."""
    adapter = ExchangeInfoSymbolsAdapter()

    response = {
        "result": "ok",
        "instruments": [
            {
                "symbol": "PI_XBTUSD",
                "type": "perpetual",
                "underlying": "XBT",
                "quoteCurrency": "USD",
                "status": "open",
                "tickSize": "0.1",
                "contractSize": "1",
            },
        ],
    }

    params = {"market_type": MarketType.FUTURES}
    result = adapter.parse(response, params)

    assert len(result) >= 1  # At least one instrument parsed
    # Find the BTCUSD symbol
    btc_symbol = next((s for s in result if s.symbol == "BTCUSD"), None)
    assert btc_symbol is not None
    assert btc_symbol.base_asset == "BTC"  # XBT converted to BTC
    assert btc_symbol.quote_asset == "USD"
    assert btc_symbol.contract_type == "perpetual"


def test_order_book_response_adapter_parses_spot():
    """Order book adapter parses Spot response."""
    adapter = OrderBookResponseAdapter()

    response = {
        "error": [],
        "result": {
            "XBT/USD": {
                "bids": [["50000.5", "10.0", 1704110400], ["50000.0", "5.0", 1704110400]],
                "asks": [["50010.0", "8.0", 1704110400], ["50011.0", "12.0", 1704110400]],
            },
        },
    }

    params = {"market_type": MarketType.SPOT, "symbol": "BTCUSD"}
    result = adapter.parse(response, params)

    assert isinstance(result, OrderBook)
    assert result.symbol == "BTCUSD"
    assert len(result.bids) == 2
    assert len(result.asks) == 2
    assert result.bids[0][0] == Decimal("50000.5")


def test_order_book_response_adapter_parses_futures():
    """Order book adapter parses Futures response."""
    adapter = OrderBookResponseAdapter()

    response = {
        "result": "ok",
        "orderBook": {
            "bids": [["50000.5", "10.0"], ["50000.0", "5.0"]],
            "asks": [["50010.0", "8.0"], ["50011.0", "12.0"]],
            "serverTime": 1704110400000,
            "sequenceNumber": 12345,
        },
    }

    params = {"market_type": MarketType.FUTURES, "symbol": "BTCUSD"}
    result = adapter.parse(response, params)

    assert isinstance(result, OrderBook)
    assert result.last_update_id == 12345
    assert len(result.bids) == 2


def test_recent_trades_adapter_parses_spot():
    """Recent trades adapter parses Spot response."""
    adapter = RecentTradesAdapter()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    time_float = base_time.timestamp()

    response = {
        "error": [],
        "result": {
            "XBT/USD": [
                ["50000.5", "1.5", time_float, "b", "m", ""],
                ["50001.0", "2.0", time_float + 1, "s", "l", ""],
            ],
        },
    }

    params = {"market_type": MarketType.SPOT, "symbol": "BTCUSD"}
    result = adapter.parse(response, params)

    assert len(result) == 2
    assert result[0].symbol == "BTCUSD"
    assert result[0].price == Decimal("50000.5")
    assert result[0].is_buyer_maker is True  # "b" = buy = maker


def test_recent_trades_adapter_parses_futures():
    """Recent trades adapter parses Futures response."""
    adapter = RecentTradesAdapter()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    time_ms = int(base_time.timestamp() * 1000)

    response = {
        "result": "ok",
        "history": [
            {
                "time": time_ms,
                "price": "50000.5",
                "size": "1.5",
                "side": "buy",
                "trade_id": "12345",
            },
        ],
    }

    params = {"market_type": MarketType.FUTURES, "symbol": "BTCUSD"}
    result = adapter.parse(response, params)

    assert len(result) == 1
    assert result[0].symbol == "BTCUSD"
    assert result[0].price == Decimal("50000.5")
    assert result[0].is_buyer_maker is True  # "buy" = buyer is maker


def test_funding_rate_adapter_parses_futures():
    """Funding rate adapter parses Futures response."""
    adapter = FundingRateAdapter()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    time_ms = int(base_time.timestamp() * 1000)

    response = {
        "result": "ok",
        "fundingRates": [
            {
                "time": time_ms,
                "fundingRate": "0.0001",
                "markPrice": "50000.0",
            },
        ],
    }

    params = {"market_type": MarketType.FUTURES, "symbol": "BTCUSD"}
    result = adapter.parse(response, params)

    assert len(result) == 1
    assert result[0].funding_rate == Decimal("0.0001")
    assert result[0].mark_price == Decimal("50000.0")


def test_open_interest_current_adapter_parses_futures():
    """Open interest current adapter parses Futures response."""
    adapter = OpenInterestCurrentAdapter()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    time_ms = int(base_time.timestamp() * 1000)

    response = {
        "result": "ok",
        "ticker": {
            "openInterest": "1000000.5",
            "openInterestValue": "50000000000",
            "serverTime": time_ms,
        },
    }

    params = {"market_type": MarketType.FUTURES, "symbol": "BTCUSD"}
    result = adapter.parse(response, params)

    assert len(result) == 1
    assert result[0].open_interest == Decimal("1000000.5")
    assert result[0].open_interest_value == Decimal("50000000000")


def test_open_interest_hist_adapter_parses_futures():
    """Open interest historical adapter parses Futures response."""
    adapter = OpenInterestHistAdapter()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    time_ms = int(base_time.timestamp() * 1000)

    response = {
        "result": "ok",
        "openInterest": [
            {
                "time": time_ms,
                "openInterest": "1000000.5",
                "openInterestValue": "50000000000",
            },
        ],
    }

    params = {"market_type": MarketType.FUTURES, "symbol": "BTCUSD"}
    result = adapter.parse(response, params)

    assert len(result) == 1
    assert result[0].open_interest == Decimal("1000000.5")


# ============================================================================
# WebSocket Endpoint Spec Tests
# ============================================================================


def test_ohlcv_spec_builds_stream_name_spot():
    """OHLCV WebSocket spec builds correct stream name for Spot."""
    spec = ohlcv_spec(MarketType.SPOT)

    params = {"interval": Timeframe.M15}
    stream_name = spec.build_stream_name("BTCUSD", params)

    assert stream_name == "ohlc-XBT/USD-15"


def test_ohlcv_spec_builds_stream_name_futures():
    """OHLCV WebSocket spec builds correct stream name for Futures."""
    spec = ohlcv_spec(MarketType.FUTURES)

    params = {"interval": Timeframe.M15}
    stream_name = spec.build_stream_name("BTCUSD", params)

    assert stream_name == "ohlc-PI_XBTUSD-15"


def test_trades_spec_builds_stream_name():
    """Trades WebSocket spec builds correct stream name."""
    spec_spot = trades_spec(MarketType.SPOT)
    spec_futures = trades_spec(MarketType.FUTURES)

    assert spec_spot.build_stream_name("BTCUSD", {}) == "trade-XBT/USD"
    assert spec_futures.build_stream_name("BTCUSD", {}) == "trade-PI_XBTUSD"


def test_order_book_ws_spec_builds_stream_name():
    """Order book WebSocket spec builds correct stream name."""
    spec_spot = ws_order_book_spec(MarketType.SPOT)
    spec_futures = ws_order_book_spec(MarketType.FUTURES)

    params = {"update_speed": "100ms"}
    assert spec_spot.build_stream_name("BTCUSD", params) == "book-XBT/USD-10"
    assert spec_futures.build_stream_name("BTCUSD", params) == "book-PI_XBTUSD-10"


def test_open_interest_ws_spec_raises_for_spot():
    """Open interest WebSocket spec raises ValueError for Spot."""
    with pytest.raises(ValueError, match="Futures-only"):
        open_interest_spec(MarketType.SPOT)


def test_funding_rate_ws_spec_raises_for_spot():
    """Funding rate WebSocket spec raises ValueError for Spot."""
    with pytest.raises(ValueError, match="Futures-only"):
        ws_funding_rate_spec(MarketType.SPOT)


# ============================================================================
# WebSocket Adapter Tests
# ============================================================================


def test_ohlcv_adapter_is_relevant():
    """OHLCV adapter correctly identifies relevant messages."""
    adapter = OhlcvAdapter()

    assert adapter.is_relevant({"channel": "ohlc", "symbol": "PI_XBTUSD"})
    assert adapter.is_relevant({"event": "ohlc", "data": []})
    assert not adapter.is_relevant({"channel": "trade", "data": []})


def test_ohlcv_adapter_parses_valid_message():
    """OHLCV adapter parses valid candle message."""
    adapter = OhlcvAdapter()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    time_ms = int(base_time.timestamp() * 1000)

    payload = {
        "channel": "ohlc",
        "symbol": "PI_XBTUSD",
        "data": [
            {
                "time": time_ms,
                "open": "50000.5",
                "high": "50100.0",
                "low": "49900.0",
                "close": "50050.0",
                "volume": "100.5",
                "closed": True,
            },
        ],
    }

    result = adapter.parse(payload)

    assert len(result) == 1
    bar = result[0]
    assert bar.symbol == "BTCUSD"  # Normalized
    assert bar.timestamp == base_time
    assert bar.open == Decimal("50000.5")
    assert bar.is_closed is True


def test_trades_adapter_parses_valid_message():
    """Trades adapter parses valid trades message."""
    adapter = TradesAdapter()
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    time_ms = int(base_time.timestamp() * 1000)

    payload = {
        "channel": "trade",
        "symbol": "PI_XBTUSD",
        "data": [
            {
                "time": time_ms,
                "price": "50000.5",
                "size": "1.5",
                "side": "buy",
                "trade_id": "12345",
            },
        ],
    }

    result = adapter.parse(payload)

    assert len(result) == 1
    trade = result[0]
    assert trade.symbol == "BTCUSD"  # Normalized
    assert trade.price == Decimal("50000.5")
    assert trade.is_buyer_maker is True  # "buy" = buyer is maker


def test_order_book_adapter_parses_valid_message():
    """Order book adapter parses valid book message."""
    adapter = OrderBookAdapter()

    payload = {
        "channel": "book",
        "symbol": "PI_XBTUSD",
        "data": {
            "bids": [["50000.5", "10.0"], ["50000.0", "5.0"]],
            "asks": [["50010.0", "8.0"], ["50011.0", "12.0"]],
            "sequenceNumber": 12345,
        },
        "time": 1704110400000,
    }

    result = adapter.parse(payload)

    assert len(result) == 1
    ob = result[0]
    assert ob.symbol == "BTCUSD"  # Normalized
    assert len(ob.bids) == 2
    assert len(ob.asks) == 2
    assert ob.last_update_id == 12345


def test_open_interest_adapter_parses_valid_message():
    """Open interest adapter parses valid message."""
    adapter = OpenInterestAdapter()

    payload = {
        "channel": "open_interest",
        "symbol": "PI_XBTUSD",
        "data": {
            "openInterest": "1000000.5",
            "openInterestValue": "50000000000",
            "time": 1704110400000,
        },
    }

    result = adapter.parse(payload)

    assert len(result) == 1
    oi = result[0]
    assert oi.symbol == "BTCUSD"  # Normalized
    assert oi.open_interest == Decimal("1000000.5")


def test_funding_rate_adapter_parses_valid_message():
    """Funding rate adapter parses valid message."""
    adapter = WSFundingRateAdapter()

    payload = {
        "channel": "funding_rate",
        "symbol": "PI_XBTUSD",
        "data": {
            "fundingRate": "0.0001",
            "markPrice": "50000.0",
            "time": 1704110400000,
        },
    }

    result = adapter.parse(payload)

    assert len(result) == 1
    fr = result[0]
    assert fr.symbol == "BTCUSD"  # Normalized
    assert fr.funding_rate == Decimal("0.0001")


def test_mark_price_adapter_parses_valid_message():
    """Mark price adapter parses valid message."""
    adapter = MarkPriceAdapter()

    payload = {
        "channel": "ticker",
        "symbol": "PI_XBTUSD",
        "data": {
            "markPrice": "50000.0",
            "indexPrice": "49950.0",
            "fundingRate": "0.0001",
            "nextFundingTime": 1704114000000,
        },
        "time": 1704110400000,
    }

    result = adapter.parse(payload)

    assert len(result) == 1
    mp = result[0]
    assert mp.symbol == "BTCUSD"  # Normalized
    assert mp.mark_price == Decimal("50000.0")
    assert mp.index_price == Decimal("49950.0")


def test_liquidations_adapter_parses_valid_message():
    """Liquidations adapter parses valid message."""
    adapter = LiquidationsAdapter()

    payload = {
        "channel": "liquidation",
        "symbol": "PI_XBTUSD",
        "data": {
            "side": "BUY",
            "size": "10.5",
            "price": "50000.0",
            "time": 1704110400000,
        },
    }

    result = adapter.parse(payload)

    assert len(result) == 1
    liq = result[0]
    assert liq.symbol == "BTCUSD"  # Normalized
    assert liq.side == "BUY"
    assert liq.original_quantity == Decimal("10.5")


# ============================================================================
# REST Provider Method Tests
# ============================================================================


@pytest.mark.asyncio
async def test_kraken_rest_fetch_ohlcv_chunking(monkeypatch):
    """REST provider handles chunking for large candle requests."""
    provider = KrakenRESTProvider()
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

    responses = [make_chunk(0, 720), make_chunk(720, 200)]
    calls: list[dict[str, Any]] = []

    async def fake_fetch(endpoint: str, params: dict[str, Any]) -> OHLCV:
        calls.append(params)
        return responses.pop(0) if responses else make_chunk(0, 0)

    monkeypatch.setattr(provider, "fetch", fake_fetch)

    result = await provider.fetch_ohlcv(
        "BTCUSD",
        Timeframe.M1,
        start_time=base_time,
        limit=920,
        max_chunks=3,
    )

    assert len(result.bars) == 920
    assert result.bars[0].timestamp == base_time
    assert result.bars[-1].timestamp == base_time + timedelta(minutes=919)
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_kraken_rest_fetch_ohlcv_respects_max_chunks(monkeypatch):
    """REST provider respects max_chunks limit."""
    provider = KrakenRESTProvider()
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

    responses = [make_chunk(0, 720), make_chunk(720, 720), make_chunk(1440, 500)]
    calls: list[dict[str, Any]] = []

    async def fake_fetch(endpoint: str, params: dict[str, Any]) -> OHLCV:
        calls.append(params)
        return responses.pop(0) if responses else make_chunk(0, 0)

    monkeypatch.setattr(provider, "fetch", fake_fetch)

    result = await provider.fetch_ohlcv(
        "BTCUSD",
        Timeframe.M1,
        start_time=base_time,
        limit=3000,
        max_chunks=2,
    )

    assert len(result.bars) == 1440  # Limited by max_chunks
    assert len(calls) == 2


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_candles_adapter_handles_missing_fields():
    """Candles adapter handles missing fields gracefully."""
    adapter = CandlesResponseAdapter()

    response = {
        "error": [],
        "result": {
            "XBT/USD": [
                [1704110400],  # Missing required fields
                [1704110400, "50000", "50100", "49900", "50050", "100", "100.0", 150],
            ],
        },
    }

    params = {"market_type": MarketType.SPOT, "symbol": "BTCUSD", "interval": Timeframe.M15}
    result = adapter.parse(response, params)

    # First row skipped, second parsed
    assert len(result.bars) == 1


def test_trades_adapter_handles_missing_fields():
    """Trades adapter handles missing fields gracefully."""
    adapter = TradesAdapter()

    payload = {
        "channel": "trade",
        "symbol": "PI_XBTUSD",
        "data": [
            {"coin": "BTC"},  # Missing required fields
            {"time": 1704110400000, "price": "50000", "size": "1.0", "side": "buy"},
        ],
    }

    result = adapter.parse(payload)

    # First trade skipped, second parsed
    assert len(result) == 1


def test_order_book_adapter_handles_empty_levels():
    """Order book adapter handles empty levels gracefully."""
    adapter = OrderBookAdapter()

    payload = {
        "channel": "book",
        "symbol": "PI_XBTUSD",
        "data": {
            "bids": [],
            "asks": [],
        },
    }

    result = adapter.parse(payload)

    # Should return empty list or OrderBook with default values
    if len(result) > 0:
        assert result[0].bids == [(Decimal("0"), Decimal("0"))]
        assert result[0].asks == [(Decimal("0"), Decimal("0"))]


def test_exchange_info_adapter_filters_by_status():
    """Exchange info adapter filters symbols by status."""
    adapter = ExchangeInfoSymbolsAdapter()

    response = {
        "error": [],
        "result": {
            "XBT/USD": {"status": "online", "base": "XBT", "quote": "USD"},
            "ETH/USD": {"status": "cancel_only", "base": "ETH", "quote": "USD"},
        },
    }

    params = {"market_type": MarketType.SPOT}
    result = adapter.parse(response, params)

    # Only "online" status should be included
    assert len(result) == 1
    assert result[0].symbol == "BTCUSD"


def test_exchange_info_adapter_filters_by_quote_asset():
    """Exchange info adapter filters symbols by quote asset."""
    adapter = ExchangeInfoSymbolsAdapter()

    response = {
        "error": [],
        "result": {
            "XBT/USD": {"status": "online", "base": "XBT", "quote": "USD"},
            "XBT/USDT": {"status": "online", "base": "XBT", "quote": "USDT"},
        },
    }

    params = {"market_type": MarketType.SPOT, "quote_asset": "USD"}
    result = adapter.parse(response, params)

    # Only USD pairs should be included
    assert len(result) == 1
    assert result[0].quote_asset == "USD"


# ============================================================================
# Integration-style Tests
# ============================================================================


def test_kraken_provider_unified_interface():
    """Unified provider correctly delegates to REST and WS providers."""
    provider = KrakenProvider(market_type=MarketType.SPOT)

    assert provider._rest.market_type == MarketType.SPOT
    assert provider._ws.market_type == MarketType.SPOT

    # Verify both providers are accessible
    assert isinstance(provider._rest, KrakenRESTProvider)
    assert isinstance(provider._ws, KrakenWSProvider)


def test_kraken_ws_provider_stream_ohlcv_format():
    """WebSocket provider uses correct stream format for OHLCV."""
    # Verify endpoint spec is correct
    spec = ohlcv_spec(MarketType.FUTURES)
    stream_name = spec.build_stream_name("BTCUSD", {"interval": Timeframe.M15})

    assert stream_name == "ohlc-PI_XBTUSD-15"
    assert spec.combined_supported is True
    assert spec.max_streams_per_connection >= 1
