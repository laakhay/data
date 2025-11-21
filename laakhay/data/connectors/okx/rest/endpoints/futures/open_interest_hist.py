"""OKX historical open interest endpoint definition and adapter.

This endpoint is Futures-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from laakhay.data.core import MarketType
from laakhay.data.models import OpenInterest
from laakhay.data.runtime.rest import ResponseAdapter, RestEndpointSpec

from ....config import OI_PERIOD_MAP, to_okx_symbol


def build_path(params: dict[str, Any]) -> str:
    """Build the open-interest-history path (futures only)."""
    market: MarketType = params["market_type"]
    if market != MarketType.FUTURES:
        raise ValueError("Open interest history endpoint is Futures-only on OKX")
    return "/api/v5/public/open-interest-history"


def build_query(params: dict[str, Any]) -> dict[str, Any]:
    """Build query parameters for open-interest-history endpoint."""
    period = params.get("period", "5m")
    period_str = OI_PERIOD_MAP.get(period, "5m")

    q: dict[str, Any] = {
        "instId": to_okx_symbol(params["symbol"]),
        "period": period_str,
        "limit": min(int(params.get("limit", 100)), 100),  # OKX max is 100
    }
    if params.get("start_time"):
        q["before"] = int(params["start_time"].timestamp() * 1000)
    if params.get("end_time"):
        q["after"] = int(params["end_time"].timestamp() * 1000)
    return q


# Endpoint specification
SPEC = RestEndpointSpec(
    id="open_interest_hist",
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
    """Adapter for parsing OKX open-interest-history response into OpenInterest list."""

    def parse(self, response: Any, params: dict[str, Any]) -> list[OpenInterest]:
        """Parse OKX open-interest-history response.

        Args:
            response: Raw response from OKX API
            params: Request parameters containing symbol

        Returns:
            List of OpenInterest objects
        """
        data = _extract_result(response)
        symbol = params["symbol"].upper()

        if not isinstance(data, list):
            return []

        out: list[OpenInterest] = []
        for row in data:
            if not isinstance(row, list) or len(row) < 2:
                continue

            try:
                # OKX format: [ts, oi, oiCcy]
                ts_str = str(row[0])
                if "T" in ts_str:
                    ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    ts_ms = int(ts_dt.timestamp() * 1000)
                else:
                    ts_ms = int(ts_str)

                oi_str = row[1] if len(row) > 1 else None
                oi_value_str = row[2] if len(row) > 2 else None

                if oi_str is None:
                    continue

                out.append(
                    OpenInterest(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
                        open_interest=Decimal(str(oi_str)),
                        open_interest_value=Decimal(str(oi_value_str)) if oi_value_str else None,
                    )
                )
            except (ValueError, TypeError, IndexError):
                continue

        return out
