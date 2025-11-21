"""MEXC exchange info endpoint definition and adapter.

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
    # MEXC uses /api/v3/exchangeInfo for spot and /api/v1/contract/symbols for futures
    return "/api/v1/contract/symbols" if market == MarketType.FUTURES else "/api/v3/exchangeInfo"


# Endpoint specification
SPEC = RestEndpointSpec(
    id="exchange_info",
    method="GET",
    build_path=build_path,
    build_query=lambda _: {},
)


class Adapter(ResponseAdapter):
    """Adapter for parsing MEXC exchangeInfo response into Symbol list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Symbol]:
        """Parse MEXC exchangeInfo response.

        Args:
            response: Raw response from MEXC API
            params: Request parameters containing market_type and optional quote_asset filter

        Returns:
            List of Symbol objects for trading pairs
        """
        market_type = params["market_type"]
        quote_asset_filter = params.get("quote_asset")
        out: list[Symbol] = []

        # MEXC response structure may vary between spot and futures
        symbols_data = response.get("symbols", []) or response.get("data", []) or []

        for sd in symbols_data:
            if isinstance(sd, dict):
                # Check status (may be "TRADING" or "ENABLED" or similar)
                status = sd.get("status") or sd.get("state")
                if status and status not in ["TRADING", "ENABLED", "1"]:
                    continue

                if quote_asset_filter:
                    quote_asset = sd.get("quoteAsset") or sd.get("quote_asset") or sd.get("quote")
                    if quote_asset != quote_asset_filter:
                        continue

                if market_type.name == "FUTURES":
                    contract_type = sd.get("contractType") or sd.get("contract_type")
                    if contract_type and contract_type != "PERPETUAL":
                        continue

                tick_size = None
                step_size = None
                min_notional = None

                # Extract filters (MEXC may structure this differently)
                filters = sd.get("filters", []) or sd.get("filters_list", []) or []
                for f in filters:
                    if isinstance(f, dict):
                        t = f.get("filterType") or f.get("filter_type")
                        if t == "PRICE_FILTER":
                            v = f.get("tickSize") or f.get("tick_size")
                            tick_size = Decimal(str(v)) if v is not None else None
                        elif t == "LOT_SIZE":
                            v = f.get("stepSize") or f.get("step_size")
                            step_size = Decimal(str(v)) if v is not None else None
                        elif t == "MIN_NOTIONAL":
                            v = f.get("minNotional") or f.get("min_notional")
                            min_notional = Decimal(str(v)) if v is not None else None

                symbol_name = sd.get("symbol") or sd.get("symbolName")
                base_asset = sd.get("baseAsset") or sd.get("base_asset") or sd.get("base")
                quote_asset = sd.get("quoteAsset") or sd.get("quote_asset") or sd.get("quote")

                if symbol_name and base_asset and quote_asset:
                    out.append(
                        Symbol(
                            symbol=symbol_name,
                            base_asset=base_asset,
                            quote_asset=quote_asset,
                            tick_size=tick_size,
                            step_size=step_size,
                            min_notional=min_notional,
                            contract_type=sd.get("contractType") or sd.get("contract_type"),
                            delivery_date=sd.get("deliveryDate") or sd.get("delivery_date"),
                        )
                    )

        return out
