"""Runtime configuration for freecase-mcp.

Every value is read from the environment *inside a function body*, never as a
module-level constant (KTD9). Two reasons:

* ``load_dotenv()`` may run after this module is imported; a module-level
  ``os.environ.get(...)`` would capture an empty value at import time and never
  see the real one (this repo's documented load-order lesson).
* An MCP host can hand us env vars at any point in the process lifetime; reading
  at call time means the very next tool call always sees the current value.
"""
from __future__ import annotations

import os

# The production backend. Overridable via FREECASE_API_BASE for local/staging.
DEFAULT_API_BASE = "https://api.freecase.ai"

# Every valid connector key carries this prefix. Used only for a friendly
# "that doesn't look like a connector key" hint — the backend is the real
# authority on whether a key is live.
KEY_PREFIX = "fc_mcp_"


def api_base() -> str:
    """Return the Freecase API base URL, without a trailing slash.

    Falls back to :data:`DEFAULT_API_BASE` when ``FREECASE_API_BASE`` is unset
    or blank.
    """
    raw = os.environ.get("FREECASE_API_BASE", "").strip()
    return (raw or DEFAULT_API_BASE).rstrip("/")


def mcp_key() -> str | None:
    """Return the connector key from ``FREECASE_MCP_KEY``, or ``None`` if unset.

    No validation happens here — public tools don't need a key, and the search
    tools raise a clear, actionable error at call time when it's missing (U12).
    A blank/whitespace-only value is treated the same as unset.
    """
    raw = os.environ.get("FREECASE_MCP_KEY", "").strip()
    return raw or None
