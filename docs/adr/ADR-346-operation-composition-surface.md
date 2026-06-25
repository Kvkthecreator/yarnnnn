# ADR-346 — The Operation Surface: a composition window for Decide · Read · Tune

**Status:** **Proposed (2026-06-19)** — surface + registry change. Implementation follows in the same arc.
**Preserved + extended by:** [ADR-370](ADR-370-context-surface-the-operations-boundary.md) (2026-06-25) — Notifications (this surface, renamed by ADR-349) **stays the operating-work composition** (To do · Activity · Schedule), NOT demoted. ADR-370 adds a *sibling* composition (Context: In · Out · Flow) over the operation's boundary. The narrative appears in both (Notifications → Activity, Context → Flow) as **deliberate tiered redundancy** — the macOS Control-Center/System-Settings principle (ADR-367 D3); same `FeedSurface` body, two mounts (ADR-340 D8), two distinct primary jobs (operate the work vs. understand the boundary).
**Date:** 2026-06-19
**Deciders:** KVK (operator) + Claude (collaborator)
**Dimensional classification:** **Channel** (Axiom 6) projected through **Purpose** (Axiom 3 — the operator's standing-loop acts). Extends FOUNDATIONS Derived Principle 29 (ADR-340).

> **Discourse base / forcing evidence:** the operator's own browser walk — the validation ADR-340 §5 reserved as *open* ("the operator's own browser walk… requires human eyes"). Walking the live cockpit, the operator reported: *"the surfaces and user controls on recurrences, attention, feed, activity are all scattered… it's extremely confusing to understand what I need to do where."* This ADR treats that report as the Stage-1 forcing evidence ADR-340 said it still needed, not as a violation of the model.

---

## 1. The problem — one concern, four surfaces, no home

A single operator concern — **operating my recurring work** (resolve what wants me · understand what just happened · tune the recurring work) — is physically fragmented across the cockpit:

| Operator act | Where it lives today | Control / read |
|---|---|---|
| **Resolve** what wants me | `/queue` (standalone window) | pending `action_proposals` approve/reject |
| **Understand** what just happened | `/feed` (standalone) **+** `/recurrence?pane=activity` (the Runs lens) | narrative timeline **+** execution-event ledger — *two surfaces for one question* |
| **Tune** the recurring work | `/recurrence` Schedule lens | pause / run-now / edit a recurrence |
| **Glance** at what wants me | the top-bar Attention bell | routes to three of the above, but **carries no controls** |

The Attention center was supposed to be the unifier (ADR-340 D3) — but it *routes only*. The moment the operator needs to **act** (approve a trade, pause a recurrence, read the full story), the bell bounces them to a different surface and they must reconstruct which one. The result is exactly the reported symptom: *"what do I do where?"*

**This is not a canon violation.** ADR-340 D2 (the act-table, lines 47–54) *already* names Decide / Read / Tune as kernel acts that **compositions carry**. But ADR-340 only built **one** composition — Home, serving the *Dwell* act (D6). Decide / Read / Tune were assigned to compositions on paper and left mounted on raw mirrors in practice. **This ADR builds the missing composition.**

## 2. The decision — a second composition window: `operation`

Add exactly one kernel surface: **`operation`** (working title "Operation"), a **composition window** (the second instance of the Composition-surface class, alongside Home). It is a `SettingsPaneShell`-shaped window with three grouped panes, one per operator act:

| Pane (`?pane=`) | Act (ADR-340 D2) | Body (reused, not rebuilt) | Escape hatch |
|---|---|---|---|
| **Resolve** (`resolve`) | Decide | the Queue proposal body (`QueueBody`, extracted from `/queue`) | "Open full Queue →" |
| **Understand** (`understand`) | Read | `FeedSurface` (the narrative) + the run ledger | "Open Feed / Runs →" |
| **Tune** (`tune`) | Tune (recurring work) | `RecurrenceList` + the Schedule/Runs lens toggle | "Open full Recurrence →" |

`operation` is **window-grade** (no `pane_of`), `register: application`, `launcher_tier: primary`, `archetype: dashboard`, `route: /operation`. It composes three substrates (`action_proposals` + `session_messages` + `_recurrences.yaml`/`execution_events`) — `substrate_paths: []` like every DB-backed composition.

### Why this is "compose few," not a fifth time-shaped read

The blur ADR-340 D3 named ("Queue / Feed / Activity / Recurrence blur because all four are time-shaped reads") is resolved correctly **only** by a composition that fronts them — not by adding a fifth peer mirror. `operation` is a *composition over* the mirrors, exactly as Home is a composition over its slots. It adds zero new substrate and owns no state.

## 3. D1 — Mirrors survive; the composition fronts them

**Queue, Feed, Recurrence, Activity are NOT deleted and NOT converted to `pane_of: "operation"`.** They remain complete, neutral mirror surfaces — the escape hatch, the `/proc` of the OS (ADR-340 D1, line 32: *"never deleted: they are the escape hatch"*).

This is the load-bearing distinction from ADR-340 P2 / ADR-341 (which *deleted* the five os-config windows and made them pure panes). That fold was correct **because those were config dials** — budget, autonomy, connectors — surfaces with no independent daily-loop value. Queue/Feed/Recurrence are a **different class**: mirrors of live operational substrate, each the complete escape-hatch view. ADR-340 D8 (line 151) settles the instinct to delete-for-dedup: *"'mirror once' governs substrate↔surface faithfulness, not launcher tile count."* The cost being optimized is **launcher breadth**, not surface count.

A mechanical asymmetry reinforces this: the os-config panes were leaf cards with no window-internal routing; Queue/Feed/Recurrence carry their own deep-link param state (`?task=`, `?pane=activity`, `?slug=`, `?agent=`). Collapsing them into `?pane=` of one window would force a nested-param scheme fighting the single-param `setSurfaceParams` model. The composition keeps each mirror's window intact and reuses its **body component**, not its routing.

**Rule:** each Operation pane mounts the mirror's body component and offers an "Open full ___ →" affordance via `foregroundSurface(...)`. One body, two mounts (the ADR-340 D8 `ActivityLog` precedent — *"one body, two mounts"*). Singular Implementation: `QueueBody` is extracted so `/queue` and `/operation?pane=resolve` share it; `FeedSurface` and `RecurrenceList` are already standalone.

## 4. D2 — Launcher re-sort: Operation is primary; Feed + Queue demote to Utilities

`operation` enters the **primary** launcher tier (the standing-loop "Workspace" group). With the composition now the default destination for operating work, the two mirrors it fronts demote out of primary prominence:

- **`feed`**: `primary` → `utilities`
- **`queue`**: `primary` → `utilities`
- **`recurrence`**: already `utilities` (unchanged)
- **`activity`**: already `search-only`, `pane_of: recurrence` (unchanged)

Result — at-rest **Workspace** (primary) group: **Home · Operation · Files**. The mirrors stay fully reachable (Utilities group + flat search), per D1; they simply stop being the *default* — *"the operator arrives by routing, not by remembering"* (ADR-340 D3, line 73, which already pre-reclassified Activity + Recurrence as Utilities; this ADR completes that reclassification for Feed + Queue now that a composition exists to front them).

This is the operator-experience inverse of the pre-ADR-340 launcher: the prominent rows are now **act-shaped compositions** (Home = Dwell, Operation = Decide/Read/Tune), not raw mirrors.

## 5. D3 — The Attention bell lands on the composition

The Attention center (`AttentionCenter.tsx`, ADR-340 D3) repoints from the bare mirrors to the Operation panes — so the bell finally lands the operator somewhere they can **act**, closing the "routes but can't resolve" gap:

- proposal rows + footer → `operation?pane=resolve` (was `foregroundSurface('queue')`)
- material-event rows → `operation?pane=understand` (was `foregroundSurface('feed')`)
- low-balance warning → unchanged (`/settings?pane=billing`)

The bell's binding discipline is untouched — still derived, never stored, no `notifications` table (ADR-340 D3 / DP29). Only the routing *target* changes from mirror to composition, which is precisely what *"compositions foreground; mirrors are reachable from compositions, never the default"* (line 37) prescribes.

### 5a. Amendment (2026-06-19) — the bell is the glanceable head of Operation: a temporal triad, one vocabulary

Operator feedback after the initial label pass: the bell was framed as "what needs you" but is really **what happened · what needs me · what's coming up** — a *temporal* triad (past · present · future) — and it spoke a different language than the surface it lands on. Two corrections, no new state:

- **The bell and the Operation surface are one object at two zooms**, and now share one vocabulary — the same operator words on both: **To do** (present, `?pane=resolve`) · **Activity** (past, `?pane=understand`) · **Coming up** (future, `?pane=tune`). The bell's section headers == the Operation pane labels.
- **The future limb was missing and is now built.** "Coming up" derives the next scheduled fires from each recurrence's `next_run_at` (future-only, non-paused, soonest-first) — a pure derivation over `api.recurrences.list` (the field already rides every recurrence row), so ADR-340 D3's *derived-never-stored* invariant holds with **zero new state**. Rows deep-link to the Schedule pane.
- **The badge stays demand-only** (`proposals + unseen Activity`). "Coming up" is *reference, not a demand* — a scheduled fire is not something that needs you — so it does **not** inflate the urgent count. The dropdown is the full glance; the badge is the demand subset.
- **Operator-vocabulary partition** (the operator's deeper question — "what happens to wakes/recurrence?"): the bell speaks operator words only (To do · Activity · Coming up · Schedule). The engine words (*wake · recurrence · invocation · proposal*) stay in substrate + ADRs + the run-ledger detail (the escape hatch). "Coming up" rows show the recurrence's operator-facing **title**, never "next wake."

Header stays **"Attention"** (= worth attending to; the three limbs clarify the breadth — it is not only "demands you"). The Operation pane labels moved from the abstract *Resolve/Understand/Tune* to plain *To do/Activity/Schedule* in the same pass (the ADR-340 D2 act identities Decide/Read/Tune + the pane KEYS are unchanged — labels only). Gate: `test_adr340_p1_attention` (+6 assertions for the temporal triad), 33/33; `test_adr346` 36/36 (asserts pane keys + bodies, not labels — unaffected).

## 6. What this does NOT change

- **The mirrors** — Queue/Feed/Recurrence/Activity keep identical bodies, routes, and deep-link params. They lose only primary-launcher prominence (Feed/Queue).
- **The permission gate** (ADR-307) — one gate, one queue; Resolve pane mounts the same Queue body over the same `action_proposals`.
- **The Attention center's derivation** (ADR-340 D3 / DP29) — derived-never-stored, unchanged; only routing targets move.
- **The window-manager machinery** — `foregroundSurface`/`setSurfaceParams`/viewport+dock pane-filtering/launcher tier-grouping/`composition_resolver` are all already generic and data-driven from the registry. `operation` inherits them for free; no shell changes.
- **No new noun above "program"** (ADR-340 line 41) — Operation is a kernel-owned act-shaped composition, program-weighted exactly as Home's slots are. Programs may later weight the Operation panes; the kernel owns the slots.

## 7. Relationship to the ADR-345 / heartbeat arc (forward pointer, not a dependency)

The concurrent ADR-345 (Expected Output) + the [operation-heartbeat discourse](../analysis/operation-heartbeat-and-autonomy-as-witness-2026-06-19.md) establish, at the *concept* layer, that an operation has a **Rhythm** (rate of attention), an **Expected Output** (what it owes), and a **Witness dial** (which beats surface) — and that these have no unified operator-legible home. The Operation surface is the natural **read/tune home** for that triad once it lands: a future pane (or a header band on the Dwell/Home composition) can surface "Rhythm: N wakes/day · on budget · owes 2 essays/mo · 0 shipped this cycle." **This ADR does not build that** — it builds the Decide/Read/Tune composition now; the heartbeat band is a clean follow-on once ADR-345 ratifies its `_expected_output.yaml` referent. Flagged so the surface is designed to *receive* it, not to require it.

## 8. Implementation scope

Registry (backend source of truth) → TS mirror → body extraction → composition page → registry mount → bell repoint → gates.

1. `api/services/kernel_surfaces.py` — add `operation` window entry; demote `feed` + `queue` `launcher_tier` to `utilities`.
2. `web/types/desk.ts` — add `'operation'` to `KernelSurfaceSlug` + `KERNEL_SURFACE_SLUGS`.
3. `web/lib/compositor/types.ts` — extend `launcher_tier` union with `'workspace-config' | 'system-config'` (rides along; fixes pre-existing drift).
4. `web/components/queue/QueueBody.tsx` (NEW) — extract the proposal body from `/queue/page.tsx`; rewire the mirror to mount it.
5. `web/app/(authenticated)/operation/page.tsx` (NEW) — mounts `SettingsPaneShell` with Resolve/Understand/Tune panes reusing `QueueBody`, `FeedSurface`, `RecurrenceList`; each pane carries an "Open full ___ →" escape hatch.
6. `web/components/shell/SurfaceRegistry.tsx` — register `operation: OperationPage`.
7. `web/components/shell/AttentionCenter.tsx` — repoint rows + footer to `operation?pane=resolve|understand`.
8. Gates: update `api/test_adr340_p3_launcher.py` (primary set → `{home, operation, files}`; feed/queue now utilities); add `api/test_adr346_operation_composition.py` (window-grade, three panes, shared `QueueBody` one-body-two-mounts, mirrors survive — `/queue`,`/feed`,`/recurrence` NOT redirect stubs); verify `api/test_adr338_surface_registry_parity.py` + `api/test_adr297_phase1.py` stay green.

No redirect stubs created — the mirrors stay live (contrast ADR-340 P2, which stubbed *because* it deleted). `useSurfacePreferences`, `SurfaceViewport`, `TopBarSurface`, `Launcher`, `composition_resolver` need no edits.

## 9. Consequences

**Positive:**
- One door for operating recurring work — the System-Settings consolidation pattern applied to the operational mirrors, resolving the operator's reported "what do I do where."
- The Attention bell becomes actionable (lands on a pane that carries controls), closing the route-but-can't-resolve gap.
- Completes ADR-340 D2 — three of the four named acts (Decide/Read/Tune) gain their composition; only Dwell (Home) existed before.
- Zero new substrate, zero new state, zero shell-machinery changes — the ADR-340/341 generality pays off.

**Costs / risks:**
- A second composition class instance to maintain; the "one body, two mounts" rule must hold (gate-enforced) or bodies drift.
- Launcher muscle-memory: operators who bookmarked `/feed`/`/queue` keep them (mirrors survive) but find them demoted in the launcher. Acceptable — searchable + Utilities-grouped.
- The Understand pane unifies two reads (narrative + run-ledger) that ADR-340 D8 had kept as two lenses on Recurrence; the pane should present them as one act without re-introducing a third copy of `ActivityLog` (reuse the shared body).

## 10. Validation

Stage-1 (this ADR's forcing evidence) is the operator's own report. Closing validation: the operator's browser re-walk against the criterion *"can I tell, from one surface, what wants me / what happened / what to tune — without hunting?"* Plus the gate suite (§8). The heartbeat band (§7) is explicitly **out of scope** and validated separately when ADR-345 lands.
