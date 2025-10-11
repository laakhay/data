"""Binance exchange data provider."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from ...core import BaseProvider, InvalidIntervalError, InvalidSymbolError, TimeInterval, MarketType
from ...models import Candle, Liquidation, OpenInterest, Symbol
from ...utils import HTTPClient, retry_async
from .constants import BASE_URLS, INTERVAL_MAP as BINANCE_INTERVAL_MAP, OI_PERIOD_MAP
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
    # Back-compat: expose INTERVAL_MAP at class level for tests/consumers
    INTERVAL_MAP = BINANCE_INTERVAL_MAP

    def __init__(
        self,
        market_type: MarketType = MarketType.SPOT,
        api_key: Optional[str] = None, 
        api_secret: Optional[str] = None,
        symbols_cache_ttl: float = 300.0,
    ) -> None:
        super().__init__(name=f"binance-{market_type.value}")
        self.market_type = market_type
        self._base_url = BASE_URLS[market_type]
        self._http = HTTPClient(base_url=self._base_url)
        self._api_key = api_key
        self._api_secret = api_secret
        # Symbols cache (full list); filter by quote_asset on read
        self._symbols_cache: Optional[List[Symbol]] = None
        self._symbols_cache_ts: Optional[float] = None
        self._symbols_cache_ttl = symbols_cache_ttl

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
        if interval not in self.INTERVAL_MAP:
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
            "interval": self.INTERVAL_MAP[interval],
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
    async def get_symbols(self, quote_asset: Optional[str] = None, use_cache: bool = True) -> List[Symbol]:
        """Fetch all trading symbols from Binance.
        
        Args:
            quote_asset: Optional filter by quote asset (e.g., "USDT", "BTC")
            use_cache: When True (default), use in-memory cache within TTL
        
        Returns:
            List of Symbol objects. For FUTURES market, returns PERPETUAL contracts only.
        """
        # Serve from cache if fresh
        if use_cache and self._symbols_cache is not None and self._symbols_cache_ts is not None:
            import time
            if (time.time() - self._symbols_cache_ts) < self._symbols_cache_ttl:
                if quote_asset:
                    return [s for s in self._symbols_cache if s.quote_asset == quote_asset]
                return list(self._symbols_cache)

        endpoint = self._get_exchange_info_endpoint()
        try:
            data = await self._http.get(endpoint)
        except Exception as e:
            raise Exception(f"Failed to fetch symbols from Binance: {e}")

        symbols: List[Symbol] = []
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
            
            # Extract trading filters for metadata
            tick_size = None
            step_size = None
            min_notional = None

            for f in symbol_data.get("filters", []):
                ftype = f.get("filterType") or f.get("filterType".lower())
                if ftype == "PRICE_FILTER":
                    # Futures/Spot both use tickSize
                    val = f.get("tickSize")
                    if val is not None:
                        try:
                            tick_size = Decimal(str(val))
                        except Exception:
                            pass
                elif ftype == "LOT_SIZE":
                    val = f.get("stepSize")
                    if val is not None:
                        try:
                            step_size = Decimal(str(val))
                        except Exception:
                            pass
                elif ftype == "MIN_NOTIONAL":
                    val = f.get("minNotional")
                    if val is not None:
                        try:
                            min_notional = Decimal(str(val))
                        except Exception:
                            pass

            symbols.append(
                Symbol(
                    symbol=symbol_data["symbol"],
                    base_asset=symbol_data["baseAsset"],
                    quote_asset=symbol_data["quoteAsset"],
                    tick_size=tick_size,
                    step_size=step_size,
                    min_notional=min_notional,
                    contract_type=symbol_data.get("contractType"),
                    delivery_date=symbol_data.get("deliveryDate"),
                )
            )
        # Update cache
        self._symbols_cache = symbols
        import time
        self._symbols_cache_ts = time.time()

        if quote_asset:
            return [s for s in symbols if s.quote_asset == quote_asset]
        return symbols

    @retry_async(max_retries=3, base_delay=1.0)
    async def get_open_interest(
        self,
        symbol: str,
        historical: bool = False,
        period: str = "5m",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 30,
    ) -> List[OpenInterest]:
        """Fetch Open Interest data from Binance.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            historical: If True, fetch historical OI data; if False, current OI
            period: Time period for historical data (5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d)
            start_time: Start time for historical data
            end_time: End time for historical data  
            limit: Maximum number of records (max 500)
            
        Returns:
            List of OpenInterest objects
            
        Raises:
            InvalidSymbolError: If symbol doesn't exist
            ProviderError: If API request fails
        """
        if self.market_type != MarketType.FUTURES:
            raise ValueError("Open Interest is only available for Futures market")
            
        symbol = symbol.upper()
        
        if historical:
            # Historical OI endpoint
            if period not in OI_PERIOD_MAP:
                raise ValueError(f"Invalid period: {period}. Valid periods: {list(OI_PERIOD_MAP.keys())}")
                
            params = {
                "symbol": symbol,
                "period": OI_PERIOD_MAP[period],
                "limit": min(limit, 500),  # Binance max limit
            }
            
            if start_time:
                params["startTime"] = int(start_time.timestamp() * 1000)
            if end_time:
                params["endTime"] = int(end_time.timestamp() * 1000)
                
            try:
                data = await self._http.get("/futures/data/openInterestHist", params=params)
            except Exception as e:
                if "Invalid symbol" in str(e):
                    raise InvalidSymbolError(f"Symbol {symbol} not found on Binance Futures")
                raise
                
            # Historical OI endpoint may return a single dict or list of data points
            if isinstance(data, dict):
                return [self._parse_open_interest_historical(data)]
            else:
                return [self._parse_open_interest_historical(oi_data) for oi_data in data]
        else:
            # Current OI endpoint
            params = {"symbol": symbol}
            try:
                data = await self._http.get("/fapi/v1/openInterest", params=params)
            except Exception as e:
                if "Invalid symbol" in str(e):
                    raise InvalidSymbolError(f"Symbol {symbol} not found on Binance Futures")
                raise
                
            return [self._parse_open_interest_current(data)]

    def _parse_open_interest_current(self, data: Dict) -> OpenInterest:
        """Parse current OI response."""
        from datetime import timezone
        
        return OpenInterest(
            symbol=data["symbol"],
            timestamp=datetime.fromtimestamp(data["time"] / 1000, tz=timezone.utc),
            open_interest=Decimal(str(data["openInterest"])),
            # Note: current OI endpoint doesn't provide openInterestValue, calculate from OI * mark price if available
            open_interest_value=None,  # Will be None for current endpoint
        )

    def _parse_open_interest_historical(self, data) -> OpenInterest:
        """Parse historical OI response - handles both dict and array formats."""
        from datetime import timezone
        
        if isinstance(data, dict):
            # Dictionary format (single data point)
            # Note: Historical endpoint may not have timestamp, use current time
            timestamp = datetime.now(timezone.utc)
            if "time" in data:
                timestamp = datetime.fromtimestamp(data["time"] / 1000, tz=timezone.utc)
            elif "timestamp" in data:
                timestamp = datetime.fromtimestamp(data["timestamp"] / 1000, tz=timezone.utc)
                
            return OpenInterest(
                symbol=data["symbol"],
                timestamp=timestamp,
                sum_open_interest=Decimal(str(data["sumOpenInterest"])),
                sum_open_interest_value=Decimal(str(data["sumOpenInterestValue"])),
                open_interest=Decimal(str(data["sumOpenInterest"])),  # Use sum as primary
                open_interest_value=Decimal(str(data["sumOpenInterestValue"])),  # Use sum value as primary
            )
        else:
            # Array format (historical data points)
            return OpenInterest(
                symbol=data[0],  # symbol
                timestamp=datetime.fromtimestamp(data[1] / 1000, tz=timezone.utc),  # timestamp
                sum_open_interest=Decimal(str(data[2])),  # sumOpenInterest
                sum_open_interest_value=Decimal(str(data[3])),  # sumOpenInterestValue
                open_interest=Decimal(str(data[2])),  # Use sum as primary
                open_interest_value=Decimal(str(data[3])),  # Use sum value as primary
            )


    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http.close()
