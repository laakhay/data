"""Bybit exchange info endpoint definition and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

import contextlib
from decimal import Decimal
from typing import Any

from laakhay.data.connectors.bybit.config import CATEGORY_MAP
from laakhay.data.core import MarketType
from laakhay.data.core.exceptions import DataError
from laakhay.data.models import Symbol
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec


def _extract_result(response: Any) -> Any:
    """Extract result from Bybit's response wrapper."""
    if not isinstance(response, dict):
        raise DataError(f"Invalid response format: expected dict, got {type(response)}")

    ret_code = response.get("retCode", -1)
    ret_msg = response.get("retMsg", "Unknown error")

    if ret_code != 0:
        raise DataError(f"Bybit API error: {ret_msg} (code: {ret_code})")

    result = response.get("result")
    if result is None:
        raise DataError("Bybit API response missing 'result' field")

    return result


def build_path(_params: dict[str, Any]) -> str:
    """Build the instruments-info path (same for both market types)."""
    return "/v5/market/instruments-info"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for instruments-info endpoint."""
    market: MarketType = params["market_type"]
    category = CATEGORY_MAP[market]
    # Bybit supports status filter, but we'll filter in adapter
    return {"category": category}


# Endpoint specification
SPEC = RestEndpointSpec(
    id="exchange_info",
    method="GET",
    build_path=build_path,
    build_query=build_query,
)


class Adapter(ResponseAdapter):
    """Adapter for parsing Bybit instruments-info response into Symbol list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Symbol]:
        """Parse Bybit instruments-info response.

        Args:
            response: Raw response from Bybit API
            params: Request parameters containing market_type and optional quote_asset filter

        Returns:
            List of Symbol objects for trading pairs
        """
        result = _extract_result(response)
        market_type = params["market_type"]
        quote_asset_filter = params.get("quote_asset")

        # Bybit returns list in "list" field
        instruments = result.get("list", []) if isinstance(result, dict) else result
        if not isinstance(instruments, list):
            instruments = []

        out: list[Symbol] = []
        for inst in instruments:
            if not isinstance(inst, dict):
                continue

            # Filter by status - Bybit uses "Trading" status
            status = inst.get("status", "")
            if status != "Trading":
                continue

            # Filter by quote asset if specified
            quote_asset = inst.get("quoteCoin", "")
            if quote_asset_filter and quote_asset != quote_asset_filter:
                continue

            # For futures, filter to perpetuals only
            if market_type.name == "FUTURES":
                contract_type = inst.get("contractType", "")
                if contract_type != "Perpetual":
                    continue

            # Extract tick size and step size from lotSizeFilter and priceFilter
            tick_size = None
            step_size = None
            min_notional = None

            # Price filter
            price_filter = inst.get("priceFilter", {})
            if isinstance(price_filter, dict):
                tick_size_str = price_filter.get("tickSize")
                if tick_size_str:
                    with contextlib.suppress(ValueError, TypeError):
                        tick_size = Decimal(str(tick_size_str))

            # Lot size filter
            lot_size_filter = inst.get("lotSizeFilter", {})
            if isinstance(lot_size_filter, dict):
                step_size_str = lot_size_filter.get("qtyStep")
                if step_size_str:
                    with contextlib.suppress(ValueError, TypeError):
                        step_size = Decimal(str(step_size_str))

            # Min notional filter
            min_notional_filter = inst.get("minNotionalFilter", {})
            if isinstance(min_notional_filter, dict):
                min_notional_str = min_notional_filter.get("notional")
                if min_notional_str:
                    with contextlib.suppress(ValueError, TypeError):
                        min_notional = Decimal(str(min_notional_str))

            symbol_str = inst.get("symbol", "")
            base_asset = inst.get("baseCoin", "")
            quote_asset = inst.get("quoteCoin", "")

            if not symbol_str or not base_asset or not quote_asset:
                continue

            contract_type = inst.get("contractType")
            delivery_date = inst.get("deliveryDate")

            out.append(
                Symbol(
                    symbol=symbol_str,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    tick_size=tick_size,
                    step_size=step_size,
                    min_notional=min_notional,
                    contract_type=contract_type,
                    delivery_date=delivery_date,
                )
            )

        return out
