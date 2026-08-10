"""
YARNNN MCP Server — ADR-543 (file-native surface) + ADR-075 (infrastructure)

Six file-native verbs expose the user's shared, attributed workspace to every
LLM they touch — each a binding of a kernel verb (ADR-512 D3):

    open      — read an EXACT file by reference (content + attribution)
    list      — enumerate the files under a folder (paths + attribution)
    search    — find files by meaning (ranked paths + excerpts + confidence)
    save      — attributed write to a named file (CAS via base_revision)
    history   — the attributed revision chain of one exact file
    share     — mint a member/viewer link (the grant act)

Each verb composes kernel primitives server-side into a one-round result (so
round-limited consumer hosts never have to chain). Caller of execute_primitive()
per ADR-164 (runtime-agnostic primitives). Composition: api/services/mcp_composition.py

Canonical product framing: docs/features/mcp/README.md

Deployment: Separate Render service using the same codebase.
  Start command: cd api && python -m mcp_server http

Module named mcp_server (not mcp) to avoid collision with the mcp pip package.
"""
