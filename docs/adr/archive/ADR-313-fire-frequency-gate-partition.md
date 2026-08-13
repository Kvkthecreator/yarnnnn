# ADR-313 — Fire-Frequency Gate Partition: Pace (Drain-Lane Rate) vs Token-Budget (Cost + Per-Slug Floor)

> **⚠ SUPERSEDED by [ADR-327](ADR-327-budget-and-the-self-improving-loop.md) (Proposed, 2026-06-08).** ADR-313 named the boundary between two cost/frequency files (`_pace.yaml` Gate A + `_token_budget.yaml` Gate B) and chose to **keep both**, fixing the developer-facing confusion with documentation. ADR-327 **dissolves the partition** by collapsing the two files into one `_budget.yaml` — because the operator-facing reframe (pace retires; tempo becomes the Reviewer's allocation problem, not an operator dial) removes Gate A's reason to be a separate gate. ADR-313's audit finding (the two gates are not duplicates *as implemented*) is preserved as accurate historical record; its *keep-both* conclusion is reversed. The per-slug `min_interval` floor (Gate 3) survives into `_budget.yaml` verbatim.

**Status**: **Superseded** by ADR-327 (was Proposed, doctrine-only — zero code change, zero behavior change)
**Date**: 2026-06-02
**Deciders**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)

> **Evidence base**: a read-only audit 2026-06-02 of every fire-frequency gate in the wake path (`services/wake.py`, `services/wake_drainer.py`, `services/token_budget.py`, `services/pace.py`) + the Reviewer prompt strategy (`agents/reviewer_agent.py`, `agents/cockpit_awareness.py`, `services/reviewer_envelope.py`). Receipts inline. Triggered by an operator thesis that "two sources govern how often work fires" creates (1) future-dev confusion and (2) functional instability / Reviewer behavior breaks. The audit confirmed (1) and falsified (2) — the two gates are a correct two-layer design that **lacks a canonical name**, not a duplicate that breaks the Reviewer.

---

## Context

"How often can work fire in a workspace?" is answered by **two gates at two layers**, both live, neither a duplicate of the other. The audit that produced this ADR twice mis-read the relationship — first calling token-budget's min-interval "dead code" (the enforcement lives in `wake.py`, not the files first grepped), then re-auditing to find it live. That mis-read by an experienced reader *is* the confusion this doctrine exists to prevent: there is no canonical statement of which gate owns what, so each reader re-derives the boundary and some get it wrong.

### The actual topology (receipts)

A wake passes through **both** layers, in series, before the Reviewer fires:

```
submit_wake_proposal (wake.py:110)  →  enqueue to wake_queue  →  returns immediately
                                                                       │
   drainer tick: drain_next_for_user (wake_drainer.py:156)             │
        │                                                              │
   GATE A — DRAIN-LANE RATE (drainer, ADR-298/301)  ←──────────────────┘
        │   paced_lane_eligible_to_drain (wake_drainer.py:63)
        │     └─ pace.min_interval_seconds         (workspace-wide drain interval, _pace.yaml)
        │   drain_can_acquire_for_user (wake_drainer.py:136)
        │     └─ single-in-flight constraint        (one Reviewer session per workspace)
        ▼
   _dispatch_drained_wake → wake.py dispatch body
        │
   GATE B — COST + PER-SLUG FLOOR (wake.py, ADR-293 D7)
        ├─ Gate 1: daily_spend_ceiling_usd          (workspace daily $ ceiling,  _token_budget.yaml)
        ├─ Gate 2: max_judgment_recurrences_per_day  (workspace daily fire count, _token_budget.yaml)
        └─ Gate 3: min_interval_for(slug)            (PER-SLUG fire floor,         _token_budget.yaml + overrides:)
        ▼
   invoke_reviewer()
```

Receipt for Gate A: `wake_drainer.py:95` — `interval_seconds = pace.min_interval_seconds` (the ADR-301 "singular pace-budget arithmetic" comment at `:94`).
Receipt for Gate B: `wake.py:415` (Gate 1), `wake.py:457` (Gate 2), `wake.py:477` `min_iv = budget.min_interval_for(recurrence.slug)` (Gate 3, with per-slug `overrides:` at `token_budget.py:54`).

