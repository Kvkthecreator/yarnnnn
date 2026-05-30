# ADR-307: Unified Permission Taxonomy — One Gate, One Queue, All Consequential Primitives

**Status**: Phase 1 Implemented (commit `6925927`); D4 revised to the generic-queue shape 2026-05-30 (first-principles consumer audit); Phases 2–4 implementation in progress.
**Date**: 2026-05-30
**Deciders**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)

> **Evidence base**: four read-only audits 2026-05-29/30 — (1) conceptual boundary against FOUNDATIONS + ADR-293 + primitives-matrix; (2) implementation sites (`should_auto_apply` callers, `action_proposals` lifecycle, dead code); (3) Claude Code permission architecture from `docs/analysis/src_claudeCC/`; (4) the `action_proposals` full consumer surface (every reader/writer of every column, the reconciler `id` round-trip, the FE card's required fields) — which drove the D4 revision from "reuse the capital table" to "generalize the queue." Receipts inline. Triggered by the [persona-frame-collapse validation](../evaluations/2026-05-29-persona-frame-collapse-VALIDATION.md), which surfaced a Reviewer `WriteFile` that **errored** under bounded autonomy (`substrate_write_requires_autonomous`) instead of queuing for approval.

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

**D4 — One *generic* queue, keyed on `(primitive, inputs)` with family-shaped `decision_context`.** *(Revised 2026-05-30 after a first-principles consumer audit — see §"D4 revision" below. The original D4 reused the capital-shaped `action_proposals` via a `workspace.write_file` action_type; the audit found that table is a capital-action queue wearing a "generic" costume, and cramming substrate writes in would inherit the mis-shape. The corrected D4 generalizes the queue itself.)*

A queued action is, from first principles, **"a primitive call the system wants to make, but autonomy says the operator must approve first."** Its irreducible essence is three things: (1) the exact call to replay on approval — `(primitive, inputs)`; (2) enough context for the operator to decide; (3) a stable identity correlating approval → execution → outcome. The `action_proposals` table already *is* this — but its schema bakes in the capital-action assumption (`action_type → ACTION_DISPATCH_MAP → platform tool`; `rationale`/`expected_effect`/`reversibility`/`risk_warnings` as *required* columns). The audit confirmed: those are **one family's (capital) decision context**, not generic queue fields.

The generic shape:
- **`primitive: text`** replaces `action_type`. Store the primitive name directly (`WriteFile`, `submit_order`, `Schedule`...). `ExecuteProposal` on approve replays `execute_primitive(primitive, inputs)` — **`ACTION_DISPATCH_MAP` is deleted entirely** (it was pure indirection; the `task.create → ManageTask` precedent already proved the map is just "verb → primitive"). This also deletes the dead `task.create → ManageTask` entry as a side effect of deleting the map (subsumes the D6 dead-code item).
- **`inputs: jsonb`** — unchanged, already generic. Holds the call's arguments. The reconciler's `signal_id` + the dispatch-layer `_proposal_id` stay here (do NOT migrate them — the reconciler's `id`-round-trip depends on it).
- **`decision_context: jsonb`** replaces the four capital columns (`rationale`, `expected_effect`, `reversibility`, `risk_warnings`). It is **family-shaped**: a `capital` family carries `{rationale, expected_effect, reversibility, risk_warnings}`; a `substrate` family carries `{diff, message}` (the content diff + the revision message — the write's "why" already lives in the Reviewer's concurrent judgment_log/standing_intent, and reversibility is a *property of the substrate layer* per ADR-209, not a per-action judgment).
- **`family: text`** — the discriminator (`capital | substrate | ...`). The cockpit renderer dispatches on it (capital → order-ticket card; substrate → diff card) — the same content-shape dispatch as ADR-306 L2/L3. Today `ProposalCard` already branches on `action_type.startsWith('trading.')`; this generalizes that to `family`.

A gated substrate write becomes a `family='substrate', primitive='WriteFile', inputs={path,content,mode}, decision_context={diff,message}` row. On approve, `execute_primitive('WriteFile', inputs)` runs with operator/execution auth (not `reviewer_caller` → no re-gate, no loop — verified: both approve paths pass non-reviewer auth). **The Phase-4 `queued_for_operator` second-queue plan (ADR-293 D10) is withdrawn** — there is one queue, now genuinely generic.

The generic-queue migration's five breakage risks (from the consumer audit) each carry a mitigation in §Risk. The `id` PK round-trip (reconciler → Alpaca `client_order_id` → P&L) is **sacred and unchanged**.

**D5 — Complete the gate across all consequential primitives.** `Schedule`, `RuntimeDispatch`, `DispatchSpecialist`, `ManageHook`, `ManageAgent`, `ManageDomains` pass through the uniform gate per D1. Their existing ad-hoc gates (pace cap on Schedule, token budget on RuntimeDispatch/DispatchSpecialist) remain as **orthogonal** checks (resource ceilings, not approval gates) — the autonomy gate is additive, not a replacement. Under `autonomous` these apply directly (subject to their resource ceilings); under `bounded`/`manual` they queue.

**D6 — Streamlining (singular implementation; rides along).**
- **`ACTION_DISPATCH_MAP` is deleted** (D4) — `ExecuteProposal` replays `execute_primitive(primitive, inputs)` directly. This subsumes the dead `task.create → ManageTask` entry + `_maybe_inject_manage_task_action` (both deleted with the map). A "proposable primitives" allow-list (or trusting the registry + the gate's own `read_only` classification) replaces the map's allow-list role (breakage risk #4).
- **Wire the `source` field** (`reviewer_addressed`/`reviewer_periodic`/`reviewer_heartbeat`) — currently a dead-write (zero live writers; the skip-re-invocation branch at `review_proposal_dispatch.py:127` never fires). With substrate writes flowing through `proposal_arrival.on_created`, **the self-wake loop becomes live**: the Reviewer would wake on its own queued writes unless `source` is set. The gate sets `source="reviewer_<trigger>"` on Reviewer-authored substrate proposals so the reactive dispatcher skips re-judging them. **This is the one real trap** in the unification.
- **Correct stale lock docs**: `_locks.yaml` is dead as a lock source (superseded by `DEFAULT_REVIEWER_WRITE_LOCKS`); the "three governance files" comments are stale (now five: `AUTONOMY.md`, `_autonomy.yaml`, `_token_budget.yaml`, `_preferences.yaml`, `_pace.yaml`). `never_auto` remains an orthogonal operator-authored soft-lock evaluated inside the gate. The dead `approved_by='auto_reversible'` filter in `routes/agents.py` (only `"user"` is ever written) is corrected/removed.
- **Lazy expiry stays** but is noted: no cron sweeps proposals to `expired`; an untouched past-TTL proposal stays `pending` until execute is attempted. Out of scope to fix here; noted for a cleanup recurrence.

## D4 revision — why the generic queue (first-principles record)

The original D4 (reuse `action_proposals` via a `workspace.write_file` action_type, auto-derive or Reviewer-supply rationale) was caught mid-implementation as a contortion: it honored the existing capital-shaped contract instead of asking what the queue *is*. The first-principles audit (3 sub-audits: schema, every consumer, the Claude-Code cross-check) established:

- The queue's essence is `(primitive, inputs)` + decision_context + stable id. `action_type → ACTION_DISPATCH_MAP → platform tool` is the platform-write assumption baked into a supposedly-generic table; `rationale/expected_effect/reversibility/risk_warnings` as *required* columns are capital framing.
- Forcing substrate writes into that shape (either auto-deriving fake rationale or extending WriteFile's contract with rationale fields) would paper over a schema mismatch — **the same class of mistake that produced the original capital/substrate bifurcation.**
- The correct move generalizes the queue: `primitive` (replaces action_type, deletes the map), `decision_context jsonb` (replaces the 4 capital columns, family-shaped), `family` discriminator (cockpit renders by family — ADR-306 L2/L3 content-shape dispatch). "One queue" becomes *literally* true (one shape) instead of "two action-classes in a capital table."

This makes ADR-307 a schema-migration ADR (touches `action_proposals` + the cockpit renderer + `ProposeAction`/`ExecuteProposal` reframed as "enqueue/replay a gated call"), not just a gate-rewiring ADR.

## What this supersedes / amends

- **Withdraws ADR-293 D10 + D13** (the Phase-4 `queued_for_operator` substrate-Queue as a *second* mechanism). The substrate-Queue *intent* (bounded substrate writes await operator approval) is **preserved and fulfilled** — via the one `action_proposals` queue, not a parallel one. ADR-293 D1 (governance/operational taxonomy) and D4 (`should_auto_apply` uniform decision function) are **preserved**.
- **Amends ADR-168** (primitive matrix) — adds `read_only` as a per-primitive property and a `consequential` capability tag; the gate is documented as a Mechanism-dimension layer over `execute_primitive`.
- **Amends ADR-249** (autonomy as approval-degree) — the approval-degree now applies uniformly to all consequential primitives, not just capital+substrate.
- **Amends ADR-193** (ProposeAction) — the `action_proposals` table is generalized from a capital-action queue (`action_type → ACTION_DISPATCH_MAP → platform tool`; required `rationale/expected_effect/reversibility/risk_warnings`) into a generic gated-action queue keyed on `(primitive, inputs)` with family-shaped `decision_context` (D4). `ProposeAction` = "enqueue a gated call"; `ExecuteProposal` = "replay `execute_primitive(primitive, inputs)` on approve" (no map). `ACTION_DISPATCH_MAP` deleted. The irreducible things the audit identified (a persisted row with stable id + decision context + wake-trigger) are *preserved* — they were never capital-specific; only the capital *framing* of the columns is generalized.
- **Builds on** the Claude-Code permission architecture (`docs/analysis/src_claudeCC/`) — uniform gate + `isReadOnly` fail-closed + deny>ask>allow precedence adopted; in-loop-pause replaced by the durable queue (documented divergence).

## What this preserves

- FOUNDATIONS Axioms 1–8; the six-dimension model (gate = Mechanism, queue = Channel — both already canon).
- `action_proposals` as the single waiting room — now generalized: the capital path's *behavior* is unchanged (it becomes `family='capital'` carrying the same decision_context fields it has today), the substrate path joins it as `family='substrate'`.
- The reconciler's `id`-round-trip (`action_proposals.id` → Alpaca `client_order_id` → P&L attribution → `_money_truth.md` per-signal bucketing → high_impact feedback). `id` stays the PK; `signal_id` stays in `inputs`. **Sacred — never repurposed.**
- All hard governance locks (`DEFAULT_REVIEWER_WRITE_LOCKS`) — they become the `deny` (bypass-immune) tier.
- ADR-209 Authored Substrate (queued writes still attribute + retain on apply).
- ADR-306 minimal frame — the gate is code, not prose; the frame narrates none of it (consistent with DP22 anti-rebloat).

## Risk + revert

The generic-queue migration's breakage risks (from the consumer audit), each with its mitigation:

1. **Reconciler `id` round-trip (highest).** `outcomes/trading.py` writes `proposal.id` to Alpaca `client_order_id` and reads it back to recover `inputs.signal_id` → P&L → `_money_truth.md` → high_impact feedback. Mitigation: `id` stays the PK; `signal_id` stays in `inputs` (NOT migrated to `decision_context`). The migration is column-additive on the reconciler's read path.
2. **FE required fields.** `ProposalCard` / `client.ts` make `reversibility` a non-nullable enum and render `expected_effect`/`rationale`/`risk_warnings` unconditionally. Mitigation: the card branches on `family` (it already branches on `action_type.startsWith('trading.')` — generalize to `family`); a `substrate` family renders `decision_context.diff`, never touching the capital fields.
3. **TTL-by-reversibility KeyError.** `DEFAULT_TTL_HOURS[reversibility]` hard-indexes the 3-value enum. Mitigation: TTL becomes family-aware — capital keeps reversibility-keyed TTL (inside `decision_context`); substrate defaults to a fixed TTL (or none). No bare `[reversibility]` index on a possibly-absent value.
4. **`ACTION_DISPATCH_MAP` allow-list gate.** `handle_propose_action` rejects any action_type not in the map. Mitigation: replaced by a "proposable primitives" allow-list (consequential + not governance-locked), or trust the registry + gate. Substrate-write primitives must be proposable or they can't queue.
5. **`_resolve_context_domain` None → observe-only.** Any proposal not `trading.`/`commerce.` gets no Reviewer judgment. Mitigation: the `substrate` family resolves to the workspace-scope (no platform domain) and the dispatcher judges it via the substrate branch — substrate-write proposals must reach the Reviewer's verdict path, not silently fall to observe-only.

Plus the **self-wake loop**: wiring substrate writes through `proposal_arrival` without `source` makes the Reviewer wake on its own writes. Mitigation: the gate sets `source="reviewer_<trigger>"` on Reviewer-authored substrate proposals; a regression test asserts the reactive dispatcher skips `source="reviewer_*"` rows.

Revert: Phase 1 (committed `6925927`, behavior-preserving) stays regardless. The Phase-2 migration is a single revertable migration + commit; reverting returns to Phase-1 state (substrate still errors, capital still queues — the pre-ADR-307 behavior minus the harmless gate scaffold).

## Implementation (phased)

- **Phase 1 — uniform gate scaffold (behavior-preserving). DONE, commit `6925927`.** `services/primitives/permission.py` (the one gate); `READ_ONLY_PRIMITIVES`; `execute_primitive` consults `resolve_permission`. Read-only short-circuits APPLY; consequential passes through (capital queues, substrate errors — unchanged). 8 assertions green.
- **Phase 2 — generalize the queue + route substrate writes (D4 + D6).** Migration: `action_proposals.action_type → primitive`; add `decision_context jsonb` + `family text`; backfill existing rows (`family='capital'`, `primitive=ACTION_DISPATCH_MAP[action_type]`, `decision_context={rationale,expected_effect,reversibility,risk_warnings}`). Rewrite `handle_propose_action` (family-aware, no map, decision_context), `handle_execute_proposal` (`execute_primitive(primitive, inputs)`, no map). Delete `ACTION_DISPATCH_MAP` + `_maybe_inject_manage_task_action`. The gate's QUEUE realization: when `resolve_permission` returns QUEUE for a Reviewer substrate write, `execute_primitive` enqueues a `family='substrate'` proposal (`primitive='WriteFile'`, `inputs`, `decision_context={diff,message}`, `source='reviewer_<trigger>'`) instead of running the handler. Remove the `workspace.py:598` inline error branch (the gate owns the decision now). FE: `ProposalCard` dispatches on `family`. Fix TTL (family-aware), the proposable-primitives allow-list, the substrate domain-resolution, and the dead `auto_reversible` filter. Test: gated substrate write under bounded → `pending family='substrate'` proposal; approve → `WriteFile` applies (non-reviewer auth, no re-gate) with ADR-209 attribution; reactive dispatcher skips the `reviewer_*` row; capital path behavior identical post-migration; reconciler `id` round-trip intact.
- **Phase 3 — complete the gate (D5).** Route `Schedule`/`RuntimeDispatch`/`DispatchSpecialist`/`ManageHook`/`ManageAgent`/`ManageDomains` through the uniform gate (each enqueues a `family='substrate'` proposal under bounded/manual; applies under autonomous). Preserve their orthogonal resource ceilings (pace cap, token budget). Test: each queues under bounded, applies under autonomous.
- **Phase 4 — canon (D3) + matrix (amend ADR-168).** FOUNDATIONS Mechanism sentence; primitives-matrix `read_only` column + `consequential` tag; CHANGELOG. Mark ADR-293 D10/D13 withdrawn; mark ADR-193 `ProposeAction`/`ExecuteProposal` reframed as "enqueue/replay a gated call."

## The falsifiable check (Phase 2 judges)

Re-run the bounded-autonomy substrate-write wake. Pre-ADR-307: `WriteFile` returns `substrate_write_requires_autonomous` error, nothing queues. Post-Phase-2: the gate enqueues a `pending family='substrate'` proposal carrying `{primitive:'WriteFile', inputs:{path,content,mode}, decision_context:{diff,message}}`; the operator approves from the cockpit Queue (rendered as a diff, not an order-ticket); approve replays `execute_primitive('WriteFile', inputs)` applying the write with `authored_by="reviewer:..."` + ADR-209 retention — with NO second Reviewer wake on its own write (the `source` skip holds), and the capital path + reconciler `id` round-trip provably unchanged. If the Reviewer re-wakes on its own queued write, or a capital proposal's reconciliation breaks, Phase 2 reverts.
