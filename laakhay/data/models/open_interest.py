"""Open Interest data model."""

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OpenInterest(BaseModel):
    """Open Interest data for futures contracts."""

    symbol: str = Field(..., min_length=1, description="Trading symbol")
    timestamp: datetime = Field(..., description="Measurement timestamp (UTC)")
    open_interest: Decimal = Field(..., ge=0, description="Number of open contracts")
    open_interest_value: Decimal | None = Field(
        default=None, ge=0, description="USDT value of open interest"
    )
    sum_open_interest: Decimal | None = Field(
        default=None, ge=0, description="Alternative format: sum of open interest"
    )
    sum_open_interest_value: Decimal | None = Field(
        default=None, ge=0, description="Alternative format: sum of open interest value"
    )

    @field_validator("open_interest")
    @classmethod
    def validate_open_interest(cls, v: Decimal) -> Decimal:
        """Validate open interest is non-negative."""
        if v < 0:
            raise ValueError("open_interest must be non-negative")
        return v

    @field_validator("open_interest_value", "sum_open_interest", "sum_open_interest_value")
    @classmethod
    def validate_optional_values(cls, v: Decimal | None) -> Decimal | None:
        """Validate optional fields are non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("Value must be non-negative")
        return v

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    # --- Developer ergonomics ---

    @property
    def timestamp_ms(self) -> int:
        """Timestamp in milliseconds."""
        return int(self.timestamp.timestamp() * 1000)

    def get_age_seconds(self) -> float:
        """Seconds since measurement timestamp."""
        from datetime import datetime

        now = datetime.now(UTC)
        return max(0.0, (now - self.timestamp).total_seconds())

    def is_fresh(self, max_age_seconds: float = 120.0) -> bool:
        """Check if OI data is fresh (age < threshold)."""
        return self.get_age_seconds() < max_age_seconds

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "open_interest": str(self.open_interest),
            "open_interest_value": (
                str(self.open_interest_value) if self.open_interest_value else None
            ),
            "sum_open_interest": str(self.sum_open_interest) if self.sum_open_interest else None,
            "sum_open_interest_value": (
                str(self.sum_open_interest_value) if self.sum_open_interest_value else None
            ),
        }
