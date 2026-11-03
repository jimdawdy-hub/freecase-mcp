"""HTTP client: success parsing, auth injection, and failure normalization."""
from __future__ import annotations

import httpx
import pytest

from freecase_mcp import client
from freecase_mcp.errors import (
    ConnectorKeyMissingError,
    FreecaseApiError,
    FreecaseConnectionError,
    FreecaseResponseError,
    FreecaseTimeoutError,
)


@pytest.fixture(autouse=True)
def connector_key(monkeypatch, _clean_env):
    monkeypatch.setenv("FREECASE_MCP_KEY", "fc_mcp_test_only")


async def test_retrieval_parses_200_and_sends_auth(mock_backend, monkeypatch):
    monkeypatch.setenv("FREECASE_MCP_KEY", "fc_mcp_live")
    mock_backend.json({"cluster_id": 42, "citations": []})

    result = await client.citations(42)

    assert result == {"cluster_id": 42, "citations": []}
    assert mock_backend.last_request.headers["Authorization"] == "Bearer fc_mcp_live"
    assert mock_backend.last_request.url.path == "/citations/42"


async def test_search_attaches_bearer_key(mock_backend, monkeypatch):
    monkeypatch.setenv("FREECASE_MCP_KEY", "fc_mcp_secret")
    mock_backend.json({"query": "x", "results": []})

    await client.search({"q": "x"}, rerank=False)

    assert mock_backend.last_request.headers["Authorization"] == "Bearer fc_mcp_secret"


async def test_search_without_key_raises_before_any_request(mock_backend, monkeypatch):
    monkeypatch.delenv("FREECASE_MCP_KEY")
    # No key set (autouse clean env). Must fail BEFORE any HTTP call.
    with pytest.raises(ConnectorKeyMissingError):
        await client.search({"q": "x"}, rerank=False)
    assert mock_backend.requests == []


async def test_rerank_uses_longer_timeout(mock_backend, monkeypatch):
    monkeypatch.setenv("FREECASE_MCP_KEY", "fc_mcp_secret")
    mock_backend.json({"query": "x", "results": []})

    await client.search({"q": "x"}, rerank=True)
    assert mock_backend.timeouts[-1] == client.RERANK_TIMEOUT_S

    await client.search({"q": "x"}, rerank=False)
    assert mock_backend.timeouts[-1] == client.DEFAULT_TIMEOUT_S


async def test_structured_backend_error_message_survives(mock_backend):
    mock_backend.error(422, {"error": "query_too_broad", "message": "Too broad."})

    with pytest.raises(FreecaseApiError) as exc:
        await client.opinion(1)

    assert exc.value.status_code == 422
    assert exc.value.code == "query_too_broad"
    assert "Too broad." in str(exc.value)


async def test_timeout_raises_clear_timeout_error(mock_backend):
    mock_backend.raises(httpx.ReadTimeout("slow"))

    with pytest.raises(FreecaseTimeoutError) as exc:
        await client.opinion(1)
    assert "timed out" in str(exc.value).lower()


async def test_connection_failure_is_distinct_from_timeout(mock_backend):
    mock_backend.raises(httpx.ConnectError("no route"))

    with pytest.raises(FreecaseConnectionError) as exc:
        await client.opinion(1)
    assert "unreachable" in str(exc.value).lower()


async def test_non_json_body_does_not_crash(mock_backend):
    mock_backend.text("<html>gateway error</html>", status_code=200)

    with pytest.raises(FreecaseResponseError) as exc:
        await client.opinion(1)
    assert "unexpected" in str(exc.value).lower()


async def test_api_base_override_is_used(mock_backend, monkeypatch):
    monkeypatch.setenv("FREECASE_API_BASE", "http://localhost:8000")
    mock_backend.json({"cluster_id": 7, "citations": []})

    await client.citations(7)
    assert str(mock_backend.last_request.url).startswith("http://localhost:8000/")


@pytest.mark.parametrize("call", [client.opinion, client.statute, client.citations])
async def test_each_retrieval_sends_key(mock_backend, call):
    mock_backend.json({})
    await call(42)
    assert mock_backend.last_request.headers["Authorization"] == "Bearer fc_mcp_test_only"


@pytest.mark.parametrize("call", [client.opinion, client.statute, client.citations])
async def test_each_retrieval_refuses_missing_key_before_network(mock_backend, monkeypatch, call):
    monkeypatch.delenv("FREECASE_MCP_KEY")
    with pytest.raises(ConnectorKeyMissingError):
        await call(42)
    assert not mock_backend.requests
