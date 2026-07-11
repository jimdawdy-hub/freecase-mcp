"""Authenticated tools: search_cases and search_statutes."""
from __future__ import annotations

import pytest

from freecase_mcp import client
from freecase_mcp.errors import ConnectorKeyMissingError, FreecaseApiError
from freecase_mcp.tools.search_cases import search_cases
from freecase_mcp.tools.search_statutes import search_statutes


async def test_search_cases_passes_score_through_unchanged(mock_backend, monkeypatch):
    monkeypatch.setenv("FREECASE_MCP_KEY", "fc_mcp_live")
    mock_backend.json(
        {
            "query": "proximate cause",
            "total_candidates": 150,
            "returned": 1,
            "reranked": False,
            "ranked_count": 0,
            "results": [{"cluster_id": 1, "case_name": "A v. B", "score": 6.42}],
        }
    )

    result = await search_cases("proximate cause", jurisdiction="il")

    # KTD7: score is not renormalized.
    assert result["results"][0]["score"] == 6.42
    assert result["query"] == "proximate cause"


async def test_search_cases_forwards_citation_query_verbatim(mock_backend, monkeypatch):
    # KTD8: the connector does no query parsing; the citation string is sent as-is.
    monkeypatch.setenv("FREECASE_MCP_KEY", "fc_mcp_live")
    mock_backend.json({"query": "410 U.S. 113", "results": []})

    await search_cases("410 U.S. 113")

    params = dict(mock_backend.last_request.url.params)
    assert params["q"] == "410 U.S. 113"


async def test_search_cases_rerank_true_uses_long_timeout_and_flag(mock_backend, monkeypatch):
    monkeypatch.setenv("FREECASE_MCP_KEY", "fc_mcp_live")
    mock_backend.json({"query": "x", "reranked": True, "results": []})

    result = await search_cases("x", rerank=True)

    assert mock_backend.timeouts[-1] == client.RERANK_TIMEOUT_S
    params = dict(mock_backend.last_request.url.params)
    assert params["rerank"] == "true"
    assert result["reranked"] is True


async def test_search_cases_without_key_errors_before_request(mock_backend):
    with pytest.raises(ConnectorKeyMissingError) as exc:
        await search_cases("anything")
    assert "connector key" in str(exc.value).lower()
    assert mock_backend.requests == []  # nothing was sent


async def test_search_cases_revoked_key_surfaces_401(mock_backend, monkeypatch):
    monkeypatch.setenv("FREECASE_MCP_KEY", "fc_mcp_revoked")
    mock_backend.error(401, {"error": "unauthorized", "message": "Backend authentication required."})

    with pytest.raises(FreecaseApiError) as exc:
        await search_cases("x")
    assert exc.value.status_code == 401
    assert "revoked" in str(exc.value).lower() or "invalid" in str(exc.value).lower()


async def test_search_cases_too_broad_surfaces_suggestions(mock_backend, monkeypatch):
    monkeypatch.setenv("FREECASE_MCP_KEY", "fc_mcp_live")
    mock_backend.error(
        422,
        {
            "error": "query_too_broad",
            "message": "This search is too broad to run efficiently.",
            "suggestions": ["Add more specific search terms", "Choose a state or court"],
        },
    )

    with pytest.raises(FreecaseApiError) as exc:
        await search_cases("the")
    assert exc.value.code == "query_too_broad"
    assert "Choose a state or court" in str(exc.value)


async def test_search_cases_omits_unset_date_params(mock_backend, monkeypatch):
    monkeypatch.setenv("FREECASE_MCP_KEY", "fc_mcp_live")
    mock_backend.json({"query": "x", "results": []})

    await search_cases("x")

    params = dict(mock_backend.last_request.url.params)
    assert "date_from" not in params
    assert "date_to" not in params
    # Defaults still forwarded.
    assert params["jurisdiction"] == "all"
    assert params["limit"] == "25"


async def test_search_statutes_forwards_params_and_returns_results(mock_backend, monkeypatch):
    monkeypatch.setenv("FREECASE_MCP_KEY", "fc_mcp_live")
    mock_backend.json(
        {
            "query": "625 ILCS 5/11-501",
            "jurisdiction": "il",
            "returned": 1,
            "results": [{"section_id": 9, "canonical_citation": "625 ILCS 5/11-501", "match_type": "citation"}],
        }
    )

    result = await search_statutes("625 ILCS 5/11-501", jurisdiction="il")

    params = dict(mock_backend.last_request.url.params)
    assert params["q"] == "625 ILCS 5/11-501"
    assert params["jurisdiction"] == "il"
    assert result["results"][0]["match_type"] == "citation"
    assert mock_backend.last_request.headers["Authorization"] == "Bearer fc_mcp_live"


async def test_search_statutes_unlaunched_jurisdiction_message_passes_through(mock_backend, monkeypatch):
    # KTD2: the backend owns the allowlist; the connector surfaces its message unchanged.
    monkeypatch.setenv("FREECASE_MCP_KEY", "fc_mcp_live")
    mock_backend.error(
        422,
        {
            "error": "jurisdiction_not_launched",
            "message": "Statutes for 'ca' are not available yet. Launched: IL, US, MN...",
        },
    )

    with pytest.raises(FreecaseApiError) as exc:
        await search_statutes("negligence", jurisdiction="ca")
    assert "not available yet" in str(exc.value)
