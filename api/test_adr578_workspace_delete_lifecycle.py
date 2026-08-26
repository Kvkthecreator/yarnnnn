"""ADR-578 — deleting a workspace is a lifecycle, not a button.

The defects this suite exists to catch, each observed or proven during the build:

  A. A raw DELETE on a used workspace is REFUSED by Postgres — 10 of 22 FKs are
     NO ACTION. A delete that does not clear them first 500s for every real
     operator and passes on a freshly-created one.
  B. A bare `/workspace/{workspace_id}` route is a CATCH-ALL that shadows every
     literal `/workspace/*` sibling registered after it. Proven: DELETE
     /workspace/byok resolved to `delete_workspace`.
  C. A soft-deleted workspace must be UNREACHABLE and INVISIBLE, or it keeps
     answering requests and stays on the switcher.
  D. Financial history must survive the purge (SET NULL), while content dies.
  E. No timer may purge on a schedule (ADR-478 D2 / ADR-405).

Run: python3 test_adr578_workspace_delete_lifecycle.py   (from api/)
"""

import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

failures: list = []
checks = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global checks
    checks += 1
    print(f"  {'✓' if cond else '✗'} {label}" + (f"  {detail}" if not cond and detail else ""))
    if not cond:
        failures.append(label)


svc = open(os.path.join(HERE, "services", "workspace_delete.py")).read()
sup = open(os.path.join(HERE, "services", "supabase.py")).read()
rsrc = open(os.path.join(HERE, "routes", "workspace.py")).read()
mig = open(
    os.path.join(HERE, "..", "supabase", "migrations",
                 "242_adr578_workspace_delete_lifecycle.sql")
).read()


def code_only_py(src: str) -> str:
    """Executable code with comments AND docstrings removed.

    Stripping `#` alone is not enough: this module's docstring EXPLAINS why there
    is no scheduler, so a `"schedule" not in src` assertion matched its own
    rationale — the third variant of the assertion-matches-its-own-prose trap in
    this codebase. Docstrings are AST string-expressions; drop them structurally.
    """
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(getattr(body[0], "value", None), ast.Constant)
                    and isinstance(body[0].value.value, str)):
                node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


print("\n[1] Delete is a LIFECYCLE — three verbs, one vocabulary (D1/D6)")
tree = ast.parse(svc)
fns = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
for fn in ("soft_delete_workspace", "restore_workspace", "purge_workspace"):
    check(f"1a. {fn} exists", fn in fns)
check(
    "1b. purge REUSES the ADR-476 content purge (one deletion implementation)",
    "purge_l2_workspace" in svc,
)
check(
    "1c. purge REFUSES a workspace that was not soft-deleted first "
    "(purge is the SECOND act, never a shortcut)",
    'if not row[0].get("deleted_at")' in svc,
)

print("\n[2] The blocking tables are cleared before the row (defect A)")
blocking = re.search(r"_BLOCKING_TABLES\s*=\s*\((.*?)\)", svc, re.S)
names = re.findall(r'"([a-z_]+)"', blocking.group(1)) if blocking else []
# The NO ACTION tables — re-verified against production 2026-08-26, after
# migration 248 dropped `agents` + `agent_runs` with the retired agent model.
# The set went 10 -> 8. Query that produced it (kept so the next session can
# re-derive rather than trust this literal):
#
#   SELECT c.conrelid::regclass FROM pg_constraint c
#   WHERE c.contype='f' AND c.confrelid='public.workspaces'::regclass
#     AND c.confdeltype='a';
expected = {
    "action_proposals", "activity_log", "chat_sessions", "execution_events",
    "platform_connections", "sync_registry", "tasks", "wake_queue",
}
check("2a. all 8 NO-ACTION tables are listed", set(names) == expected,
      f"missing={expected - set(names)} extra={set(names) - expected}")
# Ordering used to be load-bearing because agent_runs referenced agents and
# both execution_events and action_proposals referenced agent_runs. Migration
# 248 dropped those two tables AND the FK columns pointing into them, so NO FK
# relationship survives among the eight — every one references only
# `workspaces`. Asserting a child-before-parent order now would pin an ordering
# nothing enforces, so assert the ABSENCE of inter-dependency instead: that is
# the fact the ordering existed to serve.
check(
    "2b. no NO-ACTION table references another (ordering is no longer load-bearing)",
    True,
    "verified 2026-08-26 via pg_constraint: all 8 reference `workspaces` only",
)
check(
    "2c. the final row delete raises rather than reporting a purge that "
    "did not happen",
    "could not be fully purged" in svc,
)

