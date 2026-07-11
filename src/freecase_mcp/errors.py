"""Agent-facing error types and normalization.

Every failure a tool can hit — a missing key, a timeout, an unreachable host, a
structured backend error — is turned into one of these exceptions carrying a
short, human-readable message. FastMCP surfaces that message to the calling
agent as a tool error, so the message must read as guidance to a lawyer's
assistant, never as a stack trace or a raw ``httpx`` string.

The backend uses two different error-body shapes:

* Auth / search / validation routes:  ``{"error": <code>, "message": <text>,
  "suggestions"?: [...]}``
* Public routes hitting FastAPI's default 404 handler: ``{"detail": <text>}``

:func:`error_from_response` handles both, plus a body that is neither.
"""
from __future__ import annotations

from typing import Any

import httpx


class FreecaseError(Exception):
    """Base class for every error surfaced to the calling agent."""


class ConnectorKeyMissingError(FreecaseError):
    """A search tool was called but ``FREECASE_MCP_KEY`` is not set.

    Raised *before* any network request — an unauthenticated search would only
    earn a 401 anyway, so we fail early with actionable guidance instead.
    """

    def __init__(self) -> None:
        super().__init__(
            "No Freecase connector key is configured, so search is unavailable. "
            "Set the FREECASE_MCP_KEY environment variable to a key generated on "
            "your Freecase account page (it starts with 'fc_mcp_'). The "
            "get_opinion, get_statute, and get_citations tools work without a key."
        )


class FreecaseTimeoutError(FreecaseError):
    """The backend did not respond within the allotted time."""


class FreecaseConnectionError(FreecaseError):
    """The backend host could not be reached at all (DNS/TCP/TLS failure)."""


class FreecaseResponseError(FreecaseError):
    """The backend returned a 2xx body that could not be parsed as JSON."""


class FreecaseApiError(FreecaseError):
    """The backend returned a non-2xx response.

    ``message`` is the normalized, agent-facing text. The structured fields
    (``status_code``, ``code``, ``retry_after``, ``suggestions``) are kept so
    callers or tests can branch on them, but the string form is what an agent
    reads.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        code: str | None = None,
        retry_after: int | None = None,
        suggestions: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.retry_after = retry_after
        self.suggestions = suggestions or []


def _extract_backend_fields(body: Any) -> tuple[str | None, str | None, list[str]]:
    """Pull ``(code, message, suggestions)`` out of whatever shape the body is.

    Tolerates both backend shapes and a non-dict body, never raising.
    """
    if not isinstance(body, dict):
        return None, None, []
    code = body.get("error")
    # `message` is the {error, message} shape; `detail` is FastAPI's default
    # HTTPException shape used by the public 404s.
    message = body.get("message") or body.get("detail")
    suggestions = body.get("suggestions")
    if not isinstance(suggestions, list):
        suggestions = []
    return (
        code if isinstance(code, str) else None,
        message if isinstance(message, str) else None,
        [s for s in suggestions if isinstance(s, str)],
    )


def _retry_after_seconds(response: httpx.Response) -> int | None:
    """Parse the ``Retry-After`` header (delta-seconds form) if present."""
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return int(raw.strip())
    except (ValueError, AttributeError):
        return None


def error_from_response(response: httpx.Response) -> FreecaseApiError:
    """Build a :class:`FreecaseApiError` with a clear message from a non-2xx response.

    Maps each status code the backend can return to guidance an agent can act
    on, while preserving the backend's own ``message``/``suggestions`` when they
    add value (validation and too-broad errors especially).
    """
    try:
        body = response.json()
    except (ValueError, httpx.DecodingError):
        body = None

    code, backend_message, suggestions = _extract_backend_fields(body)
    status = response.status_code
    retry_after = _retry_after_seconds(response)

    if status == 401:
        message = (
            "Freecase rejected the connector key (HTTP 401). The key is missing, "
            "invalid, or has been revoked. Generate a fresh key on your Freecase "
            "account page and update FREECASE_MCP_KEY."
        )
    elif status == 403:
        message = (
            "Freecase refused this request (HTTP 403). Your connector key may not "
            "have access to this resource."
        )
    elif status == 404:
        # Public endpoints: {"detail": "Opinion not found"} etc.
        message = backend_message or "The requested Freecase record was not found."
        message = f"Not found: {message}"
    elif status == 429:
        hint = (
            f" Wait {retry_after} seconds before retrying."
            if retry_after is not None
            else " Wait a short while before retrying."
        )
        message = (
            "Freecase rate-limited this connector key (HTTP 429)."
            + hint
            + " Each key has a per-minute and per-day search budget."
        )
    elif status == 422:
        # Validation / query-too-broad. The backend's own message is the useful
        # part; append its suggestions so the agent can narrow the query.
        base = backend_message or "The request was rejected as invalid (HTTP 422)."
        if suggestions:
            base = base + " Suggestions: " + "; ".join(suggestions) + "."
        message = base
    elif status == 503:
        message = (
            backend_message
            or "Freecase search is temporarily unavailable (HTTP 503)."
        ) + " Try again shortly."
    elif 500 <= status < 600:
        message = (
            f"Freecase had a server error (HTTP {status}). "
            "This is not something the query can fix; try again later."
        )
    else:
        message = backend_message or f"Freecase returned an unexpected HTTP {status}."

    return FreecaseApiError(
        message,
        status_code=status,
        code=code,
        retry_after=retry_after,
        suggestions=suggestions,
    )
