# ADR-307: Unified Permission Taxonomy — One Gate, One Queue, All Consequential Primitives

**Status**: Proposed (2026-05-30) — decision record; implementation phased (see §Implementation).
**Date**: 2026-05-30
**Deciders**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)

> **Evidence base**: three read-only audits run 2026-05-29/30 — (1) conceptual boundary against FOUNDATIONS + ADR-293 + primitives-matrix; (2) implementation sites (`should_auto_apply` callers, `action_proposals` lifecycle, dead code); (3) Claude Code permission architecture from `docs/analysis/src_claudeCC/`. Receipts inline. Triggered by the [persona-frame-collapse validation](../evaluations/2026-05-29-persona-frame-collapse-VALIDATION.md), which surfaced a Reviewer `WriteFile` that **errored** under bounded autonomy (`substrate_write_requires_autonomous`) instead of queuing for approval.

---

## Context

YARNNN has a permission decision (`should_auto_apply`: apply-now vs wait-for-operator-approval) and a queue (`action_proposals`) where waiting actions park. The validation wake exposed that these are **incompletely and asymmetrically wired**:

1. **The gate is incomplete.** `should_auto_apply(action_class)` (`api/services/review_policy.py:306`) knows exactly two action classes — `capital` and `substrate` — and both fire **only when the caller is the Reviewer** (`workspace.py:556` guards on `reviewer_caller`). These consequential primitives pass through **no autonomy gate at all**: `Schedule` (pace cap only), `RuntimeDispatch` + `DispatchSpecialist` (token budget only), `ManageHook`, `ManageAgent`, `ManageDomains` (ungated).

2. **The "wait" outcome is asymmetric.** When the gate says wait: the **capital** path leaves a `pending` `action_proposals` row (correct — operator approves later in the cockpit Queue); the **substrate** path returns `error: substrate_write_requires_autonomous` (`workspace.py:598`) — it does not queue. The error message itself admits the gap: *"bounded/manual queueing arrives in Phase 4 (ADR-293 D10 + D13)."* The planned Phase-4 fix would build a **second** queue (a `queued_for_operator` flag on `workspace_file_versions` + a parallel cockpit surface) — two waiting rooms, two approval mechanisms.

3. **The gated-vs-ungated boundary is principled but only *implied*.** The governance-vs-operational *substrate* split is fully canon (ADR-293 D1 / FOUNDATIONS Derived Principle 20). But the general rule — *consequential mutations gate; reads and narration don't* — lives only in the **shape** of `should_auto_apply`'s `action_class` enum and one prose sentence (`tools_core.py:287`). There is **no capability tag** in `primitives-matrix.md` that marks a primitive as consequential/gateable.

The deeper question (operator-raised): is the `primitive → execute → (capital path queues / substrate path errors)` structure a symptom of a **conceptual framing mismatch**? Yes. The gate is buried *inside individual primitives* and re-implemented (or skipped) per primitive, instead of sitting as **one uniform layer above all primitives** — which is exactly how Claude Code does it.

## Claude Code cross-check (adopt 4, diverge on 1 — deliberately)

Audited from `docs/analysis/src_claudeCC/`. Claude Code draws the *same* boundary we want; we adopt its shape and diverge on one point with a documented reason.

**Adopt verbatim:**

1. **Uniform harness gate, not per-tool gating.** Every tool call routes through one chokepoint; the harness hard-guards `if (permissionDecision.behavior !== 'allow') { return }` *before* `tool.call` runs (`toolExecution.ts:995,1207`). A tool's own `call()` contains zero permission logic. Tools only *advise* via `checkPermissions`; the harness owns the decision (`Tool.ts:494-503`). → **YARNNN must lift the gate out of `WriteFile`/`review_proposal_dispatch` and into `execute_primitive()` (`registry.py:553`) — the single execute-by-name chokepoint.**

