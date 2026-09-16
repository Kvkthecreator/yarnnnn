"""
YARNNN MCP Server — ADR-543 (file-native surface) + ADR-075 (infrastructure)

The file-native verbs expose the user's shared, attributed workspace to every
LLM they touch — each a binding of a kernel verb (ADR-512 D3). The roster is
`_INTEROP_VERBS` in `server.py`; it is NOT re-listed here, because a second copy
drifts the moment the first changes (this docstring named six verbs for weeks
after whoami and request_upload landed). Read the roster, or call tools/list.

Scope tiers (ADR-563) live in `services/mcp_scopes.py`: files:read ⊂ files:write
⊂ files:share, enforced per-verb at `auth.assert_scope`.

Each verb composes kernel primitives server-side into a one-round result (so
round-limited consumer hosts never have to chain). Caller of execute_primitive()
per ADR-164 (runtime-agnostic primitives). Composition: api/services/mcp_composition.py

Canonical product framing: docs/features/mcp/README.md

Deployment: Separate Render service using the same codebase.
  Start command: cd api && python -m mcp_server http

Module named mcp_server (not mcp) to avoid collision with the mcp pip package.
"""
