#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio

from laakhay.data.core import MarketType, Timeframe
from laakhay.data.providers.binance import BinanceWSProvider


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stream Binance OHLCV via WebSocket")
    p.add_argument("symbol", nargs="?", default="BTCUSDT")
    p.add_argument("timeframe", nargs="?", default="M1")
    p.add_argument("market", nargs="?", default="SPOT", choices=["SPOT", "FUTURES"])
    p.add_argument("only_closed", nargs="?", default="false", choices=["true", "false"])
    p.add_argument("throttle_ms", nargs="?", type=int, default=250)
    p.add_argument("dedupe", nargs="?", default="true", choices=["true", "false"])
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    tf = getattr(Timeframe, args.timeframe)
    market = MarketType[args.market]
    only_closed = args.only_closed.lower() == "true"
    throttle_ms = args.throttle_ms if args.throttle_ms and args.throttle_ms > 0 else None
    dedupe = args.dedupe.lower() == "true"

    ws = BinanceWSProvider(market_type=market)
    print("=" * 72)
    print(
        f"Streaming {args.symbol} {tf.name} on {market.name} | only_closed={only_closed} | throttle_ms={throttle_ms or 0} | dedupe={dedupe}"
    )
    print("=" * 72)
    print(
        f"{'Timestamp':25} | {'Symbol':8} | {'Open':>11} | {'High':>11} | {'Low':>11} | {'Close':>11} | {'Closed':>6}"
    )
    print("-" * 72)
    async for bar in ws.stream_ohlcv(
        args.symbol, tf, only_closed=only_closed, throttle_ms=throttle_ms, dedupe_same_candle=dedupe
    ):
        print(
            f"{bar.timestamp.isoformat():25} | {bar.symbol:8} | {bar.open:>11.2f} | {bar.high:>11.2f} | {bar.low:>11.2f} | {bar.close:>11.2f} | {str(bool(bar.is_closed)):>6}"
        )


if __name__ == "__main__":
    asyncio.run(main())