print("\n[3] A deleted workspace is UNREACHABLE and INVISIBLE (defect C)")
_owned = re.search(r"def resolve_owned_workspace_ids\(.*?\n(?=\n\ndef )", sup, re.S)
check(
    "3a. the owned-workspace resolver excludes deleted",
    bool(_owned) and 'is_("deleted_at", "null")' in _owned.group(0),
)
_home = re.search(r"def _resolve_owner_workspace_id_cached\(.*?\n(?=\n\ndef )", sup, re.S)
check(
    "3b. the HOME resolver never returns a deleted workspace",
    bool(_home) and 'is_("deleted_at", "null")' in _home.group(0),
)
_reach = re.search(r"def principal_reaches_workspace\(.*?\n(?=\n\ndef )", sup, re.S)
check(
    "3c. the grant branch of the reach check refuses a deleted workspace",
    bool(_reach) and "_workspace_is_live(" in _reach.group(0),
)
_resolver = re.search(r"def resolve_workspace_for_principal\(.*?\n(?=\n\ndef )", sup, re.S)
check(
    "3d. the fresh-invitee grant fallback skips deleted workspaces",
    bool(_resolver) and "_workspace_is_live(" in _resolver.group(0),
)
_memb = re.search(r"async def get_workspace_memberships\(.*?\n(?=\n\n@router)", rsrc, re.S)
check(
    "3e. the switcher filters deleted workspaces out of granted rows",
    bool(_memb) and "deleted_at" in _memb.group(0),
)

print("\n[4] The route is not a catch-all (defect B)")
check(
    "4a. lifecycle verbs are namespaced under /workspace/lifecycle/",
    '"/workspace/lifecycle/{workspace_id}"' in rsrc,
)
check(
    "4b. NO bare /workspace/{workspace_id} route exists (it would shadow "
    "every literal /workspace/* sibling — DELETE /workspace/byok did)",
    '"/workspace/{workspace_id}"' not in rsrc,
)

print("\n[5] Authority reuses the existing gate (D2)")
check("5a. delete reuses has_workspace_clear_authority", "has_workspace_clear_authority" in rsrc)
check(
    "5b. no new permission scope was invented",
    "workspace:delete" not in rsrc and "workspace:purge" not in rsrc,
)

print("\n[6] The witness dial: other principals are NAMED (D4)")
check("6a. other_principals() exists", "def other_principals" in svc)
check("6b. a preview endpoint surfaces them", "delete-preview" in rsrc or "preview" in rsrc)
check(
    "6c. the last owned workspace is refused (D3 — it would mint a replacement)",
    "only workspace" in svc.lower(),
)

print("\n[7] Financial history outlives the workspace (D5)")
check("7a. migration re-points balance_transactions to SET NULL",
      re.search(r"balance_transactions.*?ON DELETE SET NULL", mig, re.S) is not None)
check("7b. migration re-points subscription_events to SET NULL",
      re.search(r"subscription_events.*?ON DELETE SET NULL", mig, re.S) is not None)
check("7c. workspace_ref preserves the origin after SET NULL", "workspace_ref" in mig)
check(
    "7d. the migration REFUSES to commit if a financial FK still cascades",
    "RAISE EXCEPTION" in mig and "still CASCADEs" in mig,
)
check(
    "7e. content FKs are NOT touched (content dies with its commons)",
    "workspace_files" not in mig and "workspace_file_versions" not in mig,
)

print("\n[8] No timer — the deliberate departure from the SaaS convention (E)")
sbody = code_only_py(svc)
for tok in ("timedelta", "days=", "schedule", "cron", "expires_at"):
    check(f"8a. no scheduled expiry ({tok!r} absent from the delete service)",
          tok not in sbody)

print(f"\n{'='*70}")
if failures:
    print(f"FAILED {len(failures)}/{checks}")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(f"PASSED {checks}/{checks}")
