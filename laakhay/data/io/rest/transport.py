"""Generic REST transport built on the project's HTTPClient.

Provides simple GET/POST with optional response hooks (e.g., rate-limit hints).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .http import HTTPClient


class RESTTransport:
    def __init__(self, base_url: str) -> None:
        self._http = HTTPClient(base_url=base_url)

    def add_response_hook(self, hook: Callable[[Any], float | None]) -> None:
        self._http.add_response_hook(hook)

    async def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return await self._http.get(path, params=params)

    async def post(self, path: str, *, json_body: dict[str, Any] | None = None) -> Any:
        return await self._http.post(path, json=json_body)

    async def close(self) -> None:
        await self._http.close()
