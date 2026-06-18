"""
ADR-335 Crawl-B — increment 1 receipt.

Binds the GitHub remote MCP server with a real OAuth token, lists its tool
surface, calls ONE tool, and distills the result into ONE attributed
observation (ADR-335 D3 shape). This is the receipt that discharges the
ADR-076 server-auth-shape ghost (finding §7 / amendment Open Question C):
does a real remote MCP server honor third-party OAuth-2.1 Bearer passthrough?

Run (3.11 venv with mcp installed):
    GH_MCP_TOKEN=$(gh auth token) api/.venv-mcp/bin/python api/scripts/mcp_crawlb_increment1.py

This is a developer-surface receipt (Hat B): it proves the in-kernel client
(api/integrations/core/mcp_client.py, Hat A) works end-to-end against a real
server. It writes NO substrate — it prints the distilled observation it WOULD
write, so the run is side-effect-free against any workspace.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from integrations.core.mcp_client import get_mcp_client  # noqa: E402

GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"


def distill_observation(result, watch_id: str, attestation: str) -> dict:
    """ADR-335 D3 observation contract — the attributed, distilled, dated,
    source-referenced shape. NOT the raw payload (ADR-153 distill-don't-mirror)."""
    # A real distiller would summarize; for the receipt we take the first text
    # block trimmed, which is enough to prove the contract round-trips.
    distilled = (result.text or "").strip()
    if len(distilled) > 600:
        distilled = distilled[:600] + " …[truncated]"
    return {
        "watch_id": watch_id,
        "source_ref": result.source_ref(),
        "attestation": attestation,  # GitHub = platform-published ⇒ gold (ADR-330 D2)
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "distilled_content": distilled,
    }


async def main() -> int:
    token = os.environ.get("GH_MCP_TOKEN")
    if not token:
        print("ERROR: set GH_MCP_TOKEN (e.g. GH_MCP_TOKEN=$(gh auth token))", file=sys.stderr)
        return 2

    client = get_mcp_client()

    print("=" * 70)
    print("ADR-335 Crawl-B increment 1 — GitHub-via-MCP, real OAuth token")
    print("=" * 70)

    # --- 0. RFC 9728 discovery (proves the OAuth-2.1 metadata path) ---
    print("\n[0] Resource-metadata discovery (RFC 9728)...")
    meta = await client.discover_resource_metadata(GITHUB_MCP_URL)
    if meta:
        print("    resource_name      :", meta.get("resource_name"))
        print("    authorization_servers:", meta.get("authorization_servers"))
        print("    scopes_supported   :", (meta.get("scopes_supported") or [])[:6], "…")
    else:
        print("    (no metadata — proceeding with held token)")

    # --- 1. Authenticated tool-surface listing (proves Bearer passthrough) ---
    print("\n[1] initialize + tools/list (authenticated)...")
    tools = await client.list_tools(GITHUB_MCP_URL, token)
    print(f"    server exposed {len(tools)} tools. First 8:")
    for t in tools[:8]:
        print(f"      - {t['name']}: {(t['description'] or '')[:60]}")

    # --- 2. One real tool call ---
    # Pick a safe, no-arg-ish read. Prefer a 'me'/'search' style tool that needs
    # no repo context; fall back to the first listed tool's minimal call.
    preferred = ["get_me", "search_issues", "list_notifications", "search_repositories"]
    tool_names = {t["name"] for t in tools}
    chosen = next((p for p in preferred if p in tool_names), None)
    args: dict = {}
    if chosen == "search_issues":
        args = {"query": "is:issue author:@me", "perPage": 3}
    elif chosen == "search_repositories":
        args = {"query": "user:Kvkthecreator", "perPage": 3}

    if not chosen:
        chosen = tools[0]["name"]
        print(f"\n[2] No preferred tool found; calling first tool '{chosen}' with empty args")
    else:
        print(f"\n[2] call_tool('{chosen}', {args}) ...")

    result = await client.call_tool(GITHUB_MCP_URL, token, chosen, args)
    print(f"    is_error: {result.is_error}")
    print(f"    text (first 300 chars): {result.text[:300]!r}")

    # --- 3. Distill into an attributed observation (ADR-335 D3) ---
    print("\n[3] Distilled observation (ADR-335 D3 — what WOULD be written to substrate):")
    obs = distill_observation(result, watch_id="receipt-github-mcp", attestation="platform")
    print(json.dumps(obs, indent=2)[:900])

    print("\n" + "=" * 70)
    ok = (not result.is_error) and len(tools) > 0
    print("RECEIPT:", "PASS — real server, real OAuth token, real read, contract round-trips"
          if ok else "FAIL — see output above")
    print("=" * 70)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
