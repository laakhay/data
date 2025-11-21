"""HTTP client helper with optional response hooks and throttling.

This client provides:
- Automatic session management
- Optional global response hooks invoked for every response
- Respect for Retry-After on 429/418
- Optional pre-request throttling when set by response hooks
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp


class HTTPClient:
    """Async HTTP client wrapper."""

    def __init__(self, base_url: str | None = None, timeout: float = 30.0) -> None:
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None
        # Response hooks: called with aiohttp.ClientResponse and can optionally
        # return a float indicating additional delay (seconds) before next request.
        self._response_hooks: list[
            Callable[[aiohttp.ClientResponse], None | float | Awaitable[float | None]]
        ] = []
        # Throttle until timestamp (epoch seconds) if set by hooks
        self._throttle_until: float | None = None

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get or create session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session

    def add_response_hook(
        self,
        hook: Callable[[aiohttp.ClientResponse], None | float | Awaitable[float | None]],
    ) -> None:
        """Register a response hook.

        The hook will be called for every response. If it returns a float, that
        value is interpreted as a requested delay (in seconds) before the next
        request. The maximum requested delay across hooks will be honored.
        """
        self._response_hooks.append(hook)

    def set_throttle(self, delay_seconds: float) -> None:
        """Set a throttle window for subsequent requests."""
        delay_seconds = max(0.0, float(delay_seconds))
        if delay_seconds == 0:
            return
        end = time.time() + delay_seconds
        # Extend throttle if new end is later
        if self._throttle_until is None or end > self._throttle_until:
            self._throttle_until = end

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """GET request."""
        # If base_url is set and url is relative, combine them
        if self.base_url and not url.startswith("http"):
            url = f"{self.base_url}{url}"

        # Honor throttle if set
        if self._throttle_until is not None:
            remaining = self._throttle_until - time.time()
            if remaining > 0:
                await asyncio.sleep(remaining)
            self._throttle_until = None

        # Attempt request with automatic handling for 429/418 Retry-After
        while True:
            async with self.session.get(url, params=params, headers=headers) as response:
                # Call hooks early so they can inspect headers even on error statuses
                if self._response_hooks:
                    # Collect suggested delays from hooks
                    hook_delays: list[float] = []
                    for hook in self._response_hooks:
                        try:
                            result = hook(response)
                            if asyncio.iscoroutine(result):
                                result = await result  # type: ignore[assignment]
                            if isinstance(result, int | float) and result > 0:
                                hook_delays.append(float(result))
                        except Exception:
                            # Hooks must never break requests
                            pass
                    if hook_delays:
                        # Set the max requested delay
                        self.set_throttle(max(hook_delays))

                # Handle explicit rate-limit statuses
                if response.status in (429, 418):
                    retry_after = response.headers.get("Retry-After")
                    delay = None
                    if retry_after is not None:
                        try:
                            delay = float(retry_after)
                        except Exception:
                            # Some servers send Retry-After as HTTP-date; ignore for now
                            delay = None
                    if delay is None or delay <= 0:
                        # Fallback short backoff
                        delay = 1.0
                    await asyncio.sleep(delay)
                    # Continue loop to retry
                    continue

                response.raise_for_status()
                json_result: dict[str, Any] = await response.json()
                return json_result

    async def post(
        self,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """POST request with JSON body."""
        if self.base_url and not url.startswith("http"):
            url = f"{self.base_url}{url}"

        if self._throttle_until is not None:
            remaining = self._throttle_until - time.time()
            if remaining > 0:
                await asyncio.sleep(remaining)
            self._throttle_until = None

        while True:
            async with self.session.post(url, json=json, headers=headers) as response:
                if self._response_hooks:
                    hook_delays: list[float] = []
                    for hook in self._response_hooks:
                        try:
                            result = hook(response)
                            if asyncio.iscoroutine(result):
                                result = await result  # type: ignore[assignment]
                            if isinstance(result, int | float) and result > 0:
                                hook_delays.append(float(result))
                        except Exception:
                            pass
                    if hook_delays:
                        self.set_throttle(max(hook_delays))

                if response.status in (429, 418):
                    retry_after = response.headers.get("Retry-After")
                    delay = None
                    if retry_after is not None:
                        try:
                            delay = float(retry_after)
                        except Exception:
                            delay = None
                    if delay is None or delay <= 0:
                        delay = 1.0
                    await asyncio.sleep(delay)
                    continue

                response.raise_for_status()
                json_result: dict[str, Any] = await response.json()
                return json_result

    async def close(self) -> None:
        """Close session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self) -> "HTTPClient":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()
