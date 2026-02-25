"""
YARNNN MCP Server — ADR-075

Exposes YARNNN backend services as MCP tools for Claude Desktop/Code and ChatGPT.
External LLMs call YARNNN to query context, deliverables, and platform data.

Deployment: Separate Render service using the same codebase.
  Start command: cd api && python -m mcp_server http

Module named mcp_server (not mcp) to avoid collision with the mcp pip package.
"""
