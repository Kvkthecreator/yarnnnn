# ADR-296 v2 Implementation Scope

> **Status**: Planning artifact, Hat-A canon
> **Date**: 2026-05-20
> **Authors**: KVK, Claude
> **Scope**: Full implementation plan for [ADR-296 v2](../adr/ADR-296-continuous-judgment-cycle.md) — wake-source generalization, evaluation funnel, hook substrate, FireInvocation re-scope, canon rewrite, bundle migration. Singular Implementation discipline: every change lands atomically; legacy paths delete; no dual shapes survive the migration.
> **Companion**: [`adr296-canon-and-runtime-audit.md`](adr296-canon-and-runtime-audit.md) (the audit that produced this scope), [ADR-296 v2 thesis](../adr/ADR-296-continuous-judgment-cycle.md).

---

## Commit shape commitment

**Atomic-large PR, following the ADR-261 precedent.** One PR, one squash commit to `main`, full migration including kernel + canon + bundles. Phased landing rejected — intermediate states would carry dual wake mechanisms in violation of Singular Implementation discipline.

The PR is reviewable as a sequence of clean atomic file changes; what doesn't split is *deployment*. Code, canon, bundles, and observation-discipline updates all land in the same merge.

Estimated net LOC delta: **net negative**. The ADR-261 precedent (−8.3K LOC) is a reasonable anchor — wake-source generalization deletes more dispatch branches than it adds, FireInvocation re-scope is mostly deletion, prompt cleanups are deletion, alpha-trader chain-collapse deletes inert recurrence.

---

## The three architectural commitments (ADR-296 v2 D1 + D2 + D3) and their kernel surfaces

### D1 — Wake is event-driven and evaluation-gated

**Kernel surface**: a new module `services/wake.py` is the singular invocation gateway. Every wake source submits wake-proposals; the funnel evaluates; full cycle fires only on escalation. No bypass paths exist in code after this PR.

### D2 — Recurrences are cron-tick wake source's configuration. Hooks are substrate-event wake source's configuration. Both equal in shape.

**Kernel surface**: `services/wake_sources/` package with one module per wake source. Each module reads its declaration substrate and submits wake-proposals.

### D3 — Reviewer's authority is over cadence + standing intent. Not self-invocation.

**Kernel surface**: `FireInvocation` removed from `REVIEWER_PRIMITIVES`; the Reviewer's `directives` mechanism (ADR-253 D2) dissolves. Reviewer's mid-loop primitives shrink to {`Schedule`, `WriteFile`, `ProposeAction`, `DispatchSpecialist`, `Clarify`, `ReturnVerdict`, reads}.

---

## Concrete current-state surface inventory

Captured from grep-pass 2026-05-20. Every code site that touches the wake mechanism today.

### Reviewer invocation call sites

| File | Line | What | Disposition under v2 |
|---|---|---|---|
| `routes/feed.py` | 1214 | `invoke_reviewer(trigger="addressed", ...)` for operator chat | Migrate to `services.wake.submit_wake_proposal(source="addressed", ...)` |
| `services/invocation_dispatcher.py` | 344 | `invoke_reviewer(trigger="reactive", ...)` for cron-fired judgment recurrence | Migrate to wake-source pattern; cron-tick wake source submits proposals, dispatcher's role becomes funnel-gated full-cycle invoker |
| `services/review_proposal_dispatch.py` | 384 | `invoke_reviewer(trigger="reactive", ...)` for proposal arrival | Migrate to `services.wake.submit_wake_proposal(source="proposal_arrival", ...)` |
| `services/invocation_dispatcher.py` | full file | `dispatch(recurrence, ...)` — wraps both judgment + mechanical recurrence dispatch | Split: mechanical-mode → `services/wake_sources/cron_tick.py::dispatch_mechanical`; judgment-mode → submits wake-proposal via wake.py |

### `services/invocation_dispatcher.dispatch(...)` callers (Mechanism A entry points)

