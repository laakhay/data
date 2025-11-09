#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio

from laakhay.data.core import MarketType
from laakhay.data.providers.binance import BinanceWSProvider


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stream Binance Order Book via WebSocket")
    p.add_argument("symbol", nargs="?", default="BTCUSDT")
    p.add_argument("market", nargs="?", default="SPOT", choices=["SPOT", "FUTURES"])
    p.add_argument("update_speed", nargs="?", default="100ms", choices=["100ms", "1000ms"])
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    market = MarketType[args.market]
    ws = BinanceWSProvider(market_type=market)
    print("=" * 60)
    print(f"Streaming order book deltas for {args.symbol} on {market.name} @ {args.update_speed}")
    print("=" * 60)
    async for ob in ws.stream_order_book(args.symbol, update_speed=args.update_speed):
        print(
            f"{ob.timestamp.isoformat()} {ob.symbol} LUID={ob.last_update_id} bids={len(ob.bids)} asks={len(ob.asks)}"
        )


if __name__ == "__main__":
    asyncio.run(main())