2. **`isReadOnly`, fail-closed.** Every tool declares read-only or not; the default is `false` ("assume writes", `Tool.ts:757-760`). Reads resolve `allow`; writes default to `ask`. → **Every YARNNN primitive declares `read_only` (default `false` = consequential).** This makes the boundary explicit *and complete* — Schedule/RuntimeDispatch/etc. stop being silently ungated.

3. **Decision shape `allow | ask | deny`** with precedence **deny > bypass-immune-asks > mode-bypass > allow-rule > ask-default** (`permissions.ts:1158-1317`). → maps onto YARNNN `apply | queue | hard-lock`. The "bypass-immune ask" concept = YARNNN's governance-lock (gates *even under autonomous*).

4. **Mode is a property of the gate, read per-call** — never baked into tools (`acceptEdits/plan/bypassPermissions`, resolved in `permissions.ts`). → YARNNN's autonomy mode (`manual/bounded/autonomous`) is the same shape, read per-call by the uniform gate.

**Diverge deliberately (the one point):** On "ask," Claude Code does a **synchronous in-loop pause** on an *in-memory* React callback queue — it freezes the one agent loop until the human answers, and **fails closed when no synchronous human exists** (`dontAsk → deny`, `permissions.ts:508-516`; headless `shouldAvoidPermissionPrompts → deny`, `:536-546`). Nothing is persisted.

YARNNN's Reviewer is **wake-fired, autonomous, operating in the operator's absence** — there is no human in the loop tick to pause for. So YARNNN's "ask" outcome **must persist the gated action to a durable queue** (`action_proposals`) the operator approves later. This is not baroque; it is the correct adaptation of "ask" to an absent-operator, multi-actor setting. Claude Code fails closed because it has no durable queue; YARNNN has one, so failing closed (today's `substrate_write_requires_autonomous` error) leaves capability on the table.

**Net**: the in-loop-pause is replaced by the durable `action_proposals` queue; everything else is Claude Code's architecture.

## Decision

