"""search_cases — full-text case-law search (requires a connector key)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from .. import client


async def search_cases(
    q: Annotated[
        str,
        Field(
            description=(
                "The search query, forwarded to Freecase as-is. Freecase detects "
                "reporter citations (e.g. '410 U.S. 113'), case names, keywords, "
                "and Boolean/proximity operators server-side — do not pre-parse or "
                "rewrite the query."
            )
        ),
    ],
    jurisdiction: Annotated[
        str,
        Field(
            description=(
                "One of: 'all', 'il' (Illinois), 'federal', 'scotus' (U.S. "
                "Supreme Court), 'ca7' (7th Circuit)."
            )
        ),
    ] = "all",
    date_from: Annotated[
        str | None,
        Field(description="Earliest decision date, YYYY-MM-DD. Omit for no lower bound."),
    ] = None,
    date_to: Annotated[
        str | None,
        Field(description="Latest decision date, YYYY-MM-DD. Omit for no upper bound."),
    ] = None,
    precedential: Annotated[
        bool,
        Field(description="Exclude unpublished/errata opinions. Defaults to true."),
    ] = True,
    rerank: Annotated[
        bool,
        Field(
            description=(
                "Run the AI reranker over the results for better ordering. Slower "
                "(can take up to ~90s) and metered as AI-assisted use, so it is "
                "off by default — turn it on only when ranking quality matters."
            )
        ),
    ] = False,
    fast: Annotated[
        bool,
        Field(description="When reranking, use the faster/cheaper model. Ignored if rerank is false."),
    ] = False,
    limit: Annotated[
        int,
        Field(ge=1, le=200, description="Maximum results to return (1-200). Defaults to 25."),
    ] = 25,
) -> dict[str, Any]:
    """Search the Freecase case-law corpus (Illinois, federal, SCOTUS, 7th Circuit).

    Requires a Freecase connector key in the FREECASE_MCP_KEY environment
    variable; without one, this tool returns an error explaining how to set it.

    Returns the ``query`` echoed back, candidate/return counts, whether AI
    reranking ran, and a ``results`` array. Each result mirrors the Freecase API
    fields exactly (case_name, court_full, date_filed, snippet, treatment_status,
    cluster_id, etc.). The ``score`` field is Freecase's own opaque combined
    ranking score (a weighted mix of text relevance, court authority, recency,
    and citation count) — it is NOT a normalized 0-1 relevance value; use it only
    to compare results within one response. Pass a result's ``cluster_id`` to
    ``get_opinion`` to read the full text.

    Args:
        q: The search query (see field description — forwarded unchanged).
        jurisdiction: Court scope to search within.
        date_from: Earliest decision date (YYYY-MM-DD).
        date_to: Latest decision date (YYYY-MM-DD).
        precedential: Exclude unpublished/errata opinions (default true).
        rerank: Enable AI reranking (slower, AI-metered; default false).
        fast: Use the faster rerank model (only when rerank is true).
        limit: Maximum number of results (1-200; default 25).
    """
    params: dict[str, Any] = {
        "q": q,
        "jurisdiction": jurisdiction,
        "precedential": precedential,
        "rerank": rerank,
        "fast": fast,
        "limit": limit,
    }
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to

    return await client.search(params, rerank=rerank)