| File | Line | Disposition |
|---|---|---|
| `jobs/unified_scheduler.py` | 141 | Becomes `services/wake_sources/cron_tick.py::walk_due` — submits wake-proposals to funnel |
| `services/primitives/fire_invocation.py` | 71 | Chat-side handler; submits wake-proposal with `source="manual_fire"` |
| `routes/recurrences.py` | 447 | Operator-frontend manual fire endpoint; same `source="manual_fire"` |
| `routes/admin.py` | 843 | Admin debug endpoint; same |
| `routes/agents.py` | 1201 | Agent route fire; same |
| `scripts/alpha_ops/manual_fire.py` | 40 | Developer-side override; same |
| `services/operator_proxy/scenarios.py` | 276 | Hat-B scenario harness; same |
| `services/review_proposal_dispatch.py` | 674 | **Reviewer-directives `fire_invocation` action** — DELETED (D3 — Reviewer no longer self-invokes via directives) |

### FireInvocation primitive surface

| File | Lines | Disposition |
|---|---|---|
| `services/primitives/fire_invocation.py` | full | Survives. Handler migrates from direct `dispatch(...)` call to `services.wake.submit_wake_proposal(source="manual_fire", ...)`. |
| `services/primitives/registry.py` | 33 (import), 257 (CHAT_PRIMITIVES), 313 (HEADLESS_PRIMITIVES — verify if removable), 386 (REVIEWER_PRIMITIVES), 427 (dispatch map) | **REVIEWER_PRIMITIVES entry DELETED.** Chat entry survives. Headless entry verified+kept if any current caller; deleted if not. Dispatch map entry survives. |
| `agents/reviewer_agent.py` | 781 (persona-frame "FireInvocation the relevant recurrence to commission fresh substrate") | DELETED. Replaced by cadence-authority guidance: "When upstream substrate is stale, author your next cycle via Schedule for after the mechanical mirror's next fire, or write standing intent to declare interest in the substrate transition." |
| `agents/reviewer_agent.py` | 1405 (classify mirror-refresh FireInvocations) | DELETED — classification logic dissolves with the directives mechanism |
| `agents/reviewer_agent_compat.py` | 43-64 (`action=fire_invocation` directive shim) | **ENTIRE FILE candidate for DELETION** — verify if directives compat is used anywhere else; if not, delete file |
| `agents/cockpit_awareness.py` | 197, 208 (Reviewer prompt frame teaching FireInvocation) | DELETED + replaced with cadence-authority teaching |
| `agents/prompts/tools_core.py` | 455-464 (shared primitive prompt block) | **SPLIT**: FireInvocation docs move from `tools_core` (shared) to a chat-only prompt module. Reviewer's prompt assembly stops including the FireInvocation block. |
| `agents/prompts/chat/{workspace,task_scope,entity,onboarding,behaviors}.py` | various | All chat-side mentions survive unchanged. |
| `services/reviewer_chat_surfacing.py` | 189-308 (`_is_mechanical_fire_invocation`, suppression logic) | **DELETED** — Reviewer no longer fires mirrors via FireInvocation; mechanical mirrors are kernel-dispatched from cron-tick wake source, no narration-suppression logic needed |
| `services/execution_router.py` | 76-111 (FireInvocation regex dispatch for chat) | Survives — chat-side, this is operator's deterministic "fire X now" shortcut |
| `services/review_proposal_dispatch.py` | 647-683 (Reviewer `directives` mechanism with `fire_invocation` / `write_file` / `clarify` actions) | **`fire_invocation` action DELETED.** `write_file` and `clarify` survive if still used; verify. Directives mechanism shrinks or dissolves entirely per D3. |
| `services/orchestration.py` | 651 (comment about `directive: fire_invocation(slug=...)`) | DELETED |
| `services/primitives/infer_workspace.py` | 11, 32, 82 (mentions of "follow-up ManageAgent + FireInvocation calls") | Updated to reflect new wake-source pattern |
| `services/primitives/__init__.py` | 12 (ManageRecurrence + FireInvocation pairing comment) | Updated |
| `scripts/oneshot/phaseB_unify_recurrences.py` | 153 (alpha-trader migration script) | Historical migration script — leave as historical artifact OR delete if no longer load-bearing |

### `_recurrences.yaml` consumers

| File | Disposition |
|---|---|
| `services/recurrence.py` | Renames its role: this is now the cron-tick wake source's configuration parser, not the universal recurrence registry. File survives in place; docstring updated. |
| `services/scheduling.py` | Same: cron-tick wake source's scheduling math. Survives in place; docstring updated. |
| `services/invocation_dispatcher.py` | Split into wake-source modules; the file as a whole shrinks or dissolves into `services/wake_sources/cron_tick.py`. |
| `routes/recurrences.py` | URL `/api/recurrences/*` survives as operator-facing CRUD on the cron-tick wake source's configuration. No URL rename needed at this PR. |

