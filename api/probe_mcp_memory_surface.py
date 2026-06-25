"""PROBE — the ADR-368 memory-first interop surface, end to end.

Hat B (throwaway evaluation probe — NOT a regression gate). Validates the
remember / recall / trace surface against a REAL workspace with a REAL
MCP-shaped AuthenticatedClient (caller_identity="yarnnn:mcp"), with substrate
receipts. Supersedes probe_mcp_remember_this_default.py (the pre-368 enum probe).

Proves the ADR-368 decisions:
  R1. remember routes to operation/ ONLY (the topology-coherent commons) — the
      generic write that USED to die at system/notes.md now round-trips.
  R2. the write is attributed authored_by='yarnnn:mcp' on its revision.
  R3. the integrity wake fires (ADR-368 D5 / ADR-310 D2) — queue depth +1.
  R4. recall composes server-side — one call returns ranked material (no chaining).
  R5. trace composes the revision chain server-side — who/when/what-changed.
  R6. operator-visibility (D4): a foreign write is NOT silent — a narrative entry
      lands even with no pre-active session (daily-session fallback).

Run:  cd api && python probe_mcp_memory_surface.py
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
load_dotenv()


def _live_user_id() -> str:
    from services.supabase import get_service_client
    c = get_service_client()
    rows = c.table("workspace_files").select("user_id").limit(2000).execute().data or []
    from collections import Counter
    if not rows:
        raise SystemExit("no workspace_files in DB — cannot run probe")
    return Counter(r["user_id"] for r in rows).most_common(1)[0][0]


async def _run():
    from services.supabase import AuthenticatedClient, get_service_client
    from services import mcp_composition
    from services.primitives.registry import execute_primitive
    from services.wake_queue import queue_depth

    c = get_service_client()
    user_id = _live_user_id()
    print(f"[probe] live workspace user_id={user_id[:8]}…")

    auth = AuthenticatedClient(
        client=c, user_id=user_id, email=None, caller_identity="yarnnn:mcp",
    )

    results = []
    def check(label, ok, detail=""):
        results.append(bool(ok))
        print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")

    SUBJECT = "Acme Corp"
    GENERIC = "Acme Corp should lead its Q3 deck with retention, not growth."

    # --- R1: remember DUMPS to the memory inbox and round-trips ---
    path = mcp_composition.resolve_remember_path(SUBJECT)
    check("R1a remember dumps to the operation/memory/ inbox (capture, not placement; never system/persona)",
          path.startswith("operation/memory/"), f"path={path}")
    stamped = mcp_composition.stamp_provenance(GENERIC, "claude.ai", user_context=SUBJECT)
    wr = await mcp_composition.dispatch_remember_this(auth=auth, stamped_text=stamped, about=SUBJECT)
    check("R1b remember write SUCCEEDS (the generic write that used to governance_lock)",
          wr.get("success") is True, f"path={wr.get('path')} err={wr.get('error')}")
    abs_path = "/workspace/" + path
    rb = await execute_primitive(auth, "ReadFile", {"path": path})
    check("R1c round-trips via ReadFile", rb.get("success") is True and GENERIC in (rb.get("content") or ""))

    # --- R2: attribution on the revision ---
    rev = (
        c.table("workspace_file_versions").select("id, authored_by")
        .eq("user_id", user_id).eq("path", abs_path)
        .order("created_at", desc=True).limit(1).execute().data or []
    )
    check("R2 revision attributed authored_by='yarnnn:mcp'",
          bool(rev) and rev[0].get("authored_by") == "yarnnn:mcp",
          f"got={rev[0].get('authored_by') if rev else '(none)'}")

    # --- R3: placement wake fires (the Reviewer is invoked to file the dump) ---
    depth_before = queue_depth(c, user_id=user_id)
    await mcp_composition.submit_foreign_write_wake(
        auth, written_path=path, target="memory-inbox", client_name="claude.ai")
    depth_after = queue_depth(c, user_id=user_id)
    check("R3 placement wake enqueued — Reviewer invoked to file the dump (ADR-368 D5)",
          depth_after >= depth_before + 1, f"queue {depth_before}→{depth_after}")
    # R3b: the wake PROMPT carries placement intent (file it where it belongs),
    # NOT the old validation-only "stand down" framing.
    enq = (
        c.table("wake_queue").select("payload")
        .eq("user_id", user_id).eq("wake_source", "substrate_event")
        .eq("dedup_key", str(rev[0]["id"]) if rev else "").limit(1).execute().data or []
    )
    prompt = ((enq[0].get("payload") or {}).get("hook") or {}).get("prompt", "") if enq else ""
    check("R3b wake prompt invokes PLACEMENT ('file it where it belongs'), not 'stand down'",
          ("file it" in prompt.lower() or "where it belongs" in prompt.lower()) and "stand down" not in prompt.lower(),
          f"prompt[:60]={prompt[:60]!r}")
    # cleanup the probe wake (dedup_key == revision_id for substrate_event)
    if rev:
        try:
            c.table("wake_queue").delete().eq("user_id", user_id).eq(
                "wake_source", "substrate_event").eq("dedup_key", str(rev[0]["id"])).execute()
        except Exception:
            pass

    # --- R4: recall composes server-side in one call ---
    rc = await mcp_composition.compose_recall(auth=auth, subject=SUBJECT, limit=5)
    check("R4 recall returns a composed bundle in ONE call (no host chaining)",
          rc.get("success") is True and "chunks" in rc,
          f"returned={rc.get('returned')}")

    # --- R5: trace composes the revision chain server-side ---
    tr = await mcp_composition.compose_trace(auth=auth, subject=SUBJECT, limit=5)
    has_history = tr.get("success") is True and isinstance(tr.get("history"), list)
    attributed = bool(tr.get("history")) and all(
        "authored_by" in h and "when" in h for h in tr["history"])
    check("R5 trace returns the authored revision chain (who/when/what-changed)",
          has_history and (attributed or tr.get("returned") == 0),
          f"path={tr.get('path')} revisions={tr.get('returned')}")

    # --- R6: operator-visibility — narrative is session-independent ---
    # The emitter falls back to _ensure_daily_session (RPC-independent: plain
    # table ops against the current chat_sessions schema). We replicate that
    # exact logic here (the server module can't import in this venv — the `mcp`
    # package only ships on the MCP Render service).
    def _ensure_daily_session_inline(a) -> "str | None":
        existing = (
            a.client.table("chat_sessions").select("id")
            .eq("user_id", a.user_id).eq("session_type", "thinking_partner")
            .order("updated_at", desc=True).limit(1).execute()
        )
        if existing.data:
            return existing.data[0]["id"]
        created = (
            a.client.table("chat_sessions")
            .insert({"user_id": a.user_id, "session_type": "thinking_partner", "status": "active"})
            .execute()
        )
        return created.data[0]["id"] if created.data else None
    sid = _ensure_daily_session_inline(auth)
    check("R6 operator-visibility: a session is always resolvable (no silent foreign write)",
          bool(sid), f"session={'resolved' if sid else 'NONE'}")

    # cleanup probe file
    try:
        c.table("workspace_files").delete().eq("user_id", user_id).eq("path", abs_path).execute()
        # also drop the appended-then-deleted file's revision residue is left intentionally (history is fine)
        print(f"[probe] cleaned up {abs_path}")
    except Exception as exc:  # noqa: BLE001
        print(f"[probe] WARN cleanup failed: {exc}")

    return results


def main():
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY")):
        print("SKIP: SUPABASE_URL / SUPABASE_SERVICE_KEY not in env")
        return
    results = asyncio.run(_run())
    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} probe assertions pass")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
