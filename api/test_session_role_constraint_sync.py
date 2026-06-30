"""Regression guard: services.narrative.VALID_ROLES must stay a SUBSET of the
session_messages.role CHECK constraint in the migrations.

The bug this guards (2026-06-30): the actor-identity unification renamed the
narrative role `reviewer` → `freddie` in VALID_ROLES (whose comment claims it
"Mirrors the session_messages.role CHECK constraint") — but no migration updated
the DB constraint. Every Freddie addressed reply then hit
`session_messages_role_check` on persist; write_narrative_entry is best-effort
(swallows the error), so the wake succeeded, the SSE frame rendered the reply
live ONCE, but it was never saved → the operator saw their question and a blank
panel. Migration 191 added `freddie`. This test ensures the two never drift
again: any role the app may write MUST be permitted by the DB constraint.

Pure offline: parses VALID_ROLES from the module + the CHECK constraint from the
latest migration that defines it. No DB, no LLM.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))
_REPO_ROOT = _API_ROOT.parent
_MIGRATIONS = _REPO_ROOT / "supabase" / "migrations"

PASSED = 0
FAILED = 0


def check(cond: bool, label: str) -> None:
    global PASSED, FAILED
    print(f"  {'✓' if cond else '✗'} {label}")
    if cond:
        PASSED += 1
    else:
        FAILED += 1


def _latest_constraint_roles() -> set[str]:
    """Parse the role set from the LATEST migration that (re)defines
    session_messages_role_check. Migrations are applied in numeric order, so the
    highest-numbered file that defines the constraint is the live shape."""
    pat_def = re.compile(
        r"session_messages_role_check\s+CHECK\s*\(\s*role\s+IN\s*\(([^)]*)\)",
        re.IGNORECASE | re.DOTALL,
    )
    best_num = -1
    best_roles: set[str] = set()
    for f in _MIGRATIONS.glob("*.sql"):
        m_num = re.match(r"(\d+)", f.name)
        if not m_num:
            continue
        num = int(m_num.group(1))
        text = f.read_text()
        m = pat_def.search(text)
        if m and num > best_num:
            best_num = num
            best_roles = {
                r.strip().strip("'\"")
                for r in m.group(1).split(",")
                if r.strip()
            }
    return best_roles


def test_valid_roles_subset_of_constraint():
    print("\n[role-sync] VALID_ROLES ⊆ session_messages.role CHECK constraint")
    from services.narrative import VALID_ROLES

    constraint_roles = _latest_constraint_roles()
    check(bool(constraint_roles), "found a session_messages_role_check definition in migrations")
    check("freddie" in constraint_roles,
          "constraint permits 'freddie' (migration 191 — the bug this guards)")

    missing = set(VALID_ROLES) - constraint_roles
    check(
        not missing,
        f"every VALID_ROLES role is permitted by the DB constraint "
        f"(missing from constraint: {sorted(missing) or 'none'})",
    )


if __name__ == "__main__":
    test_valid_roles_subset_of_constraint()
    print(f"\n  {PASSED} passed, {FAILED} failed")
    sys.exit(1 if FAILED else 0)
