"""Backward-compatible shim for StreamRelay exports."""

from ..runtime.relay import RelayMetrics, StreamRelay

__all__ = ["StreamRelay", "RelayMetrics"]
