"""Candle (OHLCV) data model."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Candle(BaseModel):
    """OHLCV candle data."""

    symbol: str = Field(..., min_length=1)
    timestamp: datetime
    open: Decimal = Field(..., gt=0)
    high: Decimal = Field(..., gt=0)
    low: Decimal = Field(..., gt=0)
    close: Decimal = Field(..., gt=0)
    volume: Decimal = Field(..., ge=0)

    @field_validator("high")
    @classmethod
    def validate_high(cls, v: Decimal, info) -> Decimal:
        """Validate high >= low and high >= open, close."""
        if "low" in info.data and v < info.data["low"]:
            raise ValueError("high must be >= low")
        if "open" in info.data and v < info.data["open"]:
            raise ValueError("high must be >= open")
        if "close" in info.data and v < info.data["close"]:
            raise ValueError("high must be >= close")
        return v

    @field_validator("low")
    @classmethod
    def validate_low(cls, v: Decimal, info) -> Decimal:
        """Validate low <= high and low <= open, close."""
        if "high" in info.data and v > info.data["high"]:
            raise ValueError("low must be <= high")
        if "open" in info.data and v > info.data["open"]:
            raise ValueError("low must be <= open")
        if "close" in info.data and v > info.data["close"]:
            raise ValueError("low must be <= close")
        return v

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)
