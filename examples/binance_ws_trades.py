#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio

from laakhay.data.core import MarketType
from laakhay.data.providers.binance import BinanceProvider


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stream Binance trades for a symbol")
    p.add_argument("symbol", nargs="?", default="BTCUSDT")
    p.add_argument("market", nargs="?", default="SPOT", choices=["SPOT", "FUTURES"])
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    market = MarketType[args.market]

    provider = BinanceProvider(market_type=market)
    await provider.__aenter__()
    try:
        async for trade in provider.stream_trades(args.symbol.upper()):
            print(
                f"{trade.timestamp.isoformat()} | {trade.symbol} | price={trade.price} qty={trade.quantity}"
            )
    finally:
        await provider.__aexit__(None, None, None)


if __name__ == "__main__":
    asyncio.run(main())
