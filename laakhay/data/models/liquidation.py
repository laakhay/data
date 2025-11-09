"""Liquidation data model."""

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Liquidation(BaseModel):
    """Liquidation order data for futures contracts."""

    symbol: str = Field(..., min_length=1, description="Trading symbol")
    timestamp: datetime = Field(..., description="Liquidation timestamp (UTC)")
    side: str = Field(..., description="Order side: 'BUY' or 'SELL'")
    order_type: str = Field(..., description="Order type (typically 'LIQUIDATION')")
    time_in_force: str = Field(..., description="Time in force (e.g., 'IOC', 'GTC')")
    original_quantity: Decimal = Field(..., gt=0, description="Original order quantity")
    price: Decimal = Field(..., gt=0, description="Liquidation price")
    average_price: Decimal = Field(..., gt=0, description="Average execution price")
    order_status: str = Field(..., description="Order status (e.g., 'FILLED', 'PARTIALLY_FILLED')")
    last_filled_quantity: Decimal = Field(..., ge=0, description="Last filled quantity")
    accumulated_quantity: Decimal = Field(..., ge=0, description="Total accumulated quantity")

    # Optional fields that may not be present in all responses
    commission: Decimal | None = Field(default=None, ge=0, description="Commission amount")
    commission_asset: str | None = Field(default=None, description="Commission asset")
    trade_id: int | None = Field(default=None, description="Trade ID")

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate side is BUY or SELL."""
        if v.upper() not in ["BUY", "SELL"]:
            raise ValueError("side must be 'BUY' or 'SELL'")
        return v.upper()

    @field_validator("original_quantity", "last_filled_quantity", "accumulated_quantity")
    @classmethod
    def validate_quantities(cls, v: Decimal) -> Decimal:
        """Validate quantities are non-negative."""
        if v < 0:
            raise ValueError("quantities must be non-negative")
        return v

    @field_validator("price", "average_price")
    @classmethod
    def validate_prices(cls, v: Decimal) -> Decimal:
        """Validate prices are positive."""
        if v <= 0:
            raise ValueError("prices must be positive")
        return v

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    # --- Developer ergonomics ---

    @property
    def timestamp_ms(self) -> int:
        """Timestamp in milliseconds."""
        return int(self.timestamp.timestamp() * 1000)

    @property
    def value_usdt(self) -> Decimal:
        """Liquidation value in USDT (quantity × price)."""
        return self.accumulated_quantity * self.price

    @property
    def is_long_liquidation(self) -> bool:
        """True if this is a long position liquidation (SELL side)."""
        return self.side == "SELL"

    @property
    def is_short_liquidation(self) -> bool:
        """True if this is a short position liquidation (BUY side)."""
        return self.side == "BUY"

    @property
    def is_large(self) -> bool:
        """True if liquidation value > $100k (configurable threshold)."""
        return self.value_usdt > Decimal("100000")

    def get_age_seconds(self) -> float:
        """Seconds since liquidation timestamp."""
        now = datetime.now(UTC)
        return max(0.0, (now - self.timestamp).total_seconds())

    def is_fresh(self, max_age_seconds: float = 300.0) -> bool:
        """Check if liquidation is fresh (age < threshold)."""
        return self.get_age_seconds() < max_age_seconds

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "side": self.side,
            "order_type": self.order_type,
            "time_in_force": self.time_in_force,
            "original_quantity": str(self.original_quantity),
            "price": str(self.price),
            "average_price": str(self.average_price),
            "order_status": self.order_status,
            "last_filled_quantity": str(self.last_filled_quantity),
            "accumulated_quantity": str(self.accumulated_quantity),
            "commission": str(self.commission) if self.commission else None,
            "commission_asset": self.commission_asset,
            "trade_id": self.trade_id,
        }
