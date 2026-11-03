"""freecase-mcp — an MCP connector for the Freecase legal corpus.

AI agents (Claude Desktop, Cursor, Hermes, ...) call the tools registered here
to search Freecase case law and statutes, and to read individual opinions,
statutes, and citation lists — all over HTTPS against the public Freecase
backend. This package never connects to a database (KTD1).
"""

__version__ = "0.2.0"
