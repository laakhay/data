#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio

from laakhay.data.core import MarketType
from laakhay.data.providers.binance import BinanceRESTProvider


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch Binance Order Book via REST")
    p.add_argument("symbol", nargs="?", default="BTCUSDT")
    p.add_argument("limit", nargs="?", type=int, default=50)
    p.add_argument("market", nargs="?", default="SPOT", choices=["SPOT", "FUTURES"])
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    market = MarketType[args.market]
    rest = BinanceRESTProvider(market_type=market)
    ob = await rest.get_order_book(args.symbol, limit=args.limit)
    print(f"{ob.symbol} Order Book (top {args.limit})")
    print("Bids:")
    for p, q in ob.bids[:10]:
        print(f"  {p:>12} x {q:>12}")
    print("Asks:")
    for p, q in ob.asks[:10]:
        print(f"  {p:>12} x {q:>12}")
    await rest.close()


if __name__ == "__main__":
    asyncio.run(main())
