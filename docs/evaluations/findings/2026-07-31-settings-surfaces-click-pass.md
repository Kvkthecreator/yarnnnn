# RUN RECORD 2026-07-31 — settings-surfaces click-pass (runs 1 + 2)

**Instrument**: Claude in Chrome, two isolated browser contexts, live production
(`www.yarnnn.com` → `yarnnn-api.onrender.com`).
**Principals**: `kvkthecreator@yarnnn.com` (owner) / `testacct@yarnnn.com`
(cold guest → invited → member → revoked).
**Workspace**: `bf5b25a9` (kvk-yarnnn rig, disposable).
**Manifest**: `docs/evaluations/eval-suites/settings-surfaces-click-pass.yaml`

**Run 1 verdict: NOT-READY** — one HIGH escalation (now fixed), two legibility
defects, and 5 of 13 steps not run.

**RUN 2 (same day, after the fix deployed as `fcd5022`) closed the gap.
Combined verdict: READY-WITH-FIXES.** All 13 steps now have a verdict; the
escalation is re-tested against the fix and refused; two run-1 conclusions are
CORRECTED below (one of them was mine, and it was wrong in the direction of
alarm). See "Run 2" at the bottom.

---

## Baseline / final state (both receipted)

| metric | baseline | final |
|---|---|---|
| rig active grants | 1 | 1 |
| rig `workspace_files` | 0 | 0 |
| guest active grants anywhere | 0 | 0 |
| live ws `d5b9029b` files | 191 | 191 (at end of run 1) |
| live ws seulkim88 active grant | 1 | 1 |

The live workspace was never a subject and is provably untouched. (It reads 194
at the end of RUN 2 — three `ir-deck-v3/*` rows from concurrent operator work at
02:24Z, not this pass. Accounted for in the run-2 final-state section.)

## Per-step verdicts

| # | step | verdict |
|---|---|---|
| 1 | guest-is-cold-before-invite | **PASS** |
| 2 | owner-invites-guest | **PASS w/ defect** (F2) |
| 3 | guest-accepts-and-becomes-member | **PASS** |
| 4 | owner-renders-all-workspace-panes | **PARTIAL** — Access only |
| 5 | member-renders-workspace-panes | **PARTIAL** — Access + Autonomy only |
| 6 | member-billing-shows-no-raw-wallet | **NOT RUN** |
| 7 | member-account-door-renders | **NOT RUN** (`/settings` never opened) |
| 8 | member-cannot-invite-server-side | **PASS** (403, incidental) |
| 9 | member-cannot-narrow-or-revoke-server-side | **FAIL → F1 (HIGH)** |
| 10 | member-cannot-clear-workspace-server-side | **NOT RUN** |
| 11 | member-notification-prefs-round-trip | **NOT RUN** |
| 12 | owner-revokes-guest-and-access-ends | **PASS w/ defect** (F3) |
| 13 | billing-checkout-stops-at-handoff | **NOT RUN** |

**8 of 13 attempted; 5 not run.** The run stopped pursuing coverage once F1
surfaced, because the finding + fix took priority. That is a defensible
sequencing choice but it means **the settings doors are NOT signed off** — most
of the BILLING and ACCOUNT-door surface is still unexercised.

## Findings

### F1 — member can widen their own grant (HIGH) — FIXED
Full writeup: `2026-07-31-member-can-widen-own-grant.md`. `POST
/workspace/members/{id}/narrow` had no caller authority check; a member added
`governance/` to their own `write_scopes` and the server returned 200. Fixed in
`5223750` (owner-gate on narrow + revoke; subset invariant in `narrow_grant`;
per-site gate falsified 3×). Blast-radius probe past the grant layer remains
OWED.

### F2 — invite roster does not refresh after a successful invite (LOW)
The invite row lands in substrate immediately (receipted: `608bfdb7`, status
`pending`) but the roster does not re-fetch. The row appears only after a manual
reload. An operator would reasonably read the empty roster as failure and invite
again. Not a correctness bug — a legibility one, and a duplicate-action hazard.

### F3 — a revoked member still sees rendered panes (LOW) — NARROWED in run 2
After revocation, the guest's still-open session reloads `/workspace-settings`
and the pane chrome renders (Access / Billing / Usage / Autonomy / Danger Zone
nav). **Enforcement is sound and immediate** — every workspace API call in that
session returns 403, including
`GET /workspace/file?path=/workspace/governance/_autonomy.yaml`. So this is
chrome without data, not leaked access. But a revoked principal seeing an
apparently-working settings surface is misleading.

