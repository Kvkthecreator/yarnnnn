"""ADR-596 D4 — the workspace home timezone is first-class; the prose path is dead.

Script-style (run: cd api && python3 test_adr596_workspace_timezone.py).

What this gate holds:
  1. The scheduling path resolves the ACTING WORKSPACE's `timezone` column —
     behaviorally, through the real function with the real contextvar binding.
  2. The prose path is DELETED: nothing under services/ resolves a timezone
     from persona/IDENTITY.md, and the old name `get_user_timezone` has no
     definition or caller left (a rename that leaves a live alias is two ways
     to ask one question).
  3. The one door validates: PATCH /workspace refuses a non-IANA name inside
     the `timezone` branch (AST-anchored — a comment cannot satisfy it).
  4. Migration 247 adds the column and carries its own verify block, and lets
     the runner own the transaction (the 245 precedent: dry-run stays a dry run).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
sys.path.insert(0, str(API))

FAILURES: list[str] = []


def _assert(cond: bool, msg: str) -> None:
    tag = "PASS" if cond else "FAIL"
    print(f"  [{tag}] {msg}")
    if not cond:
        FAILURES.append(msg)


# ---------------------------------------------------------------------------
# 1. Behavior — the column is what resolves, through the real binding
# ---------------------------------------------------------------------------

class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    """A minimal chainable stand-in for the supabase table query."""

    def __init__(self, rows, calls):
        self._rows = rows
        self.calls = calls

    def select(self, cols):
        self.calls.append(("select", cols))
        return self

    def eq(self, col, val):
        self.calls.append(("eq", col, val))
        return self

    def limit(self, n):
        return self

    def execute(self):
        return _Result(self._rows)


class _Client:
    def __init__(self, rows):
        self.rows = rows
        self.calls: list = []

    def table(self, name):
        self.calls.append(("table", name))
        return _Query(self.rows, self.calls)


def test_behavior():
    print("1. get_workspace_timezone reads workspaces.timezone for the bound workspace")
    from services.schedule_utils import get_workspace_timezone
    from services.workspace_context import set_request_workspace, reset_request_workspace

    token = set_request_workspace("ws-under-test")
    try:
        # A declared home timezone resolves.
        client = _Client([{"timezone": "Asia/Seoul"}])
        _assert(get_workspace_timezone(client, "user-1") == "Asia/Seoul",
                "declared IANA name resolves verbatim")
        _assert(("table", "workspaces") in client.calls,
                "the read targets the workspaces table")
        _assert(("eq", "id", "ws-under-test") in client.calls,
                "the read is keyed by the ACTING workspace (contextvar binding)")

        # Undeclared (NULL) → UTC, honestly.
        _assert(get_workspace_timezone(_Client([{"timezone": None}]), "u") == "UTC",
                "NULL column → UTC")
        _assert(get_workspace_timezone(_Client([]), "u") == "UTC",
                "no workspace row → UTC")

        # A corrupt column value degrades to UTC rather than crashing the
        # scheduler (the door validates writes; this is defense for the read).
        _assert(get_workspace_timezone(_Client([{"timezone": "Not/AZone"}]), "u") == "UTC",
                "an unresolvable name degrades to UTC, never raises")
    finally:
        reset_request_workspace(token)


# ---------------------------------------------------------------------------
# 2. The prose path is dead, and the old name has no survivors
# ---------------------------------------------------------------------------

def test_prose_path_deleted():
    print("2. the persona/IDENTITY.md timezone parse is deleted, name and all")
    src = (API / "services" / "schedule_utils.py").read_text()
    tree = ast.parse(src)

    # No function in the module is still named get_user_timezone, and the
    # module never touches the persona path or UserMemory. AST, not grep:
    # the docstring legitimately NAMES the old function it replaces.
    fn_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    _assert("get_user_timezone" not in fn_names, "no get_user_timezone definition survives")
    _assert("get_workspace_timezone" in fn_names, "get_workspace_timezone is defined")
    idents = {
        n.id for n in ast.walk(tree) if isinstance(n, ast.Name)
    } | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    _assert("PERSONA_IDENTITY_PATH" not in idents and "UserMemory" not in idents,
            "schedule_utils no longer reads persona/IDENTITY.md")

    # No CALLER anywhere still names the old function (a call that survives
    # the rename is an ImportError waiting for its first scheduler tick).
    survivors = []
    for p in (API / "services").rglob("*.py"):
        t = ast.parse(p.read_text())
        for n in ast.walk(t):
            if isinstance(n, (ast.Name, ast.Attribute)):
                name = n.id if isinstance(n, ast.Name) else n.attr
                if name == "get_user_timezone":
                    survivors.append(str(p))
            if isinstance(n, ast.ImportFrom):
                if any(a.name == "get_user_timezone" for a in n.names):
                    survivors.append(str(p))
    _assert(not survivors, f"no caller names get_user_timezone (found: {survivors or 'none'})")


# ---------------------------------------------------------------------------
# 3. The door validates IANA, inside the timezone branch
# ---------------------------------------------------------------------------

def test_door_validates():
    print("3. PATCH /workspace carries the timezone field and refuses a non-IANA name")
    tree = ast.parse((API / "routes" / "workspace.py").read_text())

    model = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.ClassDef) and n.name == "WorkspaceIdentityUpdate"),
        None,
    )
    _assert(model is not None, "WorkspaceIdentityUpdate exists")
    fields = {
        s.target.id for s in (model.body if model else [])
        if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)
    }
    _assert("timezone" in fields, "the PATCH model has a timezone field")

    fn = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.AsyncFunctionDef) and n.name == "update_workspace_identity"),
        None,
    )
    _assert(fn is not None, "update_workspace_identity exists")
    # The validation is a pytz.timezone(...) CALL inside the handler — an
    # executable fact a deleted branch cannot fake from a comment.
    calls = [
        n for n in ast.walk(fn) if fn and isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute) and n.func.attr == "timezone"
        and isinstance(n.func.value, ast.Name) and n.func.value.id == "pytz"
    ]
    _assert(bool(calls), "the handler validates via pytz.timezone(...)")

    resp = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.ClassDef) and n.name == "WorkspaceIdentityResponse"),
        None,
    )
    rfields = {
        s.target.id for s in (resp.body if resp else [])
        if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)
    }
    _assert("timezone" in rfields, "the identity response serves timezone back")

    member = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.ClassDef) and n.name == "WorkspaceMembership"),
        None,
    )
    mfields = {
        s.target.id for s in (member.body if member else [])
        if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)
    }
    _assert("timezone" in mfields, "the memberships row carries timezone (the pane's read)")


# ---------------------------------------------------------------------------
# 4. Migration 247 — column + its own verification, runner owns the txn
# ---------------------------------------------------------------------------

def test_migration():
    print("4. migration 247 adds the column, verifies itself, and stays dry-runnable")
    mig = (API.parent / "supabase" / "migrations"
           / "247_adr596_workspace_home_timezone.sql").read_text()
    _assert("ADD COLUMN IF NOT EXISTS timezone" in mig, "adds workspaces.timezone")
    _assert("RAISE EXCEPTION" in mig and "information_schema.columns" in mig,
            "carries its own landed-state verification")
    _assert("BEGIN;" not in mig and "COMMIT;" not in mig,
            "lets the runner own the transaction (dry-run stays a dry run)")


if __name__ == "__main__":
    test_behavior()
    test_prose_path_deleted()
    test_door_validates()
    test_migration()
    print()
    if FAILURES:
        print(f"FAILED — {len(FAILURES)} check(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL PASS — ADR-596 D4 holds")
