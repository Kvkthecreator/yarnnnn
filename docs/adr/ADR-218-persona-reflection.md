# ADR-218: Persona Reflection — Reviewer Self-Evolution

> **Status**: Proposed — staged implementation across five commits (this ADR, back-office task, reflection-mode invocation, write-back + visibility, E2E validation).
> **Date**: 2026-04-24
> **Authors**: KVK, Claude
> **Dimensional classification**: **Identity** (Axiom 2) primary — the Reviewer evolves its own persona character. **Mechanism** (Axiom 5) secondary — reflection is a scheduled back-office mechanism. **Purpose** (Axiom 3) — evolution serves operator-declared MANDATE, never contradicts it.
> **Implements**: [`docs/architecture/persona-reflection.md`](../architecture/persona-reflection.md) v1.1 thesis (persona-as-accumulator, operator-seeded + self-evolved).
> **Amends**: ADR-216 D4 (IDENTITY authorship: "operator-authored" → "operator-seeded, persona-evolved"), ADR-217 D4 (narrowing language: "operator-authored narrowing" → "operator + reflexive narrowing"), ADR-209 (revision chain now commonly carries `authored_by="reviewer:*"` entries, not just operator/agent/specialist/system).

---

## Context

Through ADR-216 + ADR-217 + persona-reflection.md v1.1, YARNNN's Reviewer has become a **persona-bearing Agent with operator-seeded IDENTITY + principles + delegation ceiling + precedent layer**. The operator authors direction + framework + interpretations; the Reviewer reads them at reasoning time and renders verdicts.

But the persona itself doesn't evolve. An operator who seeds a Simons-persona Reviewer at signup gets a Simons-persona Reviewer at month 12 — same IDENTITY file, same framework, even as the accumulated decisions trail + realized outcomes reveal patterns the persona's initial framework didn't anticipate. Static-config semantics, not living-actor semantics.

The E2E validation of ADR-217 surfaced this concretely: the Simons persona's cold-start narrowing condition (*"defer when `_performance.md` is empty"*) was the right day-one rule and the wrong day-twenty-five rule. Without reflection, the operator has to remember to edit principles.md manually when calibration warrants. With reflection, the persona notices its own drift and proposes framework updates, with operator auditing retrospectively.

persona-reflection.md v1.1 pinned the thesis:

> Persona is accumulated experience, not authored configuration. Operator seeds direction; persona lives its lifecycle through reflection against its own operational record. Operator's standing role shifts from "continuous config authoring" to "seeding direction + declaring precedent + auditing persona evolution."

This ADR implements that thesis. It is scope-limited to **Reviewer self-reflection on its own directory** per persona-reflection.md §2 boundary rule. Domain-Agent reflection is deferred — the Reviewer pattern must prove first.

---

## Decision

### D1 — Reflection is persona-scoped to the Reviewer's own directory

In V1, only the Reviewer persona reflects. The scope ceiling is `/workspace/review/` only:

- Writable by reflection: `IDENTITY.md`, `principles.md`, `reflections.md` (new).
- Untouchable by reflection: everything else — MANDATE.md, AUTONOMY.md, PRECEDENT.md, CONVENTIONS.md, BRAND.md, workspace IDENTITY.md, all context domain files, seat-state files (OCCUPANT.md, handoffs.md, decisions.md, calibration.md), all workspace-memory files.

Domain Agents (user-authored per ADR-216 D9) do not reflect in V1. Their single-file AGENT.md convention is preserved; they remain operator-edited until a future ADR proves reflection warrants extending to them.

The Reviewer is YARNNN's "brain" per the session's framing — intelligence that works on itself. Orchestration stays pure orchestration; context remains operator + context-task territory. Reflection is the Reviewer's only self-evolution surface.

### D2 — Reflection is substrate-triggered via back-office task

A new back-office task `back-office-reviewer-reflection` runs on operator-tunable cadence (default: daily). The task is YARNNN-owned per ADR-164 pattern; its executor is a dotted-path `services.back_office.reviewer_reflection.run`.

The task executes in two phases:

**Phase A — Zero-LLM condition check.** Scans `decisions.md`, `calibration.md`, and per-domain `_performance.md` files. Evaluates operator-declared thresholds for reflection-warranted conditions. If no threshold crossed, task exits with a "no reflection needed" log entry. Zero LLM cost.