> **Run-2 correction**: the original wording of this finding also claimed the
> pane showed "Autonomy dial buttons" as if live. Driven directly in run 2, the
> dials are inside a `<fieldset disabled>` under a read-only banner. That half
> of F3 is WITHDRAWN — see the run-2 correction section.

## Thesis half 4 (GrantGate coverage) — SUPERSEDED by the run-2 correction

Confirmed from the run: the member was presented with `Narrow access`, `Set
spend cap…`, `Revoke…` on their own row. Pre-fix, one of those (`narrow`) was
genuinely unenforced. Post-fix all are server-refused — but they are still
*offered* on the Members pane, so refusal is only discoverable after the click.
That remains the legibility gap half 4 names, and it argues for extending the
GrantGate treatment to the Members roster.

> **Run-2 correction**: this section originally also cited "an editable Autonomy
> dial" as evidence. That was a MISREAD of an a11y snapshot — the Autonomy pane
> IS gated (read-only banner + `<fieldset disabled>`). GrantGate's one call site
> demonstrably works. The open question is COVERAGE of other panes (the Members
> roster in particular), not whether the mechanism functions.

The earlier framing that this was "coverage, a design decision, not a bug" was
too generous *for `/narrow` specifically*: there it was an absent server gate,
not an illegible one. That server finding stands on its own receipts and is
unaffected by the correction above.

## What run 2 must cover

1. Steps 6, 7, 10, 11, 13 — the whole BILLING + ACCOUNT-door half.
2. **Re-run step 9 against the fix** — assert 403 where 200 was observed. The
   fix is gated and falsified but has NOT been exercised through a live member
   browser session.
3. The blast-radius probe owed by F1.
4. `revoke` called by a member (the second unguarded endpoint) — never probed
   live; now gated, still unexercised.

## Method notes worth keeping

- **Isolated browser contexts are mandatory.** Two principals in one context
  share cookies; the second login silently overwrites the first and every
  "member" observation is really the owner. `isolatedContext` per principal.
- **The DOM half genuinely cannot see this defect class.** Step 9's DOM
  observation ("the verbs are offered") is compatible with both a sound and an
  unsound server. Only the network receipt (`200` + the changed row) decided it.
  This is the ADR-501 lesson reproducing exactly one layer up.
- **Two dead receipts were found by executing them**, not by review: `user_id`
  on `member_state` (no such column) and an unpinned `status` on
  `principal_grants` (two rows for the live member — a destroyed active grant
  would have read as a pass). Criteria should be run against the DB once before
  being called authority.

---

# RUN 2 — 2026-07-31, after the fix (API deploy `fcd5022`, status `live`)

Same instrument, same rig pair, same isolated contexts. Ran the 5 unrun steps,
re-tested step 9 against the fix, and completed the partial render steps.

## Step 9 re-test — the fix HOLDS through a live member session

Identical click path to run 1: member → own row → Manage → Narrow access → add
`governance/` → Apply.

| | run 1 (pre-fix) | run 2 (post-fix) |
|---|---|---|
| grant after | `{operation/,governance/}` | **all axes NULL — unchanged** |

The escalation is refused. This is the receipt that matters: the gate was
falsified in-test, but until now it had never been exercised by a real member
browser session, which is the only thing that closes the ADR-501 defect class.

**F4 (LOW, new): the refusal is SILENT.** No error surfaces to the member — the
dialog's buttons simply go disabled and nothing else happens. Enforcement is
correct; the operator gets no explanation. Same shape as F2/F3: yarnnn refuses
correctly but does not *say* it refused.

## Steps closed in run 2

| # | step | verdict |
|---|---|---|
| 6 | member-billing-shows-no-raw-wallet | **PASS** |
| 7 | member-account-door-renders | **PASS** |
| 10 | member-cannot-clear-workspace-server-side | **PASS** (see caveat) |
| 11 | member-notification-prefs-round-trip | **PASS** |
| 13 | billing-checkout-stops-at-handoff | **PASS** |
| 4 | owner-renders-all-workspace-panes | **PASS** (completed) |
| 5 | member-renders-workspace-panes | **PASS** (completed) |

**Step 6** — the member's Billing pane shows NO raw wallet, no top-up, no plan
controls. Instead: *"Billing … is managed by the workspace owner"* and *"Plan
changes, seats, and top-ups are the owner's verbs."* Usage pane likewise:
*"This workspace's balance is managed by its owner."* This is the ADR-503
pattern done right — a read-only EXPLANATION, not a disabled control.

**Step 7** — the account door renders the member's OWN stats (all 0, correct:
they own nothing) and correctly delegates workspace-clear out to the workspace
door with honest copy: *"affects every member's work, so it lives with the
workspace."*

