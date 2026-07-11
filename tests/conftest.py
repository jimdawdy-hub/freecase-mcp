"""Shared test fixtures.

Every test here runs with ZERO network and ZERO database access. HTTP is faked
with :class:`httpx.MockTransport`, injected by monkeypatching the
``httpx.AsyncClient`` the client module constructs. The suite is green with no
environment variables set at all (proving the connector has no accidental
network/DB dependency).
"""
from __future__ import annotations

import json
from typing import Any, Callable

import httpx
import pytest

from freecase_mcp import client as client_module


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Start every test from a blank config — no key, no base URL override.

    Tests that need a key set it explicitly via ``monkeypatch.setenv``.
    """
    monkeypatch.delenv("FREECASE_MCP_KEY", raising=False)
    monkeypatch.delenv("FREECASE_API_BASE", raising=False)


class MockBackend:
    """Records outgoing requests and returns canned responses.

    Set behavior with :meth:`respond` (a handler that maps a request to an
    ``httpx.Response``) or the :meth:`json`/:meth:`error`/:meth:`raises`
    shortcuts. Inspect :attr:`requests` and :attr:`timeouts` for assertions.
    """

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.timeouts: list[Any] = []
        self._handler: Callable[[httpx.Request], httpx.Response] | None = None

    # -- configuration -----------------------------------------------------
    def respond(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self._handler = handler

    def json(self, body: Any, status_code: int = 200) -> None:
        self.respond(lambda req: httpx.Response(status_code, json=body))

    def error(
        self,
        status_code: int,
        body: Any,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.respond(
            lambda req: httpx.Response(status_code, json=body, headers=headers or {})
        )

    def text(self, body: str, status_code: int = 200) -> None:
        self.respond(lambda req: httpx.Response(status_code, text=body))

    def raises(self, exc: BaseException) -> None:
        def _raise(req: httpx.Request) -> httpx.Response:
            raise exc

        self.respond(_raise)

    # -- transport hook ----------------------------------------------------
    def _dispatch(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self._handler is None:  # pragma: no cover - test wiring guard
            raise AssertionError("MockBackend used before a response was configured")
        return self._handler(request)

    @property
    def last_request(self) -> httpx.Request:
        assert self.requests, "no request was made"
        return self.requests[-1]

    def last_json_body(self) -> Any:
        return json.loads(self.last_request.content or b"null")


@pytest.fixture
def mock_backend(monkeypatch) -> MockBackend:
    """Patch the client's ``httpx.AsyncClient`` to use a MockTransport."""
    backend = MockBackend()
    real_async_client = httpx.AsyncClient

    def factory(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        backend.timeouts.append(kwargs.get("timeout"))
        kwargs.setdefault("transport", httpx.MockTransport(backend._dispatch))
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(client_module.httpx, "AsyncClient", factory)
    return backend
