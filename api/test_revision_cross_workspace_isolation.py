"""Regression gate — cross-workspace revision-read isolation (ADR-310 follow-on).

read_revision / ReadRevision / DiffRevisions are MCP-exposed (or about to be).
A caller-supplied revision_id must not read another workspace's revision content
by UUID. authored_substrate.read_revision filters the content fetch by user_id
(defense-in-depth beyond the PK lookup). This gate proves it against real data.

Skips cleanly without live DB env (it needs two real workspaces). Run:
  cd api && python test_revision_cross_workspace_isolation.py
"""

import os
from dotenv import load_dotenv
load_dotenv()


def main():
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY")):
        print("SKIP: SUPABASE_URL / SUPABASE_SERVICE_KEY not in env")
        return

    from services.supabase import get_service_client
    from services.authored_substrate import read_revision

    c = get_service_client()

    # Pick two distinct real workspaces that both have revisions.
    rows = (
        c.table("workspace_file_versions")
        .select("user_id")
        .limit(5000)
        .execute()
        .data
        or []
    )
    from collections import Counter
    owners = [u for u, _ in Counter(r["user_id"] for r in rows).most_common(5)]
    if len(owners) < 2:
        print("SKIP: need ≥2 workspaces with revisions")
        return
    A, B = owners[0], owners[1]

    revA_rows = (
        c.table("workspace_file_versions")
        .select("id, path")
        .eq("user_id", A)
        .limit(1)
        .execute()
        .data
    )
    revA, pathA = revA_rows[0]["id"], revA_rows[0]["path"]

    results = []
    def check(label, ok):
        results.append(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {label}")

    # A reads its own revision by id → found
    check("A reads own revision by id → found",
          read_revision(c, user_id=A, path=pathA, revision_id=revA) is not None)

    # B reads A's revision_id → MUST be blocked (the closed leak)
    check("B reads A's revision_id → blocked (None)",
          read_revision(c, user_id=B, path=pathA, revision_id=revA) is None)

    # B reads its own head by offset → no regression
    bRows = c.table("workspace_file_versions").select("path").eq("user_id", B).limit(1).execute().data
    if bRows:
        check("B reads own head by offset → found (no regression)",
              read_revision(c, user_id=B, path=bRows[0]["path"], offset=0) is not None)

    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} isolation assertions pass")
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