### Why these are NOT duplicates

| | Gate A — Pace | Gate B — Token-Budget |
|---|---|---|
| **Concern** | drain *rate* — how fast the wake queue empties | *cost* ($ + daily count) + *per-slug fire floor* |
| **Scope** | workspace-wide, all wakes pooled in the paced lane | workspace ($/count) AND per-recurrence-slug (interval) |
| **Substrate** | `_pace.yaml` | `_token_budget.yaml` (incl. per-slug `overrides:`) |
| **Layer** | drainer (when a wake is pulled off the queue) | dispatch body (when a pulled wake is about to fire) |
| **Owning ADR** | ADR-298 (wake queue + pace) / ADR-301 | ADR-293 D7 (governance/compute taxonomy) |

The `min_interval_seconds` collision is the trap: **pace's** `min_interval_seconds` (drainer, workspace-wide drain interval) and **token-budget's** `min_interval_between_recurrence_fires_seconds` → `min_interval_for(slug)` (per-slug fire floor) are *different concepts wearing similar names at different layers*. Pace throttles the lane; token-budget floors a specific slug. A workspace can have a fast pace (drain freely) and still floor one chatty recurrence to 15-min spacing via `overrides:` — neither gate expresses the other's intent.

### Why the instability thesis does NOT survive the prompt audit

The operator's second claim — two gates cause Reviewer behavior breaks — was tested against the Reviewer prompt strategy and **falsified**:

- **The Reviewer models neither gate.** The wake envelope carries `pace_yaml` (`reviewer_envelope.py:92`) but deliberately **NOT** `_token_budget.yaml`. Pace enters only because the Reviewer authors cadence via `Schedule()` mid-loop and its calls must land within the pace budget (`reviewer_envelope.py:86-91`). Token-budget never enters the Reviewer's reasoning — `cockpit_awareness.py:91-93` merely notes it exists and is "enforced at fire time by the scheduler."
- **The prompt embodies ADR-307's act-with-intent model.** `reviewer_agent.py:451-456`: *"A tool call IS your action — there is no separate 'you perform a write and then watch a gate intercept it' step... let the tool result tell you what bound."* The Reviewer acts; gates intercept below its awareness. Merging the gates would change *zero* Reviewer behavior because the Reviewer treats fire-frequency as "I act, the runtime tells me what bound."
- **The one documented Reviewer-cadence break was a perception bug, already fixed, and unrelated.** `docs/evaluations/2026-05-24-...reviewer-schedule-self-misdiagnosis/findings.md` — schedule hallucination (reasoning from cached memory about its own pulse), closed by adding `schedule_index_md` + `recent_execution_md` to the envelope (ADR-301). Not a gate-consolidation issue.

