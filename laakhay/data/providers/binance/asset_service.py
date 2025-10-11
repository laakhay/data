"""Binance Asset Service adapter for product list and circulating market caps.

This adapter uses the public endpoint:
  https://www.binance.com/bapi/asset/v2/public/asset-service/product/get-products

We parse fields:
- s: trading symbol (e.g., BTCUSDT)
- b: base asset (e.g., BTC)
- q: quote asset (e.g., USDT)
- c: last price (string/number)
- cs: circulating supply (string/number)

Circulating market cap is computed as: Decimal(c) * Decimal(cs).

Caching: in-memory TTL cache with configurable refresh time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from ...utils.http import HTTPClient


BINANCE_PRODUCTS_URL = "https://www.binance.com/bapi/asset/v2/public/asset-service/product/get-products"


@dataclass(frozen=True)
class ProductCap:
    symbol: str
    base_asset: str
    quote_asset: str
    price: Decimal
    circulating_supply: Decimal
    circulating_market_cap: Decimal

    def to_dict(self) -> Dict[str, str]:
        return {
            "symbol": self.symbol,
            "base_asset": self.base_asset,
            "quote_asset": self.quote_asset,
            "price": str(self.price),
            "circulating_supply": str(self.circulating_supply),
            "circulating_market_cap": str(self.circulating_market_cap),
        }


class BinanceAssetService:
    def __init__(
        self,
        *,
        http: Optional[HTTPClient] = None,
        ttl_seconds: int = 600,
    ) -> None:
        self._http = http or HTTPClient()
        self._ttl = ttl_seconds
        self._cache_ts: float = 0.0
        self._cache: List[Dict[str, Any]] = []

    async def close(self) -> None:
        await self._http.close()

    async def _fetch_products_raw(self) -> List[Dict[str, Any]]:
        data = await self._http.get(BINANCE_PRODUCTS_URL)
        # Expected shape: { "data": [ { ... } ] }
        items = data.get("data") if isinstance(data, dict) else None
        if isinstance(items, list):
            return items  # raw product entries
        # If API returns list directly, handle it
        if isinstance(data, list):
            return data
        return []

    def _cache_valid(self) -> bool:
        if not self._cache_ts:
            return False
        return (time.time() - self._cache_ts) <= self._ttl

    async def get_products(self, *, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Return raw product list with TTL caching."""
        if not force_refresh and self._cache_valid():
            return self._cache
        items = await self._fetch_products_raw()
        self._cache = items
        self._cache_ts = time.time()
        return items

    async def get_market_caps(
        self,
        *,
        quote: Optional[str] = None,
        min_circulating_supply: Optional[Decimal] = None,
        force_refresh: bool = False,
    ) -> List[ProductCap]:
        """Compute circulating market caps from products.

        Args:
            quote: Filter by quote asset (e.g., "USDT"). If None, include all.
            min_circulating_supply: Drop assets with CS below this threshold.
            force_refresh: Bypass cache.
        """
        items = await self.get_products(force_refresh=force_refresh)
        out: List[ProductCap] = []
        for it in items:
            try:
                symbol = str(it.get("s") or it.get("symbol") or "").upper()
                base = str(it.get("b") or it.get("baseAsset") or "").upper()
                q = str(it.get("q") or it.get("quoteAsset") or "").upper()
                if not symbol or not base or not q:
                    continue
                if quote and q != quote.upper():
                    continue
                c_raw = it.get("c")
                cs_raw = it.get("cs")
                if c_raw is None or cs_raw is None:
                    continue
                price = Decimal(str(c_raw))
                circ_supply = Decimal(str(cs_raw))
                if min_circulating_supply is not None and circ_supply < min_circulating_supply:
                    continue
                mc = price * circ_supply
                out.append(
                    ProductCap(
                        symbol=symbol,
                        base_asset=base,
                        quote_asset=q,
                        price=price,
                        circulating_supply=circ_supply,
                        circulating_market_cap=mc,
                    )
                )
            except (InvalidOperation, ValueError, TypeError):
                # Skip entries with non-numeric values
                continue
        # Sort by MC descending
        out.sort(key=lambda x: x.circulating_market_cap, reverse=True)
        return out

    async def get_top_market_caps(
        self,
        n: int = 100,
        *,
        quote: Optional[str] = "USDT",
        min_circulating_supply: Optional[Decimal] = None,
        force_refresh: bool = False,
    ) -> List[ProductCap]:
        items = await self.get_market_caps(
            quote=quote,
            min_circulating_supply=min_circulating_supply,
            force_refresh=force_refresh,
        )
        return items[: max(0, n)]
