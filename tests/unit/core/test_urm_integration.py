"""Integration tests for URM registry with Binance and Kraken mappers."""

from laakhay.data.connectors.binance.urm import BinanceURM
from laakhay.data.connectors.kraken.urm import KrakenURM
from laakhay.data.core import InstrumentSpec, InstrumentType, MarketType, URMRegistry


def test_registry_with_binance_mapper():
    """Test URM registry with Binance mapper."""
    registry = URMRegistry()
    registry.register("binance", BinanceURM())

    # Test spot
    spec = registry.urm_to_spec("BTCUSDT", exchange="binance", market_type=MarketType.SPOT)
    assert spec.base == "BTC"
    assert spec.quote == "USDT"
    assert spec.instrument_type == InstrumentType.SPOT

    symbol = registry.urm_to_exchange_symbol(spec, exchange="binance", market_type=MarketType.SPOT)
    assert symbol == "BTCUSDT"

    # Test perpetual futures
    spec = registry.urm_to_spec("BTCUSDT", exchange="binance", market_type=MarketType.FUTURES)
    assert spec.instrument_type == InstrumentType.PERPETUAL

    symbol = registry.urm_to_exchange_symbol(
        spec, exchange="binance", market_type=MarketType.FUTURES
    )
    assert symbol == "BTCUSDT"


def test_registry_with_kraken_mapper():
    """Test URM registry with Kraken mapper."""
    registry = URMRegistry()
    registry.register("kraken", KrakenURM())

    # Test spot
    spec = registry.urm_to_spec("XBT/USD", exchange="kraken", market_type=MarketType.SPOT)
    assert spec.base == "BTC"  # XBT normalized to BTC
    assert spec.quote == "USD"
    assert spec.instrument_type == InstrumentType.SPOT

    symbol = registry.urm_to_exchange_symbol(spec, exchange="kraken", market_type=MarketType.SPOT)
    assert symbol == "XBT/USD"  # BTC denormalized back to XBT

    # Test futures
    spec = registry.urm_to_spec("PI_XBTUSD", exchange="kraken", market_type=MarketType.FUTURES)
    assert spec.base == "BTC"
    assert spec.instrument_type == InstrumentType.PERPETUAL

    symbol = registry.urm_to_exchange_symbol(
        spec, exchange="kraken", market_type=MarketType.FUTURES
    )
    assert symbol == "PI_XBTUSD"


def test_registry_cross_exchange():
    """Test that same spec can be converted to different exchange formats."""
    registry = URMRegistry()
    registry.register("binance", BinanceURM())
    registry.register("kraken", KrakenURM())

    # Create a canonical spec
    spec = InstrumentSpec(base="BTC", quote="USD", instrument_type=InstrumentType.SPOT)

    # Convert to Binance format
    binance_symbol = registry.urm_to_exchange_symbol(
        spec, exchange="binance", market_type=MarketType.SPOT
    )
    assert binance_symbol == "BTCUSD"

    # Convert to Kraken format
    kraken_symbol = registry.urm_to_exchange_symbol(
        spec, exchange="kraken", market_type=MarketType.SPOT
    )
    assert kraken_symbol == "XBT/USD"

    # Both should resolve back to the same spec
    binance_spec = registry.urm_to_spec(
        binance_symbol, exchange="binance", market_type=MarketType.SPOT
    )
    kraken_spec = registry.urm_to_spec(
        kraken_symbol, exchange="kraken", market_type=MarketType.SPOT
    )

    assert binance_spec.base == kraken_spec.base == "BTC"
    assert binance_spec.quote == kraken_spec.quote == "USD"
