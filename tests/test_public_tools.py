"""Public tools: get_opinion, get_statute, get_citations."""
from __future__ import annotations

import pytest

from freecase_mcp.errors import FreecaseApiError
from freecase_mcp.tools import get_opinion as get_opinion_mod
from freecase_mcp.tools.get_citations import get_citations
from freecase_mcp.tools.get_opinion import get_opinion
from freecase_mcp.tools.get_statute import get_statute


async def test_get_opinion_returns_documented_fields(mock_backend):
    body = {
        "cluster_id": 100,
        "case_name": "Doe v. Roe",
        "court_full": "Illinois Supreme Court",
        "date_filed": "2019-05-01",
        "plain_text": "Short opinion body.",
        "cited_by": [{"id": 200, "case_name": "Later v. Case"}],
        "parentheticals": [],
    }
    mock_backend.json(body)

    result = await get_opinion(100)

    assert result["cluster_id"] == 100
    assert result["case_name"] == "Doe v. Roe"
    assert result["plain_text"] == "Short opinion body."
    assert result["cited_by"][0]["id"] == 200


async def test_get_opinion_truncates_long_text_with_note_and_url(mock_backend, monkeypatch):
    monkeypatch.setattr(get_opinion_mod, "MAX_OPINION_TEXT_CHARS", 50)
    long_text = "A" * 500
    mock_backend.json({"cluster_id": 12345, "plain_text": long_text})

    result = await get_opinion(12345)

    text = result["plain_text"]
    assert text.startswith("A" * 50)
    assert len(text) < 500  # original body was cut
    assert "truncated" in text
    assert "https://freecase.ai/case/12345" in text


async def test_get_opinion_not_found_surfaces_clear_message(mock_backend):
    mock_backend.error(404, {"detail": "Opinion not found"})

    with pytest.raises(FreecaseApiError) as exc:
        await get_opinion(999999)
    assert "not found" in str(exc.value).lower()


async def test_get_citations_empty_list_is_not_an_error(mock_backend):
    mock_backend.json({"cluster_id": 5, "canonical_cluster_id": 5, "citations": []})

    result = await get_citations(5)

    assert result["citations"] == []
    assert result["canonical_cluster_id"] == 5


async def test_get_statute_repealed_returns_body_and_status(mock_backend):
    body = {
        "section_id": 77,
        "canonical_citation": "5 ILCS 100/1-1",
        "status": "repealed",
        "status_label": "Repealed by P.A. 1234",
        "body_text": "The historical text of the repealed section.",
        "text_unavailable": False,
        "successor": {"section_id": 78, "canonical_citation": "5 ILCS 100/1-2"},
    }
    mock_backend.json(body)

    result = await get_statute(77)

    assert result["status"] == "repealed"
    assert result["status_label"] == "Repealed by P.A. 1234"
    assert result["body_text"] == "The historical text of the repealed section."
    assert result["text_unavailable"] is False
    assert result["successor"]["section_id"] == 78
