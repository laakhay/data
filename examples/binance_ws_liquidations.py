#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio

from laakhay.data.core import MarketType
from laakhay.data.providers.binance import BinanceWSProvider


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stream Binance Futures liquidations via WebSocket")
    p.add_argument("market", nargs="?", default="FUTURES", choices=["FUTURES"])
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    market = MarketType[args.market]
    ws = BinanceWSProvider(market_type=market)
    print("=" * 60)
    print("Streaming global liquidations (FUTURES): !forceOrder@arr")
    print("=" * 60)
    async for liq in ws.stream_liquidations():
        print(
            f"{liq.timestamp.isoformat()} {liq.symbol} side={liq.side} price={liq.price} qty={liq.original_quantity} status={liq.order_status}"
        )


if __name__ == "__main__":
    asyncio.run(main())