### Bundle reference workspaces

| Bundle | What changes |
|---|---|
| `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` | `signal-evaluation` cycle absorbs `trade-proposal` logic inline (signal-evaluation's prompt directs the Reviewer to ProposeAction when conditions match). `trade-proposal` recurrence entry deleted. |
| `docs/programs/alpha-trader/reference-workspace/_hooks.yaml` (NEW) | Empty at activation, ready for operator/Reviewer to author substrate-event interests as they emerge. |
| `docs/programs/alpha-trader/reference-workspace/review/principles.md` | Delete "Commission substrate via FireInvocation when upstream substrate is missing AND you would otherwise stand down waiting for it" clauses (lines 21-23, 179). Replace with cadence-authoring + standing-intent-hook guidance. |
| `docs/programs/alpha-author/reference-workspace/_recurrences.yaml` | `pre-ship-audit` recurrence DELETED. |
| `docs/programs/alpha-author/reference-workspace/_hooks.yaml` (NEW) | Ships with `pre-ship-audit` substrate-event hook declaration: when `/workspace/context/authored/*/profile.md` frontmatter `status` transitions to `ready_for_review`, propose wake with the existing pre-ship-audit prompt. |
| `docs/programs/alpha-author/reference-workspace/specs/pre-ship-check.md` | Trigger section rewritten: dispatched via substrate-event hook on draft state change. No more wrong-shaped "fires when operator marks a draft ready_for_review" prose ambiguity. |
| `docs/programs/alpha-author/reference-workspace/review/principles.md` | Verify no FireInvocation references; remove if found. |

---

## New kernel modules

### `services/wake.py` — the wake-proposal layer

```
Module: services/wake.py
Purpose: singular invocation gateway. All wake sources submit proposals here.

API:
  submit_wake_proposal(
      source: WakeSource,
      user_id: str,
      payload: dict,
  ) -> WakeOutcome

  Where:
    WakeSource = Literal["cron_tick", "addressed", "proposal_arrival",
                          "substrate_event", "manual_fire"]
    payload = source-specific dict (recurrence ref, operator message,
              proposal_id, substrate event metadata, manual-fire slug+context)
    WakeOutcome = TypedDict with funnel decision + (if escalated)
                  reviewer_output

Internal flow:
  1. Build wake-context (worldview-event signal + budget state +
     operator interest + Reviewer interest + recent-fire history).
  2. Call wake_evaluation.evaluate(wake_context) → Tier 1 decision.
  3. If T1 returns "tier-2", call Tier 2 cheap Haiku.
  4. If escalate, invoke full Reviewer cycle via existing invoke_reviewer
     (now called exclusively from this module).
  5. Record funnel decision in execution_events (new column: funnel_decision).
```

### `services/wake_evaluation.py` — the funnel

```
Module: services/wake_evaluation.py
Purpose: Tier 1 (deterministic) + Tier 2 (cheap Haiku) gating.

API:
  evaluate(wake_context: WakeContext) -> EvaluationDecision

  Where:
    WakeContext = TypedDict with wake-source-agnostic signals:
      - source, payload
      - budget_state (from token_budget)
      - operator_interest (from _preferences.yaml + AUTONOMY.md)
      - reviewer_interest (from standing_intent.md frontmatter)
      - recent_fires (last N execution_events for this user)
      - worldview_event (what changed, since when)
    EvaluationDecision = Literal["skip", "tier_2", "escalate"]

Tier 1 (deterministic, no LLM):
  - Operator-addressed → ALWAYS "escalate" (operator presence is wake-warrant)
  - Proposal-arrival → ALWAYS "escalate" (proposal creation is wake-warrant)
  - Manual-fire → ALWAYS "escalate" (operator explicit assertion)
  - Cron-tick judgment recurrence + fresh + budget OK + not in cooldown → "escalate"
  - Cron-tick judgment recurrence + ambiguous freshness → "tier_2"
  - Cron-tick judgment recurrence + obviously not warranted (no signal, recent fire, budget tight) → "skip"
  - Substrate-event matching Reviewer interest hint → "escalate"
  - Substrate-event matching operator interest declaration → "escalate"
  - Substrate-event not matching any declared interest → "skip"

Tier 2 (Haiku, ~$0.001/call):
  - Minimal envelope: MANDATE + AUTONOMY + standing_intent + wake-event summary + operating context
  - Prompt: "Given this wake-event and your standing intent, does this moment
    warrant your full attention now? Respond with one of: wait | observe | escalate."
  - Cost telemetry: new caller "reviewer-tier-2-idle-tick"
```

### `services/wake_sources/` package

```
Module: services/wake_sources/__init__.py — package marker
Module: services/wake_sources/cron_tick.py
  - walk_due(client, now) → submit wake-proposals for due recurrences
  - dispatch_mechanical(recurrence) → mechanical-mode bypass (no Reviewer)
Module: services/wake_sources/addressed.py
  - submit_for_addressed_turn(client, user_id, message) → wake-proposal
Module: services/wake_sources/proposal_arrival.py
  - submit_for_proposal(client, user_id, proposal_row) → wake-proposal
Module: services/wake_sources/substrate_event.py
  - walk_hooks(client, user_id) → walk /workspace/_hooks.yaml + revisions
  - submit_for_substrate_change(client, user_id, hook_match) → wake-proposal
Module: services/wake_sources/manual_fire.py
  - submit_for_manual_fire(client, user_id, slug, context) → wake-proposal
```

### `_hooks.yaml` substrate

```yaml
# /workspace/_hooks.yaml — substrate-event wake source declarations
#
# Author: operator (via YARNNN chat) or Reviewer (mid-loop via Schedule-equivalent
# extension). Every declaration carries ADR-209 authored_by attribution via the
# revision chain.
#
# Each entry declares: a substrate transition that warrants a wake proposal.
# When the wake source detects the transition, it submits a wake-proposal to
# the funnel with the hook's `prompt` as the addressed-equivalent envelope.

hooks:
  - slug: pre-ship-audit
    event: substrate_change
    path_match: /workspace/context/authored/*/profile.md
    field_change: { status: ready_for_review }
    prompt: |
      A draft was just marked ready_for_review. Read the draft at
      /workspace/context/authored/{piece-slug}/content.md and audit per
      voice + continuity + anti-slop + editorial criteria. ...
```

The schema is intentionally compact. `event` is an enum (`substrate_change` for now; future event types extend the kernel side); `path_match` is a glob; `field_change` is a dict of frontmatter key → expected new value. The Reviewer or operator authors entries via a new `ManageHook` primitive (CHAT_PRIMITIVES + REVIEWER_PRIMITIVES — Reviewer authors hooks as part of its standing-intent authority per D3).

### `services/primitives/manage_hook.py` (NEW)

Mirror of `services/primitives/schedule.py` shape, operating on `/workspace/_hooks.yaml`. Actions: `create | update | pause | resume | archive`. Reviewer + operator both call it. Reviewer's hook authoring is part of cadence + standing intent authority per D3.

---

## Deletions per Singular Implementation discipline

The following code paths DELETE in this PR (no dual-shape survives):

| Path | Why |
|---|---|
| `services/invocation_dispatcher.py::dispatch` direct callers (8 sites) | All migrate to `services.wake.submit_wake_proposal` |
| Direct `invoke_reviewer` calls outside `services/wake.py` | Funnel is singular; nothing bypasses |
| Reviewer-directives `fire_invocation` action in `review_proposal_dispatch.py` | D3: Reviewer no longer self-invokes via directives |
| `agents/reviewer_agent_compat.py` if directives mechanism dissolves entirely | Verify compat is used nowhere else; if so, delete file |
| FireInvocation entry in `REVIEWER_PRIMITIVES` list (`services/primitives/registry.py:386` block) | D3 |
| FireInvocation Reviewer-prompt teaching (`reviewer_agent.py:781`, `cockpit_awareness.py:197-208`) | D3 |
| `services/reviewer_chat_surfacing.py::_is_mechanical_fire_invocation` + suppression logic (189-308) | Reviewer-fired mirrors dissolve; suppression no longer needed |
| alpha-trader bundle `trade-proposal` recurrence entry | Inline into signal-evaluation |
| alpha-author bundle `pre-ship-audit` recurrence entry | Replaced by `_hooks.yaml` declaration |
| alpha-trader bundle `principles.md` "Commission substrate via FireInvocation" clauses (lines 21-23, 179) | D3 |
| Stale doc references in `services/orchestration.py:651`, `services/primitives/__init__.py:12`, `services/primitives/infer_workspace.py:11,32,82` | Vocabulary cleanup per CLAUDE.md item 7b grep protocol |

---

## Canon rewrite scope

| Doc | What changes |
|---|---|
| **`docs/architecture/FOUNDATIONS.md`** | Axiom 2: Reviewer is event-fired (not session-entity-invoked). Axiom 4: trigger sub-shapes reframe under wake-source vocabulary; Axiom 4 v8.5 amendment on "Trigger authoring is an Identity-layer responsibility" preserved + sharpened. New Derived Principle naming the funnel + evaluation-gate pattern. |
| **`docs/architecture/GLOSSARY.md`** | New entries: Wake source, Wake proposal, Wake evaluation funnel, Hook. Amended entries: Reviewer (event-fired), Recurrence (cron-tick wake source's configuration), Pulse (deleted or absorbed), Trigger (kernel-internal vocabulary). |
| **`docs/architecture/invocation-and-narrative.md`** | Rewrite: wake-as-irreducible-unit at top, recurrences demoted to "one wake source's configuration," new section on the funnel + evaluation. |
| **`docs/architecture/primitives-matrix.md`** | `FireInvocation` row narrows to chat-only column. New `ManageHook` primitive row. |
| **`docs/architecture/SERVICE-MODEL.md`** | "Execution Flow" rewrite: wake sources → funnel → Reviewer cycle, replacing the current "scheduler → dispatcher → Reviewer" model. |
| **`docs/adr/ADR-256.md` / `ADR-260.md` / `ADR-261.md` / `ADR-263.md` / `ADR-274.md` / `ADR-275.md` / `ADR-276.md`** | Status banners on each: which decisions ADR-296 v2 supersedes, amends, or preserves. The lineage stays as audit trail. |
| **`docs/adr/ADR-253.md`** (Reviewer directives) | D2 directives mechanism `fire_invocation` action superseded. Note + status banner. |
| **`docs/architecture/adr296-canon-and-runtime-audit.md`** | Archive to `docs/architecture/archive/` once ADR-296 v2 is `Implemented` — the audit's load-bearing role is pre-implementation; post-implementation it's historical. |
| **`docs/adr/ADR-296.md`** | Status → Implemented. Implementation phases noted. Canon-relationship sections (Supersedes / Amends / Preserves) added now that audit-grounded. |
| **`CLAUDE.md`** | ADR-296 summary added. Stale ADR-261 / ADR-263 / ADR-274 / ADR-275 / ADR-276 summary lines updated to reflect ADR-296 v2 supersession of their wake-mechanism portions. |
| **`api/prompts/CHANGELOG.md`** | New entry per CLAUDE.md prompt-change protocol. Names the persona-frame deletion of FireInvocation guidance + addition of cadence-authority + standing-intent-hook guidance. |

---

## Bundle migration scope

### alpha-trader

1. `_recurrences.yaml`:
   - DELETE `trade-proposal` recurrence entry.
   - REWRITE `signal-evaluation` prompt to direct the Reviewer to ProposeAction inline when signals fire: "Evaluate the universe against signals IH-1 through IH-5. **When a signal fires with sufficient confidence per principles, ProposeAction inline with sizing math.** ..."
2. `_hooks.yaml`: NEW, empty (`hooks: []`). Forks at activation.
3. `review/principles.md`:
   - DELETE "Commission substrate via FireInvocation when upstream substrate is missing AND you would otherwise stand down waiting for it" clauses (lines 21-23) and line 179 directive.
   - REPLACE with cadence-authority guidance: "When upstream substrate is stale, either (a) update standing_intent.md to declare interest in the substrate transition that would unblock you, or (b) author your next cycle via Schedule for after the relevant mechanical mirror's next fire. Do not invoke the mirror directly from your loop."
4. `_workspace_guide.md` (if applicable): verify no FireInvocation references; remove if found.

### alpha-author

1. `_recurrences.yaml`:
   - DELETE `pre-ship-audit` recurrence entry.
2. `_hooks.yaml`: NEW, with `pre-ship-audit` substrate-event hook entry (event: substrate_change, path_match: `/workspace/context/authored/*/profile.md`, field_change: `{status: ready_for_review}`, prompt: existing pre-ship-audit prompt).
3. `specs/pre-ship-check.md`:
   - REWRITE lines 14-19 trigger section: "Dispatched via substrate-event hook (declared in `_hooks.yaml`) when a draft's `profile.md` frontmatter `status` transitions to `ready_for_review`. The kernel's substrate-event wake source detects the transition and submits a wake-proposal; the funnel escalates to full Reviewer cycle with this spec's prompt as the envelope."
4. `review/principles.md`: verify no FireInvocation references; remove if found.

---

## Regression gates

New test files, each landing in the same PR:

### `api/test_adr296_wake_funnel.py`
- Funnel module exists at `services/wake_evaluation.py`.
- Tier 1 returns deterministic decisions for known wake-event shapes.
- Tier 2 fires only when Tier 1 returns "tier_2"; cost telemetry routes to `reviewer-tier-2-idle-tick` caller.
- Escalation invokes full `invoke_reviewer` exactly once per escalation.
- No bypass paths exist (grep gate: every `invoke_reviewer` call site is inside `services/wake.py`).

### `api/test_adr296_wake_sources.py`
- Each of five wake sources (`cron_tick`, `addressed`, `proposal_arrival`, `substrate_event`, `manual_fire`) submits valid wake-proposals.
- All call sites that previously called `dispatch(...)` or `invoke_reviewer(...)` now route through `services.wake.submit_wake_proposal`.

### `api/test_adr296_fireinvocation_chat_only.py`
- `FireInvocation` absent from `REVIEWER_PRIMITIVES` list in registry.
- `FireInvocation` present in `CHAT_PRIMITIVES`.
- `reviewer_agent.py::_PERSONA_FRAME` contains no `FireInvocation` mentions.
- `cockpit_awareness.py` contains no `FireInvocation` mentions.
- `review_proposal_dispatch.py` directives mechanism does not contain `fire_invocation` action.

### `api/test_adr296_hooks.py`
- `/workspace/_hooks.yaml` parser exists and validates schema.
- `services/wake_sources/substrate_event.py` walks hooks correctly.
- Hook authoring via `ManageHook` primitive works for operator (CHAT_PRIMITIVES) and Reviewer (REVIEWER_PRIMITIVES).
- Hook authorship attributed via ADR-209 `authored_by` on `workspace_file_versions` rows.

### `api/test_adr296_no_legacy_invoke_paths.py`
- Grep gate: zero non-test code references to deleted patterns:
  - No `invoke_reviewer(` outside `services/wake.py` and `agents/reviewer_agent.py` (the definition site).
  - No `dispatch(...)` direct calls outside `services/wake_sources/cron_tick.py`.
  - No `action="fire_invocation"` in `review_proposal_dispatch.py`.
  - No "Commission substrate via FireInvocation" in any `principles.md` in bundles.
  - No FireInvocation references in `reviewer_agent.py::_PERSONA_FRAME`.

### Existing gates updated against new shape
- `api/test_adr261_phaseB.py` — `FireInvocation in REVIEWER_PRIMITIVES` assertion flips to `not in REVIEWER_PRIMITIVES`.
- `api/test_adr290_lifecycle_posture.py` — "Commission substrate via FireInvocation" assertion deleted (replaced by cadence-authority guidance assertion).
- `api/test_adr275_introspection_cadence.py` — verify cadence-authoring assertions still hold under new wake-source shape.
- `api/test_adr276_reactive_envelope.py` — verify envelope assembly still feeds full-cycle escalation correctly.
- `api/test_adr289_invocation_id_anchoring.py` — verify `invocation_id` anchoring still works at the funnel layer.

---

## Render service parity check (per CLAUDE.md item 6)

Changes affecting which services?

| Service | Impact |
|---|---|
| API (yarnnn-api) | All — every wake source originates here (operator chat in feed.py, proposal-arrival in review_proposal_dispatch.py, manual-fire endpoints in routes/recurrences.py + routes/admin.py + routes/agents.py) |
| Unified Scheduler (cron) | cron-tick wake source migration — scheduler now calls `services/wake_sources/cron_tick.py::walk_due` instead of `services/invocation_dispatcher.dispatch` directly |
| MCP Server | None (MCP doesn't invoke Reviewer — it's a read-only context hub per ADR-169) |
| Output Gateway | None |

No env var changes. No schema changes (existing `execution_events` table gains a `funnel_decision` column via migration in this PR; existing `tasks` table unchanged; new substrate file `_hooks.yaml` per workspace is workspace_files row, no DDL).

---

## Open implementation questions resolved during planning

The eight deferred items from ADR-296 v2 §"What this ADR does not yet say" — resolution at scope time:

1. **Canon-relationship sections** — added to ADR-296 v2 in the same PR. The implementation evidence justifies the supersedes/amends/preserves declarations.
2. **Hook substrate location** — `/workspace/_hooks.yaml`, sibling of `_recurrences.yaml`. Operator authors via YARNNN chat → `ManageHook` primitive; Reviewer authors mid-loop via same primitive. Both attributed via ADR-209.
3. **Tier 1 + Tier 2 location in code** — `services/wake_evaluation.py`, called from `services/wake.py::submit_wake_proposal`. Funnel is upstream of `invoke_reviewer`, not inside it.
4. **Migration plan for bundles** — alpha-trader + alpha-author both migrate in this PR. Other bundles (none active currently) gain `_hooks.yaml` schema at next activation.
5. **Substrate-event detection mechanism** — at every scheduler tick, `services/wake_sources/substrate_event.py::walk_hooks` queries recent `workspace_file_versions` rows (since last walk), matches against hook declarations, submits proposals for matches. Per-tick walk, not event-listener; this preserves the existing scheduler poll cadence and avoids new infrastructure.
6. **Cycle-terminus contract** — soft default. Reviewer's `_PERSONA_FRAME` guidance is updated to direct cadence + standing-intent authoring at terminus. No hard primitive contract; the discipline is prompt-layer per ADR-274 / ADR-275 precedent.
7. **Backwards compatibility** — none. Singular Implementation. Legacy paths delete in this PR.
8. **alpha-author back-edge action coverage** — out of scope for this PR. Tracked separately as a bundle-design follow-up (alpha-author's autonomy demo can still test internal-worldview half of the loop with v2; full back-edge testing waits on publish-action surface, a separate bundle ADR).

---

## What this PR does NOT do

- Does not change ProposeAction shape (ADR-193) — back-edge primitive unchanged.
- Does not change AUTONOMY shape (ADR-293) — governance unchanged.
- Does not change self-amendment discipline (ADR-295) — Reviewer authority to edit operator-canon under thresholds unchanged.
- Does not change mechanical-mirror recurrence shape — they continue under cron-tick wake source as mechanical-mode bypass.
- Does not change Authored Substrate (ADR-209) — attribution chain unchanged.
- Does not introduce continuously-running daemons or persistent processes — wake remains event-fired per D1.
- Does not commit to per-recurrence Render Crons or pg_cron migration — ADR-261 D3's three implementation candidates remain deferred; current 5-minute polling scheduler survives, will be revisited when scale demands.
- Does not add new database tables — `execution_events.funnel_decision` column added; everything else stays substrate-level.
- Does not change MCP surface — read-only context hub unchanged per ADR-169.

---

## Open questions for the operator before the PR drafts (none blocking, but worth flagging)

1. **Hat-B observation discipline updates** — the alpha-trader + alpha-author session-start guides reference the current wake mechanism in their cadence interpretation contracts. These update as part of the PR per CLAUDE.md doc-alongside-code discipline. Confirm.

2. **Render env var verification** — no new env vars expected. But the migration runs DDL (the `execution_events.funnel_decision` column). Should land via `psql` migration file in `supabase/migrations/` per existing convention. Confirm.

3. **Test gate cost on Tier 2** — the `test_adr296_wake_funnel.py` Tier 2 path test fires a real Haiku call per execution. At ~$0.001/call this is negligible, but worth noting it's a non-zero CI cost (unlike pure assertion gates). Confirm acceptable.

If these confirm clean, the PR drafts straight from this scope.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-05-20 | v1 — Initial scope. Atomic-large PR shape committed per ADR-261 precedent. Funnel ships in same landing. Hooks at `/workspace/_hooks.yaml` (single canonical location). Surface inventory grounded in 2026-05-20 grep pass. Deletions ledger + canon rewrite scope + bundle migration scope + regression gate spec + render parity check + open implementation question resolutions all named. |
