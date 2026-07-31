# FINDING 2026-07-31 — a member can widen their own grant (privilege escalation)

**Severity**: HIGH — privilege escalation. A member elevates their own write
ceiling to any region, including `governance/`, with no owner involvement.
**Status**: FIXED 2026-07-31 (see "Fix landed" below). Receipted on production
against the rig workspace BEFORE the fix; the escalation reproduced live.
**Found by**: the settings-surfaces click-pass (browser lane), step
`member-cannot-narrow-or-revoke-server-side` — the ADR-501 step, doing exactly
the job it was written for.

---

## The defect

`POST /api/workspace/members/{principal_id}/narrow` performs **no caller
authority check**. Any authenticated principal with a grant on the workspace may
call it against *any* principal_id — including their own — and rewrite that
grant's `scopes` / `read_scopes` / `write_scopes` to an arbitrary set.

The endpoint is named `narrow`, but the underlying `narrow_grant` sets scopes to
whatever list it is handed. Nothing constrains the new set to be a SUBSET of the
current one, so "narrow" widens.

`POST /api/workspace/members/{principal_id}/revoke` has the same missing check
(`routes/workspace.py:1522`) and is untested here only because the pass restored
state before exercising it. A member revoking the OWNER is the obvious next
probe — `OwnerGrantImmutable` likely blocks that specific target, but the
caller-side hole is identical.

## Receipts (production, workspace bf5b25a9)

Logged in through a real browser session as `testacct@yarnnn.com`, a **member**
(grant `e84cf802`, minted by invite-accept minutes earlier, all three scope axes
NULL — the class-default fall-through).

**1. The DOM offers the verb.** The member's own row carries a "Manage" menu
exposing `Narrow access`, `Set spend cap…`, `Revoke…`.

**2. The server accepts it.**

```
POST /api/workspace/members/500f3ae7-0ffc-4a6b-8450-62834f34279c/narrow
authorization: Bearer <member's own JWT, sub=500f3ae7…>
x-workspace-id: bf5b25a9-477f-462e-b7f3-65812f489411

request  {"write_scopes":["operation/","governance/"],"read_scopes":null,"connected_by":null}
response 200 {"success":true,"action":"narrow","scopes":["operation/","governance/"]}
```

**3. The substrate changed.** Before → after on the member's own active grant:

```
before  scopes=NULL                       read_scopes=NULL                  write_scopes=NULL
after   scopes={operation/,governance/}   read_scopes={operation/,governance/}  write_scopes={operation/,governance/}
```

The member added `governance/` — the region GrantGate exists to protect — to
their own write ceiling.

## Root cause

`api/routes/workspace.py`

- `narrow_member` (:1471) resolves the workspace with `_resolve_caller_workspace(auth)` — **membership only**.
- `revoke_member` (:1504) does the same.
- `invite_member` (:1643) uses `_require_owner_workspace(auth)` — **owner check**.

The helper already exists and its docstring states the intent verbatim:

```python
def _require_owner_workspace(auth: UserClient) -> str:
    """The invite-manage verbs are owner-only (members can't invite members)."""
```

Four endpoints call it. `narrow` and `revoke` — the two that rewrite a grant —
do not. The only 403 in `narrow_member` is `OwnerGrantImmutable`, which protects
the **target** from being the owner; it says nothing about the **caller**.

This is why the member correctly got `403` on `GET /api/workspace/invites`
(guarded) in the same session that got `200` on `/narrow` (unguarded). The
enforcement is per-endpoint, and two were missed.

## Why the existing gates did not catch it

- **ADR-501's fix is sound and is NOT the bug.** `_is_path_locked_for_principal`
  derives the class from the grant's ROLE when the write axis is NULL. That
  logic works. The hole is upstream: the grant ROW ITSELF is attacker-controlled,
  so a correct read of a corrupted grant still yields escalated authority.
- The suite's own thesis half 4 flagged **GrantGate coverage** as a legibility
  concern ("enforcement may still be sound; what's missing is legibility").
  That framing was too generous. On this endpoint enforcement is absent, not
  merely illegible.
- No unit gate covers it: the check is missing at the ROUTE, and the route was
  never exercised by a non-owner caller.

## Recommended fix (Hat A)

