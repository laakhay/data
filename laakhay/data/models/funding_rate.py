"""Funding Rate data model."""

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FundingRate(BaseModel):
    """Funding rate data for futures contracts."""

    symbol: str = Field(..., min_length=1, description="Trading symbol")
    funding_time: datetime = Field(..., description="Funding time (UTC)")
    funding_rate: Decimal = Field(..., description="Funding rate (decimal, not percentage)")
    mark_price: Decimal | None = Field(default=None, ge=0, description="Mark price at funding time")

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    # --- Developer ergonomics ---

    @property
    def funding_time_ms(self) -> int:
        """Funding time in milliseconds."""
        return int(self.funding_time.replace(tzinfo=UTC).timestamp() * 1000)

    @property
    def funding_rate_percentage(self) -> Decimal:
        """Funding rate as percentage (multiply by 100)."""
        return self.funding_rate * Decimal("100")

    @property
    def annual_rate_percentage(self) -> Decimal:
        """Estimated annual rate percentage (funding every 8 hours = 3x per day = 1095x per year)."""
        return self.funding_rate_percentage * Decimal("1095")

    @property
    def is_positive(self) -> bool:
        """True if funding rate is positive (longs pay shorts)."""
        return self.funding_rate > 0

    @property
    def is_negative(self) -> bool:
        """True if funding rate is negative (shorts pay longs)."""
        return self.funding_rate < 0

    @property
    def is_high(self) -> bool:
        """True if absolute funding rate > 0.01% (high funding pressure)."""
        return abs(self.funding_rate_percentage) > Decimal("0.01")

    def get_age_seconds(self, now_ms: int | None = None) -> float:
        """Seconds since funding time."""
        if now_ms is None:
            now_ms = int(datetime.now(UTC).timestamp() * 1000)
        return max(0.0, (now_ms - self.funding_time_ms) / 1000.0)

    def is_fresh(self, max_age_seconds: float = 300.0) -> bool:
        """Check if funding rate is fresh (age < threshold)."""
        return self.get_age_seconds() < max_age_seconds

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "funding_time": self.funding_time.isoformat(),
            "funding_rate": str(self.funding_rate),
            "funding_rate_percentage": str(self.funding_rate_percentage),
            "mark_price": str(self.mark_price) if self.mark_price else None,
            "is_positive": self.is_positive,
            "is_high": self.is_high,
        }
