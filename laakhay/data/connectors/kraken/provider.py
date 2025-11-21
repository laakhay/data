"""Unified Kraken connector provider.

This provider combines REST and WebSocket connectors for use by DataRouter
or direct research use. It registers all feature handlers for capability
discovery.

Note: This is a minimal stub implementation. Full provider implementation
will be added once REST and WS connectors are complete.
"""

from __future__ import annotations

from laakhay.data.connectors.kraken.urm import KrakenURM
from laakhay.data.core import MarketType
from laakhay.data.core.base import BaseProvider


class KrakenProvider(BaseProvider):
    """Unified Kraken provider (stub implementation).

    This is a minimal stub to enable provider registration until the full
    implementation is complete. Currently only the URM mapper is functional.
    """

    def __init__(
        self,
        *,
        market_type: MarketType = MarketType.SPOT,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        """Initialize Kraken provider stub.

        Args:
            market_type: Market type (spot or futures)
            api_key: Optional API key (not used in stub)
            api_secret: Optional API secret (not used in stub)
        """
        super().__init__(name="kraken")
        self.market_type = market_type

    async def close(self) -> None:
        """Close provider resources (no-op for stub)."""
        pass