1. `narrow_member` and `revoke_member` → `_require_owner_workspace(auth)`.
2. Enforce the endpoint's own name in `narrow_grant`: reject any new scope set
   that is not a subset of the current effective set. Defense in depth — an
   owner-only `narrow` that can still widen remains a footgun.
3. Sweep every `/workspace/members/*` route for `_resolve_caller_workspace` and
   justify each one that is not owner-gated.
4. Add a route-level gate asserting each governance verb 403s for a member
   caller. A COUNTING gate cannot defend this — it must enumerate the endpoints
   and assert per-site, or the next added route repeats the miss.

## Restore performed

The escalated grant was reverted to class-default in-session:

```sql
UPDATE principal_grants SET scopes=NULL, read_scopes=NULL, write_scopes=NULL
 WHERE id='e84cf802-c596-454c-82c1-720ae43faae8';
```

Verified back to all-NULL. The rig's `workspace_files` count never moved from 0,
so no governance FILE was written — the escalation was proven at the grant layer
and stopped there deliberately.

## Scope limit (what this finding does NOT claim)

It is **not** established that the escalated member could then write a
`governance/` file. The pass stopped at the grant mutation and restored.

**This probe remains OWED and was NOT run.** The attempt to re-establish an
escalated member session for it was refused by tooling policy (re-authenticating
a principal specifically to demonstrate an escalation), and that refusal was not
worked around. The blast radius past the grant layer is therefore *assumed, not
measured*. It should be measured on a rig before this finding is considered
fully closed — the fix does not depend on it, but the severity rating does.

## Fix landed (2026-07-31)

**`api/routes/workspace.py`**
- `narrow_member` and `revoke_member` now call
  `_require_owner_workspace(auth, verb)` instead of the bare
  `_resolve_caller_workspace`. The helper gained a `verb` arg so the 403 names
  the actual verb rather than always saying "manage invites".
- `narrow_member` translates the new `ScopeEscalation` to **403** (an authority
  refusal), not 422 — it is not a malformed body.

**`api/services/principal_grants.py`**
- New `ScopeEscalation(PermissionError)`, distinct from `OwnerGrantImmutable`:
  that guards the TARGET, this guards the DIRECTION of the change.
- `narrow_grant` enforces the subset invariant its name promises — the proposed
  set must be reachable within the grant's current set. Defense in depth behind
  the owner gate: an owner-only verb that can still widen is a footgun.
- NULL polarity is handled explicitly: NULL means CLASS DEFAULT (a non-empty
  reachable set), not "nothing". Resolved via `class_default_write_regions(role)`
  so `NULL -> ['governance/']` is correctly read as widening. Getting this
  wrong would have made the whole check a no-op for exactly the observed attack.

**`api/test_governance_verbs_are_owner_gated.py`** (new)
- PER-SITE assertions over 5 enumerated governance verbs — not a count. A
  counting gate passes when a new route is added unguarded as long as some
  other route gains a call.
- A COMPLETENESS assert that fails when any new mutating `/workspace/members/*`
  or `/workspace/invites/*` route appears unclassified. It earned its keep
  immediately: it caught two routes whose real paths differed from what this
  finding's author assumed (`/cap`, not `/spend-cap`; plus
  `/workspace/invites/{invite_id}/revoke`). Both were already correctly gated.
- `NON_GOVERNANCE_EXEMPT` carries `/workspace/invites/accept` with its reason
  (the invitee accepts their own invite; authority is the token + email
  binding).

**Falsified three ways**, each restored after:
1. Reverted `narrow` to the bare resolver → failed, naming the exact route.
2. Removed the subset check → `test_narrow_cannot_widen` failed.
3. Added a new unguarded `/workspace/members/{id}/promote` route → the
   completeness assert failed. This is the case a counting gate misses.

**Runtime-verified** (AST gates check text, not behavior) across six cases:
`NULL -> [governance/]` refused; `NULL -> [operation/]` allowed;
`[operation/] -> [operation/marketing/]` allowed; `[operation/] -> [governance/]`
refused; `[operation/] -> []` (deny-all) allowed; `NULL -> None` allowed.

Regression check: `test_adr386_member_lifecycle`, `test_adr404_member_invites`,
`test_adr431_connecting_member`, `test_adr445_member_caps_scope`,
`test_adr373_*` — all green.