**D1 — One uniform gate at `execute_primitive()`.** The permission decision moves out of individual primitives and into the single execute-by-name chokepoint (`registry.py:553`). Before dispatching to a handler, `execute_primitive` resolves a `PermissionDecision ∈ {apply | queue | deny}` from `(autonomy_mode × primitive.read_only × action_class × locks)` and:
- `apply` → run the handler (today's behavior).
- `queue` → route to `action_proposals` (one waiting room) instead of running the handler; return the proposal_id.
- `deny` → return a structured `governance_locked` error (bypass-immune; gates even under autonomous).

No primitive gates itself. `should_auto_apply` becomes the gate's decision function, called from one place, not two.

**D2 — Every primitive declares `read_only`, fail-closed.** The primitive registry gains a per-primitive `read_only: bool` (default `false`). Reads (`ReadFile`, `ListFiles`, `SearchFiles`, `ListRevisions`, `ReadRevision`, `DiffRevisions`, `QueryKnowledge`, `LookupEntity`, `ListEntities`, `SearchEntities`, `GetSystemState`, `WebSearch`, `list_integrations`, `DiscoverAgents`) declare `read_only=true` → never gate, never queue. Interaction/narration (`Clarify`, `ReturnVerdict`) are non-consequential → `read_only=true` (they emit narrative, mutate no substrate). Everything else defaults consequential. **This makes the implied boundary canon and complete.**

**D3 — The gated-vs-ungated boundary is stated as canon.** New FOUNDATIONS sentence (Mechanism dimension): *"A consequential action — any primitive that mutates substrate or has external effect — passes the permission gate (Mechanism). The gate resolves apply / queue / deny from the autonomy mode, the action's governance class, and operator-declared locks. Reads and narration are not consequential and never gate. When the gate says queue, the action waits in the single operator-approval queue (`action_proposals`, the Channel surface) until the operator approves — because the Reviewer acts in the operator's absence and cannot pause in-loop for a human."* Cites ADR-293 (governance/operational), DP12 (Channel legibility), DP21 (autonomy = Mechanism dial), and this ADR's Claude-Code cross-check.

**D4 — One queue. Substrate writes become proposals.** A gated substrate write routes through the existing `action_proposals` mechanism via a new `workspace.write_file` action_type in `ACTION_DISPATCH_MAP` → dispatches the `WriteFile` primitive on approve (the proven `task.create → ManageTask` pattern, repurposed from its now-dead slot). `inputs` carries `{path, content, mode}`. The Reviewer supplies `rationale` + `expected_effect` on the gated write (the one irreducible thing a queued write needs that a bare tool call lacks — see ADR-193/audit). **The Phase-4 `queued_for_operator` second-queue plan (ADR-293 D10) is withdrawn** — there is one queue.

**D5 — Complete the gate across all consequential primitives.** `Schedule`, `RuntimeDispatch`, `DispatchSpecialist`, `ManageHook`, `ManageAgent`, `ManageDomains` pass through the uniform gate per D1. Their existing ad-hoc gates (pace cap on Schedule, token budget on RuntimeDispatch/DispatchSpecialist) remain as **orthogonal** checks (resource ceilings, not approval gates) — the autonomy gate is additive, not a replacement. Under `autonomous` these apply directly (subject to their resource ceilings); under `bounded`/`manual` they queue.

**D6 — Streamlining (singular implementation; rides along).**
- **Delete** the dead `task.create → ManageTask` entry + `_maybe_inject_manage_task_action` (`ManageTask` was deleted by ADR-231; the slot crashes on execute). Its pattern is reused by D4's `workspace.write_file`.
- **Wire the `source` field** (`reviewer_addressed`/`reviewer_periodic`/`reviewer_heartbeat`) — currently a dead-write (zero live writers; the skip-re-invocation branch at `review_proposal_dispatch.py:128` never fires). With substrate writes flowing through `proposal_arrival.on_created`, **the self-wake loop becomes live**: the Reviewer would wake on its own queued writes unless `source` is set. D4 must set `source="reviewer_<trigger>"` on Reviewer-authored substrate proposals so the reactive dispatcher skips re-judging them. **This is the one real trap** in the unification.
- **Correct stale lock docs**: `_locks.yaml` is dead as a lock source (superseded by `DEFAULT_REVIEWER_WRITE_LOCKS`); the "three governance files" comments are stale (now five: `AUTONOMY.md`, `_autonomy.yaml`, `_token_budget.yaml`, `_preferences.yaml`, `_pace.yaml`). `never_auto` remains an orthogonal operator-authored soft-lock evaluated inside the gate.
- **Lazy expiry stays** but is noted: no cron sweeps `action_proposals` to `expired`; an untouched past-TTL proposal stays `pending` until execute is attempted. Out of scope to fix here; noted for a cleanup recurrence.

## What this supersedes / amends

- **Withdraws ADR-293 D10 + D13** (the Phase-4 `queued_for_operator` substrate-Queue as a *second* mechanism). The substrate-Queue *intent* (bounded substrate writes await operator approval) is **preserved and fulfilled** — via the one `action_proposals` queue, not a parallel one. ADR-293 D1 (governance/operational taxonomy) and D4 (`should_auto_apply` uniform decision function) are **preserved**.
- **Amends ADR-168** (primitive matrix) — adds `read_only` as a per-primitive property and a `consequential` capability tag; the gate is documented as a Mechanism-dimension layer over `execute_primitive`.
- **Amends ADR-249** (autonomy as approval-degree) — the approval-degree now applies uniformly to all consequential primitives, not just capital+substrate.
- **Amends ADR-193** (ProposeAction) — ProposeAction is reframed as "the durable form of a gated action" rather than a distinct LLM choice; capital proposals and substrate-write proposals share the mechanism. (ProposeAction is NOT deleted — the audit proved it carries irreducible LLM-authored rationale/expected_effect + the stable intent↔outcome id + the wake-trigger that a transparent wrapper cannot.)
- **Builds on** the Claude-Code permission architecture (`docs/analysis/src_claudeCC/`) — uniform gate + `isReadOnly` fail-closed + deny>ask>allow precedence adopted; in-loop-pause replaced by the durable queue (documented divergence).

## What this preserves

- FOUNDATIONS Axioms 1–8; the six-dimension model (gate = Mechanism, queue = Channel — both already canon).
- `action_proposals` as the single waiting room (capital path unchanged; substrate path joins it).
- All hard governance locks (`DEFAULT_REVIEWER_WRITE_LOCKS`) — they become the `deny` (bypass-immune) tier.
- ADR-209 Authored Substrate (queued writes still attribute + retain on apply).
- ADR-306 minimal frame — the gate is code, not prose; the frame narrates none of it (consistent with DP22 anti-rebloat).

## Risk + revert

- **Self-wake loop (D6)** is the load-bearing risk: wiring substrate writes through `proposal_arrival` without setting `source` makes the Reviewer wake on its own writes. Mitigation: D4 sets `source` on every Reviewer-authored substrate proposal; a regression test asserts the reactive dispatcher skips `source="reviewer_*"` rows.
- **Gate-everywhere (D5)** could over-gate a primitive that should apply freely. Mitigation: `read_only=true` declarations are explicit per primitive; the fail-closed default is reviewed primitive-by-primitive in Phase 2, with a test asserting every read primitive is `read_only=true`.
- Each phase is independently revertable. Phase 1 (uniform gate + read_only, behavior-preserving) ships before Phase 2 (substrate-into-queue), which ships before Phase 3 (complete the gate across D5 primitives).

## Implementation (phased)

- **Phase 1 — uniform gate scaffold (behavior-preserving).** Add `read_only` to the registry per primitive (reads + narration `true`, rest `false`). Add the gate resolution in `execute_primitive` that, for now, reproduces today's behavior exactly (capital queues, substrate still errors) but routes the decision through one function. Test: every read primitive `read_only=true`; gate decision matches pre-refactor for capital + substrate. No behavior change.
- **Phase 2 — substrate-into-queue (D4 + D6 dead-code).** Add `workspace.write_file` action_type → `WriteFile` dispatch. Replace `workspace.py:598` error-return with a `handle_propose_action(action_type="workspace.write_file", source="reviewer_<trigger>", ...)` call carrying `{path, content, mode}` + Reviewer rationale. Wire `source` to close the self-wake loop. Delete dead `task.create`/`_maybe_inject_manage_task_action`; correct `_locks.yaml`/"three locks" docs. Test: gated substrate write under bounded → `pending` proposal (not error); approve → WriteFile applies with ADR-209 attribution; reactive dispatcher skips the `reviewer_*`-sourced row. Re-run the [collapse validation wake](../evaluations/2026-05-29-persona-frame-collapse-VALIDATION.md) — the bounded WriteFile now queues.
- **Phase 3 — complete the gate (D5).** Route `Schedule`/`RuntimeDispatch`/`DispatchSpecialist`/`ManageHook`/`ManageAgent`/`ManageDomains` through the uniform gate; preserve their orthogonal resource ceilings. Test: each queues under bounded/manual, applies under autonomous.
- **Phase 4 — canon (D3) + matrix (amend ADR-168).** FOUNDATIONS Mechanism sentence; primitives-matrix `read_only` column + `consequential` tag; CHANGELOG. Mark ADR-293 D10/D13 withdrawn.

## The falsifiable check (Phase 2 judges)

Re-run the bounded-autonomy substrate-write wake against the Reviewer. Pre-ADR-307: WriteFile returns `substrate_write_requires_autonomous` error, nothing queues. Post-Phase-2: WriteFile under bounded returns a `pending` `action_proposals` row (one queue), the operator can approve it from the existing cockpit Queue, and on approve the write applies with `authored_by="reviewer:..."` + ADR-209 retention — with NO second wake of the Reviewer on its own write (the `source` skip holds). If the Reviewer re-wakes on its own queued write, the self-wake trap is unclosed and Phase 2 reverts.
