"""Trade data model."""

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class Trade(BaseModel):
    """Individual trade execution data.

    Represents a single trade that occurred on the exchange.
    Used for analyzing trade flow, volume, and market activity.
    """

    symbol: str = Field(..., min_length=1, description="Trading symbol")
    trade_id: int = Field(..., description="Unique trade ID")
    price: Decimal = Field(..., gt=0, description="Trade execution price")
    quantity: Decimal = Field(..., gt=0, description="Trade quantity")
    quote_quantity: Decimal | None = Field(
        default=None, ge=0, description="Quote asset quantity (price * quantity)"
    )
    timestamp: datetime = Field(..., description="Trade execution time (UTC)")
    is_buyer_maker: bool = Field(
        ..., description="True if buyer was maker (sell market order hit bid)"
    )
    is_best_match: bool | None = Field(
        default=None, description="Whether trade was best price match"
    )

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    # --- Core Properties ---

    @property
    def value(self) -> Decimal:
        """Trade value (price * quantity)."""
        if self.quote_quantity is not None:
            return self.quote_quantity
        return self.price * self.quantity

    @property
    def side(self) -> str:
        """Trade side from taker perspective: 'buy' or 'sell'."""
        # If buyer is maker, that means a sell market order hit the bid
        # So the taker was selling
        return "sell" if self.is_buyer_maker else "buy"

    @property
    def is_buy(self) -> bool:
        """True if taker was buying (buy market order hit ask)."""
        return not self.is_buyer_maker

    @property
    def is_sell(self) -> bool:
        """True if taker was selling (sell market order hit bid)."""
        return self.is_buyer_maker

    # --- Size Classification ---

    @property
    def is_large(self) -> bool:
        """Check if trade is large (> $50k)."""
        return self.value > Decimal("50000")

    @property
    def is_whale(self) -> bool:
        """Check if trade is whale-sized (> $1M)."""
        return self.value > Decimal("1000000")

    @property
    def size_category(self) -> str:
        """Categorize trade size: small, medium, large, whale."""
        if self.value < Decimal("1000"):  # < $1k
            return "small"
        elif self.value < Decimal("10000"):  # $1k - $10k
            return "medium"
        elif self.value < Decimal("100000"):  # $10k - $100k
            return "large"
        else:  # > $100k
            return "whale"

    # --- Time-based Properties ---

    @property
    def timestamp_ms(self) -> int:
        """Timestamp in milliseconds."""
        return int(self.timestamp.replace(tzinfo=UTC).timestamp() * 1000)

    def get_age_seconds(self, now_ms: int | None = None) -> float:
        """Seconds since trade."""
        if now_ms is None:
            now_ms = int(datetime.now(UTC).timestamp() * 1000)
        return max(0.0, (now_ms - self.timestamp_ms) / 1000.0)

    def is_fresh(self, max_age_seconds: float = 60.0) -> bool:
        """Check if trade is fresh (< 60 seconds old by default)."""
        return self.get_age_seconds() < max_age_seconds

    # --- Serialization ---

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "trade_id": self.trade_id,
            "price": str(self.price),
            "quantity": str(self.quantity),
            "value": str(self.value),
            "timestamp": self.timestamp.isoformat(),
            "side": self.side,
            "is_buyer_maker": self.is_buyer_maker,
            "is_large": self.is_large,
            "size_category": self.size_category,
        }
