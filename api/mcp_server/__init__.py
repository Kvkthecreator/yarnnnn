"""
YARNNN MCP Server — ADR-368 (memory-first surface) + ADR-075 (infrastructure)

Three memory verbs expose YARNNN as a portable memory across every LLM:

    remember  — save something into memory (writes the operation/ commons)
    recall    — pull what the user knows about a subject (composed retrieval)
    trace     — show how a recorded fact changed over time (the revision chain)

Each verb composes kernel primitives server-side into a one-round result (so
round-limited consumer hosts never have to chain). Caller of execute_primitive()
per ADR-164 (runtime-agnostic primitives). Composition: api/services/mcp_composition.py

Canonical product framing: docs/features/mcp/README.md

Deployment: Separate Render service using the same codebase.
  Start command: cd api && python -m mcp_server http

Module named mcp_server (not mcp) to avoid collision with the mcp pip package.
"""