**Phase B — LLM reflection invocation.** If Phase A identifies a trigger, the task invokes the Reviewer agent in *reflection mode* (distinct from verdict mode) with a structured input bundle: current IDENTITY + principles, recent decisions + outcomes, calibration deltas, PRECEDENT.md, the triggering condition. Reviewer returns structured output: list of proposed file changes + reasoning + evidence citations.

**Phase C — Scope-bounded write + visibility.** Proposed changes are applied via `write_revision()` per ADR-209 with `authored_by="reviewer:{occupant_identity}"`. Each change lands as a new revision on IDENTITY or principles. reflections.md gets an append-only entry summarizing the reflection run. Material changes trigger a `role='system'` chat notification per ADR-212 pattern.

The Reviewer during proposal verdicts (verdict mode) never enters reflection mode. The two modes are invocation-separated:

- Verdict mode: invoked by `review_proposal_dispatch.py::_run_ai_reviewer` on every proposal. Reads substrate, reasons, returns approve/reject/defer. Existing behavior.
- Reflection mode: invoked by `back-office-reviewer-reflection` task executor on cadence when condition thresholds cross. Reads accumulated substrate + its own track record, reasons about framework, returns proposed changes.

This separation is structural. Verdict mode doesn't know reflection exists; reflection mode doesn't interrupt verdicts.

### D3 — Invocation gate is a cost floor, not a threshold DSL

**Amended 2026-04-24 (Commit 2 rewrite).** An earlier draft of this ADR proposed an operator-authored trigger DSL — YAML `when` expressions with comparator operators, metric names, AND/OR composition — that would fire reflections when thresholds crossed. That design re-imposed continuous config-authoring on the operator (the canon thesis explicitly wants to eliminate this) and put *the noticing of drift* in a zero-LLM expression parser rather than in the persona's judgment (which is what `docs/architecture/persona-reflection.md` actually asks for).

The correct shape — mirroring `ManageTask(action="evaluate")` exactly — is:

- **Invocation gate** (zero LLM, cost floor only): *is it worth invoking the persona?* Two rules:
  1. At least one new decision in `decisions.md` since the last reflection (nothing to reflect on otherwise).
  2. At least 24 hours since the last reflection (rate limit, prevents reactive cascades).
- **Persona judgment** (one LLM call, Haiku): the persona itself reads IDENTITY + principles + PRECEDENT + MANDATE + AUTONOMY + recent decisions + per-domain `_performance.md`, and *it* decides whether anything warrants framework change. Same shape as task-evaluation deciding whether a task output is on-spec.
- **Structured verdict**: `no_change | narrow | relax | character_note` + reasoning + evidence citations. `no_change` is the common outcome — invocation cost is cheap vs the thesis value.

No operator-authored metrics. No YAML `when` expressions. No threshold arithmetic. The persona is the judgment; the task runner is the cadence.

The two gate constants live in `services/back_office/reviewer_reflection.py` as module-level constants (`_MIN_NEW_DECISIONS = 1`, `_MIN_HOURS_BETWEEN_REFLECTIONS = 24`). Future work may let operators tune these via principles.md prose, but the zero-knob default is correct for V1 — same "operator seeds direction, persona lives its lifecycle" thesis.

### D3 rationale — why this isn't the same mistake as a DSL

A DSL *could* have zero-width — a trivial DSL like `every_day_after_one_new_decision` is still a tiny language, still operator-authored, still re-imposing config work. Reducing DSL expressiveness doesn't solve the category mistake; deleting the DSL does. The module has two constants, the operator has no YAML to write, and the persona does the judging. If a pattern emerges where operators *need* to tune invocation cadence, it surfaces as a single `min_hours_between_reflections:` prose line in principles.md — not as an expression grammar.

### D4 — Reflection-mode prompt is distinct from verdict-mode prompt

A new system prompt `_REFLECTION_SYSTEM_PROMPT` in `api/agents/reviewer_agent.py`. Distinct from `_SYSTEM_PROMPT` but persona-aware in the same way — it reads IDENTITY.md to know *who* is reflecting.

Reflection-mode prompt structure:

```
You are reflecting on your own performance as the judgment seat.

[IDENTITY.md] — who you are. Your character shapes how you reason about
your own track record.

Substrate available:
- Your current principles.md (the framework you've been applying).
- PRECEDENT.md — operator-authored durable interpretations you must
  respect in any framework adjustment. Precedent always wins over
  framework; your reflection cannot propose changes that contradict
  precedent.
- Recent decisions.md trail (last N verdicts).
- Per-domain _performance.md (realized outcomes from your approvals).
- calibration.md (rolling windows).
- The triggering condition that brought this reflection about.

Your task: propose framework adjustments grounded in the substrate.
Possible outcomes:
  - no_change: evidence doesn't warrant framework adjustment.
  - narrow: tighten an existing rule or add a new defer condition.
    Cite specific decisions + outcomes that justify the narrowing.
  - relax: remove an overly conservative rule. Cite specific decisions
    that show the rule was too conservative (approvals deferred unnecessarily
    that would have succeeded). Relaxation is the highest-bar change;
    require stronger evidence than narrowing.
  - character_note: propose an edit to IDENTITY.md. Rare — only when
    decisions reveal a persona trait that isn't in the declared
    character or that's been contradicted by actual behavior.

Constraints you must honor:
  - You may only propose changes to IDENTITY.md or principles.md.
  - You cannot propose changes to AUTONOMY.md, MANDATE.md, PRECEDENT.md,
    or anywhere outside /workspace/review/.
  - You cannot propose changes that would widen the autonomy delegation.
    Your principles can only narrow the raw ceiling, never widen it.
  - You cannot propose changes that contradict PRECEDENT.md. Operator
    interpretation always wins.
  - Every proposed change must cite specific substrate evidence
    (decision IDs, outcome deltas, threshold crossings). Changes
    without evidence must be declared no_change.

Return structured output via the `return_reflection_proposals` tool
(forced tool call).
```

Model: Claude Sonnet 4.6 (same as verdict mode). Reflection is heavier reasoning but not categorically different cognitive workload; the same model tier is appropriate. Cost tradeoff revisit is an open question (§Open Questions).

### D5 — Write-back is revision-chained via ADR-209

Every reflexive file change is a `write_revision()` call with:

- `authored_by="reviewer:{occupant_identity}"` (e.g. `"reviewer:ai:reviewer-sonnet-v4"`).
- `message` containing the proposed change's rationale + substrate citations.

Operator's revert path is the existing ADR-209 revision chain — open Files tab, find last `authored_by="operator"` revision, revert. No new primitive required.

Reflections.md append-only entries follow the same pattern: `write_revision(path="/workspace/review/reflections.md", content=full_entry, authored_by="reviewer:{...}", message="reflection run <timestamp>")`. The file is append-only by convention; the revision chain preserves the full history.

### D6 — Operator visibility: chat notification + briefing section

When a reflection run produces material changes (anything beyond `no_change`), the task executor publishes:

1. A `role='system'` message in the workspace's active chat thread (pattern symmetric to ADR-212 unified chat verdict messages). Message content:
   ```
   Reviewer reflected on {N} verdicts + {M} outcomes. Trigger: {name}.
   Changes: {count} proposed, {applied} applied.
     - principles.md: {summary of changes}
     - IDENTITY.md: {summary of changes or "no change"}
   Full reasoning: /workspace/review/reflections.md
   ```
2. A dedicated section in the next daily-update briefing (if scaffolded):
   ```
   ## Reviewer evolution
   {ranging} over {N} verdicts. Most recent reflection: {timestamp}.
   Last material change: {summary}.
   ```

Reflections.md itself is the full audit surface — append-only, with every reflection entry carrying trigger, decisions analyzed, outcomes analyzed, changes made, reasoning, evidence citations.

Operator never encounters a "silent" material change. `no_change` reflections don't notify (they are noise-suppression for the audit surface), but the reflections.md entry is still written so the operator can inspect retrospectively if they want.

### D7 — Invariants (per persona-reflection.md §4)

All six invariants from the canon doc carry through:

1. **Never widens delegation.** ADR-217 D4. Scope ceiling enforces this structurally — reflection cannot write to AUTONOMY.md. The reflection-mode prompt explicitly declares this.

2. **Rate-limited.** Default at most one reflection per back-office task cadence (daily). Individual triggers have per-trigger `min_days_between` values to prevent reactive cascades. The back-office task itself runs on a single schedule; multiple triggers firing on the same run result in one reflection (the task picks the highest-priority trigger by declared ordering; subsequent triggers wait until their rate-limit interval elapses).