So the instability the operator sensed, if real, has no receipt tracing it to dual-gate disagreement, and the prompt architecture structurally insulates the Reviewer from both gates. The proven problem is **dev/canon confusion**, which doctrine fixes; the unproven problem is functional instability, which a code merge would not address (the Reviewer doesn't see the gates) and which would cost a real capability (per-slug `overrides:`) to attempt.

## Decision

**D1 — Two gates are canon; this ADR names the partition.** Fire-frequency in YARNNN is governed by two sequential gates with a fixed division of labor. The partition is:

- **Pace (`_pace.yaml`, drainer, ADR-298/301) owns DRAIN-LANE RATE** — how fast the paced wake lane empties, workspace-wide, all wakes pooled. It answers *"at what tempo does this workspace's queued work get pulled and run?"* It is the operator's Trigger-dimension tempo dial (Pace + Autonomy + Persona trifecta, ADR-298 D11).
- **Token-Budget (`_token_budget.yaml`, dispatch body, ADR-293 D7) owns COST + PER-SLUG FLOOR** — the workspace daily spend ceiling, the workspace daily judgment-fire count, and the per-recurrence-slug minimum interval (with per-slug `overrides:`). It answers *"how much compute may this workspace spend, and may this specific recurrence fire this soon?"* It is the operator's compute-resource governance.

**The boundary statement (the canonical sentence this ADR exists to provide):**

> *Pace governs the **tempo of the lane** (workspace-wide drain rate). Token-budget governs **cost and per-slug frequency** (how much the workspace spends + how soon a specific recurrence may re-fire). They are sequential, not redundant: a wake must satisfy the pace lane to be pulled, then satisfy token-budget to fire. `pace.min_interval_seconds` is a drain interval; `token_budget.min_interval_for(slug)` is a per-recurrence floor — same word, different layer, different scope.*

**D2 — No code change, no behavior change.** The two gates remain exactly as implemented. No field moves, no field is deleted, no envelope changes, no prompt changes. This ADR is a canon-layer Singular Implementation: *one canonical statement* of a partition that already exists in code but was unnamed. The prior-session proposal to "delete the dead duplicate" is **withdrawn** — the audit proved there is no dead duplicate (Gate 3 is live in `wake.py:477`).

**D3 — The Reviewer's gate-insulation is canon, not accident.** The wake envelope's asymmetry (carries `pace_yaml`, omits `_token_budget.yaml`) is correct and intentional per this ADR: the Reviewer authors cadence (needs pace as a budget) but never reasons about cost/floor (token-budget enforces below its awareness, per ADR-307's act-with-intent gate model). Future envelope or prompt changes must preserve this asymmetry — adding `_token_budget.yaml` to the Reviewer's reasoning surface would re-introduce gate-modeling the architecture deliberately removed (ADR-306 minimal-frame, ADR-307 uniform-gate, ADR-281 substrate-canonical).

**D4 — Future consolidation is gated on a receipt, not on tidiness.** A code merge (collapsing the two gates into one frequency authority) is **not** undertaken on Singular-Implementation grounds alone, because (a) the gates are legitimately distinct concerns at distinct layers, and (b) token-budget's per-slug `overrides:` is a real capability pace does not model. If a future evaluation produces a substrate receipt (an `execution_events` skip row or a reproduced Reviewer stall) tracing a genuine break to dual-gate *disagreement* — pace and token-budget gating the same wake to contradictory outcomes — that receipt scopes a follow-on ADR. Absent the receipt, the partition doctrine is the complete and honest fix.

## What this amends / preserves

- **Amends ADR-293** (Governance / Operational Substrate Taxonomy) — names token-budget's role as the COST + PER-SLUG-FLOOR gate, distinct from pace's drain-rate gate. ADR-293 D7's three gates (spend ceiling, judgment cap, per-slug min-interval) are preserved verbatim.
- **Amends ADR-298** (Reviewer Wake Queue + Pace Dial) — names pace's role as the DRAIN-LANE RATE gate, distinct from token-budget's per-slug floor. The pace dial and drain arithmetic are preserved.
- **Amends ADR-301** (Reviewer Pulse Envelope) — confirms the envelope asymmetry (pace in, token-budget out) as canon per D3.
- **Builds on ADR-307** (Unified Permission Taxonomy) — the Reviewer's act-with-intent posture is why gate-insulation works; fire-frequency gates are Tier-1 kernel gates upstream of the ADR-307 permission gate (they decide *whether a wake fires*, not *whether a primitive call applies/queues/denies*).
- **Preserves** all gate code, both substrate files, the envelope shape, the Reviewer prompt, and the per-slug `overrides:` capability. Zero migration. Zero behavior change.

## Falsifiable check

This ADR is correct if and only if: (a) both gates remain live and independently configurable (a workspace can set a fast pace AND a per-slug floor that bind independently), and (b) no Reviewer prompt/envelope change is required to enact the doctrine. Both hold by construction — the ADR changes no code. The doctrine is falsified as *insufficient* only if a future receipt shows a Reviewer break traceable to dual-gate disagreement (D4) — in which case this ADR is amended, not the code silently changed.

## Implementation

Doc-only. No phases. The canonical boundary sentence (D1) is added to:
- This ADR (canonical home).
- `services/wake.py` module docstring (the gate stack) — cross-reference to D1.
- `services/pace.py` and `services/token_budget.py` module docstrings — each names its half of the partition and points to ADR-313.

No CHANGELOG entry (no prompt/primitive change). No test gate (no behavior to assert beyond what ADR-293/298/301 gates already test). A grep for `ADR-313` after the docstring cross-references confirms the doctrine is reachable from each gate's code home.
