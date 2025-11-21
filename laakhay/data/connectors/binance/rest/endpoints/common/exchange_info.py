"""Binance exchange info endpoint definition and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.models import Symbol
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def build_path(params: dict[str, Any]) -> str:
    """Build the exchangeInfo path based on market type."""
    market: MarketType = params["market_type"]
    return "/fapi/v1/exchangeInfo" if market == MarketType.FUTURES else "/api/v3/exchangeInfo"


# Endpoint specification
SPEC = RestEndpointSpec(
    id="exchange_info",
    method="GET",
    build_path=build_path,
    build_query=lambda _: {},
)


class Adapter(ResponseAdapter):
    """Adapter for parsing Binance exchangeInfo response into Symbol list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Symbol]:
        """Parse Binance exchangeInfo response.

        Args:
            response: Raw response from Binance API
            params: Request parameters containing market_type and optional quote_asset filter

        Returns:
            List of Symbol objects for trading pairs
        """
        market_type = params["market_type"]
        quote_asset_filter = params.get("quote_asset")
        out: list[Symbol] = []
        for sd in response.get("symbols", []) or []:
            if sd.get("status") != "TRADING":
                continue
            if quote_asset_filter and sd.get("quoteAsset") != quote_asset_filter:
                continue
            if market_type.name == "FUTURES" and sd.get("contractType") != "PERPETUAL":
                continue
            tick_size = None
            step_size = None
            min_notional = None
            for f in sd.get("filters", []) or []:
                t = f.get("filterType")
                if t == "PRICE_FILTER":
                    v = f.get("tickSize")
                    tick_size = Decimal(str(v)) if v is not None else None
                elif t == "LOT_SIZE":
                    v = f.get("stepSize")
                    step_size = Decimal(str(v)) if v is not None else None
                elif t == "MIN_NOTIONAL":
                    v = f.get("minNotional")
                    min_notional = Decimal(str(v)) if v is not None else None

            out.append(
                Symbol(
                    symbol=sd["symbol"],
                    base_asset=sd["baseAsset"],
                    quote_asset=sd["quoteAsset"],
                    tick_size=tick_size,
                    step_size=step_size,
                    min_notional=min_notional,
                    contract_type=sd.get("contractType"),
                    delivery_date=sd.get("deliveryDate"),
                )
            )
        return out
