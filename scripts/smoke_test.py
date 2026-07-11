#!/usr/bin/env python3
"""Manual end-to-end smoke test against a REAL, running Freecase backend.

This is NOT part of the automated test suite (``pytest`` never imports it). It
makes real network calls and therefore requires:

  * FREECASE_MCP_KEY  — a live connector key (starts with 'fc_mcp_')
  * FREECASE_API_BASE — optional; defaults to https://api.freecase.ai
                        (set to http://localhost:8000 to hit a local backend)

It runs the five representative queries from the plan's manual-verification list
end to end through the connector's own tools, and prints pass/fail per query.

Usage:
    FREECASE_MCP_KEY=fc_mcp_... python scripts/smoke_test.py
    FREECASE_MCP_KEY=fc_mcp_... FREECASE_API_BASE=http://localhost:8000 \
        python scripts/smoke_test.py

Exit code is 0 only if every query passed.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv

from freecase_mcp import config
from freecase_mcp.tools.get_citations import get_citations
from freecase_mcp.tools.get_opinion import get_opinion
from freecase_mcp.tools.search_cases import search_cases
from freecase_mcp.tools.search_statutes import search_statutes


async def _run() -> int:
    passed = 0
    failed = 0

    def report(name: str, ok: bool, detail: str) -> None:
        nonlocal passed, failed
        mark = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"[{mark}] {name}: {detail}")

    print(f"Backend: {config.api_base()}")
    print(f"Key configured: {'yes' if config.mcp_key() else 'NO — search will fail'}\n")

    # 1. Illinois proximate-cause case search (authenticated).
    first_cluster_id: int | None = None
    try:
        res = await search_cases("proximate cause negligence", jurisdiction="il", limit=5)
        n = len(res.get("results", []))
        if n:
            first_cluster_id = res["results"][0].get("cluster_id")
        report("search_cases (IL proximate cause)", n > 0, f"{n} results")
    except Exception as exc:  # noqa: BLE001 - smoke script reports, never crashes mid-run
        report("search_cases (IL proximate cause)", False, repr(exc))

    # 2. Reporter-citation lookup, forwarded as-is (KTD8).
    try:
        res = await search_cases("410 U.S. 113", jurisdiction="scotus", limit=5)
        n = len(res.get("results", []))
        report("search_cases (citation 410 U.S. 113)", n > 0, f"{n} results")
    except Exception as exc:  # noqa: BLE001
        report("search_cases (citation 410 U.S. 113)", False, repr(exc))

    # 3. Illinois statute search (authenticated).
    try:
        res = await search_statutes("625 ILCS 5/11-501", jurisdiction="il", limit=5)
        n = len(res.get("results", []))
        report("search_statutes (625 ILCS 5/11-501)", n > 0, f"{n} results")
    except Exception as exc:  # noqa: BLE001
        report("search_statutes (625 ILCS 5/11-501)", False, repr(exc))

    # 4. Full text of a specific cluster (public) — reuse the first search hit.
    if first_cluster_id is not None:
        try:
            op = await get_opinion(first_cluster_id)
            has_text = bool(op.get("plain_text"))
            report(
                f"get_opinion (cluster {first_cluster_id})",
                has_text,
                f"{len(op.get('plain_text') or '')} chars",
            )
        except Exception as exc:  # noqa: BLE001
            report(f"get_opinion (cluster {first_cluster_id})", False, repr(exc))

        # 5. That case's citing cases / citations (public).
        try:
            cites = await get_citations(first_cluster_id)
            report(
                f"get_citations (cluster {first_cluster_id})",
                "citations" in cites,
                f"{len(cites.get('citations', []))} citations",
            )
        except Exception as exc:  # noqa: BLE001
            report(f"get_citations (cluster {first_cluster_id})", False, repr(exc))
    else:
        report("get_opinion / get_citations", False, "skipped: no cluster_id from search #1")

    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    load_dotenv()
    if not os.environ.get("FREECASE_MCP_KEY"):
        print(
            "ERROR: FREECASE_MCP_KEY is not set. This gated smoke test needs a real "
            "connector key and a reachable backend. See this script's docstring.",
            file=sys.stderr,
        )
        sys.exit(2)
    sys.exit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
