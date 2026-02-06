"""
Integration Readers - DEPRECATED.

This module previously contained direct API clients (SlackReader, NotionReader).
Per ADR-026, YARNNN uses MCP as the primary integration stack.

All read operations should go through MCPClientManager.
See: api/integrations/core/client.py

The readers were removed because:
1. MCP servers already handle API calls, pagination, rate limiting
2. Direct APIs duplicate work that MCP servers do
3. ADR-026 explicitly rejected "Native API Integrations (No MCP)"
"""

# No exports - use MCPClientManager instead
__all__ = []
