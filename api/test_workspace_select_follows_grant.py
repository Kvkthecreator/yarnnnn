"""The `workspaces` SELECT policy follows the GRANT, not just ownership (mig 243).

THE DEFECT (falsified on production as the real member 2be30ac5…):

    member_sees_own_ws     | 1
    member_sees_GRANTED_ws | 0     ← holds an ACTIVE grant into it

`workspaces` SELECT was `owner_id = auth.uid()`, written in migration 001 when a
workspace had one principal. ADR-373 made it a multi-principal commons and
re-keyed the substrate; this policy never learned about grants.

Why it hid: the surfaces that matter most (switcher, /workspace/memberships)
read through the SERVICE client, which bypasses RLS — so the product LOOKED
correct. The member-client readers degrade SILENTLY instead:
`get_subscription_status` returns tier="free" on zero rows while
`has_billing_authority` (service client) says the caller MAY manage billing.
An incorrect success, not an error.

What this suite pins:
  1. SELECT follows reach (owner OR active grant) — the RLS mirror of
     `services/supabase.py::principal_reaches_workspace`.
  2. UPDATE stays OWNER-ONLY. `update_workspace_identity` writes through the
     CALLER's client precisely so that policy is the gate; widening it would let
     any granted member rename the commons. This is the assertion most likely to
     be broken by a future "make RLS consistent" pass.
  3. The reach predicate is SEPARATE from `is_workspace_member()` (mig 221),
     which is role-restricted to owner|member and answers grant VISIBILITY —
     and omits `viewer`, who must be able to read a workspace they can enter
     (ADR-517 D6).

Run: python3 test_workspace_select_follows_grant.py   (from api/)
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MIG = os.path.join(
    HERE, "..", "supabase", "migrations",
    "243_workspace_select_follows_the_grant.sql",
)

failures: list = []
checks = 0


def check(label: str, cond: bool) -> None:
    global checks
    checks += 1
    print(f"  {'✓' if cond else '✗'} {label}")
    if not cond:
        failures.append(label)


mig = open(MIG).read()

print("\n[1] SELECT follows reach")
check("1a. the old owner-only SELECT policy is dropped",
      'DROP POLICY IF EXISTS "Users can view own workspaces"' in mig)
check("1b. the new SELECT policy uses the reach predicate",
      re.search(r"FOR SELECT\s+USING \(public\.principal_reaches_workspace_rls\(id\)\)", mig) is not None)
check("1c. reach = owner OR active grant (the app's own definition)",
      "owner_id = auth.uid()" in mig and "status = 'active'" in mig)

print("\n[2] The write policies are NOT widened (the dangerous half)")
# The migration must not touch UPDATE/DELETE/INSERT at all.
for cmd in ("UPDATE", "DELETE", "INSERT"):
    check(
        f"2a. no CREATE POLICY ... FOR {cmd} (widening it would let a granted "
        f"member act as owner)",
        re.search(rf"CREATE POLICY[^;]*FOR {cmd}", mig, re.S) is None,
    )
check("2b. the migration ASSERTS the UPDATE policy is still owner-only",
      "must remain owner-only" in mig)
check("2c. it REFUSES to commit on a wrong shape",
      mig.count("RAISE EXCEPTION") >= 3)

print("\n[3] The predicate is its own function, not a mutation of mig 221's")
check("3a. a dedicated reach predicate is created",
      "CREATE OR REPLACE FUNCTION public.principal_reaches_workspace_rls" in mig)
check("3b. is_workspace_member() is NOT redefined (it answers a DIFFERENT "
      "question — grant visibility — and omits viewer)",
      "CREATE OR REPLACE FUNCTION public.is_workspace_member" not in mig)
check("3c. SECURITY DEFINER (else the policy recurses through RLS)",
      "SECURITY DEFINER" in mig)
check("3d. execute is granted to authenticated, revoked from PUBLIC",
      "REVOKE ALL ON FUNCTION public.principal_reaches_workspace_rls" in mig
      and "GRANT EXECUTE ON FUNCTION public.principal_reaches_workspace_rls" in mig)
check("3e. the predicate does NOT role-filter (a viewer reaches too, ADR-517 D6)",
      not re.search(r"principal_reaches_workspace_rls.*?role IN", mig, re.S))

print("\n[4] The app-side reach check is unchanged (one definition, two homes)")
sup = open(os.path.join(HERE, "services", "supabase.py")).read()
_reach = re.search(r"def principal_reaches_workspace\(.*?\n(?=\n\ndef )", sup, re.S)
check("4a. the Python reach check still exists", _reach is not None)
check("4b. it still means owner OR active grant",
      bool(_reach) and "resolve_owned_workspace_ids(" in _reach.group(0)
      and 'eq("status", "active")' in _reach.group(0))

print(f"\n{'='*66}")
if failures:
    print(f"FAILED {len(failures)}/{checks}")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(f"PASSED {checks}/{checks}")
