"""Regression gate for ADR-407 Phase 1 — the operational read layer re-keys
to the workspace.

Migration 201: workspace_id on tasks/agents/agent_runs/activity_log/wake_queue/
action_proposals/platform_connections/sync_registry + owner backfill + trigger
safety net + search RPCs re-keyed p_workspace_id. Code: request-layer reads go
through substrate_scope_filter; request-context writes stamp the ACTING
workspace; the MCP recall reads + MCP→wake seam reach the commons.

Run:
    cd api && python test_adr407_phase1_read_layer.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_PASS: list[str] = []
_FAIL: list[tuple[str, str]] = []


def _ok(name: str) -> None:
    _PASS.append(name)
    print(f"  ✓ {name}")


def _bad(name: str, reason: str) -> None:
    _FAIL.append((name, reason))
    print(f"  ✗ {name}\n      {reason}")


REKEYED_TABLES = [
    "tasks", "agents", "agent_runs", "activity_log", "wake_queue",
    "action_proposals", "platform_connections", "sync_registry",
]

# The request-layer files swept in Phase 1 — these must not scope the
# re-keyed tables by bare user_id anymore.
SWEPT_FILES = [
    "routes/recurrences.py",
    "routes/agents.py",
    "routes/proposals.py",
    "routes/documents.py",
    "routes/sources.py",
    "routes/authored.py",
    "services/agent_creation.py",
    "services/activity_log.py",
    "services/primitives/propose_action.py",
    "services/mcp_composition.py",
]


# ---------------------------------------------------------------------------
# 1. Migration 201 shape
# ---------------------------------------------------------------------------

def test_migration_shape() -> None:
    path = REPO_ROOT / "supabase/migrations/201_adr407_phase1_read_layer_rekey.sql"
    if not path.exists():
        _bad("migration 201 exists", str(path))
        return
    sql = path.read_text()

    for t in REKEYED_TABLES:
        if f"ALTER TABLE {t}" in sql and "ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id)" in sql:
            _ok(f"migration: {t} gains workspace_id")
        else:
            _bad(f"migration: {t} gains workspace_id", "ALTER missing")

    checks = [
        ("agent_runs backfilled via agents join", "FROM agents a WHERE a.id = r.agent_id" in sql),
        ("wake_queue dedup constraint KEEPS its name (code matches on it)",
         "ADD CONSTRAINT wake_queue_dedup_unique" in sql
         and "UNIQUE (workspace_id, wake_source, dedup_key)" in sql),
        ("tasks slug identity moves to workspace", "tasks_workspace_slug_unique UNIQUE (workspace_id, slug)" in sql),
        ("search_workspace re-keyed", "search_workspace(\n    p_workspace_id uuid" in sql
         and "wf.workspace_id = p_workspace_id" in sql),
        ("search_workspace_semantic re-keyed", "search_workspace_semantic(\n    p_workspace_id uuid" in sql),
        ("old search signatures dropped", "DROP FUNCTION IF EXISTS public.search_workspace(uuid, text, text, integer)" in sql),
        ("insert trigger safety net present", "fill_workspace_id_from_owner" in sql and "trg_fill_workspace_id" in sql),
        ("agent_runs trigger derives via agents", "fill_agent_run_workspace_id" in sql),
    ]
    for name, cond in checks:
        _ok(f"migration: {name}") if cond else _bad(f"migration: {name}", "pattern missing")


# ---------------------------------------------------------------------------
# 2. Swept files: no bare user_id scoping on re-keyed tables
# ---------------------------------------------------------------------------

def test_swept_files_use_scope_helper() -> None:
    # Heuristic: in each swept file, any .eq("user_id", ...) that appears within
    # 12 lines after a .table("<rekeyed>") is a miss. Substrate tables count too.
    tables = REKEYED_TABLES + ["workspace_files", "workspace_file_versions"]
    table_re = re.compile(r'\.table\("(' + "|".join(tables) + r')"\)')
    for rel in SWEPT_FILES:
        path = ROOT / rel
        if not path.exists():
            _bad(f"sweep: {rel}", "file missing")
            continue
        lines = path.read_text().splitlines()
        misses = []
        for i, line in enumerate(lines):
            if table_re.search(line):
                window = lines[i:i + 12]
                for j, w in enumerate(window):
                    if re.search(r'\.eq\(\s*"user_id"\s*,', w):
                        misses.append(f"{rel}:{i + j + 1}")
                        break
        if not misses:
            _ok(f"sweep: {rel} scoped")
        else:
            _bad(f"sweep: {rel} scoped", f"bare user_id scoping at {misses}")


# ---------------------------------------------------------------------------
# 3. Scope helper behavior (functional)
# ---------------------------------------------------------------------------

def test_scope_helper() -> None:
    from services import workspace_context as wc

    GRANTED = "00000000-0000-0000-0000-00000000bbbb"
    USER = "00000000-0000-0000-0000-000000000001"

    token = wc.set_request_workspace(GRANTED)
    try:
        col, val = wc.substrate_scope_filter(USER)
    finally:
        wc.reset_request_workspace(token)
    if (col, val) == ("workspace_id", GRANTED):
        _ok("helper: contextvar → workspace scope (member path)")
    else:
        _bad("helper: contextvar → workspace scope (member path)", f"got {(col, val)}")

    orig = wc.effective_workspace_id
    wc.effective_workspace_id = lambda *a, **k: None  # type: ignore
    try:
        col, val = wc.substrate_scope_filter(USER)
    finally:
        wc.effective_workspace_id = orig  # type: ignore
    if (col, val) == ("user_id", USER):
        _ok("helper: unresolvable → legacy user_id fallback (N=1 byte-identity)")
    else:
        _bad("helper: unresolvable → legacy user_id fallback (N=1 byte-identity)", f"got {(col, val)}")


# ---------------------------------------------------------------------------
# 4. Search RPC callers pass p_workspace_id
# ---------------------------------------------------------------------------

def test_search_rpc_callers() -> None:
    offenders = []
    for base in (ROOT / "services", ROOT / "routes", ROOT / "mcp_server"):
        for py in base.rglob("*.py"):
            text = py.read_text()
            for m in re.finditer(r'rpc\("search_workspace(_semantic)?"', text):
                window = text[m.start():m.start() + 300]
                if '"p_user_id"' in window:
                    offenders.append(f"{py.relative_to(ROOT)}")
    if not offenders:
        _ok("search: all search_workspace* RPC calls keyed p_workspace_id")
    else:
        _bad("search: all search_workspace* RPC calls keyed p_workspace_id", str(set(offenders)))


# ---------------------------------------------------------------------------
# 5. MCP seam
# ---------------------------------------------------------------------------

def test_mcp_seam() -> None:
    text = (ROOT / "services/mcp_composition.py").read_text()
    if '.eq("user_id", auth.user_id)' not in text:
        _ok("mcp: recall reads no longer user-scoped")
    else:
        _bad("mcp: recall reads no longer user-scoped", "bare eq(user_id) remains")
    if "_substrate_scope(auth)" in text and "substrate_scope_filter" in text:
        _ok("mcp: reads route through the scope helper")
    else:
        _bad("mcp: reads route through the scope helper", "helper not wired")
    # ADR-408 D2 refactored the inline owner lookup into the shared
    # acting_workspace_owner seam helper — accept either form, reject the TODO.
    if "TODO(shared-workspace / Phase 3)" not in text and (
        "acting_workspace_owner(" in text or 'select("owner_id")' in text
    ):
        _ok("mcp: wake seam resolves acting-workspace → owner (TODO closed)")
    else:
        _bad("mcp: wake seam resolves acting-workspace → owner (TODO closed)", "TODO remains or owner lookup missing")


# ---------------------------------------------------------------------------

def main() -> int:
    print("ADR-407 Phase 1 — read-layer regression")
    print("=" * 60)
    test_migration_shape()
    test_swept_files_use_scope_helper()
    test_scope_helper()
    test_search_rpc_callers()
    test_mcp_seam()
    print("=" * 60)
    print(f"{len(_PASS)} passed, {len(_FAIL)} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
