"""Tool implementations for the Freecase MCP connector.

Each module defines one async function that is registered as an MCP tool in
:mod:`freecase_mcp.server`. Tools are thin: they call
:mod:`freecase_mcp.client` and reshape nothing except where documented (only
``get_opinion`` post-processes, to cap opinion length).
"""
