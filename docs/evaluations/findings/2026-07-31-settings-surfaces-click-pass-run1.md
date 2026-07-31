# RUN RECORD 2026-07-31 — settings-surfaces click-pass, run 1 (rig pair)

**Instrument**: Claude in Chrome, two isolated browser contexts, live production
(`www.yarnnn.com` → `yarnnn-api.onrender.com`).
**Principals**: `kvkthecreator@yarnnn.com` (owner) / `testacct@yarnnn.com`
(cold guest → invited → member → revoked).
**Workspace**: `bf5b25a9` (kvk-yarnnn rig, disposable).
**Manifest**: `docs/evaluations/eval-suites/settings-surfaces-click-pass.yaml`

**Verdict: NOT-READY** — one HIGH escalation (now fixed), two legibility
defects, and **5 of 13 steps not run**. This is run 1 of the pass, not a
sign-off. `mark-validated.sh web` was deliberately NOT invoked.

---

## Baseline / final state (both receipted)

| metric | baseline | final |
|---|---|---|
| rig active grants | 1 | 1 |
| rig `workspace_files` | 0 | 0 |
| guest active grants anywhere | 0 | 0 |
| live ws `d5b9029b` files | 191 | 191 |
| live ws seulkim88 active grant | 1 | 1 |

The live workspace was never a subject and is provably untouched.

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

### F3 — a revoked member still sees rendered panes (LOW)
After revocation, the guest's still-open session reloads `/workspace-settings`
and the pane chrome renders (Access / Billing / Usage / Autonomy / Danger Zone
nav, Autonomy dial buttons). **Enforcement is sound and immediate** — every
workspace API call in that session returns 403, including
`GET /workspace/file?path=/workspace/governance/_autonomy.yaml`. So this is
chrome without data, not leaked access. But a revoked principal seeing an
apparently-working settings surface is misleading.

## Thesis half 4 (GrantGate coverage) — recorded, unresolved

Confirmed from the run: the member was presented with `Narrow access`, `Set
spend cap…`, `Revoke…` on their own row, and with an editable Autonomy dial.
Pre-fix, one of those (`narrow`) was genuinely unenforced. Post-fix all are
server-refused — but they are still *offered*, so refusal is only discoverable
after the click. That is precisely the legibility gap half 4 names, and it is
now the strongest argument for widening GrantGate coverage beyond its single
call site (`SystemAgentPanes.tsx:109`).

The earlier framing that this was "coverage, a design decision, not a bug" was
too generous: on `/narrow` it was an absent gate, not an illegible one.

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
