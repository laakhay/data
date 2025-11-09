"""Order Book data model."""

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrderBook(BaseModel):
    """Order book (market depth) data.

    Represents the current state of bids and asks for a symbol.
    Used for analyzing liquidity, spread, and market depth.
    """

    symbol: str = Field(..., min_length=1, description="Trading symbol")
    last_update_id: int = Field(..., description="Last update ID from exchange")
    bids: list[tuple[Decimal, Decimal]] = Field(
        ..., description="Bid levels [(price, quantity), ...] sorted by price descending"
    )
    asks: list[tuple[Decimal, Decimal]] = Field(
        ..., description="Ask levels [(price, quantity), ...] sorted by price ascending"
    )
    timestamp: datetime = Field(..., description="Snapshot timestamp (UTC)")

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    @field_validator("bids", "asks")
    @classmethod
    def validate_levels(cls, v):
        """Validate order book levels."""
        if not v:
            raise ValueError("Order book must have at least one level")

        for level in v:
            if len(level) != 2:
                raise ValueError("Each level must be a tuple of (price, quantity)")
            price, qty = level
            if price <= 0:
                raise ValueError("Price must be positive")
            if qty < 0:
                raise ValueError("Quantity cannot be negative")

        return v

    # --- Core Properties ---

    @property
    def best_bid(self) -> tuple[Decimal, Decimal] | None:
        """Highest bid (price, quantity)."""
        return self.bids[0] if self.bids else None

    @property
    def best_ask(self) -> tuple[Decimal, Decimal] | None:
        """Lowest ask (price, quantity)."""
        return self.asks[0] if self.asks else None

    @property
    def best_bid_price(self) -> Decimal | None:
        """Best bid price."""
        return self.best_bid[0] if self.best_bid else None

    @property
    def best_ask_price(self) -> Decimal | None:
        """Best ask price."""
        return self.best_ask[0] if self.best_ask else None

    @property
    def best_bid_qty(self) -> Decimal | None:
        """Best bid quantity."""
        return self.best_bid[1] if self.best_bid else None

    @property
    def best_ask_qty(self) -> Decimal | None:
        """Best ask quantity."""
        return self.best_ask[1] if self.best_ask else None

    # --- Spread Analysis ---

    @property
    def spread(self) -> Decimal | None:
        """Absolute spread (ask - bid)."""
        if self.best_bid_price is None or self.best_ask_price is None:
            return None
        return self.best_ask_price - self.best_bid_price

    @property
    def spread_bps(self) -> Decimal | None:
        """Spread in basis points (10000 * spread / mid)."""
        if self.spread is None or self.mid_price is None or self.mid_price == 0:
            return None
        return (self.spread / self.mid_price) * Decimal("10000")

    @property
    def spread_percentage(self) -> Decimal | None:
        """Spread as percentage (100 * spread / mid)."""
        if self.spread is None or self.mid_price is None or self.mid_price == 0:
            return None
        return (self.spread / self.mid_price) * Decimal("100")

    @property
    def mid_price(self) -> Decimal | None:
        """Mid price ((bid + ask) / 2)."""
        if self.best_bid_price is None or self.best_ask_price is None:
            return None
        return (self.best_bid_price + self.best_ask_price) / Decimal("2")

    @property
    def is_tight_spread(self) -> bool:
        """Check if spread is tight (< 10 bps = 0.10%)."""
        if self.spread_bps is None:
            return False
        return self.spread_bps < Decimal("10")

    @property
    def is_wide_spread(self) -> bool:
        """Check if spread is wide (> 50 bps = 0.50%)."""
        if self.spread_bps is None:
            return False
        return self.spread_bps > Decimal("50")

    # --- Depth Analysis ---

    @property
    def total_bid_volume(self) -> Decimal:
        """Total volume on bid side."""
        return Decimal(sum(qty for _, qty in self.bids))

    @property
    def total_ask_volume(self) -> Decimal:
        """Total volume on ask side."""
        return Decimal(sum(qty for _, qty in self.asks))

    @property
    def total_bid_value(self) -> Decimal:
        """Total value on bid side (price * quantity)."""
        return Decimal(sum(price * qty for price, qty in self.bids))

    @property
    def total_ask_value(self) -> Decimal:
        """Total value on ask side (price * quantity)."""
        return Decimal(sum(price * qty for price, qty in self.asks))

    @property
    def bid_ask_volume_ratio(self) -> Decimal | None:
        """Ratio of bid volume to ask volume (> 1 = more buyers)."""
        if self.total_ask_volume == 0:
            return None
        return self.total_bid_volume / self.total_ask_volume

    @property
    def imbalance(self) -> Decimal | None:
        """Order book imbalance ((bid_vol - ask_vol) / (bid_vol + ask_vol))."""
        total = self.total_bid_volume + self.total_ask_volume
        if total == 0:
            return None
        return (self.total_bid_volume - self.total_ask_volume) / total

    @property
    def depth_score(self) -> str:
        """Categorize market depth: thin, moderate, deep."""
        if self.mid_price is None:
            return "unknown"

        # Analyze depth within 1% of mid price
        depth_range = self.mid_price * Decimal("0.01")
        bid_depth = sum(qty for price, qty in self.bids if self.mid_price - price <= depth_range)
        ask_depth = sum(qty for price, qty in self.asks if price - self.mid_price <= depth_range)
        total_depth = bid_depth + ask_depth

        # Convert to USD value (approximate)
        depth_value = total_depth * self.mid_price

        if depth_value < Decimal("10000"):  # < $10k
            return "thin"
        elif depth_value < Decimal("100000"):  # $10k - $100k
            return "moderate"
        else:  # > $100k
            return "deep"

    # --- Market Direction ---

    @property
    def is_bid_heavy(self) -> bool:
        """True if significantly more bid volume (> 60% of total)."""
        total = self.total_bid_volume + self.total_ask_volume
        if total == 0:
            return False
        return self.total_bid_volume / total > Decimal("0.6")

    @property
    def is_ask_heavy(self) -> bool:
        """True if significantly more ask volume (> 60% of total)."""
        total = self.total_bid_volume + self.total_ask_volume
        if total == 0:
            return False
        return self.total_ask_volume / total > Decimal("0.6")

    @property
    def market_pressure(self) -> str:
        """Categorize market pressure: bullish, bearish, neutral."""
        if self.is_bid_heavy:
            return "bullish"
        elif self.is_ask_heavy:
            return "bearish"
        else:
            return "neutral"

    # --- Level Analysis ---

    def get_depth_at_price(self, price: Decimal, side: str = "both") -> Decimal:
        """Get total volume available up to a price level.

        Args:
            price: Price threshold
            side: "bid", "ask", or "both"

        Returns:
            Total volume available up to that price
        """
        volume = Decimal("0")

        if side in ["bid", "both"]:
            volume += sum(qty for p, qty in self.bids if p >= price)

        if side in ["ask", "both"]:
            volume += sum(qty for p, qty in self.asks if p <= price)

        return volume

    def get_depth_percentage(self, percentage: Decimal) -> dict:
        """Get order book depth within percentage of mid price.

        Args:
            percentage: Percentage range (e.g., 1 for 1%)

        Returns:
            Dict with bid/ask volumes within range
        """
        if self.mid_price is None:
            return {"bid_volume": Decimal("0"), "ask_volume": Decimal("0")}

        price_range = self.mid_price * (percentage / Decimal("100"))

        bid_volume = sum(qty for price, qty in self.bids if self.mid_price - price <= price_range)

        ask_volume = sum(qty for price, qty in self.asks if price - self.mid_price <= price_range)

        return {
            "bid_volume": bid_volume,
            "ask_volume": ask_volume,
            "total_volume": bid_volume + ask_volume,
            "ratio": bid_volume / ask_volume if ask_volume > 0 else None,
        }

    # --- Time-based Properties ---

    @property
    def timestamp_ms(self) -> int:
        """Timestamp in milliseconds."""
        return int(self.timestamp.replace(tzinfo=UTC).timestamp() * 1000)

    def get_age_seconds(self, now_ms: int | None = None) -> float:
        """Seconds since snapshot."""
        if now_ms is None:
            now_ms = int(datetime.now(UTC).timestamp() * 1000)
        return max(0.0, (now_ms - self.timestamp_ms) / 1000.0)

    def is_fresh(self, max_age_seconds: float = 5.0) -> bool:
        """Check if order book is fresh (< 5 seconds old by default)."""
        return self.get_age_seconds() < max_age_seconds

    # --- Serialization ---

    def to_dict(self, include_levels: bool = False) -> dict:
        """Convert to dictionary for JSON serialization.

        Args:
            include_levels: Include full bid/ask levels (can be large)
        """
        data = {
            "symbol": self.symbol,
            "last_update_id": self.last_update_id,
            "best_bid_price": str(self.best_bid_price) if self.best_bid_price else None,
            "best_ask_price": str(self.best_ask_price) if self.best_ask_price else None,
            "spread": str(self.spread) if self.spread else None,
            "spread_bps": str(self.spread_bps) if self.spread_bps else None,
            "mid_price": str(self.mid_price) if self.mid_price else None,
            "total_bid_volume": str(self.total_bid_volume),
            "total_ask_volume": str(self.total_ask_volume),
            "bid_ask_ratio": str(self.bid_ask_volume_ratio) if self.bid_ask_volume_ratio else None,
            "imbalance": str(self.imbalance) if self.imbalance else None,
            "market_pressure": self.market_pressure,
            "depth_score": self.depth_score,
            "timestamp": self.timestamp.isoformat(),
        }

        if include_levels:
            data["bids"] = [[str(p), str(q)] for p, q in self.bids]
            data["asks"] = [[str(p), str(q)] for p, q in self.asks]
        else:
            data["bid_levels"] = len(self.bids)
            data["ask_levels"] = len(self.asks)

        return data
