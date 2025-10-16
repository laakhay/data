"""Series metadata model."""

from pydantic import BaseModel, Field


class SeriesMeta(BaseModel):
    """Metadata for a price series containing symbol and timeframe information."""

    symbol: str = Field(..., min_length=1, description="Trading symbol (e.g., 'BTCUSDT')")
    timeframe: str = Field(..., description="Time interval for the series")

    model_config = {"frozen": True, "str_strip_whitespace": True}

    def __str__(self) -> str:
        """String representation: SYMBOL@TIMEFRAME."""
        return f"{self.symbol}@{self.timeframe}"

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"SeriesMeta(symbol='{self.symbol}', timeframe={self.timeframe})"

    @property
    def symbol_upper(self) -> str:
        """Symbol in uppercase for consistent comparison."""
        return self.symbol.upper()

    @property
    def key(self) -> tuple[str, str]:
        """Unique key for this series (symbol, timeframe)."""
        return (self.symbol_upper, self.timeframe)
