"""Real-time Liquidations feed with cache, subscriptions, and health tracking."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from ..models import Liquidation
from .base_feed import BaseStreamFeed

Callback = Callable[[Liquidation], Awaitable[None]] | Callable[[Liquidation], None]


class LiquidationFeed(BaseStreamFeed[Liquidation]):
    """Thin liquidation feed built on top of the generic BaseStreamFeed."""

    def __init__(
        self,
        provider: Any,
        *,
        stale_threshold_seconds: int = 900,
    ) -> None:
        super().__init__(
            provider,
            key_selector=lambda liq: liq.symbol.upper(),
            stale_threshold_seconds=stale_threshold_seconds,
        )

    async def start(self) -> None:  # type: ignore[override]
        await super().start()

    def subscribe(self, callback: Callback, *, symbols: Iterable[str] | None = None) -> str:  # type: ignore[override]
        symbol_keys = None
        if symbols is not None:
            symbol_keys = {s.upper() for s in symbols}
        return super().subscribe(callback, keys=symbol_keys)

    def get_latest(self, symbol: str) -> Liquidation | None:  # type: ignore[override]
        return super().get_latest(symbol.upper())

    def snapshot(self, symbols: Iterable[str] | None = None) -> dict[str, Liquidation | None]:
        symbols = {s.upper() for s in symbols} if symbols is not None else None
        return super().snapshot(symbols)

    async def _stream_iterator(self):
        async for liq in self._provider.stream_liquidations():
            yield liq
