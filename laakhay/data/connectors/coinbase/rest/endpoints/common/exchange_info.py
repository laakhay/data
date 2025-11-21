"""Coinbase exchange info endpoint definition and adapter."""

from __future__ import annotations

import contextlib
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.models import Symbol
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec
from laakhay.data.connectors.coinbase.config import normalize_symbol_from_coinbase


def build_path(params: dict[str, Any]) -> str:
    """Build the products path."""
    market: MarketType = params["market_type"]
    if market != MarketType.SPOT:
        raise ValueError("Coinbase Advanced Trade API only supports Spot markets")
    return "/products"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for products endpoint."""
    # Coinbase supports limit and offset for pagination
    # We'll fetch all products and filter by quote_asset if needed
    q: dict[str, Any] = {
        "limit": 250,  # Coinbase max per page
    }
    return q


# Endpoint specification
SPEC = RestEndpointSpec(
    id="exchange_info",
    method="GET",
    build_path=build_path,
    build_query=build_query,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing Coinbase products response into Symbol list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Symbol]:
        """Parse Coinbase products response.

        Coinbase returns: {
            "products": [
                {
                    "product_id": "BTC-USD",
                    "price": "42800.00",
                    ...
                },
                ...
            ]
        }
        """
        quote_asset_filter = params.get("quote_asset")

        # Exchange API returns array directly (not wrapped in "products")
        products_data = response if isinstance(response, list) else response.get("products", [])
        if not isinstance(products_data, list):
            products_data = []

        out: list[Symbol] = []

        for product in products_data:
            if not isinstance(product, dict):
                continue

            try:
                # Filter by status - Coinbase uses "online" for active products
                status = product.get("status", "")
                if status != "online":
                    continue

                # Filter by trading disabled
                if product.get("trading_disabled", False):
                    continue

                # Exchange API doesn't have product_type field - all are spot
                # Advanced Trade API has product_type - filter for SPOT
                product_type = product.get("product_type")
                if product_type and product_type != "SPOT":
                    continue

                # Extract product_id (Exchange API uses "id", Advanced Trade uses "product_id")
                product_id = product.get("id") or product.get("product_id", "")
                if not product_id:
                    continue

                # Normalize symbol to standard format
                symbol = normalize_symbol_from_coinbase(product_id)

                # Extract base and quote assets
                # Exchange API uses "base_currency"/"quote_currency"
                # Advanced Trade API uses "base_currency_id"/"quote_currency_id"
                base_asset = product.get("base_currency") or product.get("base_currency_id", "")
                quote_asset = product.get("quote_currency") or product.get("quote_currency_id", "")

                # Filter by quote asset if specified
                if quote_asset_filter and quote_asset != quote_asset_filter:
                    continue

                # Extract tick size (price increment)
                # Exchange API uses "quote_increment", Advanced Trade uses "price_increment"
                price_increment_str = product.get("quote_increment") or product.get(
                    "price_increment"
                )
                tick_size = None
                if price_increment_str:
                    with contextlib.suppress(ValueError, TypeError):
                        tick_size = Decimal(str(price_increment_str))

                # Extract step size (size increment)
                # Exchange API uses "base_increment", Advanced Trade uses "size_increment"
                size_increment_str = product.get("base_increment") or product.get("size_increment")
                step_size = None
                if size_increment_str:
                    with contextlib.suppress(ValueError, TypeError):
                        step_size = Decimal(str(size_increment_str))

                # Extract min notional (quote min size)
                # Exchange API uses "min_market_funds", Advanced Trade uses "quote_min_size"
                quote_min_size_str = product.get("min_market_funds") or product.get(
                    "quote_min_size"
                )
                min_notional = None
                if quote_min_size_str:
                    with contextlib.suppress(ValueError, TypeError):
                        min_notional = Decimal(str(quote_min_size_str))

                out.append(
                    Symbol(
                        symbol=symbol,
                        base_asset=base_asset,
                        quote_asset=quote_asset,
                        tick_size=tick_size,
                        step_size=step_size,
                        min_notional=min_notional,
                        contract_type=None,  # Spot markets don't have contract types
                        delivery_date=None,  # Spot markets don't have delivery dates
                    )
                )
            except (ValueError, TypeError, KeyError):
                # Skip invalid products
                continue

        return out

