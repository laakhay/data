"""Binance exchange data provider."""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from ...core import BaseProvider, InvalidIntervalError, InvalidSymbolError, TimeInterval
from ...models import Candle, Symbol
from ...utils import HTTPClient, retry_async


class BinanceProvider(BaseProvider):
    """Binance exchange data provider."""

    BASE_URL = "https://api.binance.com"
    
    # Binance interval mapping
    INTERVAL_MAP = {
        TimeInterval.M1: "1m",
        TimeInterval.M3: "3m",
        TimeInterval.M5: "5m",
        TimeInterval.M15: "15m",
        TimeInterval.M30: "30m",
        TimeInterval.H1: "1h",
        TimeInterval.H2: "2h",
        TimeInterval.H4: "4h",
        TimeInterval.H6: "6h",
        TimeInterval.H8: "8h",
        TimeInterval.H12: "12h",
        TimeInterval.D1: "1d",
        TimeInterval.D3: "3d",
        TimeInterval.W1: "1w",
        TimeInterval.MO1: "1M",
    }

    def __init__(self) -> None:
        super().__init__(name="binance")
        self._http = HTTPClient()

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
            params["limit"] = min(limit, 1000)  # Binance max is 1000

        try:
            data = await self._http.get(f"{self.BASE_URL}/api/v3/klines", params=params)
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
    async def get_symbols(self) -> List[Symbol]:
        """Fetch all trading symbols from Binance."""
        try:
            data = await self._http.get(f"{self.BASE_URL}/api/v3/exchangeInfo")
        except Exception as e:
            raise Exception(f"Failed to fetch symbols from Binance: {e}")

        symbols = []
        for symbol_data in data.get("symbols", []):
            if symbol_data.get("status") == "TRADING":
                symbols.append(
                    Symbol(
                        symbol=symbol_data["symbol"],
                        base_asset=symbol_data["baseAsset"],
                        quote_asset=symbol_data["quoteAsset"],
                    )
                )
        return symbols

    async def close(self) -> None:
        """Close HTTP client session."""
        await self._http.close()
