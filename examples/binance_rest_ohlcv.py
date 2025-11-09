#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio

from laakhay.data.core import MarketType, Timeframe
from laakhay.data.providers.binance import BinanceRESTProvider


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch recent Binance OHLCV via REST")
    p.add_argument("symbol", nargs="?", default="BTCUSDT")
    p.add_argument("timeframe", nargs="?", default="M1")
    p.add_argument("limit", nargs="?", type=int, default=10)
    p.add_argument("market", nargs="?", default="SPOT", choices=["SPOT", "FUTURES"])
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    tf = getattr(Timeframe, args.timeframe)
    market = MarketType[args.market]

    rest = BinanceRESTProvider(market_type=market)
    ohlcv = await rest.get_candles(args.symbol, tf, limit=args.limit)
    print("=" * 65)
    print(f"Symbol     : {ohlcv.meta.symbol}")
    print(f"Timeframe  : {ohlcv.meta.timeframe}")
    print(f"Bars count : {len(ohlcv.bars)}")
    print("=" * 65)
    print(
        f"{'Timestamp':25} | {'Open':>11} | {'High':>11} | {'Low':>11} | {'Close':>11} | {'Volume':>13}"
    )
    print("-" * 83)
    for b in ohlcv.bars:
        print(
            f"{b.timestamp.isoformat():25} | {b.open:>11.2f} | {b.high:>11.2f} | {b.low:>11.2f} | {b.close:>11.2f} | {b.volume:>13.2f}"
        )
    print("=" * 65)
    await rest.close()


if __name__ == "__main__":
    asyncio.run(main())
