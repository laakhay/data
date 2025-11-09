#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio

from laakhay.data.clients.data_feed import DataFeed

from laakhay.data.core import MarketType, Timeframe
from laakhay.data.providers.binance import BinanceProvider, BinanceRESTProvider


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Quickstart for DataFeed streaming + cache")
    p.add_argument("symbols", nargs="*", default=["BTCUSDT", "ETHUSDT"])
    p.add_argument("timeframe", nargs="?", default="M1")
    p.add_argument("market", nargs="?", default="SPOT", choices=["SPOT", "FUTURES"])
    p.add_argument("duration", nargs="?", type=int, default=30, help="Seconds to run")
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    tf = getattr(Timeframe, args.timeframe)
    market = MarketType[args.market]

    ws = BinanceProvider(market_type=market)
    rest = BinanceRESTProvider(market_type=market)
    feed = DataFeed(ws_provider=ws, rest_provider=rest, throttle_ms=500, max_bar_history=5)

    # Simple bar callback
    def on_bar(bar):
        print(
            f"BAR {bar.timestamp.isoformat()} | {bar.symbol} | {bar.open:>10.2f} {bar.high:>10.2f} {bar.low:>10.2f} {bar.close:>10.2f} | closed={bar.is_closed}"
        )

    # Subscribe to bars for BTC only
    feed.on_bar(on_bar, symbols=["BTCUSDT"])  # optional; otherwise receives all symbols

    # Connection status callback
    def on_event(evt):
        if evt.event_type.name == "CONNECTION":
            print(f"CONNECTION {evt.connection_status} | {evt.connection_id}")

    feed.subscribe_connection_events(on_event)

    await feed.start(
        symbols=[s.upper() for s in args.symbols], interval=tf, only_closed=True, warm_up=10
    )
    try:
        await asyncio.sleep(args.duration)
        # Snapshot and history examples
        snap = feed.snapshot()
        print("Snapshot (latest bars):", {k: (v.close if v else None) for k, v in snap.items()})
        hist = feed.get_bar_history("BTCUSDT", count=3)
        print("BTC last 3 closes:", [b.close for b in hist])
    finally:
        await feed.stop()
        await rest.close()


if __name__ == "__main__":
    asyncio.run(main())
