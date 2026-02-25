"""
YARNNN MCP Server — ADR-075

Exposes YARNNN backend services as MCP tools for Claude Desktop/Code and ChatGPT.
This is the inbound MCP server (external LLMs call YARNNN), complementing the
outbound MCP Gateway (YARNNN calls platform MCP servers via ADR-050).

Deployment: Separate Render service using the same codebase.
  Start command: cd api && python -m mcp_server

Module named mcp_server (not mcp) to avoid collision with the mcp pip package.
"""
