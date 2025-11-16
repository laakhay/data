"""Shared fixtures for integration tests."""

import os

import pytest

# Skip all integration tests unless RUN_LAAKHAY_NETWORK_TESTS=1
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LAAKHAY_NETWORK_TESTS") != "1",
    reason="Requires network access. Set RUN_LAAKHAY_NETWORK_TESTS=1 to run",
)
