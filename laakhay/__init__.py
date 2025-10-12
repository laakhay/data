"""Laakhay Data top-level package."""

from .data import (  # noqa: F401
	# Core
	BaseProvider,
	DataError,
	InvalidIntervalError,
	InvalidSymbolError,
	MarketType,
	ProviderError,
	RateLimitError,
	TimeInterval,
	ValidationError,
	# Models
	Candle,
	Symbol,
	# Clients
	DataFeed,
	# Providers
	BinanceProvider,
	BinanceFuturesProvider,
	BinanceSpotProvider,
)

# Keep __version__ dynamic via package metadata (setuptools_scm)
try:  # Python 3.8+
	from importlib.metadata import version, PackageNotFoundError  # type: ignore
except Exception:  # pragma: no cover
	version = None  # type: ignore
	PackageNotFoundError = Exception  # type: ignore

def _pkg_version() -> str:
	try:
		if version:
			return version("laakhay-data")
	except PackageNotFoundError:
		pass
	# Fallback for editable installs without metadata
	return "0.0.0"

__version__ = _pkg_version()

__all__ = [
	"__version__",
	# Core
	"BaseProvider",
	"TimeInterval",
	"MarketType",
	"DataError",
	"ProviderError",
	"RateLimitError",
	"InvalidSymbolError",
	"InvalidIntervalError",
	"ValidationError",
	# Models
	"Candle",
	"Symbol",
	# Clients
	"DataFeed",
	# Providers
	"BinanceProvider",
	"BinanceFuturesProvider",
	"BinanceSpotProvider",
]
