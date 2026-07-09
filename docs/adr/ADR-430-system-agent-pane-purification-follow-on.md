# ADR-430 — System Agent Pane Purification Follow-On (Autonomy · Budget · Activity)

> **Status**: **Accepted** (2026-07-09, operator-ruled from a four-pane audit). FE-facing purification: the three live System Agent panes are trimmed to what the current cost/witness canon says the steward's door should show. No schema, no gate-code, no migration — this changes what the operator SEES + EDITS, not what the kernel enforces.
> **Date**: 2026-07-09
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimension**: Channel (Axiom 6 — what the system agent's door surfaces) + Purpose (Axiom 3 — the witness dial vs the permission grant, which the "never auto-execute" list conflated)
> **Relates to**: ADR-426 (the Freddie System Agent door — the surface this trims), ADR-418 (the prior purification pass — kept Autonomy · Budget · Activity as Freddie's real surface; this continues that pass into the pane CONTENTS), ADR-405 (the witness dial — permission=grant, autonomy=witness-timing; the split the never-auto list violated), ADR-320/366 (topology lock — already hard-stops locked-root writes, making the never-auto `path:` form redundant), ADR-391 (budget/balance/three-layer cost model — allocation is the principal's dial, balance is not an agent concern), ADR-396 (Type-B pricing — "dollar amounts are NOT shown to the user"), ADR-416 (workspace = billing unit — Billing/Usage live on Workspace Settings, not an agent dial), ADR-380 D3 (harness honesty — Freddie is Rung-1; "operation" framing is a Rung-2 hired-agent concept), ADR-410 D4 ("Reviewer" banned as an operator-facing string), ADR-415 (Activity = the singular "what happened" surface — the collision the Freddie Activity pane's label invites)
> **Amends**: ADR-338 D4.2 (the operator-facing `never_auto` editor is retired — the field stays a dormant backend safety hook, no longer an operator surface), the BudgetCard content contract (allocation-only), the Freddie Activity pane label
> **Preserves**: the three modes' backend enforcement (`should_auto_apply` — untouched), the `_autonomy.yaml::never_auto` field + `_check_never_auto` (dormant, re-surfaceable), the Budget pane's PLACEMENT on Freddie (ADR-418 D1 — it is the allocation dial), the Freddie Activity endpoint + component (ADR-418 D1 read-only legibility)

---

## 1. Context — a four-pane audit against current canon

The Freddie System Agent door (`/system-agent`, ADR-426) shows four panes:
About · Autonomy · Budget · Activity. An operator audit (2026-07-09) questioned
three of them against the cost/witness canon that has moved since the panes were
built. The findings, each with receipts:

**Autonomy.** The three modes (Manual/Bounded/Autonomous) ARE honestly enforced
— `should_auto_apply` (`api/services/review_policy.py`) branches on
`delegation` for both the capital gate and the substrate gate. But the pane also
carries a **"NEVER AUTO-EXECUTE"** editor (ADR-338 D4.2) whose headline example
is `path: constitution/`. That `path:` form is **redundant with the ADR-320/366
topology lock**: the gate hard-stops writes to locked roots
(`_is_path_locked_for_principal`, `permission.py`) *before* and *independent of*
the autonomy mode. ADR-405 D1/D2 ratified the two as separate axes — **permission
is the grant** (who may act on which region) vs **autonomy is the witness dial**
(when an act binds). A per-file "never auto-execute" override list on the
autonomy pane re-fuses the axis ADR-405 split, and asks the operator to
re-declare protection the grant layer already enforces. The one non-redundant
form — an action-type hold (e.g. `retraction`) — is a bundle-authored capital
*floor* that belongs in a hired agent's shipped `agents/{slug}/_autonomy.yaml`,
not an operator editor on the workspace file; and at Rung-1 (Freddie takes no
consequential external action, ADR-380 D3) it has nothing to hold back.

**Budget.** The pane's PLACEMENT is canon-correct — ADR-418 D1 kept Budget as
one of Freddie's two legitimate operator-tunable dials (the `_budget.yaml`
allocation, ADR-414 D2; ADR-391 D3 homes allocation on the principal's pane).
But the pane CONTENT carries two out-of-scope things: (a) a **dollar
utilization bar** ("$17.63 of $50 used · $2.16/day burn") reading the metering
ledger — which **violates ADR-396: "dollar amounts are NOT shown to the user"**
(the sibling `UsagePaneBody` already obeys this, showing "% used", never
`.toFixed(2)`); and (b) a **"Balance & billing" link** deep-linking to
Workspace-Settings billing — Layer ① balance, which ADR-391 D3 calls "not an
agent concern" and ADR-416 homed on the workspace door. The header label
**"Operation budget" / "this operation may spend"** is also a mislabel: Freddie
is the Altitude-1 steward, not "the operation" — ADR-416 §4 explicitly retired
the "operation" frame for these dials as "no longer fitting."

**Activity.** This one is defensible. The Freddie Activity pane reads a
*different* endpoint (`GET /api/agents/freddie/activity`) over *different*
substrate (judgment-mode recurrences + Freddie's runs + Freddie-originated
proposals) and answers a *different* question — "is my agent alive and behaving
as told?" (health · upcoming wakes · autonomous-action trail · recent runs) —
than the global Activity surface's "what happened across the workspace." ADR-418
D1 explicitly kept it as read-only legibility; DP29 (mirror-once) + ADR-367 D3
(tiered redundancy) sanction the co-existence. The only defect is that the
**label "Activity" collides** with the global Activity surface (inviting "isn't
this the same thing?"), and the pane's code carries **stale vocabulary**
("Reviewer supervision surface", `back-office.yaml`, ADR-251) — "Reviewer" is a
banned operator-facing string (ADR-410 D4).

## 2. Decisions

### D1 — Retire the operator-facing "NEVER AUTO-EXECUTE" editor
Remove `NeverAutoEditor` from `AutonomyCard` (full variant) and the
`setNeverAuto` plumbing from the `useAutonomy` content-shape. The Autonomy pane
becomes the three-mode dial alone (+ the bounded ceiling line). Rationale: the
`path:` form is redundant with the ADR-320/366 topology lock (a bypass-immune
DENY, already enforced independent of mode); the `action_type` form is a
bundle-authored capital floor, not an operator dial, and has nothing to gate at
Rung-1. Keeping the editor invites the operator to add guards that silently do
nothing (or, on a program workspace, land on a file/block the gate does not read
— see §3).

**The `_autonomy.yaml::never_auto` FIELD stays** — `_check_never_auto`
(`review_policy.py`) remains a live backend safety hook that bundles author into
their shipped `agents/{slug}/_autonomy.yaml`. It is removed as an *operator
surface*, not as a *mechanism*. Re-surfaceable if a Rung-2 need emerges.

### D2 — Budget pane → allocation-only
The Budget pane stays on Freddie's door (ADR-418 D1) but is trimmed to the
**allocation dial**: amount + window (writing `_budget.yaml`), plus a
**non-dollar** draw-down indicator (percent, honoring ADR-396). Removed: the
dollar utilization figures (`$X of $Y used`, `$Z left`, `$/day burn`, the
`$30/$50/$100/$200` dollar presets rendered as dollars) and the "Balance &
billing" link (balance is Layer ①, on the workspace door per ADR-416). The
header relabels from **"Operation budget"** to the **allocation/envelope**
framing (ADR-416 §4 / ADR-414 D6) — "this operation may spend" drops.

> **Draw-down legibility survives** (ADR-327 D8 — a budget is only honest if the
> operator can see it draw down) but is expressed as an **allowance %**, not a
> dollar meter. Amount presets remain (the operator must pick a dollar
> *envelope*) — declaring a budget is inherently a dollar act; ADR-396's rule is
> about not showing a running *spend* dollar meter, which is the utilization bar
> we remove, not the envelope the operator sets.

### D3 — Activity pane → relabel + de-stale
Keep the pane and its endpoint. Relabel it from **"Activity"** to **"Health"**
(its actual job — liveness + supervision of the one autonomous agent), ending
the collision with the global Activity surface. Strip the stale operator-facing
and comment vocabulary: "Reviewer" → "your agent" / "Freddie" (ADR-410 D4),
drop the `back-office.yaml` / ADR-251 lineage references that describe a retired
model.

### D4 — About unchanged
The About pane (ADR-426 amendment) is correct as-is.

## 3. Known deeper divergence — flagged, scoped OUT of this ADR

The audit surfaced a **load-bearing FE↔backend wiring divergence** larger than
the pane-content questions, which this ADR deliberately does NOT fix (it needs
its own discourse + test):

- **Per-agent home split (ADR-414 D6).** `load_autonomy` reads
  `agents/{slug}/_autonomy.yaml` FIRST when a hire grant exists
  (`resolve_judgment_home`), falling back to `governance/_autonomy.yaml` only
  with no hire. The FE (`autonomy.ts`) hardcodes `governance/_autonomy.yaml`.
  On a **hired-program** workspace, the pane's mode selector edits a file the
  gate ignores.
- **Two-class schema (ADR-408 D3).** Genesis seeds a `substrate:` block that
  governs the steward's file writes; the FE parser understands only `default:`/
  `domains:`, never `substrate:`. So the substrate-write autonomy is not
  editable from the pane.

**Why scoped out:** (a) it is orthogonal to "is the pane content right" — it is
"does the pane target the right file"; (b) it bites only on hired-program
workspaces (N=1 solo/steward workspaces have no hire → `governance/_autonomy.yaml`
IS the gate's file, byte-identical); (c) the fix (make the pane
judgment-home-aware + `substrate:`-aware) is a real feature with its own gate,
not a purification. **Tracked as a follow-on.** Removing the never-auto editor
(D1) *reduces* the divergence's blast radius (one fewer shadowed control).

## 4. What this is NOT

- **Not a gate change.** `should_auto_apply`, `_check_never_auto`,
  `_is_path_locked_for_principal` are untouched. The three modes enforce exactly
  as before; locked roots hard-stop exactly as before.
- **Not a Budget-pane removal.** The allocation dial is Freddie's, per ADR-418
  D1. Only the billing/dollar-usage content leaves.
- **Not an Activity-pane removal.** The supervision endpoint + view stay; only
  the label + stale strings change.
- **Not the per-agent-home wiring fix (§3)** — that is the named follow-on.

## 5. Consequences

- The Autonomy pane reads as one clean witness dial — the operator is no longer
  invited to re-declare grant-layer protection or add silently-shadowed guards.
- The Budget pane stops showing dollars (ADR-396 conformance) and stops
  re-importing workspace-billing onto an agent dial; it reads as the steward's
  allocation envelope.
- The Health (ex-Activity) pane stops colliding with the global Activity
  surface and drops banned vocabulary.
- A stale `review_policy.py` header (documents `never_auto` as ADR-261-deleted,
  contradicting the live `_check_never_auto`) is corrected in passing.

## 6. Gates

- FE typecheck (`tsc --noEmit`) clean.
- No backend gate touched — `test_adr293_governance_taxonomy` /
  `test_adr408_d3_steward_dial` (which exercise `_check_never_auto` +
  `should_auto_apply`) stay green (the field + function are untouched).
- CHANGELOG entry for the AutonomyCard/BudgetCard prompt-surface change.
