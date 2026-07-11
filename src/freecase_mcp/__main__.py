"""Allow ``python -m freecase_mcp`` to launch the stdio server.

Mirrors the ``freecase-mcp`` console script, for hosts (or debugging) that
prefer the module invocation form.
"""
from .server import main

if __name__ == "__main__":
    main()
