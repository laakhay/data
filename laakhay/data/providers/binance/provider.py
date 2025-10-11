"""Binance exchange data provider."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from ...core import BaseProvider, InvalidIntervalError, InvalidSymbolError, TimeInterval, MarketType
from ...models import Candle, Symbol
from ...utils import HTTPClient, retry_async
from .constants import BASE_URLS, INTERVAL_MAP
from .websocket_mixin import BinanceWebSocketMixin

logger = logging.getLogger(__name__)


class BinanceProvider(BinanceWebSocketMixin, BaseProvider):
    """Binance exchange data provider.
    
    Supports both Spot and Futures markets via market_type parameter.
    Default is SPOT for backward compatibility.
    
    Args:
        market_type: Market type (SPOT or FUTURES)
        api_key: Optional API key for authenticated endpoints
        api_secret: Optional API secret for authenticated endpoints

    """

    # REST and interval configuration (WebSocket config lives in constants + mixin)

    def __init__(
        self,
        market_type: MarketType = MarketType.SPOT,
        api_key: Optional[str] = None, 
        api_secret: Optional[str] = None
    ) -> None:
        super().__init__(name=f"binance-{market_type.value}")
        self.market_type = market_type
        self._base_url = BASE_URLS[market_type]
        self._http = HTTPClient(base_url=self._base_url)
        self._api_key = api_key
        self._api_secret = api_secret

    def set_credentials(self, api_key: str, api_secret: str) -> None:
        """Set API credentials for authenticated endpoints."""
        self._api_key = api_key
        self._api_secret = api_secret

    @property
    def has_credentials(self) -> bool:
        """Check if API credentials are set."""
        return bool(self._api_key and self._api_secret)

    def _get_klines_endpoint(self) -> str:
        """Get the klines endpoint for the market type."""
        if self.market_type == MarketType.FUTURES:
            return "/fapi/v1/klines"
        return "/api/v3/klines"
    
    def _get_exchange_info_endpoint(self) -> str:
        """Get the exchange info endpoint for the market type."""
        if self.market_type == MarketType.FUTURES:
            return "/fapi/v1/exchangeInfo"
        return "/api/v3/exchangeInfo"

    def validate_interval(self, interval: TimeInterval) -> None:
        """Validate interval is supported by Binance."""
        if interval not in INTERVAL_MAP:
            raise InvalidIntervalError(f"Interval {interval} not supported by Binance")

    @retry_async(max_retries=3, base_delay=1.0)
    async def get_candles(
        self,
        symbol: str,
        interval: TimeInterval,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[Candle]:
        """Fetch OHLCV candles from Binance."""
        self.validate_symbol(symbol)
        self.validate_interval(interval)

        params: Dict = {
            "symbol": symbol.upper(),
            "interval": INTERVAL_MAP[interval],
        }

        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)
        if limit:
            max_limit = 1000  # Conservative limit that works for both markets
            params["limit"] = min(limit, max_limit)

        endpoint = self._get_klines_endpoint()
        try:
            data = await self._http.get(endpoint, params=params)
        except Exception as e:
            if "Invalid symbol" in str(e):
                raise InvalidSymbolError(f"Symbol {symbol} not found on Binance")
            raise

        return [self._parse_candle(symbol, candle_data) for candle_data in data]

    def _parse_candle(self, symbol: str, data: List) -> Candle:
        """Parse Binance kline data into Candle model."""
        return Candle(
            symbol=symbol.upper(),
            timestamp=datetime.fromtimestamp(data[0] / 1000),
            open=Decimal(str(data[1])),
            high=Decimal(str(data[2])),
            low=Decimal(str(data[3])),
            close=Decimal(str(data[4])),
            volume=Decimal(str(data[5])),
        )

    @retry_async(max_retries=3, base_delay=1.0)
    async def get_symbols(self, quote_asset: Optional[str] = None) -> List[Symbol]:
        """Fetch all trading symbols from Binance.
        
        Args:
            quote_asset: Optional filter by quote asset (e.g., "USDT", "BTC")
        
        Returns:
            List of Symbol objects. For FUTURES market, returns PERPETUAL contracts only.
        """
        endpoint = self._get_exchange_info_endpoint()
        try:
            data = await self._http.get(endpoint)
        except Exception as e:
            raise Exception(f"Failed to fetch symbols from Binance: {e}")

        symbols = []
        for symbol_data in data.get("symbols", []):
            # Skip non-trading symbols
            if symbol_data.get("status") != "TRADING":
                continue
            
            # Filter by quote asset if specified
            if quote_asset and symbol_data.get("quoteAsset") != quote_asset:
                continue
            
            # For futures, filter for PERPETUAL contracts only
            if self.market_type == MarketType.FUTURES:
                if symbol_data.get("contractType") != "PERPETUAL":
                    continue
            
            symbols.append(
                Symbol(
                    symbol=symbol_data["symbol"],
                    base_asset=symbol_data["baseAsset"],
                    quote_asset=symbol_data["quoteAsset"],
                )
            )
        return symbols

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http.close()
