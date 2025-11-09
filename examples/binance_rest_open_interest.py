#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from laakhay.data.core import MarketType
from laakhay.data.providers.binance import BinanceRESTProvider


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch Binance Open Interest via REST")
    p.add_argument("symbol", nargs="?", default="BTCUSDT")
    p.add_argument("mode", nargs="?", default="current", choices=["current", "hist"])
    p.add_argument(
        "period", nargs="?", default="5m", help="Binance OI period for history (e.g., 5m, 15m, 1h)"
    )
    p.add_argument("limit", nargs="?", type=int, default=30)
    return p.parse_args()


async def main() -> None:
    args = parse_args()

    rest = BinanceRESTProvider(market_type=MarketType.FUTURES)
    if args.mode == "current":
        data = await rest.get_open_interest(args.symbol, historical=False)
        print("Current Open Interest:")
        for oi in data:
            print(f"{oi.timestamp.isoformat()} | {oi.symbol} | OI={oi.open_interest}")
    else:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=1)
        data = await rest.get_open_interest(
            args.symbol,
            historical=True,
            period=args.period,
            start_time=start,
            end_time=end,
            limit=args.limit,
        )
        print("Historical Open Interest:")
        for oi in data:
            print(f"{oi.timestamp.isoformat()} | {oi.symbol} | OI={oi.open_interest}")

    await rest.close()


if __name__ == "__main__":
    asyncio.run(main())
