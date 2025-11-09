#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio

from laakhay.data.core import MarketType
from laakhay.data.providers.binance import BinanceRESTProvider


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch Binance recent trades via REST")
    p.add_argument("symbol", nargs="?", default="BTCUSDT")
    p.add_argument("limit", nargs="?", type=int, default=20)
    p.add_argument("market", nargs="?", default="SPOT", choices=["SPOT", "FUTURES"])
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    market = MarketType[args.market]

    rest = BinanceRESTProvider(market_type=market)
    trades = await rest.get_recent_trades(args.symbol, limit=args.limit)
    print(f"Recent trades for {args.symbol} ({args.market}) — showing {len(trades)}:")
    print(f"{'Time':25} | {'Side':>4} | {'Price':>12} | {'Qty':>12} | {'Value':>14}")
    print("-" * 80)
    for t in trades:
        print(
            f"{t.timestamp.isoformat():25} | {t.side:>4} | {t.price:>12} | {t.quantity:>12} | {t.value:>14}"
        )
    await rest.close()


if __name__ == "__main__":
    asyncio.run(main())
