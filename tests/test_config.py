"""config reads env at call time (KTD9) and defaults sensibly."""
from __future__ import annotations

from freecase_mcp import config


def test_api_base_defaults_when_unset():
    assert config.api_base() == "https://api.freecase.ai"


def test_api_base_returns_env_value_without_trailing_slash(monkeypatch):
    monkeypatch.setenv("FREECASE_API_BASE", "http://localhost:8000/")
    assert config.api_base() == "http://localhost:8000"


def test_api_base_blank_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("FREECASE_API_BASE", "   ")
    assert config.api_base() == "https://api.freecase.ai"


def test_mcp_key_none_when_unset():
    assert config.mcp_key() is None


def test_mcp_key_returns_raw_value(monkeypatch):
    monkeypatch.setenv("FREECASE_MCP_KEY", "fc_mcp_abc123")
    assert config.mcp_key() == "fc_mcp_abc123"


def test_mcp_key_blank_is_none(monkeypatch):
    monkeypatch.setenv("FREECASE_MCP_KEY", "  ")
    assert config.mcp_key() is None


def test_env_is_read_at_call_time_not_import(monkeypatch):
    # No key at first call...
    assert config.mcp_key() is None
    # ...set it, and the very next call sees it (no cached module constant).
    monkeypatch.setenv("FREECASE_MCP_KEY", "fc_mcp_late")
    assert config.mcp_key() == "fc_mcp_late"
