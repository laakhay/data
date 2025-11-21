"""OKX exchange info endpoint definition and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

import contextlib
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.models import Symbol
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec

from ...config import INST_TYPE_MAP


def build_path(params: dict[str, Any]) -> str:
    """Build the instruments path."""
    return "/api/v5/public/instruments"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for instruments endpoint."""
    market_type: MarketType = params["market_type"]
    inst_type = INST_TYPE_MAP[market_type]
    return {"instType": inst_type}


# Endpoint specification
SPEC = RestEndpointSpec(
    id="exchange_info",
    method="GET",
    build_path=build_path,
    build_query=build_query,
)


def _extract_result(response: Any) -> Any:
    """Extract result from OKX's response wrapper.

    OKX API v5 returns: {code: "0", msg: "", data: [...]}
    """
    if not isinstance(response, dict):
        raise ValueError(f"Invalid response format: expected dict, got {type(response)}")

    code = response.get("code", "-1")
    msg = response.get("msg", "Unknown error")

    if code != "0":
        raise ValueError(f"OKX API error: {msg} (code: {code})")

    data = response.get("data")
    if data is None:
        raise ValueError("OKX API response missing 'data' field")

    return data


class Adapter(ResponseAdapter):
    """Adapter for parsing OKX instruments response into Symbol list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Symbol]:
        """Parse OKX instruments response.

        Args:
            response: Raw response from OKX API
            params: Request parameters containing market_type and optional quote_asset filter

        Returns:
            List of Symbol objects for trading pairs
        """
        data = _extract_result(response)
        market_type = params["market_type"]
        quote_asset_filter = params.get("quote_asset")

        if not isinstance(data, list):
            data = []

        out: list[Symbol] = []
        for inst in data:
            if not isinstance(inst, dict):
                continue

            # Filter by state - OKX uses "live" state for active trading
            state = inst.get("state", "")
            if state != "live":
                continue

            # Filter by quote asset if specified
            quote_asset = inst.get("quoteCcy", "")
            if quote_asset_filter and quote_asset != quote_asset_filter:
                continue

            # For futures, filter to SWAP only (perpetuals)
            if market_type == MarketType.FUTURES:
                inst_type = inst.get("instType", "")
                if inst_type != "SWAP":
                    continue

            # Extract tick size and step size from lotSz and tickSz
            tick_size = None
            step_size = None
            min_notional = None

            tick_size_str = inst.get("tickSz")
            if tick_size_str:
                with contextlib.suppress(ValueError, TypeError):
                    tick_size = Decimal(str(tick_size_str))

            lot_size_str = inst.get("lotSz")
            if lot_size_str:
                with contextlib.suppress(ValueError, TypeError):
                    step_size = Decimal(str(lot_size_str))

            min_notional_str = inst.get("minSz")
            if min_notional_str:
                with contextlib.suppress(ValueError, TypeError):
                    min_notional = Decimal(str(min_notional_str))

            symbol_str = inst.get("instId", "")
            base_asset = inst.get("baseCcy", "")
            quote_asset = inst.get("quoteCcy", "")

            if not symbol_str or not base_asset or not quote_asset:
                continue

            contract_type = inst.get("instType")
            delivery_date = inst.get("expTime")  # OKX uses expTime for delivery

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
