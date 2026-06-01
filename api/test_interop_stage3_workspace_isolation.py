"""Stage 3 — multi-workspace isolation proving ground (ADR-310 / Phase-3 readiness).

Hat B evaluation scaffold. Proves the cross-operator boundary at the FULL stack:
an MCP-shaped AuthenticatedClient scoped to workspace A (caller_identity=
"yarnnn:mcp", the shape api/mcp_server/auth.py::resolve_request_client produces)
cannot read or write workspace B's substrate through the real execute_primitive
path. This is the isolation property the cross-operator viral destination
(Phase 3) depends on — validated NOW against the single-tenant code, against two
real live workspaces.

The single-tenant code achieves isolation via service-key + explicit
.eq("user_id", ...). This gate proves that filter actually holds end-to-end for
every MCP-exposed read, and that a write lands only in the caller's own scope.

Skips cleanly without live-DB env. Run:
  cd api && python test_interop_stage3_workspace_isolation.py
"""

import asyncio
import os
from collections import Counter
from dotenv import load_dotenv
load_dotenv()


def _mcp_auth(user_id):
    from services.supabase import AuthenticatedClient, get_service_client
    return AuthenticatedClient(
        client=get_service_client(),
        user_id=user_id,
        email=None,
        caller_identity="yarnnn:mcp",
    )


async def _run():
    from services.supabase import get_service_client
    from services.primitives.registry import execute_primitive

    c = get_service_client()
    rows = c.table("workspace_files").select("user_id, path").limit(5000).execute().data or []
    owners = [u for u, _ in Counter(r["user_id"] for r in rows).most_common(5)]
    if len(owners) < 2:
        print("SKIP: need ≥2 workspaces with files")
        return []
    A, B = owners[0], owners[1]
    print(f"[stage3] A={A[:8]}…  B={B[:8]}…")

    # Find a path that exists in B but (ideally) is B-specific. Use any B file.
    b_files = c.table("workspace_files").select("path").eq("user_id", B).limit(50).execute().data or []
    a_paths = {r["path"] for r in c.table("workspace_files").select("path").eq("user_id", A).limit(500).execute().data or []}
    # a path in B that A does NOT have (true cross-workspace target)
    b_only = next((r["path"] for r in b_files if r["path"] not in a_paths), b_files[0]["path"] if b_files else None)
    if not b_only:
        print("SKIP: workspace B has no files")
        return []
    rel_b_only = b_only[len("/workspace/"):] if b_only.startswith("/workspace/") else b_only
    print(f"[stage3] B-only target path: {b_only}")

    authA = _mcp_auth(A)
    results = []
    def check(label, ok, detail=""):
        results.append(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")

    # 1. A ReadFile of a B-only path → must NOT return B's content
    rf = await execute_primitive(authA, "ReadFile", {"path": b_only})
    leaked = rf.get("success") is True and bool(rf.get("content"))
    check("A ReadFile B-only path → no B content", not leaked, f"success={rf.get('success')}")

    # 2. A ListFiles → every returned path belongs to A (none of B's exclusive files)
    lf = await execute_primitive(authA, "ListFiles", {"path": "/workspace/context"})
    listed = lf.get("files") or lf.get("entries") or []
    # extract path-ish strings
    listed_paths = []
    for it in listed:
        if isinstance(it, dict):
            listed_paths.append(it.get("path") or it.get("name") or "")
        else:
            listed_paths.append(str(it))
    # none of A's listing should equal the B-only absolute path
    check("A ListFiles → B-only path absent", all(rel_b_only not in p and b_only not in p for p in listed_paths),
          f"listed={len(listed_paths)}")

    # 3. A QueryKnowledge → results all belong to A (scoped). We assert the call
    #    is scoped by confirming returned paths exist under A (not exclusively B).
    qk = await execute_primitive(authA, "QueryKnowledge", {"query": "the", "limit": 20})
    qk_paths = [r.get("path", "") for r in (qk.get("results") or [])]
    # every returned path must be one of A's paths (scoped query guarantee)
    all_a = all(p in a_paths for p in qk_paths if p)
    check("A QueryKnowledge → all results are A's paths", all_a, f"returned={len(qk_paths)}")

    # 4. A WriteFile → lands in A's scope only. Write a probe, confirm B can't see it.
    probe = "context/_interop_probe/stage3.md"
    await execute_primitive(authA, "WriteFile", {
        "scope": "workspace", "path": probe,
        "content": "stage3 isolation probe", "mode": "overwrite",
        "message": "stage3 isolation probe",
    })
    abs_probe = "/workspace/" + probe
    a_has = c.table("workspace_files").select("path").eq("user_id", A).eq("path", abs_probe).execute().data
    b_has = c.table("workspace_files").select("path").eq("user_id", B).eq("path", abs_probe).execute().data
    check("A WriteFile lands in A scope", bool(a_has))
    check("A WriteFile NOT visible in B scope", not b_has)
    # cleanup
    c.table("workspace_files").delete().eq("user_id", A).eq("path", abs_probe).execute()
    print(f"[stage3] cleaned up {abs_probe}")

    return results


def main():
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY")):
        print("SKIP: SUPABASE_URL / SUPABASE_SERVICE_KEY not in env")
        return
    results = asyncio.run(_run())
    if not results:
        return
    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} isolation assertions pass")
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