**Step 10 — CAVEAT ON METHOD.** Both clear buttons are disabled with the exact
`can_clear` copy, plus a multi-principal warning (*"This workspace has 1 other
member"*). Server enforcement was verified two ways: both destructive routes
(`DELETE /account/work-history`, `DELETE /account/workspace`) call
`_require_workspace_clear_authority`, and `has_workspace_clear_authority`
evaluated against the LIVE grants returns `True` for the owner and `False` for
the member. **It was NOT verified by a live member HTTP call** — the attempt
returned 401 (unauthenticated probe), which proves nothing, and the bearer
could not be extracted without cookie-reading that tooling policy refuses.
Recorded as verified-by-code-plus-live-grant-data, which is weaker than the
other steps in this pass. Do not upgrade this to "probed" in a later summary.

**Step 11** — `member_state` absent → present, correctly scoped to `bf5b25a9`,
both writes landed (`delivery_email: false`, `witness_email: "all"`), and the
value SURVIVED a reload (not an optimistic echo). Restored to absent. This is
the receipt run 1's manifest could not have produced — it queried a `user_id`
column that does not exist.

**Step 13** — boundary receipt: `yarnnn.lemonsqueezy.com/checkout`, title
*"yarnnn - Usage Top Up - Checkout"*, $5.00 carried through. Stopped there; no
payment details entered.

## CORRECTION to run 1 — F3 was partly wrong, and so was the half-4 framing

Run 1 reported the member's Autonomy pane as rendering "editable dial buttons".
**That was a misread.** Driven directly in run 2, the member's Autonomy pane
shows:

> *"Read-only — your access to this workspace doesn't include writing the
> grant."*

…with the body wrapped in a `<fieldset disabled>` — dials visible but inert to
both pointer and keyboard. **GrantGate is working exactly as designed.**

The error was reading an accessibility snapshot, which lists `<button>`
descendants of a disabled fieldset without surfacing the disabled state, and
concluding "editable". The lesson: an a11y snapshot is not a substitute for
querying the actual DOM state of a control before calling it live.

Consequences for the record:
- **F3 is narrowed.** A revoked member seeing pane chrome stands (that was
  observed via network 403s, which are unambiguous). But "the member had an
  editable Autonomy dial" is WITHDRAWN.
- **Thesis half 4 is materially better than run 1 claimed.** The single
  GrantGate call site (`SystemAgentPanes.tsx:109`) demonstrably works: correct
  banner, correct disabling, grant-derived not role-derived. The open question
  is COVERAGE of other panes, not whether the mechanism functions.
- Run 1's line "on `/narrow` it was an absent gate, not an illegible one"
  remains true and is unaffected — that was a server finding with its own
  receipts.

`covers()` verified against the real `write_regions`: member `covers('governance/')`
= false, owner = true. The documented fail-open on an unresolved grant is
legibility-only; the server gate is enforcement.

## Final state vs baseline

| metric | baseline | final |
|---|---|---|
| rig active grants | 1 | 1 |
| rig `workspace_files` | 0 | 0 |
| guest `notification_prefs` rows | 0 | 0 |
| live ws seulkim88 active grant | 1 | 1 (untouched) |
| live ws testacct invites | 0 | 0 |

**Live-workspace file count moved 191 → 194 and this pass did NOT cause it.**
The three rows are `/workspace/operation/ir-deck-v3/*` created at 02:24Z —
concurrent operator work, not a pass artifact. Every write this pass made was
receipted against `bf5b25a9`. Noted rather than silently absorbed, because a
baseline that moves for an unexplained reason is exactly the thing a run record
must not hand-wave.

## Combined verdict: READY-WITH-FIXES

The two settings doors behave correctly for owner vs member across render,
write, ceiling, and lifecycle. The HIGH escalation is fixed and re-verified
live. What remains is a consistent LEGIBILITY class, not a correctness one:

- **F2** invite roster does not refresh after a successful invite (LOW)
- **F3** revoked member sees pane chrome; every API call 403s (LOW)
- **F4** the narrow refusal is silent — no message to the member (LOW)

All three are the same defect shape: **yarnnn enforces correctly and explains
poorly.** That is the right direction to fail, and it is the coherent next
piece of work.

Still OWED (unchanged): the F1 blast-radius probe (can an escalated member
actually WRITE a governance file), and a live member HTTP call against the
DangerZone endpoints per the step-10 caveat.

`mark-validated.sh web` — NOT invoked. Two of the thirteen steps rest on
code-reading rather than live probes, and the three legibility findings are
open. A lane marked green should mean a later session can trust it without
re-reading this file.
