"""Connector namespace for exchange-specific implementations.

This package contains exchange connectors that can be used directly by researchers
or wrapped by providers for DataRouter consumption.

Architecture:
    Connectors are organized by exchange: `connectors/<exchange>/rest|ws|urm`
    Each connector is self-contained with endpoint definitions and adapters.
"""

__all__: list[str] = []