3. **Evidence-cited.** Every proposed change carries substrate citations. Changes without evidence must be declared `no_change`. The reflection-mode tool schema requires evidence strings on every proposal.

4. **Revertible.** ADR-209 revision chain + `authored_by` attribution. Operator reverts any file to its last operator-authored revision at any time.

5. **Never silent.** Material changes trigger chat notification + briefing section. Only `no_change` reflections are quiet (the reflections.md entry is still written).

6. **Mandate-preserving.** Reflection cannot produce a framework that contradicts MANDATE. The reflection-mode prompt declares this explicitly; the post-reflection write-back step includes a programmatic sanity check that the proposed file content doesn't eliminate narrowing conditions tied to the declared MANDATE boundaries.

### D8 — Staging: five commits, same discipline as ADR-216 / ADR-217

- **Commit 1** (this ADR): Ratification only. Docs.
- **Commit 2**: Back-office task `back-office-reviewer-reflection` + invocation-gate module `services/back_office/reviewer_reflection.py`. Zero-LLM gate (new-decisions + hours-elapsed floors), substrate gather, exits when gate doesn't pass. Phase B (LLM invocation) + Phase C (write-back) stubbed behind `_APPLY_WRITEBACK = False` so Commit 2 ships green. Task materializes on commerce + trading connect (same trigger as reviewer-calibration per ADR-211 D6). No operator-authored DSL, no YAML triggers in principles.md — the original DSL-style draft of this commit was reverted; the gate is two module-level constants and the persona does the judgment.
- **Commit 3**: Reflection-mode invocation. `reviewer_agent.py::run_reflection()` sibling function to `review_proposal()`. `_REFLECTION_SYSTEM_PROMPT` constant. `_REFLECTION_TOOL` forced tool-call schema (`return_reflection_proposals` returning structured list of proposed changes + reasoning + evidence citations + `no_change` fallback). Reads IDENTITY + current principles + PRECEDENT + decisions tail + calibration + relevant _performance.md.
- **Commit 4**: Write-back + visibility. `services/reflection_writer.py` applies the structured output via ADR-209 `write_revision()`. Mandate-preservation sanity check. `role='system'` chat notification via existing `write_reviewer_message` (or sibling). Daily-update briefing template gains "Reviewer evolution" section. reflections.md append.
- **Commit 5**: alpha-trader E2E validation. Let Simons-persona accumulate real + synthetic decisions, force-trigger reflection, observe the full loop: condition check → reflection invocation → proposed changes → write-back → chat notification → revision chain audit. Write observation log documenting the first cycle.

Each commit lands independently green. Commit 1 docs-only; Commits 2–4 are code; Commit 5 is alpha validation.

---

## Implementation details

### Back-office task declaration

Registered in `api/services/task_types.py` with `output_kind="system_maintenance"`, `default_schedule="daily"`, `executor="services.back_office.reviewer_reflection"`. Materializes on commerce or trading platform connect (`api/routes/integrations.py`) alongside `back-office-outcome-reconciliation` and `back-office-reviewer-calibration` — same trigger, same substrate lineage (reconciler writes `_performance.md`; calibration summarizes per-occupant verdict tallies; reflection reads both plus raw decisions to let the persona notice drift).

### reviewer_reflection module

```
services/back_office/reviewer_reflection.py

- run(client, user_id, task_slug) -> dict  # task executor entry point
  Same task-assessment shape as ManageTask._handle_evaluate:
    1. Read substrate (decisions.md + _performance.md + last-reflection ts)
    2. Invocation gate (two constants, zero LLM):
         - at least _MIN_NEW_DECISIONS since last reflection, AND
         - at least _MIN_HOURS_BETWEEN_REFLECTIONS elapsed
       If gate doesn't pass: return "skipped: reason" verdict. Zero cost.
    3. If gate passes: gather full persona substrate (IDENTITY +
       principles + PRECEDENT + MANDATE + AUTONOMY + recent decisions +
       performance summary) for the Commit 3 reflection-mode prompt.
    4. Commit 2 stops here with _APPLY_WRITEBACK=False; returns
       "would invoke" verdict + evidence summary. Commits 3 + 4 wire
       the LLM call + reflection_writer.
  Returns the standard back-office executor shape
    {"content": "<markdown report>", "structured": {...}}

- _decisions_since(decisions, cutoff) -> list[dict]
- _hours_since(then, now) -> float | None
- _format_recent_decisions(decisions, limit=30) -> str  # for prompt
- _format_performance_summary(outcome_totals) -> str     # for prompt
- _read_last_reflection_ts(client, user_id) -> datetime | None
```

