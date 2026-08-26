"""Regression gate for ADR-407 Phase 4 — chat sessions scope to (workspace, principal).

Migration 203: chat_sessions.workspace_id + owner backfill + insert trigger +
get_or_create_chat_session gains p_workspace_id DEFAULT NULL (owner fallback
inside — no deploy-order window). Code: session resolution/creation/listing
carries the acting workspace everywhere; find_active_workspace_session (the
autonomous-narrative target) resolves within the workspace. The ledger-derived
shared Flow is the named Phase-4b follow-on.

Run:
    cd api && python test_adr407_phase4_chat_scope.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_PASS: list[str] = []
_FAIL: list[tuple[str, str]] = []


def _ok(name):
    _PASS.append(name); print(f"  ✓ {name}")


def _bad(name, reason):
    _FAIL.append((name, reason)); print(f"  ✗ {name}\n      {reason}")


def test_migration_shape() -> None:
    path = REPO_ROOT / "supabase/migrations/203_adr407_phase4_chat_sessions_scope.sql"
    if not path.exists():
        _bad("migration 203 exists", str(path)); return
    sql = path.read_text()
    checks = [
        ("chat_sessions gains workspace_id", "ALTER TABLE chat_sessions" in sql and "ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id)" in sql),
        ("owner backfill", "w.owner_id = s.user_id" in sql),
        ("(workspace, user) index", "idx_chat_sessions_workspace_user" in sql),
        ("insert trigger safety net", "trg_fill_workspace_id BEFORE INSERT ON chat_sessions" in sql),
        ("RPC gains p_workspace_id DEFAULT NULL", "p_workspace_id uuid DEFAULT NULL" in sql),
        ("RPC owner fallback (no deploy window)", "SELECT id FROM workspaces WHERE owner_id = p_user_id" in sql),
        ("RPC resolution filters workspace", sql.count("(workspace_id = v_ws OR (v_ws IS NULL AND workspace_id IS NULL))") >= 2),
        ("RPC inserts stamp workspace", sql.count("INSERT INTO chat_sessions (user_id, workspace_id, session_type, status, agent_id)") == 2),
    ]
    for name, cond in checks:
        _ok(f"migration: {name}") if cond else _bad(f"migration: {name}", "pattern missing")


def test_callers_pass_workspace() -> None:
    feed = (ROOT / "routes/feed.py").read_text()
    if '"p_workspace_id": acting_ws' in feed:
        _ok("feed: session RPC passes the acting workspace")
    else:
        _bad("feed: session RPC passes the acting workspace", "param missing")
    if 'data["workspace_id"] = acting_ws' in feed:
        _ok("feed: fallback session insert stamps the acting workspace")
    else:
        _bad("feed: fallback session insert stamps the acting workspace", "stamp missing")

    # notifications.py no longer resolves a chat session — the ADR-593/605 work
    # removed that call site, so the old "passes p_workspace_id" row asserted a
    # caller that does not exist. It had been failing UNSEEN behind the
    # working_memory crash above. Re-anchored to the invariant that still has a
    # subject: no caller may reach the session RPC WITHOUT the acting workspace.
    notif = (ROOT / "services/notifications.py").read_text()
    if "get_or_create_chat_session" not in notif:
        _ok("notifications: no unscoped session-RPC call site")
    else:
        _bad(
            "notifications: no unscoped session-RPC call site",
            "it calls the session RPC again — it must pass p_workspace_id",
        )

    # Count INVOCATIONS, not mentions: the name also appears in prose above,
    # explaining why the RPC is broken. Counting the bare name would read a
    # docstring as a call site (it did — 3 vs 1 on the first cut).
    feed_rpc_calls = feed.count('"get_or_create_chat_session",')
    feed_rpc_scoped = feed.count('"p_workspace_id": acting_ws')
    if feed_rpc_calls and feed_rpc_calls == feed_rpc_scoped:
        _ok("feed: every session-RPC call carries the acting workspace")
    else:
        _bad(
            "feed: every session-RPC call carries the acting workspace",
            f"{feed_rpc_calls} invocation(s) vs {feed_rpc_scoped} scoped",
        )

    narr = (ROOT / "services/narrative.py").read_text()
    if 'query = query.eq("workspace_id", ws)' in narr:
        _ok("narrative: autonomous target resolves within the workspace")
    else:
        _bad("narrative: autonomous target resolves within the workspace", "filter missing")

    for rel, marker, name in [
        # routes/narrative.py DELETED (ADR-603 D5, 2026-08-24) — the
        # services/narrative.py check above still gates the live writer.
        ("routes/feed.py", 'q.eq("workspace_id", _hist_ws)', "feed history: scoped (workspace, principal)"),
        ("routes/feed.py", '_list_q.eq("workspace_id", _list_ws)', "feed session list: scoped (workspace, principal)"),
        # services/working_memory.py rows DELETED 2026-08-26 — the module went
        # with the retired agent model (commit 00e30fe, 1,690 lines / 0 callers).
        # They had been CRASHING this gate on a missing file, which hides every
        # assertion after them; a gate that cannot run is not a gate.
    ]:
        path = ROOT / rel
        if not path.exists():
            _bad(name, f"{rel}: file missing — re-anchor or delete this row")
            continue
        text = path.read_text()
        _ok(name) if marker in text else _bad(name, f"{rel}: marker missing")


def main() -> int:
    print("ADR-407 Phase 4 — chat scope regression")
    print("=" * 60)
    test_migration_shape()
    test_callers_pass_workspace()
    print("=" * 60)
    print(f"{len(_PASS)} passed, {len(_FAIL)} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
