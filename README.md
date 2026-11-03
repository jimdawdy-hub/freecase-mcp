# freecase-mcp

An [MCP](https://modelcontextprotocol.io) connector that lets AI agents —
Claude Desktop, Cursor, Hermes, and any other MCP host — search and read the
[Freecase](https://freecase.ai) legal corpus: U.S. case law (Illinois, federal,
the Supreme Court, the 7th Circuit) and a growing set of state and federal
statutes.

It is a thin client. It calls the public Freecase backend over HTTPS and never
touches a database — nothing to install a database driver for, no credentials on
your machine beyond your personal connector key.

---

## What you get

Five tools:

| Tool | Needs a key? | What it does |
|------|:---:|------|
| `search_cases` | Yes | Full-text case-law search (Illinois, federal, SCOTUS, 7th Circuit). Returns ranked results with citations, courts, dates, and snippets. |
| `search_statutes` | Yes | Statute search by citation (`625 ILCS 5/11-501`) or plain text, across the launched jurisdictions. |
| `get_opinion` | Yes | Full text of one opinion by `cluster_id`, plus its cited-by list and parentheticals. |
| `get_statute` | Yes | Full text of one statute section by `section_id`, including repealed/renumbered history. |
| `get_citations` | Yes | The parsed reporter citations for one case. |

All five tools require a **connector key** owned by an account with Solo or
equivalent Founder, Student, or approved complimentary beta benefits. Usage limits
apply. Public case and statute webpages and free website basic search remain available.

---

## Prerequisites

You need a way to run the connector on your machine. The config examples below
use [`uv`](https://docs.astral.sh/uv/) (specifically `uvx`), which downloads and
runs `freecase-mcp` in one step with no manual install.

Install `uv` once:

- **macOS / Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Windows (PowerShell):** `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

`uv` bundles its own Python, so you do not need a separate Python install.

> **Note:** `uvx freecase-mcp` works once the package is published to PyPI.
> Until then, run it from a local checkout — see
> [Running from a local checkout](#running-from-a-local-checkout).

---

## Get your connector key

1. Sign in at [freecase.ai](https://freecase.ai) with an eligible account and open your **account page**. See [plans](https://freecase.ai/pricing).
2. In the **Connector keys** section, click **Generate key**.
3. Copy the key — it is shown **once** and starts with `fc_mcp_`.

The account page can also generate a ready-to-paste config block for each
platform below, with your key already filled in. If you use that, you can skip
straight to the restart step.

> **Protect your key like a password.** Anyone who has it can run searches
> billed to your account. Don't commit it to git, don't paste it into a shared
> doc, and don't sync the config file to a public location. If a machine or
> config is ever compromised, revoke the key on your account page and generate a
> new one — revocation is immediate.

---

## Set it up in your agent

Each MCP host has its own config file. Add a `freecase` server entry, put your
key in the `env` block, then **restart the app** — MCP hosts only load new
servers on restart, and a skipped restart is the most common "it isn't working"
cause.

### Claude Desktop

Edit `claude_desktop_config.json`:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "freecase": {
      "command": "uvx",
      "args": ["freecase-mcp"],
      "env": {
        "FREECASE_MCP_KEY": "fc_mcp_your_key_here"
      }
    }
  }
}
```

Then quit and reopen Claude Desktop.

### Cursor

Edit `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "freecase": {
      "command": "uvx",
      "args": ["freecase-mcp"],
      "env": {
        "FREECASE_MCP_KEY": "fc_mcp_your_key_here"
      }
    }
  }
}
```

Then restart Cursor (or toggle the server off/on in Settings → MCP).

### Hermes

Add the server to your Hermes MCP config (`mcpServers` block):

```json
{
  "mcpServers": {
    "freecase": {
      "command": "uvx",
      "args": ["freecase-mcp"],
      "env": {
        "FREECASE_MCP_KEY": "fc_mcp_your_key_here"
      }
    }
  }
}
```

Then restart Hermes so it picks up the new server.

### Pointing at a non-production backend

To talk to a local or staging backend, add `FREECASE_API_BASE` to the `env`
block (it defaults to `https://api.freecase.ai`):

```json
"env": {
  "FREECASE_MCP_KEY": "fc_mcp_your_key_here",
  "FREECASE_API_BASE": "http://localhost:8000"
}
```

---

## Try it

Once configured and restarted, ask your agent something like:

- "Search Illinois case law for proximate cause in a slip-and-fall."
- "Look up 410 U.S. 113 and summarize the holding."
- "Find the Illinois DUI statute 625 ILCS 5/11-501 and show me the text."
- "What cases cite cluster 12345?"

The agent will call `search_cases` / `search_statutes` / `get_opinion` and read
the results back to you.

---

## Running from a local checkout

Until the package is on PyPI (or for development), point the host at a checkout
instead of `uvx`:

```json
{
  "mcpServers": {
    "freecase": {
      "command": "/absolute/path/to/freecase-mcp/.venv/bin/freecase-mcp",
      "env": {
        "FREECASE_MCP_KEY": "fc_mcp_your_key_here"
      }
    }
  }
}
```

Or with `uv` from the project directory:

```json
{
  "mcpServers": {
    "freecase": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/freecase-mcp", "freecase-mcp"],
      "env": { "FREECASE_MCP_KEY": "fc_mcp_your_key_here" }
    }
  }
}
```

You can also run `python -m freecase_mcp` from an environment where the package
is installed.

---

## Configuration reference

| Env var | Required | Default | Notes |
|---------|:---:|---------|-------|
| `FREECASE_MCP_KEY` | Yes | *(none)* | Your subscriber connector key (`fc_mcp_...`), used by all five tools. |
| `FREECASE_API_BASE` | No | `https://api.freecase.ai` | Override only for local/staging backends. |

Both are read at call time, so a host that injects env vars late still works.

---

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest -q            # unit tests: fully mocked, no network, no database
```

`scripts/smoke.py` runs a handful of real queries end to end against a live
backend. It is **not** part of the automated test suite — it needs a real
`FREECASE_MCP_KEY` and a reachable backend. Run `python scripts/smoke.py
--help` for details.

---

## Not yet available

These are planned but **not implemented** in this version. Silence here means
"not built yet," not "not planned":

- **`check_treatment`** — citator treatment (overruled / questioned / etc.) for a case.
- **`find_cases_citing_statute`** — cases that cite a given statute section.
- **`search_by_citation`** — dedicated citation-lookup tool (for now, just pass a
  citation string to `search_cases` — Freecase detects citations server-side).
- **`get_court_hierarchy`** — court structure / binding-authority relationships.
- **`get_parentheticals`** — a standalone parentheticals tool (parentheticals are
  currently returned as part of `get_opinion`, not on their own).
- **SSE / remote hosted deployment** — this version is **stdio-local only**: it
  runs on your machine and speaks to the backend over HTTPS. A hosted remote MCP
  endpoint (one URL, no local install) is a possible future step, not a current
  feature.

---

## How it fits together

```
Your agent  ──stdio──▶  freecase-mcp (this package)  ──HTTPS──▶  api.freecase.ai
```

The connector holds no legal data and no database credentials. All search,
ranking, and query handling happen on the Freecase backend; this package just
forwards requests (adding your connector key on all five tools) and
returns the results.

## Release notes

### 0.2.0

All five tools send the connector key. Update existing installations before the
backend enables subscriber-only API retrieval; older versions omit the key on
record reads. A 403 explains missing subscriber benefits, while a 401 identifies
an invalid or revoked key. Complimentary beta access must be approved by Freecase.
