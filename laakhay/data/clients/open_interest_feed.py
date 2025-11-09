"""Real-time Open Interest feed leveraging the generic SymbolStreamFeed."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from ..models import OpenInterest
from .base_feed import SymbolStreamFeed

Callback = Callable[[OpenInterest], Awaitable[None]] | Callable[[OpenInterest], None]


class OpenInterestFeed(SymbolStreamFeed[OpenInterest]):
    """Provider-agnostic open interest feed with cache and pub/sub."""

    def __init__(
        self,
        provider: Any,
        *,
        stale_threshold_seconds: int = 900,
    ) -> None:
        super().__init__(
            provider,
            key_selector=lambda oi: oi.symbol.upper(),
            stale_threshold_seconds=stale_threshold_seconds,
        )
        self._period: str = "5m"

    async def start(self, *, symbols: Iterable[str], period: str = "5m") -> None:  # type: ignore[override]
        self._period = period
        await super().start(symbols=symbols, period=period)

    async def set_symbols(self, symbols: Iterable[str]) -> None:  # type: ignore[override]
        await super().set_symbols(symbols)

    async def add_symbols(self, symbols: Iterable[str]) -> None:  # type: ignore[override]
        await super().add_symbols(symbols)

    async def remove_symbols(self, symbols: Iterable[str]) -> None:  # type: ignore[override]
        await super().remove_symbols(symbols)

    async def set_period(self, period: str) -> None:
        if period == self._period:
            return
        self._period = period
        await self.update_stream(period=period)

    def subscribe(self, callback: Callback, *, symbols: Iterable[str] | None = None) -> str:  # type: ignore[override]
        symbol_keys = None
        if symbols is not None:
            symbol_keys = {s.upper() for s in symbols}
        sub_id = super().subscribe(callback, keys=symbol_keys)
        self._schedule_update()
        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        super().unsubscribe(subscription_id)
        self._schedule_update()

    def get_latest(self, symbol: str) -> OpenInterest | None:  # type: ignore[override]
        return super().get_latest(symbol.upper())

    def snapshot(self, symbols: Iterable[str] | None = None) -> dict[str, OpenInterest | None]:
        symbols = {s.upper() for s in symbols} if symbols is not None else None
        return super().snapshot(symbols)

    def _prepare_stream_args(self, args: dict[str, Any]) -> dict[str, Any]:
        args = dict(args)
        args["period"] = args.get("period", self._period)
        self._period = args["period"]
        return super()._prepare_stream_args(args)

    async def _stream_iterator(self):
        async for oi in self._provider.stream_open_interest(self._symbols, period=self._period):
            yield oi
