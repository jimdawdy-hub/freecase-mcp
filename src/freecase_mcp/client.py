"""Thin async HTTP client over the public Freecase backend.

This is the *only* module that talks to the network, and it never talks to
anything else — no database, no local files, no query parsing. It wraps the five
backend endpoints the connector exposes, injects the ``Authorization: Bearer``
connector key on all five, and turns every failure into a clean
:mod:`freecase_mcp.errors` exception (never a raw ``httpx`` error or stack
trace).

Timeouts mirror the Freecase frontend's own values (``frontend/src/lib/api.ts``):
15s for normal calls, 95s for a reranked search, since the backend's reranking
latency is what drives that longer budget.
"""
from __future__ import annotations

from typing import Any

import httpx

from . import config
from .errors import (
    ConnectorKeyMissingError,
    FreecaseConnectionError,
    FreecaseResponseError,
    FreecaseTimeoutError,
    error_from_response,
)

# Matches frontend/src/lib/api.ts: DEFAULT_TIMEOUT_MS = 15_000, and 95_000 for
# a reranked search.
DEFAULT_TIMEOUT_S = 15.0
RERANK_TIMEOUT_S = 95.0

_USER_AGENT = "freecase-mcp"


async def _request(
    path: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT_S,
) -> Any:
    """Make one GET request and return the decoded JSON body.

    Reads the base URL and connector key at call time. If no key is configured, raises
    :class:`ConnectorKeyMissingError` *before* any network I/O.
    """
    headers = {"Accept": "application/json", "User-Agent": _USER_AGENT}

    key = config.mcp_key()
    if key is None:
        raise ConnectorKeyMissingError()
    headers["Authorization"] = f"Bearer {key}"

    url = f"{config.api_base()}{path}"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params, headers=headers)
    except httpx.TimeoutException as exc:
        raise FreecaseTimeoutError(
            f"The Freecase API timed out after {timeout:g}s. It may be under load "
            "or a reranked search may need more time; try again."
        ) from exc
    except httpx.RequestError as exc:
        # DNS failure, refused connection, TLS error, etc. — reachability, not
        # an HTTP status.
        raise FreecaseConnectionError(
            "The Freecase API is unreachable. Check your network connection and "
            "that FREECASE_API_BASE is correct."
        ) from exc

    if not response.is_success:
        raise error_from_response(response)

    try:
        return response.json()
    except (ValueError, httpx.DecodingError) as exc:
        raise FreecaseResponseError(
            "The Freecase API returned an unexpected (non-JSON) response."
        ) from exc


# --- Endpoint wrappers -----------------------------------------------------
# Each returns the backend's JSON body unchanged; tools do any reshaping.


async def search(params: dict[str, Any], *, rerank: bool) -> dict[str, Any]:
    """GET /search — authenticated. Uses the longer timeout when reranking."""
    return await _request(
        "/search",
        params=params,
        timeout=RERANK_TIMEOUT_S if rerank else DEFAULT_TIMEOUT_S,
    )


async def opinion(cluster_id: int) -> dict[str, Any]:
    """GET /opinion/{cluster_id} — subscriber connector key required."""
    return await _request(f"/opinion/{cluster_id}")


async def statutes_search(params: dict[str, Any]) -> dict[str, Any]:
    """GET /statutes/search — authenticated."""
    return await _request("/statutes/search", params=params)


async def statute(section_id: int) -> dict[str, Any]:
    """GET /statute/{section_id} — subscriber connector key required."""
    return await _request(f"/statute/{section_id}")


async def citations(cluster_id: int) -> dict[str, Any]:
    """GET /citations/{cluster_id} — subscriber connector key required."""
    return await _request(f"/citations/{cluster_id}")
