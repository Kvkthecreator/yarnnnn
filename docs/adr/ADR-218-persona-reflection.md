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

### D3 — Triggers are operator-declared thresholds, substrate-detected

Reflection triggers are authored in `principles.md` under a new `## Reflection triggers` section. Operator-friendly syntax, zero-LLM parseable. Default seeded template:

```yaml
---
# Reflection triggers — operator-declared conditions under which the
# Reviewer should reflect on its own framework. Each trigger is a
# condition + rate-limit tuple. Any trigger that fires invokes one
# reflection run; multiple firing triggers still run one reflection
# (rate-limited per §3 Invariants).

triggers:
  - name: cold_start_threshold_crossed
    description: "_performance.md transitioned from empty to non-empty"
    when: performance_md_first_populated
    min_days_between: 1

  - name: twenty_trade_calibration
    description: "Reviewer has rendered ≥20 verdicts since last reflection"
    when: verdicts_since_last_reflection >= 20
    min_days_between: 7

  - name: sharpe_drift
    description: "Realized Sharpe on approved trades drops ≥1.5× below declared baseline"
    when: sharpe_delta_vs_baseline >= 1.5
    min_days_between: 14

  - name: defer_rate_anomaly
    description: "Defer rate on last 50 verdicts ≥ 80% or ≤ 10%"
    when: defer_rate_last_50 >= 0.8 OR defer_rate_last_50 <= 0.1
    min_days_between: 7
---
```

Zero-LLM trigger evaluation: Phase A reads the YAML, computes each `when` expression against substrate (all observable from `decisions.md` counts + `_performance.md` fields + `calibration.md` rolling windows), returns `(triggered: bool, which_trigger: str | None)`.

Operators can add, remove, or tune triggers by editing principles.md. The triggers YAML lives inside principles.md because it is *framework* (what conditions warrant framework reflection) rather than *delegation* (AUTONOMY) or *interpretation* (PRECEDENT).

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
- **Commit 2**: Back-office task `back-office-reviewer-reflection` + condition-check module `services/back_office/reviewer_reflection.py`. Phase A zero-LLM logic, trigger evaluation against substrate, exits on "no trigger crossed" without invoking LLM. Task scaffolded at workspace_init Phase 5 as an essential YARNNN-owned task. Also: principles.md default template gains the "Reflection triggers" YAML block.
- **Commit 3**: Reflection-mode invocation. `reviewer_agent.py::run_reflection()` sibling function to `review_proposal()`. `_REFLECTION_SYSTEM_PROMPT` constant. `_REFLECTION_TOOL` forced tool-call schema (`return_reflection_proposals` returning structured list of proposed changes + reasoning + evidence citations + `no_change` fallback). Reads IDENTITY + current principles + PRECEDENT + decisions tail + calibration + relevant _performance.md.
- **Commit 4**: Write-back + visibility. `services/reflection_writer.py` applies the structured output via ADR-209 `write_revision()`. Mandate-preservation sanity check. `role='system'` chat notification via existing `write_reviewer_message` (or sibling). Daily-update briefing template gains "Reviewer evolution" section. reflections.md append.
- **Commit 5**: alpha-trader E2E validation. Let Simons-persona accumulate real + synthetic decisions, force-trigger reflection, observe the full loop: condition check → reflection invocation → proposed changes → write-back → chat notification → revision chain audit. Write observation log documenting the first cycle.

Each commit lands independently green. Commit 1 docs-only; Commits 2–4 are code; Commit 5 is alpha validation.

---

## Implementation details

### Back-office task declaration

Task TASK.md in `api/services/task_types.py`:

```python
"back-office-reviewer-reflection": {
    "agent_slug": "thinking-partner",
    "team": ["thinking-partner"],
    "required_capabilities": [],
    "mode": "recurring",
    "schedule": "0 3 * * *",  # Daily 03:00 UTC
    "delivery": "cockpit-only",
    "output_kind": "system_maintenance",
    "context_reads": [],
    "context_writes": [],
    "essential": True,
    "executor": "services.back_office.reviewer_reflection.run",
    "objective": {
        "deliverable": "Reviewer framework evolution (revisions to /workspace/review/IDENTITY.md + principles.md + reflections.md) when operator-declared triggers fire",
        "audience": "Operator (retrospective audit) + future Reviewer invocations (reads evolved substrate)",
        "purpose": "Persona-as-accumulator — the Reviewer evolves its framework from its own operational record per persona-reflection.md + ADR-218",
    },
    ...
}
```

Workspace-init Phase 5 scaffolds the task like other essential YARNNN-owned back-office tasks.

### reviewer_reflection module

```
services/back_office/reviewer_reflection.py

- run(client, user_id, task_slug) -> dict  # entry point called by task pipeline
  - Phase A: load_triggers(principles_md), evaluate_triggers(substrate), decide
  - Phase B: if triggered, invoke run_reflection() from reviewer_agent
  - Phase C: if changes proposed, apply_reflection_writes(), publish notifications
  - Returns structured run record for the task output folder

- load_triggers(principles_md: str) -> list[dict]
- evaluate_triggers(triggers, decisions_summary, performance_summary, calibration)
    -> tuple[bool, dict | None]  # (crossed, winning_trigger)
- decisions_summary(client, user_id, since_ts) -> dict
- performance_summary(client, user_id) -> dict  # aggregated across domains
```

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

- **Commit 1** (this ADR): Proposed.
- **Commit 2** (back-office task + condition-check): Pending.
- **Commit 3** (reflection-mode invocation): Pending.
- **Commit 4** (write-back + visibility): Pending.
- **Commit 5** (alpha-trader E2E validation): Pending.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-24 | v1 — initial draft. Implements persona-reflection.md v1.1 thesis. Eight decisions (D1 scope, D2 substrate-triggered, D3 operator-declared thresholds, D4 reflection-mode prompt, D5 revision-chained write-back, D6 chat + briefing visibility, D7 invariants, D8 five-commit staging). Implementation details for back-office task + reflection_writer module. Stress tests lifted from persona-reflection.md §8 as acceptance criteria. Five alternatives considered and rejected. |
