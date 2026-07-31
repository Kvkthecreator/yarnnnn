# SESSION HANDOFF — settings-surfaces E2E: Phase 1 DONE, Phase 2 blocked on pairing

> Rewritten 2026-07-31 at `849f2ae` (supersedes the Phase-1 brief written at
> `c42a25e`, now absorbed). Delete this file in the commit that absorbs it.

## Where the arc stands

**Phase 1 (DEFINE the criteria) is COMPLETE and committed at `849f2ae`.**
**Phase 2 (RUN the passes) has NOT started — it is blocked on a precondition.**

### The blocker

The session that wrote Phase 1 had **no browser tools**. Two ToolSearch sweeps
returned only `WebFetch`. `/config chrome=true` sets the *preference*; it does
not perform the *pairing*. The operator must run `/chrome` → **Enable** in an
interactive session with the Chrome extension installed, then start a FRESH
session (tool schemas load at startup, not hot-reload).

Phase 2 was deliberately NOT faked via API-only probing — that is half a sweep,
and the half that cannot see the defect class this pass hunts (ADR-501: the
ceiling was display-only; the endpoint still accepted the call).

### Also owed

`849f2ae` is committed on local `main` but **NOT PUSHED** — the push was denied
by the permission classifier. Push it, or re-run with approval.

## What Phase 1 landed

- `docs/evaluations/eval-suites/settings-surfaces-click-pass.yaml` — the
  manifest (authority). Four-sided thesis; 10 steps; every `mutates: true` step
  carries `receipt:` + `restore:`.
- `docs/evaluations/OPERATOR-PACKET-settings-click-pass.md` — the portable form
  for a browser principal with NO repo access (Claude desktop / Cowork). Splits
  the pass into a DOM half (browser records) and a SUBSTRATE half (repo
  verifies). Has a fill-in report template in §6.
- `api/scripts/operator/browser_login_link.py` — mints a navigable single-use
  magic link. Roster-guarded in code; refuses non-test emails (verified).
- `api/test_eval_suite_gate.py` — `suite_kind: browser` + the per-step receipt
  invariant + `test_llm_runner_refuses_browser_suites`. Proven RED twice.
- README + VERIFICATION.md updated; the stale `permission.py` pointer in
  `GrantGate.tsx` corrected.

## Phase 2 — how to run it (two viable paths)

**Path A (preferred): Claude in Chrome, in-repo.** Pair, restart, then drive the
manifest directly — DOM and substrate receipts in one session.

**Path B: Claude desktop drives the browser, repo session verifies.** Hand the
operator packet to desktop Claude. It fills in §6 and hands it back; a repo
session runs the receipt queries and pairs them. This path exists because
desktop reportedly has working browser access.

Either way: **the receipts are not optional.** A returned §6 with DOM
observations but no substrate queries closes nothing.

## Phase 3 — still owed

Per-surface verdict (READY / READY-WITH-FIXES / NOT-READY) with receipts; the
dated finding under `docs/evaluations/`; `mark-validated.sh web` ONLY for what
the passes actually covered; commit + push.

## Findings already receipted (do not re-derive)

- **"GrantGate on 6 regions" is ONE region.** Only call site:
  `web/components/agents/SystemAgentPanes.tsx:109`, gating Autonomy on
  `governance/`. Members / Billing / DangerZone / the whole account door gate by
  other means (`readOnly` prop, 403 catch, `can_clear`) or not at all. This is
  thesis half 4 of the manifest — a coverage *decision* to make, not a bug to
  fix silently.
- **ADR-501's fix is real** (`_is_path_locked_for_principal` derives class from
  the grant's ROLE when the write axis is NULL). Receipted NEGATIVE on the
  suspicion. Live member-session behavior is still unproven — that is step C.
- **Live grant state**: seulkim88's member grant on `d5b9029b` is `active` with
  `scopes` / `read_scopes` / `write_scopes` ALL NULL → every caller takes the
  class-default fall-through. The grant-honored branch is unexercised in prod.
- **L4 reset** passes `workspace_id=None`, so `_purge_scope` falls back to
  `user_id`: a member's reset deletes only their own rows. Correct, but resting
  on an implicit default.

## Guardrails (unchanged, still binding)

`d5b9029b` read-mostly · never revoke seulkim's grant · destructive verbs on rigs
only · billing stops at the LemonSqueezy handoff · real externals are never
subjects · `git commit --only`, never `git add -A`.
