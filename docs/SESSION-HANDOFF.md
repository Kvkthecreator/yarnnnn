# SESSION HANDOFF — E2E sign-off: workspace-settings + user-settings surfaces

> Written 2026-07-31 (the eval-layer-audit / closed-loop session). Delete this
> file after absorbing it. Operator intent: define the verification criteria
> (none exist yet for these surfaces), run the browser passes, and verdict the
> settings surfaces as production-ready or not.

## Describe

The E2E closed-loop direction is ratified and its infrastructure is live
(memory: `project_e2e_closed_loop_direction.md`;
`docs/evaluations/VERIFICATION.md`; the verification-radar SessionStart hook).
Claude Code acts as the operator's testing principal via Claude in Chrome. This
is the first real production sign-off pass: workspace-settings and user/account-
settings surfaces + their workflows. DEFINING the criteria is Phase 1 of this
session, not a prerequisite for it.

Owed items these surfaces carry (memory-receipted, do not re-derive):
- The ADR-501 "human member-session click-pass" has been OWED since the
  workspace-binding audit — this session discharges it.
- GrantGate on 6 regions (owed, same audit) — verify current state, don't assume.
- ADR-382 roster dial rows (open per ADR-490/491 state) and the ADR-495
  "you were added" notification (deferred by design) — KNOWN-DEFERRED; record
  as such, do not fail sign-off on them.

Test principals (the declared roster, memory-receipted):
- kvkthecreator@gmail.com (`kvk`, 2abf3f96) — OWNER of the live workspace d5b9029b.
- seulkim88@gmail.com (2be30ac5) — MEMBER of d5b9029b + owner of its own ws
  4ca9c664. The owner/member pair is the core instrument.
- Rigs for anything destructive: `kvk-yarnnn` (67c5c637, ws bf5b25a9),
  `bare-kernel`, testacct@yarnnn.com (500f3ae7 — NO grants yet; provision if needed).
- Login: magic links via `api/scripts/alpha_ops/_shared.py` generate_link machinery.

## Preconditions (check before anything else)

1. Browser tools present? ToolSearch for chrome/browser tools. If absent, the
   Claude-in-Chrome pairing isn't enabled — STOP and tell the operator to run
   `/chrome` → Enable by default. Do not fall back to API-only and call it E2E.
2. Read the verification radar's output (fires at SessionStart). If the web lane
   is due for unrelated changes, note it; this session's passes discharge it
   only for what they actually cover.
3. Local stack or prod? Default: prod (the sign-off target is what users get),
   read-mostly on d5b9029b; destructive/seeded flows on rigs only.

## Task — three phases, in order

**Phase 1 — DEFINE the criteria.** Derive the surface + workflow inventory from
CODE, not memory: the FE `SurfaceRegistry` and the workspace-settings /
account-settings pane components (`web/`), cross-checked against
`docs/design/WORKSPACE.md` (per-tab contracts) and the governing ADRs (491
settings re-cut · 445 seat-sync/billing · 396/490 balance-legibility/pricing ·
501/502/503 binding+wallet · 373/386/431 members + AI connections · 404
invites). For each surface/workflow write a manifest in the
Describe/Task/Guardrails/Exit shape — formalize `suite_kind: browser` in the
eval-suites registry (status: current), extending `api/test_eval_suite_gate.py`
to validate the new kind (gate proven red before trusted green). Every
manifest's Exit criteria must pair a DOM observation with a SUBSTRATE receipt
for each state-changing step (revision id / DB row / grant state / webhook
effect). If scope feels ambiguous, get operator sign-off on the manifest set
before firing; otherwise proceed.

**Phase 2 — RUN the passes.** As owner (kvk) and as member (seulkim88), through
the real browser: every settings pane renders correct data for that principal;
every verb does what it claims AND writes what it claims (verify in DB with the
service key); every member-invisible or member-forbidden affordance is actually
absent/refused SERVER-SIDE, not display-only (the ADR-501 lesson: the gate
keyed on transport, not grant role — enumerate the DOORS). Billing: verify
usage-display (no raw dollars for members per ADR-503 wallet-follows-grant);
do NOT complete real checkout — stop at the LemonSqueezy handoff and record the
boundary. Members/AI-connections: narrow/revoke verbs on a RIG pairing only —
never revoke seulkim's live member grant (the standing test pair); restore any
state you change. DangerZone/purge: rig workspaces ONLY, never d5b9029b.

**Phase 3 — VERDICT.** Per surface: READY / READY-WITH-FIXES / NOT-READY, with
receipts. Fix what's small and obvious in-session (separate commits, gates, the
usual discipline); NOT-READY items get a named defect with reproduction. Write
the finding (`docs/evaluations/`, dated, session records per
EVAL-SUITE-DISCIPLINE §6 — screenshots where load-bearing). Mark the validated
lanes (`mark-validated.sh`) ONLY for what the passes actually covered. Commit
manifests + gate + finding + ledger; push to main.

## Guardrails

- d5b9029b is LIVE substrate: read-mostly; deliberate writes reversible and
  reverted or tombstoned; reset-to-clean (S2) before any seeded scenario.
- Real externals (s.colopy@ccgrhc.com, b.tharalson@gmail.com) are NEVER subjects.
- No real payments, no external emails/sends from test flows.
- `git commit --only`; never `git add -A`; concurrent lanes are active.
- A green gate you didn't watch fail is an unrun gate; a pass without a
  substrate receipt is narrative.

## Exit criteria

- A committed browser-manifest set covering both settings surfaces, gate-checked.
- Owner AND member passes executed with per-step receipts.
- A finding with per-surface verdicts and the sign-off summary: production-ready
  / named defects / known-deferred.
- Ledger updated for covered lanes; everything pushed to main.
- "These surfaces are NOT ready, here's the defect list" is an acceptable
  outcome — a receipted negative is a real result.
