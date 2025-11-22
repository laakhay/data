"""REST request runner using endpoint specs and response adapters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..chunking import ChunkHint, ChunkPolicy, WeightPolicy
from .transport import RESTTransport


@dataclass(frozen=True)
class RestEndpointSpec:
    id: str
    method: str  # "GET" | "POST"
    build_path: Callable[[dict[str, Any]], str]
    build_query: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    build_body: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    build_headers: Callable[[dict[str, Any]], dict[str, str]] | None = None
    next_cursor: Callable[[Any], dict[str, Any] | None] | None = None
    # Chunk policy can be static or a factory function that creates policy from params
    chunk_policy: ChunkPolicy | Callable[[dict[str, Any]], ChunkPolicy] | None = None
    chunk_hint: ChunkHint | None = None
    weight_policy: WeightPolicy | Callable[[dict[str, Any]], WeightPolicy] | None = (
        None  # Optional weight policy
    )


class ResponseAdapter:
    def parse(self, response: Any, params: dict[str, Any]) -> Any:
        return response


class RestRunner:
    def __init__(self, transport: RESTTransport) -> None:
        self._t = transport

    async def run(
        self, *, spec: RestEndpointSpec, adapter: ResponseAdapter, params: dict[str, Any]
    ) -> Any:
        path = spec.build_path(params)
        query = spec.build_query(params) if spec.build_query else None
        body = spec.build_body(params) if spec.build_body else None
        headers = spec.build_headers(params) if spec.build_headers else None

        if spec.method.upper() == "GET":
            data = await self._t.get(path, params=query, headers=headers)
        else:
            data = await self._t.post(path, json_body=body, headers=headers)

        # Simple non-paginated; pagination handler can be added later if needed
        return adapter.parse(data, params)
