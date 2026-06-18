"""
MCP Client — ADR-335 D4 (Crawl-B): the one transport that earns kernel status.

YARNNN is already an MCP *server* (ADR-169 — context out). This is the symmetric
move: ONE in-kernel MCP *client* that makes every platform's MCP server a Mode-A
read transport. It is the generic, transport-blind driver behind the tail of the
perception field — the infinite set of watches YARNNN would never hand-author.

This is NOT a per-platform client (contrast slack_client / notion_client /
github_client, the hand-authored *head* drivers). It is keyed on
`(server_url, access_token)` — any MCP server is a binding, not a code change.
Adding a tail platform is authorizing a binding, never writing a driver.

Architecture (ADR-335):
  - §6 transport-blind: this client returns raw tool output to its caller; the
    caller distills into an attributed observation (D3). Nothing above the
    observation contract knows an MCP server was involved.
  - §7 (per the 2026-06-18 derived-tier amendment): trust is NOT a property of
    this transport. A binding carries an `attestation_grade`; the gate compares
    grade ≥ required_tier(read). This module is grade-agnostic — it fetches; it
    does not decide whether a fetch is permitted.
  - Stateless-over-substrate (Axiom 1): no persistent session, no subprocess
    (the ADR-076 retreat was from a Node *subprocess gateway* — this is an
    in-process streamable-HTTP client, the exact shape ADR-076 left the door
    open for). One call = open transport → initialize → act → close.

Auth: remote MCP servers standardized on OAuth 2.1 Bearer + RFC 9728
protected-resource discovery. The caller passes a decrypted access token
(same TokenManager path as the head drivers). GitHub's remote server accepts a
standard GitHub OAuth token over `Authorization: Bearer` — verified 2026-06-18.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger(__name__)

_MCP_TIMEOUT_SECONDS = 30.0


@dataclass
class MCPToolResult:
    """Raw result of one tool call. The caller distills this into an
    attributed observation (ADR-335 D3) — this module never writes substrate."""

    server_url: str
    tool_name: str
    # Structured content if the server returned it, else None.
    structured: Optional[Any] = None
    # Text blocks concatenated (the common case).
    text: str = ""
    is_error: bool = False
    raw_blocks: list[dict] = field(default_factory=list)

    def source_ref(self) -> str:
        """The transport + container this observation came from (ADR-335 D3
        `source_ref`). Carried on the observation; judgment never reads it."""
        return f"mcp:{self.server_url}#{self.tool_name}"


class MCPClient:
    """
    Generic in-kernel MCP client. One instance serves every binding.

    Usage:
        client = MCPClient()
        tools = await client.list_tools(server_url, access_token)
        result = await client.call_tool(server_url, access_token, "list_issues", {...})

    `access_token` is passed per call (never stored) — same posture as the head
    drivers (github_client passes `token=` per request).
    """

    @staticmethod
    def _auth_headers(access_token: str) -> dict[str, str]:
        # RFC 9728 / OAuth 2.1: bearer_methods_supported = ["header"] for the
        # GitHub MCP server (verified via .well-known/oauth-protected-resource).
        return {"Authorization": f"Bearer {access_token}"}

    async def discover_resource_metadata(self, server_url: str) -> Optional[dict]:
        """
        RFC 9728 protected-resource discovery. The metadata is path-suffixed
        (NOT at host root) — the unauthenticated server response advertises it
        via the `WWW-Authenticate: ... resource_metadata="..."` header. For
        `https://host/mcp/` the doc lives at
        `https://host/.well-known/oauth-protected-resource/mcp/`.

        Returns the parsed metadata (authorization_servers, scopes_supported,
        attestation-relevant `resource_name`, etc.) or None if unavailable.
        Discovery is advisory here — used to surface auth-server + scopes for the
        binding UX; the actual read uses the token the caller already holds.
        """
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as http:
                # Probe unauthenticated to read the WWW-Authenticate pointer.
                probe = await http.post(
                    server_url,
                    headers={"Accept": "application/json, text/event-stream"},
                    json={"jsonrpc": "2.0", "id": 0, "method": "ping"},
                )
                www_auth = probe.headers.get("www-authenticate", "")
                meta_url = _extract_resource_metadata_url(www_auth)
                if not meta_url:
                    return None
                meta_resp = await http.get(meta_url)
                if meta_resp.status_code != 200:
                    return None
                return meta_resp.json()
        except Exception as exc:  # discovery is best-effort
            logger.info("[MCP] resource-metadata discovery failed for %s: %s", server_url, exc)
            return None

    async def list_tools(self, server_url: str, access_token: str) -> list[dict[str, Any]]:
        """Open transport → initialize → list the server's tool surface → close.
        Returns [{name, description, input_schema}, ...]."""
        async with streamablehttp_client(
            server_url,
            headers=self._auth_headers(access_token),
            timeout=_MCP_TIMEOUT_SECONDS,
        ) as (read_stream, write_stream, _get_session_id):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                listed = await session.list_tools()
                return [
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "input_schema": t.inputSchema,
                    }
                    for t in listed.tools
                ]

    async def call_tool(
        self,
        server_url: str,
        access_token: str,
        tool_name: str,
        arguments: Optional[dict[str, Any]] = None,
    ) -> MCPToolResult:
        """
        Invoke one tool. This is the ONLY call site shape ADR-335 B3 permits:
        a bounded, deterministic, mechanical-mode read — never a foreign tool
        injected into the Reviewer's judgment tool loop.

        Returns raw output. The caller distills + attributes (D3); this module
        does not touch substrate, does not decide trust, does not meter cost
        (metering is the caller's mechanical-executor responsibility per the
        amendment's Open Question B).
        """
        async with streamablehttp_client(
            server_url,
            headers=self._auth_headers(access_token),
            timeout=_MCP_TIMEOUT_SECONDS,
        ) as (read_stream, write_stream, _get_session_id):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments or {})

        text_parts: list[str] = []
        raw_blocks: list[dict] = []
        for block in result.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                text_parts.append(block.text)
                raw_blocks.append({"type": "text", "text": block.text})
            else:
                raw_blocks.append({"type": btype or "unknown", "repr": str(block)[:500]})

        return MCPToolResult(
            server_url=server_url,
            tool_name=tool_name,
            structured=getattr(result, "structuredContent", None),
            text="\n".join(text_parts),
            is_error=bool(getattr(result, "isError", False)),
            raw_blocks=raw_blocks,
        )


def _extract_resource_metadata_url(www_authenticate: str) -> Optional[str]:
    """Parse `resource_metadata="<url>"` out of a WWW-Authenticate header (RFC 9728)."""
    if "resource_metadata" not in www_authenticate:
        return None
    marker = 'resource_metadata="'
    start = www_authenticate.find(marker)
    if start == -1:
        return None
    start += len(marker)
    end = www_authenticate.find('"', start)
    if end == -1:
        return None
    return www_authenticate[start:end]


# Module-level singleton (matches get_slack_client / get_github_client pattern).
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
