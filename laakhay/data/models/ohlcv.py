"""OHLCV series data model."""

from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from .bar import Bar
from .series_meta import SeriesMeta


class OHLCV(BaseModel):
    """OHLCV series containing metadata and a list of bars."""

    meta: SeriesMeta = Field(..., description="Series metadata (symbol, timeframe)")
    bars: list[Bar] = Field(default_factory=list, description="List of OHLCV bars")

    model_config = {"frozen": True}

    @field_validator("bars")
    @classmethod
    def validate_bars(cls, bars: list[Bar]) -> list[Bar]:
        """Validate that bars are sorted by timestamp and have consistent time intervals."""
        if not bars:
            return bars

        # Check if bars are sorted by timestamp
        for i in range(1, len(bars)):
            if bars[i].timestamp <= bars[i - 1].timestamp:
                raise ValueError("Bars must be sorted by timestamp")

        return bars

    # --- Access methods ---
    def __len__(self) -> int:
        """Number of bars in the series."""
        return len(self.bars)

    def __getitem__(self, index: int) -> Bar:
        """Get bar by index."""
        return self.bars[index]

    def __iter__(self) -> Iterator[Bar]:  # type: ignore[override]
        """Iterate over bars."""
        return iter(self.bars)

    @property
    def is_empty(self) -> bool:
        """True if no bars in the series."""
        return len(self.bars) == 0

    @property
    def latest(self) -> Bar | None:
        """Latest bar in the series, or None if empty."""
        return self.bars[-1] if self.bars else None

    @property
    def earliest(self) -> Bar | None:
        """Earliest bar in the series, or None if empty."""
        return self.bars[0] if self.bars else None

    # --- Time range properties ---
    @property
    def start_time(self) -> datetime | None:
        """Start time of the series (earliest bar timestamp)."""
        return self.earliest.timestamp if self.earliest else None

    @property
    def end_time(self) -> datetime | None:
        """End time of the series (latest bar timestamp)."""
        return self.latest.timestamp if self.latest else None

    # --- Price statistics ---
    @property
    def highest_price(self) -> Decimal | None:
        """Highest price across all bars."""
        return max(bar.high for bar in self.bars) if self.bars else None

    @property
    def lowest_price(self) -> Decimal | None:
        """Lowest price across all bars."""
        return min(bar.low for bar in self.bars) if self.bars else None

    @property
    def total_volume(self) -> Decimal | None:
        """Total volume across all bars."""
        return Decimal(sum(bar.volume for bar in self.bars)) if self.bars else None

    # --- Convenience methods ---
    def get_bars_in_range(self, start: datetime, end: datetime) -> "OHLCV":
        """Get bars within a time range."""
        filtered_bars = [bar for bar in self.bars if start <= bar.timestamp <= end]

        return OHLCV(meta=self.meta, bars=filtered_bars)

    def get_last_n_bars(self, n: int) -> "OHLCV":
        """Get the last n bars."""
        if n <= 0:
            return OHLCV(meta=self.meta, bars=[])
        return OHLCV(meta=self.meta, bars=self.bars[-n:])

    def get_closed_bars(self) -> "OHLCV":
        """Get only closed bars."""
        closed_bars = [bar for bar in self.bars if bar.is_closed]
        return OHLCV(meta=self.meta, bars=closed_bars)

    def get_open_bars(self) -> "OHLCV":
        """Get only open (streaming) bars."""
        open_bars = [bar for bar in self.bars if not bar.is_closed]
        return OHLCV(meta=self.meta, bars=open_bars)

    def append_bar(self, bar: Bar) -> "OHLCV":
        """Create a new OHLCV with an additional bar appended."""
        new_bars = self.bars + [bar]
        return OHLCV(meta=self.meta, bars=new_bars)

    def extend_bars(self, bars: list[Bar]) -> "OHLCV":
        """Create a new OHLCV with additional bars."""
        new_bars = self.bars + bars
        return OHLCV(meta=self.meta, bars=new_bars)

    # --- Conversion methods ---
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "meta": {
                "symbol": self.meta.symbol,
                "timeframe": self.meta.timeframe,
            },
            "bars": [
                {
                    "timestamp": bar.timestamp.isoformat(),
                    "open": str(bar.open),
                    "high": str(bar.high),
                    "low": str(bar.low),
                    "close": str(bar.close),
                    "volume": str(bar.volume),
                    "is_closed": bar.is_closed,
                }
                for bar in self.bars
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OHLCV":
        """Create OHLCV from dictionary representation."""
        from datetime import datetime

        from .series_meta import SeriesMeta

        meta = SeriesMeta(
            symbol=data["meta"]["symbol"],
            timeframe=data["meta"]["timeframe"],
        )

        bars = [
            Bar(
                timestamp=datetime.fromisoformat(bar_data["timestamp"]),
                open=Decimal(bar_data["open"]),
                high=Decimal(bar_data["high"]),
                low=Decimal(bar_data["low"]),
                close=Decimal(bar_data["close"]),
                volume=Decimal(bar_data["volume"]),
                is_closed=bar_data["is_closed"],
            )
            for bar_data in data["bars"]
        ]

        return cls(meta=meta, bars=bars)

    def __str__(self) -> str:
        """String representation."""
        return f"OHLCV({self.meta}, {len(self.bars)} bars)"

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"OHLCV(meta={self.meta!r}, bars={len(self.bars)} items)"
