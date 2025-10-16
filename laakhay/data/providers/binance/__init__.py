"""Binance provider with futures and spot support."""

from ...core import MarketType
from .provider import BinanceProvider

__all__ = [
    "BinanceProvider",
    "BinanceFuturesProvider",
    "BinanceSpotProvider",
]


class BinanceFuturesProvider(BinanceProvider):
    """Binance Futures market data provider.

    Convenience alias for BinanceProvider(market_type=MarketType.FUTURES).
    Uses Binance Futures API: https://fapi.binance.com

    This provider automatically filters for PERPETUAL contracts only.

    Examples:
        >>> provider = BinanceFuturesProvider()
        >>> async with provider:
        ...     # Get candles for BTC perpetual futures
        ...     candles = await provider.get_candles("BTCUSDT", Timeframe.M1)
        ...     # Get all USDT perpetual contracts
        ...     symbols = await provider.get_symbols(quote_asset="USDT")
    """

    def __init__(self, api_key: str | None = None, api_secret: str | None = None) -> None:
        super().__init__(market_type=MarketType.FUTURES, api_key=api_key, api_secret=api_secret)


class BinanceSpotProvider(BinanceProvider):
    """Binance Spot market data provider.

    Convenience alias for BinanceProvider(market_type=MarketType.SPOT).
    Uses Binance Spot API: https://api.binance.com

    Examples:
        >>> provider = BinanceSpotProvider()
        >>> async with provider:
        ...     # Get candles for BTC spot
        ...     candles = await provider.get_candles("BTCUSDT", Timeframe.M1)
        ...     # Get all USDT spot pairs
        ...     symbols = await provider.get_symbols(quote_asset="USDT")
    """

    def __init__(self, api_key: str | None = None, api_secret: str | None = None) -> None:
        super().__init__(market_type=MarketType.SPOT, api_key=api_key, api_secret=api_secret)
