"""get_citations — parsed reporter citations for one case (subscriber connector key required)."""
from __future__ import annotations

from typing import Any

from .. import client


async def get_citations(cluster_id: int) -> dict[str, Any]:
    """List the parsed reporter citations for a single case by its cluster id.

    Returns the requested ``cluster_id``, the ``canonical_cluster_id`` actually
    served (these differ when the requested id was a duplicate that resolved to
    a canonical case), and a ``citations`` array of reporter rows (volume,
    reporter, page, type). A case with no parsed citations returns an empty
    ``citations`` array — that is a normal result, not an error.

    Args:
        cluster_id: The case cluster id (an integer), e.g. from a search result.
    """
    return await client.citations(cluster_id)
