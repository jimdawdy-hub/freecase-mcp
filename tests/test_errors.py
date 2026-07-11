"""error_from_response: status-code mapping + both backend body shapes."""
from __future__ import annotations

import httpx

from freecase_mcp.errors import error_from_response


def _resp(status, body=None, headers=None, text=None):
    if text is not None:
        return httpx.Response(status, text=text, headers=headers or {})
    return httpx.Response(status, json=body, headers=headers or {})


def test_401_gives_key_guidance():
    err = error_from_response(_resp(401, {"error": "unauthorized", "message": "Backend authentication required."}))
    assert err.status_code == 401
    msg = str(err).lower()
    assert "connector key" in msg
    assert "revoked" in msg or "invalid" in msg


def test_429_includes_retry_after_seconds():
    err = error_from_response(
        _resp(429, {"error": "rate_limited", "message": "slow down"}, headers={"Retry-After": "30"})
    )
    assert err.status_code == 429
    assert err.retry_after == 30
    assert "30 seconds" in str(err)


def test_429_without_retry_after_still_clear():
    err = error_from_response(_resp(429, {"error": "rate_limited", "message": "slow down"}))
    assert err.retry_after is None
    assert "rate-limited" in str(err).lower()


def test_404_uses_fastapi_detail_shape():
    # Public endpoints return {"detail": ...}, not {"error", "message"}.
    err = error_from_response(_resp(404, {"detail": "Opinion not found"}))
    assert err.status_code == 404
    assert "not found" in str(err).lower()
    assert "Opinion not found" in str(err)


def test_422_too_broad_carries_message_and_suggestions():
    body = {
        "error": "query_too_broad",
        "message": "This search is too broad to run efficiently.",
        "suggestions": ["Add more specific search terms", "Choose a state or court"],
    }
    err = error_from_response(_resp(422, body))
    assert err.code == "query_too_broad"
    assert err.suggestions == body["suggestions"]
    s = str(err)
    assert "too broad" in s.lower()
    assert "Choose a state or court" in s


def test_503_service_unavailable():
    err = error_from_response(
        _resp(503, {"error": "service_unavailable", "message": "Search is temporarily unavailable. Try again shortly."})
    )
    assert err.status_code == 503
    assert "unavailable" in str(err).lower()


def test_500_generic_server_error_without_body():
    err = error_from_response(_resp(500, text="Internal Server Error"))
    assert err.status_code == 500
    assert "server error" in str(err).lower()


def test_non_json_body_is_tolerated():
    err = error_from_response(_resp(502, text="<html>bad gateway</html>"))
    assert err.status_code == 502
    # Doesn't raise while building; produces some message.
    assert str(err)
