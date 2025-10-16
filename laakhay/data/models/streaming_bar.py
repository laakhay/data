"""Streaming bar wrapper that includes symbol context."""

from dataclasses import dataclass

from .bar import Bar


@dataclass(frozen=True)
class StreamingBar:
    """Bar with symbol context for streaming scenarios."""

    symbol: str
    bar: Bar

    @property
    def timestamp(self):
        """Delegated to bar."""
        return self.bar.timestamp
    
    @property
    def open(self):
        """Delegated to bar."""
        return self.bar.open
    
    @property
    def high(self):
        """Delegated to bar."""
        return self.bar.high
    
    @property
    def low(self):
        """Delegated to bar."""
        return self.bar.low
    
    @property
    def close(self):
        """Delegated to bar."""
        return self.bar.close
    
    @property
    def volume(self):
        """Delegated to bar."""
        return self.bar.volume
    
    @property
    def is_closed(self):
        """Delegated to bar."""
        return self.bar.is_closed
    
    # Delegate all other properties and methods to bar
    def __getattr__(self, name):
        return getattr(self.bar, name)
