#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio

from laakhay.data.core import MarketType, Timeframe
from laakhay.data.providers.binance import BinanceProvider


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stream Binance OHLCV for multiple symbols")
    p.add_argument("symbols", nargs="*", default=["BTCUSDT", "ETHUSDT"])
    p.add_argument("timeframe", nargs="?", default="M1")
    p.add_argument("market", nargs="?", default="SPOT", choices=["SPOT", "FUTURES"])
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    tf = getattr(Timeframe, args.timeframe)
    market = MarketType[args.market]

    provider = BinanceProvider(market_type=market)
    await provider.__aenter__()
    try:
        async for bar in provider.stream_ohlcv_multi([s.upper() for s in args.symbols], tf):
            print(
                f"{bar.timestamp.isoformat()} | {bar.symbol} | {bar.open:>10.2f} {bar.high:>10.2f} {bar.low:>10.2f} {bar.close:>10.2f} | closed={bar.is_closed}"
            )
    finally:
        await provider.__aexit__(None, None, None)


if __name__ == "__main__":
    asyncio.run(main())
