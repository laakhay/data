"""Kraken exchange info endpoint definition and adapter.

This endpoint is available for both spot and futures markets.
"""

from __future__ import annotations

import contextlib
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.core.exceptions import DataError
from laakhay.data.models import Symbol
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec

from ....urm import KrakenURM

_urm = KrakenURM()


def build_path(params: dict[str, Any]) -> str:
    """Build the exchangeInfo path based on market type."""
    market: MarketType = params["market_type"]
    if market == MarketType.FUTURES:
        # Kraken Futures API
        return "/instruments"
    else:
        # Kraken Spot API
        return "/0/public/AssetPairs"


# Endpoint specification
SPEC = RestEndpointSpec(
    id="exchange_info",
    method="GET",
    build_path=build_path,
    build_query=lambda _: {},  # No query params for exchange info
)


def _extract_result(response: Any, market_type: MarketType) -> Any:
    """Extract result from Kraken's response wrapper."""
    if not isinstance(response, dict):
        raise DataError(f"Invalid response format: expected dict, got {type(response)}")

    # Check for errors in Kraken Spot format
    errors = response.get("error", [])
    if errors and len(errors) > 0:
        error_msg = errors[0] if isinstance(errors, list) else str(errors)
        raise DataError(f"Kraken API error: {error_msg}")

    # Kraken Spot wraps in "result" field
    if "result" in response:
        result_value = response["result"]
        # For Futures, if result is "ok", return the full response (data is in other fields)
        if result_value == "ok" and market_type == MarketType.FUTURES:
            return response
        return result_value

    # Kraken Futures may return direct result or wrapped
    if "error" in response and response["error"]:
        raise DataError(f"Kraken API error: {response.get('error', 'Unknown error')}")

    # Return response itself if no wrapper
    return response


class Adapter(ResponseAdapter):
    """Adapter for parsing Kraken exchangeInfo response into Symbol list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[Symbol]:
        """Parse Kraken exchangeInfo response.

        Args:
            response: Raw response from Kraken API
            params: Request parameters containing market_type and optional quote_asset filter

        Returns:
            List of Symbol objects for trading pairs
        """
        market_type = params["market_type"]
        quote_asset_filter = params.get("quote_asset")

        result = _extract_result(response, market_type)
        out: list[Symbol] = []

        if market_type == MarketType.FUTURES:
            # Kraken Futures format: {result: "ok", instruments: [{symbol, type, underlying, ...}, ...]}
            instruments = result.get("instruments", []) if isinstance(result, dict) else result
            if not isinstance(instruments, list):
                instruments = []

            for inst in instruments:
                if not isinstance(inst, dict):
                    continue

                # Filter by status if available
                status = inst.get("status", "open")
                if status != "open":
                    continue

                symbol_str = inst.get("symbol", "")
                if not symbol_str:
                    continue

                # Convert to canonical symbol using URM
                try:
                    spec = _urm.to_spec(symbol_str, market_type=market_type)
                    canonical_symbol = f"{spec.base}{spec.quote}"
                except Exception:
                    # Fallback: normalize manually
                    canonical_symbol = symbol_str.replace("PI_", "").replace("XBT", "BTC")

                # Extract base and quote assets
                base_asset = inst.get("underlying", "").replace("XBT", "BTC")
                quote_asset = inst.get("quoteCurrency", "USD")

                # Filter by quote asset if specified
                if quote_asset_filter and quote_asset.upper() != quote_asset_filter.upper():
                    continue

                # Extract tick size and step size
                tick_size = None
                step_size = None
                min_notional = None

                tick_size_str = inst.get("tickSize")
                if tick_size_str:
                    with contextlib.suppress(ValueError, TypeError):
                        tick_size = Decimal(str(tick_size_str))

                step_size_str = inst.get("contractSize") or inst.get("lotSize")
                if step_size_str:
                    with contextlib.suppress(ValueError, TypeError):
                        step_size = Decimal(str(step_size_str))

                contract_type = inst.get("type", "perpetual")
                delivery_date = inst.get("expiry") or inst.get("expiryDate")

                out.append(
                    Symbol(
                        symbol=canonical_symbol,
                        base_asset=base_asset or canonical_symbol[:3],
                        quote_asset=quote_asset or canonical_symbol[-3:],
                        tick_size=tick_size,
                        step_size=step_size,
                        min_notional=min_notional,
                        contract_type=contract_type,
                        delivery_date=delivery_date,
                    )
                )

        else:
            # Kraken Spot format: {result: {PAIR: {altname, wsname, base, quote, ...}, ...}}
            if not isinstance(result, dict):
                return out

            for pair_key, pair_info in result.items():
                if not isinstance(pair_info, dict):
                    continue

                # Filter by status
                status = pair_info.get("status", "")
                if status and status != "online":
                    continue

                # Convert to canonical symbol using URM
                try:
                    spec = _urm.to_spec(pair_key, market_type=market_type)
                    canonical_symbol = f"{spec.base}{spec.quote}"
                except Exception:
                    # Fallback: normalize manually
                    canonical_symbol = pair_key.replace("/", "").replace("XBT", "BTC")

                # Extract base and quote assets
                base_asset = pair_info.get("base", "")
                quote_asset = pair_info.get("quote", "")

                # Convert XBT to BTC
                if base_asset == "XBT":
                    base_asset = "BTC"

                # Filter by quote asset if specified
                if quote_asset_filter and quote_asset.upper() != quote_asset_filter.upper():
                    continue

                # Extract tick size and step size
                tick_size = None
                step_size = None
                min_notional = None

                tick_size_str = pair_info.get("tick_size")
                if tick_size_str:
                    with contextlib.suppress(ValueError, TypeError):
                        tick_size = Decimal(str(tick_size_str))

                step_size_str = pair_info.get("lot_decimals")
                if step_size_str is not None:
                    with contextlib.suppress(ValueError, TypeError):
                        # lot_decimals is number of decimals, calculate step size
                        step_size = Decimal("1") / (Decimal("10") ** int(step_size_str))

                min_notional_str = pair_info.get("ordermin")
                if min_notional_str:
                    with contextlib.suppress(ValueError, TypeError):
                        min_notional = Decimal(str(min_notional_str))

                out.append(
                    Symbol(
                        symbol=canonical_symbol,
                        base_asset=base_asset or canonical_symbol[:3],
                        quote_asset=quote_asset or canonical_symbol[-3:],
                        tick_size=tick_size,
                        step_size=step_size,
                        min_notional=min_notional,
                        contract_type=None,
                        delivery_date=None,
                    )
                )

        return out
