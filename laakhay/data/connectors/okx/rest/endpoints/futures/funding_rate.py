"""OKX funding rate endpoint definition and adapter.

This endpoint is Futures-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.models import FundingRate
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec

from ....config import to_okx_symbol


def build_path(params: dict[str, Any]) -> str:
    """Build the fundingRate path (futures only)."""
    market: MarketType = params["market_type"]
    if market != MarketType.FUTURES:
        raise ValueError("Funding rate endpoint is Futures-only on OKX")
    return "/api/v5/public/funding-rate"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for fundingRate endpoint."""
    q: dict[str, Any] = {
        "instId": to_okx_symbol(params["symbol"]),
    }
    if params.get("limit"):
        q["limit"] = min(int(params.get("limit", 100)), 100)  # OKX max is 100
    return q


# Endpoint specification
SPEC = RestEndpointSpec(
    id="funding_rate",
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
    """Adapter for parsing OKX fundingRate response into FundingRate list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[FundingRate]:
        """Parse OKX fundingRate response.

        Args:
            response: Raw response from OKX API (list of funding rate data)
            params: Request parameters containing symbol

        Returns:
            List of FundingRate objects
        """
        data = _extract_result(response)
        symbol = params["symbol"].upper()

        if not isinstance(data, list):
            return []

        out: list[FundingRate] = []
        for row in data:
            if not isinstance(row, dict):
                continue

            try:
                # OKX format: {instId, fundingRate, fundingTime, nextFundingTime, markPx}
                fr_str = row.get("fundingRate")
                ts_str = row.get("fundingTime", "")
                mark_price_str = row.get("markPx")

                if fr_str is None or not ts_str:
                    continue

                # Convert timestamp
                if "T" in ts_str:
                    ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    ts_ms = int(ts_dt.timestamp() * 1000)
                else:
                    ts_ms = int(ts_str)

                funding_rate = Decimal(str(fr_str))
                mark_price = Decimal(str(mark_price_str)) if mark_price_str else None

                out.append(
                    FundingRate(
                        symbol=symbol,
                        funding_time=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                        funding_rate=funding_rate,
                        mark_price=mark_price,
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue

        return out
