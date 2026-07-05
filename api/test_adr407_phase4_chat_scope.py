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

    notif = (ROOT / "services/notifications.py").read_text()
    if '"p_workspace_id": effective_workspace_id(user_id)' in notif:
        _ok("notifications: chat continuity passes the workspace")
    else:
        _bad("notifications: chat continuity passes the workspace", "param missing")

    narr = (ROOT / "services/narrative.py").read_text()
    if 'query = query.eq("workspace_id", ws)' in narr:
        _ok("narrative: autonomous target resolves within the workspace")
    else:
        _bad("narrative: autonomous target resolves within the workspace", "filter missing")

    for rel, marker, name in [
        ("routes/narrative.py", 'sessions_query.eq("workspace_id", _ws)', "narrative route: session ids scoped (workspace, principal)"),
        ("routes/feed.py", 'q.eq("workspace_id", _hist_ws)', "feed history: scoped (workspace, principal)"),
        ("routes/feed.py", '_list_q.eq("workspace_id", _list_ws)', "feed session list: scoped (workspace, principal)"),
        ("services/working_memory.py", 'session_query.eq("workspace_id", _sess_ws)', "working memory: active session scoped"),
        ("services/working_memory.py", 'summaries_query.eq("workspace_id", _sum_ws)', "working memory: summaries scoped"),
    ]:
        text = (ROOT / rel).read_text()
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
