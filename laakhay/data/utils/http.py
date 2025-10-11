"""HTTP client helper."""

from typing import Any, Dict, Optional

import aiohttp


class HTTPClient:
    """Async HTTP client wrapper."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0) -> None:
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get or create session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """GET request."""
        # If base_url is set and url is relative, combine them
        if self.base_url and not url.startswith("http"):
            url = f"{self.base_url}{url}"
        
        async with self.session.get(url, params=params, headers=headers) as response:
            response.raise_for_status()
            return await response.json()

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
