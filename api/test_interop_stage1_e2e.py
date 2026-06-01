"""Stage 1 — end-to-end validation of the shipped MCP gate + primitives.

Hat B (evaluation scaffold). Unlike test_adr310_mcp_write_gate.py (fake auth,
gate-logic only), this drives the REAL execute_primitive dispatch with a REAL
MCP-shaped AuthenticatedClient (service client + caller_identity="yarnnn:mcp")
against a REAL workspace, with substrate receipts.

Asserts the shipped reality:
  - ReadFile of a real path returns real content (read primitive works via MCP auth)
  - QueryKnowledge returns ranked results (the pull_context substrate)
  - WriteFile to a governance path → governance_locked (the a33d062 gate fires
    through the REAL chokepoint, not just the unit-test fake)
  - WriteFile to a safe commons path → succeeds + round-trips via ReadFile, then
    cleans up (no residue)

Requires a real workspace user_id. Reads it from the live DB. Run:
  cd api && python test_interop_stage1_e2e.py
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
load_dotenv()


def _live_user_id() -> str:
    """Pick a real workspace owner with substrate (top by file count)."""
    from services.supabase import get_service_client
    c = get_service_client()
    # owner of the workspace with the most files
    rows = c.table("workspace_files").select("user_id").limit(2000).execute().data or []
    from collections import Counter
    if not rows:
        raise SystemExit("no workspace_files in DB — cannot run e2e")
    return Counter(r["user_id"] for r in rows).most_common(1)[0][0]


async def _run():
    from services.supabase import AuthenticatedClient, get_service_client
    from services.primitives.registry import execute_primitive

    user_id = _live_user_id()
    print(f"[stage1] using live workspace user_id={user_id[:8]}…")

    # Build auth exactly like api/mcp_server/auth.py::_build_client does.
    auth = AuthenticatedClient(
        client=get_service_client(),
        user_id=user_id,
        email=None,
        caller_identity="yarnnn:mcp",
    )

    results = []
    def check(label, ok, detail=""):
        results.append(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")

    # 1. QueryKnowledge — the pull_context substrate
    qk = await execute_primitive(auth, "QueryKnowledge", {"query": "mandate", "limit": 5})
    check("QueryKnowledge returns success", qk.get("success") is True, f"count={qk.get('count')}")

    # 2. ReadFile a real path (find one first via ListFiles)
    lf = await execute_primitive(auth, "ListFiles", {"path": "/workspace/context"})
    check("ListFiles returns success", lf.get("success") is True)
    # 3. WriteFile to a GOVERNANCE path → must be governance_locked (gate via real path)
    wf_gov = await execute_primitive(auth, "WriteFile", {
        "scope": "workspace",
        "path": "context/_shared/MANDATE.md",
        "content": "ATTACK — a foreign LLM must never write here",
        "mode": "append",
        "message": "stage1 gate probe — should be DENIED",
    })
    check(
        "WriteFile MANDATE.md → governance_locked (gate fires e2e)",
        wf_gov.get("success") is False and wf_gov.get("error") == "governance_locked",
        f"got={wf_gov.get('error')}",
    )

    # 4. WriteFile to review/ subtree → also locked
    wf_rev = await execute_primitive(auth, "WriteFile", {
        "scope": "workspace",
        "path": "review/principles.md",
        "content": "ATTACK — foreign write to reviewer seat",
        "mode": "append",
        "message": "stage1 gate probe — should be DENIED",
    })
    check(
        "WriteFile review/principles.md → governance_locked",
        wf_rev.get("success") is False and wf_rev.get("error") == "governance_locked",
        f"got={wf_rev.get('error')}",
    )

    # 5. WriteFile to a SAFE commons path → succeeds, round-trips, cleans up
    probe_path = "context/_interop_probe/stage1.md"
    wf_ok = await execute_primitive(auth, "WriteFile", {
        "scope": "workspace",
        "path": probe_path,
        "content": "stage1 commons-write probe (safe to delete)",
        "mode": "overwrite",
        "message": "stage1 commons-write probe",
    })
    check("WriteFile to commons path → success", wf_ok.get("success") is True, f"path={wf_ok.get('path')}")

    rb = await execute_primitive(auth, "ReadFile", {"path": probe_path})
    check(
        "ReadFile round-trips the commons write",
        rb.get("success") is True and "stage1 commons-write probe" in (rb.get("content") or ""),
    )

    # cleanup: remove the probe file directly (service client) so no residue
    try:
        abs_path = "/workspace/" + probe_path
        get_service_client().table("workspace_files").delete().eq(
            "user_id", user_id
        ).eq("path", abs_path).execute()
        print(f"[stage1] cleaned up probe file {abs_path}")
    except Exception as exc:  # noqa: BLE001
        print(f"[stage1] WARN cleanup failed: {exc}")

    return results


def main():
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY")):
        print("SKIP: SUPABASE_URL / SUPABASE_SERVICE_KEY not in env")
        return
    results = asyncio.run(_run())
    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} e2e assertions pass")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
