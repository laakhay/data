"""Unit tests for Kraken REST/WS providers.

Note: This test file is skipped until KrakenProvider is fully implemented
in the new connectors architecture. Currently only KrakenURM is available.
"""

import pytest

pytestmark = pytest.mark.skip(
    reason="KrakenProvider not yet implemented in new connectors architecture"
)
