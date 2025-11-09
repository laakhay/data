"""Bar (OHLCV) data model."""

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class Bar(BaseModel):
    """Single OHLCV bar/candle data."""

    timestamp: datetime = Field(..., description="Opening time of the bar")
    open: Decimal = Field(..., gt=0, description="Opening price")
    high: Decimal = Field(..., gt=0, description="Highest price")
    low: Decimal = Field(..., gt=0, description="Lowest price")
    close: Decimal = Field(..., gt=0, description="Closing price")
    volume: Decimal = Field(..., ge=0, description="Volume traded")
    is_closed: bool = Field(True, description="Whether this bar is finalized")

    model_config = {"frozen": True}

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

    # --- Time utilities ---
    @property
    def open_time_ms(self) -> int:
        """Opening time in milliseconds since epoch."""
        return int(self.timestamp.replace(tzinfo=UTC).timestamp() * 1000)

    def close_time_ms(self, interval_seconds: int = 60) -> int:
        """Approximate close time in ms given interval seconds (default 60s).

        For closed bars this equals open_time + interval; for streaming open
        bars the caller may pass the actual interval used.
        """
        return self.open_time_ms + (interval_seconds * 1000)

    def get_age_seconds(self, *, is_closed: bool = True, interval_seconds: int = 60) -> float:
        """Get age of this bar in seconds."""
        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        ref = self.close_time_ms(interval_seconds) if is_closed else now_ms
        return max(0.0, (now_ms - ref) / 1000.0)

    def is_fresh(
        self, max_age_seconds: float = 120.0, *, is_closed: bool = True, interval_seconds: int = 60
    ) -> bool:
        """Check if this bar is fresh (not too old)."""
        return (
            self.get_age_seconds(is_closed=is_closed, interval_seconds=interval_seconds)
            < max_age_seconds
        )

    # --- Price calculations ---
    @property
    def hl2(self) -> Decimal:
        """(High + Low) / 2 - typical price."""
        return (self.high + self.low) / Decimal("2")

    @property
    def hlc3(self) -> Decimal:
        """(High + Low + Close) / 3 - typical price."""
        return (self.high + self.low + self.close) / Decimal("3")

    @property
    def ohlc4(self) -> Decimal:
        """(Open + High + Low + Close) / 4 - typical price."""
        return (self.open + self.high + self.low + self.close) / Decimal("4")

    @property
    def range(self) -> Decimal:
        """High - Low - price range."""
        return self.high - self.low

    @property
    def body_size(self) -> Decimal:
        """|Close - Open| - candle body size."""
        return abs(self.close - self.open)

    @property
    def upper_shadow(self) -> Decimal:
        """High - max(Open, Close) - upper shadow size."""
        return self.high - max(self.open, self.close)

    @property
    def lower_shadow(self) -> Decimal:
        """min(Open, Close) - Low - lower shadow size."""
        return min(self.open, self.close) - self.low

    @property
    def is_bullish(self) -> bool:
        """True if close > open (bullish bar)."""
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        """True if close < open (bearish bar)."""
        return self.close < self.open
