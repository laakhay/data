"""Universal Representation Mapping (URM) protocol and registry.

URM provides symbol normalization across exchanges. Each exchange implements
a mapper that converts between exchange-native symbols and canonical InstrumentSpec.

URM ID Format:
    urm://{exchange|*}:{base}/{quote}:{instrument_type}[:qualifiers]

Examples:
    - urm://binance:btc/usdt:spot
    - urm://kraken:xbt/usd:spot
    - urm://*:btc/usdt:perpetual
    - urm://okx:btc/usdt:future:20240329
    - urm://deribit:btc/usd:option:C:35000:20240628
"""

from __future__ import annotations

import re
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Protocol

from .enums import InstrumentSpec, InstrumentType, MarketType
from .exceptions import SymbolResolutionError


class UniversalRepresentationMapper(Protocol):
    """Protocol for exchange-specific symbol mappers.

    Each exchange implements this protocol to handle its unique symbol formats
    and naming conventions (e.g., XBT vs BTC, USDT vs USD, delivery dates).
    """

    def to_spec(
        self,
        exchange_symbol: str,
        *,
        market_type: MarketType,
    ) -> InstrumentSpec:
        """Convert exchange-native symbol to canonical InstrumentSpec.

        Args:
            exchange_symbol: Exchange-specific symbol (e.g., "BTCUSDT", "XBT/USD", "PI_XBTUSD")
            market_type: Market type (spot or futures)

        Returns:
            Canonical InstrumentSpec

        Raises:
            SymbolResolutionError: If symbol cannot be resolved
        """
        ...

    def to_exchange_symbol(
        self,
        spec: InstrumentSpec,
        *,
        market_type: MarketType,
    ) -> str:
        """Convert canonical InstrumentSpec to exchange-native symbol.

        Args:
            spec: Canonical InstrumentSpec
            market_type: Market type (spot or futures)

        Returns:
            Exchange-specific symbol string

        Raises:
            SymbolResolutionError: If spec cannot be converted to exchange format
        """
        ...


class URMRegistry:
    """Registry for Universal Representation Mappers.

    Simple registry that stores mappers per exchange and provides lookup methods.
    Each exchange's mapper handles all conversion logic.
    """

    def __init__(self) -> None:
        """Initialize URM registry."""
        self._mappers: dict[str, UniversalRepresentationMapper] = {}
        # Simple cache: (exchange, symbol, market_type) -> spec
        self._cache: dict[tuple[str, str, MarketType], InstrumentSpec] = {}
        self._cache_timestamps: dict[tuple[str, str, MarketType], datetime] = {}
        self._cache_ttl_seconds = 300  # 5 minutes default

    def register(
        self,
        exchange: str,
        mapper: UniversalRepresentationMapper,
    ) -> None:
        """Register a mapper for an exchange.

        Args:
            exchange: Exchange name (e.g., "binance", "kraken")
            mapper: Mapper implementing UniversalRepresentationMapper protocol
        """
        self._mappers[exchange.lower()] = mapper

    def unregister(self, exchange: str) -> None:
        """Unregister a mapper and clear its caches.

        Args:
            exchange: Exchange name to unregister
        """
        exchange_lower = exchange.lower()
        if exchange_lower in self._mappers:
            del self._mappers[exchange_lower]

        # Clear cache entries for this exchange
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
        """Convert exchange-native symbol to InstrumentSpec using registered mapper.

        Args:
            exchange_symbol: Exchange-specific symbol
            exchange: Exchange name
            market_type: Market type

        Returns:
            Canonical InstrumentSpec

        Raises:
            SymbolResolutionError: If exchange not registered or symbol cannot be resolved
        """
        exchange_lower = exchange.lower()

        if exchange_lower not in self._mappers:
            raise SymbolResolutionError(
                f"No mapper registered for exchange '{exchange}'",
                exchange=exchange,
                value=exchange_symbol,
                market_type=market_type,
            )

        # Check cache
        cache_key = (exchange_lower, exchange_symbol.upper(), market_type)
        if cache_key in self._cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        # Use mapper
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

        # Cache the result
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
        """Convert InstrumentSpec to exchange-native symbol using registered mapper.

        Args:
            spec: Canonical InstrumentSpec
            exchange: Exchange name
            market_type: Market type

        Returns:
            Exchange-specific symbol string

        Raises:
            SymbolResolutionError: If exchange not registered or conversion fails
        """
        exchange_lower = exchange.lower()

        if exchange_lower not in self._mappers:
            raise SymbolResolutionError(
                f"No mapper registered for exchange '{exchange}'",
                exchange=exchange,
            )

        # Use mapper
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
        """Clear cache for an exchange or all exchanges.

        Args:
            exchange: Optional exchange name. If None, clears all caches.
        """
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
        """Check if cache entry is still valid."""
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


