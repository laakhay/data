#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from laakhay.data.core import MarketType
from laakhay.data.providers.binance import BinanceRESTProvider


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch Binance funding rates via REST (Futures)")
    p.add_argument("symbol", nargs="?", default="BTCUSDT")
    p.add_argument("limit", nargs="?", type=int, default=20)
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    rest = BinanceRESTProvider(market_type=MarketType.FUTURES)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=2)
    try:
        rates = await rest.get_funding_rate(
            args.symbol, start_time=start, end_time=end, limit=args.limit
        )
        print(f"Funding rates for {args.symbol} — showing {len(rates)}:")
        print(f"{'Funding Time':25} | {'Rate (%)':>10} | {'Annualized (%)':>16}")
        print("-" * 60)
        for r in rates:
            print(
                f"{r.funding_time.isoformat():25} | {r.funding_rate_percentage:>10.6f} | {r.annual_rate_percentage:>16.2f}"
            )
    finally:
        await rest.close()


if __name__ == "__main__":
    asyncio.run(main())
