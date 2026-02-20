"""Universal Representation Mapping (URM) protocol and registry for laakhay-data.

This module provides the runtime registry for exchange mappers, using standardized
URM utilities from laakhay-core.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .enums import MarketType

from laakhay.core import (
    BaseURMMapper,
    InstrumentSpec,
    UniversalRepresentationMapper,
    parse_urm_id,
    spec_to_urm_id,
    validate_urm_id,
)

from .exceptions import SymbolResolutionError


class URMRegistry:
    """Registry for Universal Representation Mappers.

    Maintains mapper instances and symbol resolution cache for performance.
    """

    def __init__(self) -> None:
        # Mapper storage: exchange -> mapper
        self._mappers: dict[str, UniversalRepresentationMapper] = {}

        # Cache: (exchange, symbol, market_type) -> InstrumentSpec
        self._cache: dict[tuple[str, str, MarketType], InstrumentSpec] = {}
        self._cache_timestamps: dict[tuple[str, str, MarketType], datetime] = {}
        self._cache_ttl_seconds = 300  # 5 minutes default

    def register(self, exchange: str, mapper: UniversalRepresentationMapper) -> None:
        """Register a mapper for an exchange."""
        self._mappers[exchange.lower()] = mapper

    def register_quotes(self, exchange: str, quotes: set[str] | list[str]) -> None:
        """Register known quote assets for an exchange to assist its mapper."""
        exchange_lower = exchange.lower()
        if exchange_lower in self._mappers:
            mapper = self._mappers[exchange_lower]
            if hasattr(mapper, "set_quotes"):
                mapper.set_quotes(quotes)

    def unregister(self, exchange: str) -> None:
        """Unregister a mapper and clear its caches."""
        exchange_lower = exchange.lower()
        if exchange_lower in self._mappers:
            del self._mappers[exchange_lower]

        keys_to_remove = [key for key in self._cache if key[0] == exchange_lower]
        for key in keys_to_remove:
            del self._cache[key]
            if key in self._cache_timestamps:
                del self._cache_timestamps[key]

    def urm_to_spec(
        self,
        exchange_symbol: str,
        *,
        exchange: str,
        market_type: MarketType,
    ) -> InstrumentSpec:
        """Convert exchange-native symbol to InstrumentSpec using registered mapper."""
        exchange_lower = exchange.lower()

        if exchange_lower not in self._mappers:
            raise SymbolResolutionError(
                f"No mapper registered for exchange '{exchange}'",
                exchange=exchange,
                value=exchange_symbol,
                market_type=market_type,
            )

        cache_key = (exchange_lower, exchange_symbol.upper(), market_type)
        if cache_key in self._cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        mapper = self._mappers[exchange_lower]
        try:
            spec = mapper.to_spec(exchange_symbol, market_type=market_type)
        except Exception as e:
            raise SymbolResolutionError(
                f"Failed to resolve symbol '{exchange_symbol}' for {exchange}: {e}",
                exchange=exchange,
                value=exchange_symbol,
                market_type=market_type,
            ) from e

        self._cache[cache_key] = spec
        self._cache_timestamps[cache_key] = datetime.now()
        return spec

    def urm_to_exchange_symbol(
        self,
        spec: InstrumentSpec,
        *,
        exchange: str,
        market_type: MarketType,
    ) -> str:
        """Convert InstrumentSpec to exchange-native symbol using registered mapper."""
        exchange_lower = exchange.lower()

        if exchange_lower not in self._mappers:
            raise SymbolResolutionError(
                f"No mapper registered for exchange '{exchange}'",
                exchange=exchange,
            )

        mapper = self._mappers[exchange_lower]
        try:
            exchange_symbol = mapper.to_exchange_symbol(spec, market_type=market_type)
        except Exception as e:
            raise SymbolResolutionError(
                f"Failed to convert spec to {exchange} symbol: {e}",
                exchange=exchange,
                value=str(spec),
                market_type=market_type,
            ) from e

        return exchange_symbol

    def clear_cache(self, exchange: str | None = None) -> None:
        """Clear cache for an exchange or all exchanges."""
        if exchange:
            exchange_lower = exchange.lower()
            keys_to_remove = [key for key in self._cache if key[0] == exchange_lower]
            for key in keys_to_remove:
                del self._cache[key]
                if key in self._cache_timestamps:
                    del self._cache_timestamps[key]
        else:
            self._cache.clear()
            self._cache_timestamps.clear()

    def _is_cache_valid(self, cache_key: tuple[str, str, MarketType]) -> bool:
        if cache_key not in self._cache_timestamps:
            return False
        timestamp = self._cache_timestamps[cache_key]
        return datetime.now() - timestamp < timedelta(seconds=self._cache_ttl_seconds)


# Global registry instance
_default_registry: URMRegistry | None = None


def get_urm_registry() -> URMRegistry:
    """Get the default global URM registry instance."""
    global _default_registry
    if _default_registry is None:
        _default_registry = URMRegistry()
    return _default_registry


# Re-export pure utilities from core for backward compatibility
__all__ = [
    "URMRegistry",
    "get_urm_registry",
    "BaseURMMapper",
    "UniversalRepresentationMapper",
    "parse_urm_id",
    "spec_to_urm_id",
    "validate_urm_id",
]
