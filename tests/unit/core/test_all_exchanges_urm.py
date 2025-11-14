"""Integration tests for all exchange URM mappers."""

from laakhay.data.core import InstrumentSpec, InstrumentType, MarketType, URMRegistry
from laakhay.data.providers.binance.urm import BinanceURM
from laakhay.data.providers.bybit.urm import BybitURM
from laakhay.data.providers.coinbase.urm import CoinbaseURM
from laakhay.data.providers.hyperliquid.urm import HyperliquidURM
from laakhay.data.providers.kraken.urm import KrakenURM
from laakhay.data.providers.okx.urm import OKXURM


def test_all_exchanges_registered():
    """Test that all exchanges can be registered in the registry."""
    registry = URMRegistry()

    registry.register("binance", BinanceURM())
    registry.register("bybit", BybitURM())
    registry.register("kraken", KrakenURM())
    registry.register("okx", OKXURM())
    registry.register("hyperliquid", HyperliquidURM())
    registry.register("coinbase", CoinbaseURM())

    assert len(registry._mappers) == 6


def test_cross_exchange_conversion():
    """Test converting same spec to different exchange formats."""
    registry = URMRegistry()
    registry.register("binance", BinanceURM())
    registry.register("kraken", KrakenURM())
    registry.register("okx", OKXURM())
    registry.register("coinbase", CoinbaseURM())

    spec = InstrumentSpec(base="BTC", quote="USD", instrument_type=InstrumentType.SPOT)

    # Convert to different exchange formats
    binance_symbol = registry.urm_to_exchange_symbol(
        spec, exchange="binance", market_type=MarketType.SPOT
    )
    kraken_symbol = registry.urm_to_exchange_symbol(
        spec, exchange="kraken", market_type=MarketType.SPOT
    )
    okx_symbol = registry.urm_to_exchange_symbol(spec, exchange="okx", market_type=MarketType.SPOT)
    coinbase_symbol = registry.urm_to_exchange_symbol(
        spec, exchange="coinbase", market_type=MarketType.SPOT
    )

    assert binance_symbol == "BTCUSD"
    assert kraken_symbol == "XBT/USD"
    assert okx_symbol == "BTC-USD"
    assert coinbase_symbol == "BTC-USD"

    # All should resolve back to same spec
    binance_spec = registry.urm_to_spec(
        binance_symbol, exchange="binance", market_type=MarketType.SPOT
    )
    kraken_spec = registry.urm_to_spec(
        kraken_symbol, exchange="kraken", market_type=MarketType.SPOT
    )
    okx_spec = registry.urm_to_spec(okx_symbol, exchange="okx", market_type=MarketType.SPOT)
    coinbase_spec = registry.urm_to_spec(
        coinbase_symbol, exchange="coinbase", market_type=MarketType.SPOT
    )

    assert binance_spec.base == kraken_spec.base == okx_spec.base == coinbase_spec.base == "BTC"
    # Note: Kraken normalizes USD to USD, others keep it
    assert all(
        s.quote in ("USD", "USDT") for s in [binance_spec, kraken_spec, okx_spec, coinbase_spec]
    )


def test_futures_cross_exchange():
    """Test futures conversion across exchanges."""
    registry = URMRegistry()
    registry.register("binance", BinanceURM())
    registry.register("bybit", BybitURM())
    registry.register("kraken", KrakenURM())
    registry.register("okx", OKXURM())
    registry.register("hyperliquid", HyperliquidURM())

    # USDT spec for exchanges that support USDT
    usdt_spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.PERPETUAL)
    binance_symbol = registry.urm_to_exchange_symbol(
        usdt_spec, exchange="binance", market_type=MarketType.FUTURES
    )
    bybit_symbol = registry.urm_to_exchange_symbol(
        usdt_spec, exchange="bybit", market_type=MarketType.FUTURES
    )
    okx_symbol = registry.urm_to_exchange_symbol(
        usdt_spec, exchange="okx", market_type=MarketType.FUTURES
    )
    hyperliquid_symbol = registry.urm_to_exchange_symbol(
        usdt_spec, exchange="hyperliquid", market_type=MarketType.FUTURES
    )

    assert binance_symbol == "BTCUSDT"
    assert bybit_symbol == "BTCUSDT"
    assert okx_symbol == "BTC-USDT-SWAP"
    assert hyperliquid_symbol == "BTC"

    # USD spec for Kraken (which only supports USD, not USDT)
    usd_spec = InstrumentSpec(base="BTC", quote="USD", instrument_type=InstrumentType.PERPETUAL)
    kraken_symbol = registry.urm_to_exchange_symbol(
        usd_spec, exchange="kraken", market_type=MarketType.FUTURES
    )
    assert kraken_symbol == "PI_XBTUSD"