def parse_urm_id(urm_id: str) -> InstrumentSpec:
    """Parse a scoped URM ID into InstrumentSpec.

    Format: urm://{exchange|*}:{base}/{quote}:{instrument_type}[:qualifiers]

    Args:
        urm_id: URM ID string (e.g., "urm://binance:btc/usdt:spot")

    Returns:
        Canonical InstrumentSpec

    Raises:
        SymbolResolutionError: If URM ID format is invalid

    Examples:
        >>> parse_urm_id("urm://binance:btc/usdt:spot")
        InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.SPOT)

        >>> parse_urm_id("urm://*:btc/usdt:perpetual")
        InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.PERPETUAL)

        >>> parse_urm_id("urm://okx:btc/usdt:future:20240329")
        InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.FUTURE, expiry=datetime(2024, 3, 29))
    """
    # Validate format
    pattern = r"^urm://([^:]+):([^/]+)/([^:]+):([^:]+)(?::(.+))?$"
    match = re.match(pattern, urm_id)
    if not match:
        raise SymbolResolutionError(
            f"Invalid URM ID format: {urm_id}. Expected format: urm://{{exchange|*}}:{{base}}/{{quote}}:{{instrument_type}}[:qualifiers]",
            value=urm_id,
        )

    exchange, base, quote, instrument_type_str, qualifiers = match.groups()

    # Validate exchange (can be * for wildcard or exchange name)
    if exchange != "*" and not exchange.isalnum():
        raise SymbolResolutionError(
            f"Invalid exchange in URM ID: {exchange}. Must be '*' or alphanumeric exchange name",
            value=urm_id,
        )

    # Validate and parse instrument type
    try:
        instrument_type = InstrumentType(instrument_type_str.lower())
    except ValueError as e:
        raise SymbolResolutionError(
            f"Invalid instrument type '{instrument_type_str}' in URM ID. Valid types: {[it.value for it in InstrumentType]}",
            value=urm_id,
        ) from e

    # Parse qualifiers (expiry, strike, etc.)
    expiry: datetime | None = None
    strike: float | None = None
    metadata: dict[str, str] = {}

    if qualifiers:
        parts = qualifiers.split(":")
        for part in parts:
            # Try to parse as date (YYYYMMDD)
            if len(part) == 8 and part.isdigit():
                with suppress(ValueError):
                    expiry = datetime.strptime(part, "%Y%m%d")
            # Try to parse as option (C:35000 or P:35000)
            elif ":" in part and len(part) > 2 and part[0] in ("C", "P"):
                option_type, strike_str = part.split(":", 1)
                metadata["option_type"] = option_type
                with suppress(ValueError):
                    strike = float(strike_str)

    spec = InstrumentSpec(
        base=base.upper(),
        quote=quote.upper(),
        instrument_type=instrument_type,
        expiry=expiry,
        strike=strike,
        metadata=metadata,
    )

    # Store exchange in metadata if specified
    if exchange != "*":
        spec.metadata["exchange"] = exchange.lower()

    return spec


def spec_to_urm_id(
    spec: InstrumentSpec,
    *,
    exchange: str | None = None,
) -> str:
    """Convert InstrumentSpec to scoped URM ID.

    Args:
        spec: Canonical InstrumentSpec
        exchange: Exchange name or "*" for wildcard. If None, uses spec.metadata.get("exchange", "*")

    Returns:
        Scoped URM ID string (e.g., "urm://binance:btc/usdt:spot")

    Examples:
        >>> spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.SPOT)
        >>> spec_to_urm_id(spec, exchange="binance")
        "urm://binance:btc/usdt:spot"

        >>> spec = InstrumentSpec(base="BTC", quote="USDT", instrument_type=InstrumentType.PERPETUAL)
        >>> spec_to_urm_id(spec)
        "urm://*:btc/usdt:perpetual"
    """
    exchange_scope = exchange or spec.metadata.get("exchange", "*")
    base = spec.base.lower()
    quote = spec.quote.lower()

    parts = [f"urm://{exchange_scope}:{base}/{quote}:{spec.instrument_type.value}"]

    # Add qualifiers for futures/options
    if spec.expiry:
        parts.append(spec.expiry.strftime("%Y%m%d"))
    if spec.strike:
        option_type = spec.metadata.get("option_type", "C")
        parts.append(f"{option_type}:{int(spec.strike)}")

    return ":".join(parts)


def validate_urm_id(urm_id: str) -> bool:
    """Validate URM ID format.

    Args:
        urm_id: URM ID string to validate

    Returns:
        True if format is valid, False otherwise
    """
    try:
        parse_urm_id(urm_id)
        return True
    except SymbolResolutionError:
        return False
