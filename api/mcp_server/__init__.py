"""
YARNNN MCP Server — ADR-169 (tool surface) + ADR-075 (infrastructure)

Three intent-shaped tools expose YARNNN as a cross-LLM context hub:

    work_on_this    — curated start-of-session bundle for a subject
    pull_context    — ranked chunks of accumulated material (primary cross-LLM tool)
    remember_this   — write observations back to the workspace

Fifth caller of execute_primitive() per ADR-164 (runtime-agnostic primitives).
Composition layer: api/services/mcp_composition.py

Canonical product framing: docs/features/mcp/README.md

Deployment: Separate Render service using the same codebase.
  Start command: cd api && python -m mcp_server http

Module named mcp_server (not mcp) to avoid collision with the mcp pip package.
"""
