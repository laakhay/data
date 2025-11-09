"""Mark Price and Index Price data model."""

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MarkPrice(BaseModel):
    """Mark Price and Index Price data for perpetual futures.

    Mark Price is used for liquidations and unrealized PnL calculations.
    Index Price is the weighted average spot price from multiple exchanges.

    These prices prevent market manipulation and unfair liquidations.
    """

    symbol: str = Field(..., min_length=1, description="Trading symbol")
    mark_price: Decimal = Field(..., gt=0, description="Mark price (used for liquidations)")
    index_price: Decimal | None = Field(
        default=None, gt=0, description="Index price (spot reference)"
    )
    estimated_settle_price: Decimal | None = Field(
        default=None, gt=0, description="Estimated settlement price"
    )
    last_funding_rate: Decimal | None = Field(default=None, description="Last applied funding rate")
    next_funding_time: datetime | None = Field(default=None, description="Next funding time (UTC)")
    timestamp: datetime = Field(..., description="Data timestamp (UTC)")

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    # --- Price Analysis Properties ---

    @property
    def mark_index_spread(self) -> Decimal | None:
        """Spread between mark and index price (mark - index)."""
        if self.index_price is None:
            return None
        return self.mark_price - self.index_price

    @property
    def mark_index_spread_bps(self) -> Decimal | None:
        """Spread in basis points (10000 * (mark - index) / index)."""
        if self.index_price is None or self.index_price == 0:
            return None
        spread = self.mark_price - self.index_price
        return (spread / self.index_price) * Decimal("10000")

    @property
    def mark_index_spread_percentage(self) -> Decimal | None:
        """Spread as percentage (100 * (mark - index) / index)."""
        if self.index_price is None or self.index_price == 0:
            return None
        spread = self.mark_price - self.index_price
        return (spread / self.index_price) * Decimal("100")

    @property
    def is_premium(self) -> bool | None:
        """True if mark price is above index (futures trading at premium)."""
        if self.mark_index_spread is None:
            return None
        return self.mark_index_spread > 0

    @property
    def is_discount(self) -> bool | None:
        """True if mark price is below index (futures trading at discount)."""
        if self.mark_index_spread is None:
            return None
        return self.mark_index_spread < 0

    @property
    def is_high_spread(self) -> bool:
        """Check if spread exceeds 30 bps threshold (0.30%)."""
        if self.mark_index_spread_bps is None:
            return False
        return abs(self.mark_index_spread_bps) > Decimal("30")

    @property
    def spread_severity(self) -> str:
        """Categorize spread severity: normal, moderate, high, extreme."""
        if self.mark_index_spread_bps is None:
            return "unknown"

        abs_spread = abs(self.mark_index_spread_bps)

        if abs_spread < 10:  # < 0.10%
            return "normal"
        elif abs_spread < 30:  # 0.10% - 0.30%
            return "moderate"
        elif abs_spread < 100:  # 0.30% - 1.00%
            return "high"
        else:  # > 1.00%
            return "extreme"

    # --- Time-based Properties ---

    @property
    def timestamp_ms(self) -> int:
        """Timestamp in milliseconds."""
        return int(self.timestamp.replace(tzinfo=UTC).timestamp() * 1000)

    @property
    def next_funding_time_ms(self) -> int | None:
        """Next funding time in milliseconds."""
        if self.next_funding_time is None:
            return None
        return int(self.next_funding_time.replace(tzinfo=UTC).timestamp() * 1000)

    @property
    def seconds_to_funding(self) -> int | None:
        """Seconds until next funding time."""
        if self.next_funding_time is None:
            return None
        now = datetime.now(UTC)
        delta = self.next_funding_time - now
        return max(0, int(delta.total_seconds()))

    def get_age_seconds(self, now_ms: int | None = None) -> float:
        """Seconds since timestamp."""
        if now_ms is None:
            now_ms = int(datetime.now(UTC).timestamp() * 1000)
        return max(0.0, (now_ms - self.timestamp_ms) / 1000.0)

    def is_fresh(self, max_age_seconds: float = 10.0) -> bool:
        """Check if data is fresh (age < threshold)."""
        return self.get_age_seconds() < max_age_seconds

    # --- Comparison Methods ---

    def compare_to_last_price(self, last_price: Decimal) -> dict:
        """Compare mark price to last traded price.

        Returns dict with spread analysis useful for dislocation alerts.
        """
        spread = self.mark_price - last_price
        spread_bps = (spread / last_price) * Decimal("10000") if last_price > 0 else None
        spread_pct = (spread / last_price) * Decimal("100") if last_price > 0 else None

        return {
            "last_price": last_price,
            "mark_price": self.mark_price,
            "spread": spread,
            "spread_bps": spread_bps,
            "spread_percentage": spread_pct,
            "is_dislocation": abs(spread_bps) > 30 if spread_bps else False,  # > 30 bps
            "severity": self._categorize_spread(spread_bps) if spread_bps else "unknown",
        }

    def compare_to_exchange_spot(self, exchange_spot_price: Decimal) -> dict:
        """Compare index price to exchange spot price.

        Returns dict with analysis useful for venue anomaly alerts.
        """
        if self.index_price is None:
            return {"error": "Index price not available"}

        spread = self.index_price - exchange_spot_price
        spread_bps = (
            (spread / exchange_spot_price) * Decimal("10000") if exchange_spot_price > 0 else None
        )
        spread_pct = (
            (spread / exchange_spot_price) * Decimal("100") if exchange_spot_price > 0 else None
        )

        return {
            "exchange_spot_price": exchange_spot_price,
            "index_price": self.index_price,
            "spread": spread,
            "spread_bps": spread_bps,
            "spread_percentage": spread_pct,
            "is_venue_anomaly": abs(spread_bps) > 50 if spread_bps else False,  # > 50 bps
            "severity": self._categorize_spread(spread_bps) if spread_bps else "unknown",
        }

    @staticmethod
    def _categorize_spread(spread_bps: Decimal) -> str:
        """Categorize spread magnitude."""
        abs_spread = abs(spread_bps)
        if abs_spread < 10:
            return "normal"
        elif abs_spread < 30:
            return "moderate"
        elif abs_spread < 50:
            return "high"
        elif abs_spread < 100:
            return "severe"
        else:
            return "extreme"

    # --- Serialization ---

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "mark_price": str(self.mark_price),
            "index_price": str(self.index_price) if self.index_price else None,
            "estimated_settle_price": (
                str(self.estimated_settle_price) if self.estimated_settle_price else None
            ),
            "mark_index_spread_bps": (
                str(self.mark_index_spread_bps) if self.mark_index_spread_bps else None
            ),
            "spread_severity": self.spread_severity,
            "is_premium": self.is_premium,
            "last_funding_rate": str(self.last_funding_rate) if self.last_funding_rate else None,
            "seconds_to_funding": self.seconds_to_funding,
            "timestamp": self.timestamp.isoformat(),
        }
