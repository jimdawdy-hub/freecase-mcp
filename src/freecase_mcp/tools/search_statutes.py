"""search_statutes — statute-corpus search (requires a connector key)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from .. import client


async def search_statutes(
    q: Annotated[
        str,
        Field(
            description=(
                "The search query, forwarded to Freecase as-is: a statute "
                "citation (e.g. '625 ILCS 5/11-501') or natural-language text. "
                "Freecase handles citation vs. full-text detection server-side."
            )
        ),
    ],
    jurisdiction: Annotated[
        str,
        Field(
            description=(
                "Statute jurisdiction to search. 'all' or a state/federal code: "
                "il, us, mn, fl, nm, wi, ar, ga, ky, me, nc, nd, ri, tn, vt, wy "
                "(the launched set). If a jurisdiction is not yet launched, "
                "Freecase returns a message listing the ones that are."
            )
        ),
    ] = "all",
    limit: Annotated[
        int,
        Field(ge=1, le=100, description="Maximum results to return (1-100). Defaults to 25."),
    ] = 25,
) -> dict[str, Any]:
    """Search the Freecase statute corpus by citation or natural-language text.

    Requires a Freecase connector key in the FREECASE_MCP_KEY environment
    variable; without one, this tool returns an error explaining how to set it.

    Returns the ``query`` echoed back, counts, and a ``results`` array. Each
    result mirrors the Freecase API fields exactly (section_id,
    canonical_citation, jurisdiction, code_family, heading, status, snippet,
    match_type). Exact-citation hits are pinned above full-text hits, and current
    law floats above repealed/renumbered sections. Pass a result's ``section_id``
    to ``get_statute`` to read the full section text.

    Args:
        q: The search query (a citation or text — forwarded unchanged).
        jurisdiction: Statute jurisdiction to search within.
        limit: Maximum number of results (1-100; default 25).
    """
    params: dict[str, Any] = {"q": q, "jurisdiction": jurisdiction, "limit": limit}
    return await client.statutes_search(params)