Reuses `reviewer_calibration._read_decisions` + `_read_domain_outcome_totals` via import (singular-implementation, no duplicated parsing).

### reflection_writer

```
services/reflection_writer.py

- apply_reflection_writes(client, user_id, reviewer_identity, proposals) -> dict
  - Validate each proposal against scope ceiling + mandate-preservation
  - write_revision() via authored_substrate for each approved proposal
  - Append reflections.md entry
  - Return summary for chat notification

- validate_proposal(proposal, current_mandate, autonomy_ceiling) -> tuple[bool, str]
- render_reflections_md_entry(run_timestamp, trigger, proposals_applied) -> str
```

### Chat + briefing notifications

`role='system'` message in the workspace's active chat session via existing `write_reviewer_message` (already plumbed per ADR-212 unified chat thread). Same message is considered for daily-update briefing "Reviewer evolution" section inclusion if a briefing exists.

---

## Stress tests (acceptance criteria)

All eight stress tests from persona-reflection.md §8 become acceptance criteria for this ADR's implementation:

1. **ST1 (unbounded reflection)**: back-office task cadence + per-trigger min_days_between prevents cascade.
2. **ST2 (delegation widening)**: scope ceiling (reflection cannot write AUTONOMY.md) + reflection-mode prompt + mandate-preservation sanity check.
3. **ST3 (mandate rewriting)**: scope ceiling prevents writes outside /workspace/review/.
4. **ST4 (silent drift)**: material changes → chat notification + reflections.md entry. `no_change` still logs to reflections.md.
5. **ST5 (incoherence)**: evidence-citation requirement + revert path + operator audit.
6. **ST6 (rotation inheritance)**: OCCUPANT rotation doesn't touch IDENTITY/principles/reflections.md; new occupant inherits evolved state.
7. **ST7 (corrupted _performance.md)**: reconciliation task has its own gates; reflection reads without re-verifying. Garbage-in-garbage-out mitigated by rate limit + evidence citation (bad data produces reflections that can't cite legitimate evidence, surfacing as weak proposals the operator can revert).
8. **ST8 (always-revertible)**: ADR-209 revision chain + `authored_by` distinction.

Each acceptance criterion must be testable in the Commit 5 E2E validation.

---

## Alternatives considered

### Alt 1 — Verdict-time reflection

Let the Reviewer decide mid-verdict to also reflect. Rejected because it conflates two reasoning modes and risks the Reviewer choosing when to "fix itself" in the middle of a time-sensitive decision. Separation of invocation modes per D2 is cleaner.

### Alt 2 — Operator-triggered reflection only

Require the operator to explicitly request reflection. Rejected because it re-imposes the continuous-config-authoring burden the thesis explicitly wants to eliminate. Operator can still pause reflection by disabling the task; substrate-triggered is the default.

### Alt 3 — Broader scope (domain Agents reflect too)

Extend reflection to `/agents/{slug}/` for user-authored Agents. Deferred — Reviewer pattern must prove first. Domain Agents use a different file convention (single-file AGENT.md per ADR-216 D9) and may warrant a different reflection shape. Handle in a future ADR.

### Alt 4 — Let reflection edit PRECEDENT.md

Allow reflection to propose precedent entries. Rejected — precedent is operator-authored declaration by definition (persona-reflection.md v1.1). The persona can cite precedent and honor it; authoring it remains the operator's privilege. If the persona notices a gap that *should* become precedent, it says so in reflections.md; operator decides whether to author.

### Alt 5 — Eliminate rate-limit

Let reflection run every verdict. Rejected — violates persona-reflection.md §3 rate-limit invariant. The framework author who rewrites their framework every hour is overreacting, not learning.

---

## Cross-references

- `docs/architecture/persona-reflection.md` v1.1 — the canon doc this ADR implements.
- `docs/architecture/agent-composition.md` — will be amended in Commit 3 with reflection-mode prompt + substrate reads.
- `api/prompts/CHANGELOG.md` [2026.04.24.5] entry — Reviewer v4 PRECEDENT wiring. v4 is the v-baseline for v5 reflection-mode additions (reflection-mode prompt is new, doesn't replace v4 verdict prompt).
- ADR-164 — Back-office tasks pattern. Reflection follows this pattern (YARNNN-owned, executor declaration, task runtime).
- ADR-194 v2 — Reviewer seat interchangeability. Rotation doesn't touch reflected substrate.
- ADR-195 v2 — Money-truth accumulation. Reflection reads `_performance.md` as substrate evidence; it doesn't reconcile outcomes itself.
- ADR-209 — Authored Substrate. Revision chain + `authored_by` is the reflection-safety mechanism.
- ADR-216 — Persona wiring. Reflection evolves the persona ADR-216 introduced.
- ADR-217 — Workspace autonomy. AUTONOMY.md is outside scope ceiling; reflection cannot touch it.
- Shared governance hardening (commit `fd4917a`) — PRECEDENT.md. Reflection reads + honors but cannot write.

---

## Implementation status

- **Commit 1** (this ADR): Implemented 2026-04-24 (commit `e457474`).
- **Commit 2** (back-office task + invocation-gate module): Implemented 2026-04-24 (clean version `9f8480e`). Note: an earlier DSL-style draft of Commit 2 (`34c5822`) was reverted (`d4c0d88`) before the cleaner task-assessment-shape version landed. D3 rewritten in-place on the same day to reflect the simpler approach.
- **Commit 3** (reflection-mode invocation): Implemented 2026-04-24 (commit `b5a7ee8`). `agents/reviewer_agent.py` gains `run_reflection()` sibling of `review_proposal()` + `_REFLECTION_SYSTEM_PROMPT` + `_REFLECTION_TOOL` + `ReflectionVerdict` TypedDict. Cost-conscious Haiku model via `REFLECTION_MODEL_SLUG`. `REVIEWER_MODEL_IDENTITY` bumped `v4 → v5`. `back_office/reviewer_reflection.py` flipped from stub to invoking `run_reflection` when gate passes; verdict populated in structured output. Write-back still stubbed (`_APPLY_WRITEBACK = False`) — Commit 4 lands writer.
- **Commit 4** (write-back + visibility): Implemented 2026-04-24. `services/reflection_writer.py` implements `apply_reflection_writes` — validates proposals against scope ceiling (principles.md / IDENTITY.md only) + mandate-preservation forbidden-phrase heuristic + content-length minimum, writes via ADR-209 `write_revision` with `authored_by="reviewer:{occupant_identity}"`, appends structured entry to `/workspace/review/reflections.md`, publishes `role='reviewer'` chat notification for material verdicts via ADR-212 `write_reviewer_message`. `back_office/reviewer_reflection.py` flipped `_APPLY_WRITEBACK = True` and wired writer into `run()`. Never raises — partial-failure still produces a clean task-output summary.
- **Commit 5** (alpha-trader E2E validation): Pending.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-24 | v1 — initial draft. Implements persona-reflection.md v1.1 thesis. Eight decisions (D1 scope, D2 substrate-triggered, D3 operator-declared thresholds, D4 reflection-mode prompt, D5 revision-chained write-back, D6 chat + briefing visibility, D7 invariants, D8 five-commit staging). Implementation details for back-office task + reflection_writer module. Stress tests lifted from persona-reflection.md §8 as acceptance criteria. Five alternatives considered and rejected. |
| 2026-04-24 | v1.1 — D3 rewritten in-place during Commit 2 work. The original D3 (operator-authored trigger DSL with YAML `when` expressions, comparator grammar, metric table) re-imposed continuous config-authoring on the operator — contradicting the canon thesis "operator's standing role shifts from config authoring to seeding direction." Commit 2's DSL-shape implementation (`34c5822`) was reverted (`d4c0d88`). Rewritten D3: invocation gate is two module-level constants (`_MIN_NEW_DECISIONS = 1`, `_MIN_HOURS_BETWEEN_REFLECTIONS = 24`) and the persona itself is the judgment that notices its own drift. Same task-assessment shape as `ManageTask._handle_evaluate`. No DSL. Implementation details + Staging §Commit 2 updated accordingly. Other decisions (D1 scope, D2 substrate-triggered, D4 reflection-mode prompt, D5–D8) unchanged. |
