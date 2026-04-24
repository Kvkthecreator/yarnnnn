# Persona Reflection — Reviewer-Self-Evolving Substrate

> **Status**: Canonical framing.
> **Audience**: Engineers and operators touching Reviewer substrate, persona lifecycle, or the back-office task set.
> **Purpose**: Establish that the Reviewer's persona is a **living accumulator**, not a static authored configuration — and lay the ground rules for how, when, and how much the persona evolves through reflection on its own operational record. This doc precedes any ADR that implements reflection; every such ADR should cite and amend this doc in the same commit.

---

## 1. The thesis

**Persona is accumulated experience, not authored configuration.**

Under ADR-216, YARNNN introduced the persona as a first-class substrate concept — the operator authors `/workspace/review/IDENTITY.md` + `/workspace/review/principles.md` to declare *who* the Reviewer is and *what framework* it applies. ADR-217 separated delegation (AUTONOMY.md, operator-only) from framework (principles.md, operator-authored).

Both ADRs treated persona files as static-authored-content that the operator writes and the Reviewer reads.

That model is incomplete. Real judgment actors — human CROs, seasoned portfolio managers, domain experts — are not static. They start with a declared framework and accumulate experience that changes how they reason. The framework they apply at year three is genuinely different from the framework at day one, even if the declared character is stable. Our architecture has no way to express this: file content stays in whatever shape the operator first wrote, and the persona reasons against that frozen snapshot indefinitely.

The canonical fix is symmetric to how the rest of YARNNN handles accumulation:

- `_performance.md` accumulates **money-truth** from platform outcomes (ADR-195). The operator doesn't hand-write P&L; the reconciliation task writes it from reality.
- Context domains accumulate **domain knowledge** from platform syncs (ADR-151 + platform bots). The operator doesn't hand-write competitive intelligence; platform-sync tasks write it from reality.
- `PRECEDENT.md` accumulates **operator-authored durable interpretations** from recurring ambiguities (commit `fd4917a`, 2026-04-24). The operator writes a precedent once; all agents honor it thereafter.
- Persona files should accumulate **judgment character** from the Reviewer's own decisions + outcomes. The operator seeds it; reflection writes the rest from reality.

**Precedent and reflection are operator-sided and persona-sided halves of the same gap.** Both answer "how does framework evolve as reality accumulates?" — but via different authorship paths. Precedent is the operator declaring a new interpretation they've decided to lock in ("if signal has <20 realized trades, never auto-approve"). Reflection is the persona noticing its own track record has drifted and proposing a framework adjustment ("my cold-start defer condition should relax now that 20 trades have accumulated"). Both accumulate inside the MANDATE + AUTONOMY boundaries the operator sets; neither widens delegation.

The operator's standing role shifts from *"continuous config authoring"* to *"seeding direction + declaring precedent + auditing persona evolution."* The operator writes MANDATE (what this workspace is running), AUTONOMY (how autonomous AI may be), PRECEDENT as the operation matures (durable interpretations the operator has decided), and the initial IDENTITY + principles (the starting character). From then on, the persona lives its lifecycle through reflection — with the operator reviewing retrospectively rather than manually updating framework files.

This is what closes the autonomous loop your mandate expects. Without reflection, the persona either stays naive (cold-start condition I defer forever) or demands continuous operator intervention to keep its framework fresh. Neither is the autonomous operation YARNNN promises.

---

## 2. What's reflective vs what isn't

Explicit scope, with a clean boundary between what evolves autonomously and what stays operator-owned.

### Reflective substrate (persona writes to itself)

Under `/workspace/review/` — the Reviewer's own directory, seat-bound:

| File | Operator's role | Persona's role via reflection |
|------|-----------------|-------------------------------|
| `IDENTITY.md` | Seeds initial persona at scaffold time | Evolves character declarations as accumulated decisions show what the persona actually does under pressure |
| `principles.md` | Seeds initial framework | Adjusts narrowing conditions, tightens or relaxes defer rules as realized outcomes validate or invalidate prior framework claims |
| `reflections.md` **(new)** | Read-only (audit) | Writes meta-reasoning about its own evolution — the running log of *why* the persona changed, cited to specific substrate evidence |

### Operator-owned substrate (persona never writes)

Under `/workspace/context/_shared/` — workspace-scoped standing declarations:

| File | Author | Why persona doesn't touch |
|------|--------|---------------------------|
| `MANDATE.md` | Operator only | Principal's declaration of what the operation is running. A servant rewriting the mandate would be the servant declaring what the master is doing — inversion of principal-agent. |
| `AUTONOMY.md` | Operator only | Delegation ceiling. A servant cannot widen their own permission. ADR-217 D4 invariant. |
| `PRECEDENT.md` | Operator only | Operator-authored durable interpretations / boundary-case resolutions (committed `fd4917a`, 2026-04-24). Read by YARNNN + Reviewer + domain Agents. This is the *operator-authored sibling* to reflection: when the operator notices a recurring ambiguity, they write a precedent; when the persona notices its own framework drift, it reflects. Precedent declares; reflection evolves. Both accumulate within operator-declared MANDATE + AUTONOMY. |
| `IDENTITY.md` (workspace) | Operator only | The operator's self-description. Persona's opinion about who the operator is is not authoritative. |
| `BRAND.md` | Operator only | The operation's voice. Persona isn't authorized to redefine the operator's voice. |
| `CONVENTIONS.md` | Operator only | Workspace conventions. Structural; operator's to set. |

### Seat-state substrate (rotation primitive writes)

| File | Author |
|------|--------|
| `OCCUPANT.md` | `rotate_occupant()` only |
| `handoffs.md` | `rotate_occupant()` only (append-only) |
| `decisions.md` | Reviewer itself at verdict time (append-only) |
| `calibration.md` | Back-office calibration task (regenerates per cadence) |

### Context domain substrate

Under `/workspace/context/{domain}/` — accumulated domain intelligence (competitors, trading, customers, etc.). Persona doesn't reflect into these directly. If accumulated context seems wrong, that's an operator + context-task responsibility — the Reviewer can *notice* drift and flag it in reflections.md, but doesn't rewrite domain files.

### The boundary rule

**The Reviewer reflects only on substrate it authored or wrote.** decisions.md is its output; calibration.md is its track record; IDENTITY + principles are its character. MANDATE, AUTONOMY, `_shared/` files, context domains are operator + orchestration territory.

This boundary is symmetric to how orchestration and operator divide labor: operator declares direction; orchestration accumulates within that direction. Persona reflection is a specific instance of that pattern — the persona accumulates within operator-declared boundaries.

---

## 3. The reflection loop

Reflection is **substrate-triggered**, executed by a back-office task (analogous to `back-office-outcome-reconciliation` per ADR-195). The Reviewer during proposal verdicts stays focused on the current proposal — it never decides to reflect mid-verdict. Reflection is a separate invocation mode, on a separate cadence.

### The loop, step by step

**Step 1 — Scheduled scan.** A back-office task `back-office-reviewer-reflection` runs on cadence (default: daily, operator-tunable). Task reads:

- `decisions.md` — verdict trail since last reflection.
- `_performance.md` per context domain — realized outcomes tied to this Reviewer's approvals.
- `calibration.md` — per-occupant × verdict rolling windows.
- The current `IDENTITY.md` + `principles.md` (the frozen-in-file version).

**Step 2 — Condition check (zero-LLM).** Task evaluates operator-declared thresholds:

- Has the Reviewer rendered ≥ N verdicts since last reflection? (rate limit)
- Has realized outcome attribution for this Reviewer's approvals drifted from declared baselines by ≥ X%?
- Has decision distribution (approve/reject/defer ratios) shifted materially vs baseline?
- Has a transition condition fired (cold-start → steady-state crossover, regime shift detection, etc.)?

If none of the thresholds are crossed, task exits without invoking reflection. Zero LLM cost. Reflection is *expensive deliberation*; it shouldn't run every cron tick.

**Step 3 — Reflection invocation (LLM).** If a threshold crossed, the task invokes the Reviewer in a new **reflection mode** (distinct from verdict mode). Input:

- Persona-as-currently-authored (IDENTITY + principles).
- Recent decisions.md trail.
- Performance data relevant to recent approvals.
- Calibration deltas from declared baselines.
- The trigger that fired — what condition specifically brought this reflection about.

The Reviewer reasons in reflection mode: *"Given my record of decisions + the realized outcomes of my approvals + the threshold that triggered this reflection, what should change in my framework? My character?"*

**Step 4 — Scope-bounded write.** Reflection produces structured output:

- **No change** — "evidence does not warrant framework adjustment, continuing as-is." Common outcome. Written as a `reflections.md` entry only.
- **Principles narrowing adjustment** — "remove this defer condition because N successful approvals under it contradicted it" or "add this defer condition because pattern X emerged in recent rejections."
- **Principles widening adjustment** — "loosen this narrowing because evidence shows it was too conservative."
- **IDENTITY character refinement** — rarer, only when decisions reveal a persona trait that wasn't in the declared character or one that's been contradicted by actual behavior.

Each adjustment is written as a revision to the relevant file, with `authored_by="reviewer:{occupant_identity}"` per ADR-209 revision chain. The revision message cites specific substrate evidence.

**Step 5 — reflections.md entry.** A running log at `/workspace/review/reflections.md` (append-only) records every reflection run:

```markdown
--- reflection ---
timestamp: 2026-05-15T04:00:00Z
trigger: 30-trade-calibration-crossover
reviewer_identity: ai:reviewer-sonnet-v3
decisions_analyzed: 32
outcomes_analyzed: 28 (4 open positions)
changes_made:
  - principles.md: removed narrowing condition "defer when
    _performance.md empty" (no longer applicable post-calibration)
  - principles.md: added narrowing condition "defer when Signal 3
    recent-10-trade realized expectancy drops below 0.2R"
    (evidence: 3 of last 5 Signal 3 trades underperformed declared
    baseline by 30%+)
  - IDENTITY.md: no change
  - reflections.md: this entry
reasoning: |
  Signal 3 (PEAD) showed declared baseline Sharpe of 0.5 but
  realized 10-trade Sharpe is 0.24 with high realized variance.
  This is borderline retirement territory per the declared
  risk decay rule but not yet triggered. Adding an intermediate
  narrowing condition lets me tighten without auto-retiring
  until the next quarterly audit decides. This narrows my
  delegation within the same AUTONOMY.md ceiling — no
  overreach beyond what's authorized.
---
```

**Step 6 — Operator visibility.** When material changes land (anything beyond "no change"), a `role='system'` message lands in the active chat thread:

> *"Your Reviewer reflected on 32 recent verdicts + 28 outcomes. Added one narrowing condition on Signal 3 (declining expectancy). Removed cold-start condition (no longer applicable). Full reasoning in `/workspace/review/reflections.md`."*

Same message goes in the daily-update briefing. Operator can inspect decisions.md + reflections.md + the revision chain on IDENTITY/principles to audit. Any reflexive change can be reverted to the prior operator-authored revision if the operator disagrees with the persona's self-update.

### The loop, as a dimensional picture

Reflection is a **Mechanism-axis** operation (Axiom 5) operating on **Substrate-axis** state (Axiom 1) to refine **Identity-axis** expression (Axiom 2) per operator-declared **Purpose-axis** delegation (Axiom 3). It sits between the continuous judgment loop (proposal verdicts) and the continuous outcome loop (money-truth reconciliation), closing the recursion the architecture wants: outcomes feed back to persona character, which feeds forward to better judgment, which produces better outcomes.

---

## 4. Scope and invariants

### Scope ceiling

Reflection can rewrite:
- `IDENTITY.md` (full rewrite permitted; see magnitude limit below)
- `principles.md` (full rewrite permitted; see magnitude limit below)
- `reflections.md` (append-only)

Reflection cannot touch:
- `MANDATE.md` (operator-only, ADR-207)
- `AUTONOMY.md` (operator-only, ADR-217)
- `/workspace/context/_shared/*.md` (operator-only, ADR-206)
- `/workspace/context/{domain}/*.md` (context-task-only, ADR-151/195)
- `OCCUPANT.md`, `handoffs.md` (rotation primitive only)
- `decisions.md` (verdict-mode only, never reflection-mode)
- `calibration.md` (calibration task only)
- Anything outside `/workspace/review/`

### Invariants

1. **Never widens delegation.** ADR-217 D4. A reflection that loosens a narrowing condition is legal; a reflection that rewrites AUTONOMY.md or declares "I can auto-approve X class of actions" is not. The scope ceiling enforces this structurally.

2. **Rate-limited.** At most one reflection per scheduled cadence (default: daily). Prevents reactive over-correction. A single bad trading day can't trigger a cascade of persona rewrites.

3. **Evidence-cited.** Every change ships with substrate evidence in the revision message and reflections.md entry. The persona cannot justify a framework change without citing specific decision patterns, outcome deltas, or threshold crossings. This makes magnitude self-limiting — you can't make big changes without commensurate evidence.

4. **Revertible.** Every reflexive write lands a new revision via ADR-209. Operator can revert to the last `authored_by="operator"` revision at any time. The revision chain is the audit floor and the undo path.

5. **Never silent.** Material reflexive changes surface to operator via chat + briefing. A persona that evolves without operator visibility is indistinguishable from drift.

6. **Mandate-preserving.** No reflection can produce a framework that contradicts the declared MANDATE. If the operator's mandate says "submit equity orders per declared signals," the persona can't reflect itself into "I should refuse all trades because trades are risky." The persona's evolution is always *in service of the mandate*, never *contrary to it*.

### What prevents drift

The five invariants plus one authorship rule:

- Scope ceiling keeps reflection inside `/workspace/review/`.
- Rate-limit prevents reactive cascades.
- Evidence-citation prevents unjustified changes.
- Revert path gives operator the final say.
- Material-change surfacing gives operator visibility.
- `authored_by` attribution per ADR-209 separates reflexive revisions from operator revisions, so provenance is always clear.

Drift is possible in theory (a persona that writes bad reflections, accumulating into a degraded framework). The invariants prevent *silent* drift. Operator audit + revert path corrects *visible* drift. This is the same discipline humans apply to junior analysts: give them scope, require citations for changes, check their work periodically, correct when needed.

---

## 5. Operator visibility and override

### What the operator sees

Three surfaces:

1. **Chat inline notifications** when material reflections land. `role='system'` messages in the active thread describe what changed with a link to the full reflections.md entry. Persistent, in-context.

2. **Daily-update briefing section** — a "Reviewer evolution" line showing whether the persona changed overnight, and if so what kind (narrowing / widening / no change). Retrospective.

3. **`/workspace/review/reflections.md` stream** — full trail of every reflection run, with reasoning, citations, and change summary. Auditable at any time via the Files tab.

4. **Revision chain per file** — `IDENTITY.md` and `principles.md` show every revision with `authored_by` attribution. Operator can diff between revisions to see exactly what the persona changed and when.

### How the operator overrides

- **Revert a specific change**: operator edits the affected file via Files tab, returning it to whatever content they want. This lands as a new `authored_by="operator"` revision. The persona reads the operator's current revision on the next verdict — reflexive drift is overridable just by editing.

- **Pause reflection**: operator disables the `back-office-reviewer-reflection` task. Persona remains at current state indefinitely. Useful during known-volatile periods where the operator doesn't want autonomous framework drift.

- **Reset persona**: operator rewrites IDENTITY.md + principles.md from scratch. Reflection starts accumulating from zero against the new declared character. `authored_by="operator"` revision is a hard reset point.

- **Tighten scope**: operator can author a `reflection-scope.md` (optional, future work if needed) declaring "this persona may reflect on principles but not IDENTITY." Narrows the ceiling further if an operator is uncomfortable with full persona-character evolution.

### What the operator doesn't need to do

- Manually update persona files on cadence.
- Read decisions.md in raw form to judge whether the persona is working.
- Hand-tune narrowing conditions as calibration accumulates.
- Worry about which file changed — the revision chain + reflections.md tell the story.

This is the delegation completion the autonomous loop promises. Operator-authored direction + autonomy delegation + initial character seed → persona lives its own lifecycle → operator reviews retrospectively rather than tuning continuously.

---

## 6. What this supersedes and amends

### Supersedes

- **The implicit "static persona" model** in ADR-216 + ADR-217. Both ADRs described IDENTITY + principles as operator-authored artifacts. This doc widens that to operator-seeded, persona-evolved. The ADRs themselves remain authoritative for the substrate split and the categorical decisions; this doc reframes ongoing file ownership.

### Amends

- **GLOSSARY "Persona" entry** (ADR-216 D5 introduced). New definition:

  > **Persona** — a persona-bearing Agent's accumulated judgment character, seeded by operator at scaffold time and evolved by the persona itself through scheduled reflection against outcomes and decision history. Distinct from *principles* (the framework the persona applies) — though note that principles is itself part of the persona substrate that reflects, so the boundary between "character" and "framework" softens over time as the persona matures.

- **ADR-216 D4 read ordering**. Previously: "IDENTITY.md is operator-authored; Reviewer reads it at reasoning time." Now: "IDENTITY.md is operator-seeded and persona-evolved; Reviewer reads the current revision at reasoning time, with ADR-209 revision chain preserving the full authorship history."

- **ADR-217 D8 rotation semantics**. Previously: rotation does not touch IDENTITY/principles/AUTONOMY. That stands. Extended: rotation also does not touch reflections.md or the revision chain. A rotated occupant inherits the fully-evolved persona state; if the operator wants a reset on rotation, the reset is explicit (`authored_by="operator"` revision that overwrites).

- **`agent-composition.md` §3.2 Reviewer substrate read table**. Add `reflections.md` as a reviewer-generated file (scope: written in reflection mode, read by audit surfaces + the Reviewer itself for meta-awareness in subsequent reflections).

- **`agent-composition.md` §4.2 Reviewer-bound substrate table**. Update IDENTITY.md + principles.md author from "Operator" to "Operator (seed) + Reviewer (reflection)". Add reflections.md row.

---

## 7. Implementation staging

This doc precedes implementation. The implementation will land as a dedicated ADR with its own five-commit staging pattern (same discipline as ADR-216 / ADR-217):

### Stage 1 — ADR ratification

New ADR (next available number after 217) titled "Persona Reflection — Reviewer Self-Evolution." Decisions:

- D1: Reflection is persona-scoped (Reviewer evolves; domain Agents don't reflect in V1, deferred).
- D2: Substrate-triggered via back-office task, not verdict-time.
- D3: Scope ceiling = `/workspace/review/` only, with enumerated untouchable files.
- D4: Rate-limited (at most one reflection per task cadence).
- D5: Evidence-cited (every change carries substrate evidence in revision message + reflections.md).
- D6: Operator-revertible via ADR-209 revision chain + the `authored_by` attribution.
- D7: Operator-visible via chat notifications + briefing + reflections.md stream.
- D8: Reflexive writes never widen delegation (ADR-217 D4 upheld structurally).

### Stage 2 — Back-office task + condition check

- New task type: `back-office-reviewer-reflection`.
- Scaffolded at workspace_init Phase 5 as an essential task (operator-editable cadence; default daily).
- Condition-check logic in `api/services/back_office/reviewer_reflection.py`: reads decisions.md + calibration.md + _performance.md, evaluates operator-declared thresholds, returns "reflect" or "no-op."
- Thresholds declared in `principles.md` operator-authored section (or a separate `reflection-config.md` if cleaner).

### Stage 3 — Reflection-mode invocation

- New reflection-mode prompt for the Reviewer agent (`reviewer_agent.py::run_reflection` or sibling function distinct from `review_proposal`).
- Forced-tool-call returns structured output: list of proposed file changes + reasoning + evidence citations.
- `REVIEWER_MODEL_IDENTITY` strategy: keep `v3` for verdict-mode; reflection-mode uses same identity (reflection is the same occupant deliberating, just in a different mode).

### Stage 4 — Write-back + visibility

- New service `reflection_writer.py` that applies the structured output: writes revisions to IDENTITY/principles via ADR-209 `write_revision()` with `authored_by="reviewer:{occupant_identity}"`, appends to reflections.md.
- Chat notification via `role='system'` message (pattern symmetric to ADR-212 unified chat Reviewer verdicts).
- Daily-update briefing template gains "Reviewer evolution" section.

### Stage 5 — Alpha-trader E2E validation

- Let the Simons-persona accumulate 20+ trades' worth of decisions.
- Fire the first real reflection cycle.
- Observe: does the persona correctly remove its cold-start narrowing once `_performance.md` has sufficient trades? Does it add appropriate narrowing conditions based on observed patterns? Does the revision chain show clean authorship attribution?
- Write observation log documenting the first reflective cycle end-to-end.

Each stage ships independently green. Stage 1 is docs-only (this doc + the ADR); Stages 2–4 are code; Stage 5 is alpha validation.

---

## 8. Stress tests (what must not happen)

Writing these as acceptance criteria for whatever ADR implements reflection.

### ST1 — Unbounded reflection

*If reflection runs every minute, does the persona cascade?*

Should be impossible: rate limit is operator-declared with a floor of at minimum-daily cadence at default. The back-office task's cron interval is the floor; no verdict-time reflection exists.

### ST2 — Reflection widens delegation

*If the persona decides it should auto-approve more things, can it?*

Should be impossible: `AUTONOMY.md` is outside the scope ceiling. Reflexive writes to `/workspace/review/principles.md` can only narrow; removing a narrowing condition is not the same as widening delegation because the ceiling is in AUTONOMY.md which reflection cannot touch.

### ST3 — Reflection rewrites mandate

*If the persona decides the operation should run differently, can it edit MANDATE?*

Should be impossible: `_shared/*` is outside the scope ceiling. The persona can note in reflections.md that it thinks the mandate is ambiguous or contradicts accumulated outcomes; the operator must then decide.

### ST4 — Silent reflection drift

*Can the persona evolve without the operator noticing?*

Should be impossible: material changes trigger chat notification + briefing line + reflections.md entry. Only "no change" reflections are silent (they're noise suppression for the operator's audit surface).

### ST5 — Persona reflects itself into incoherence

*Can the persona produce a contradictory or nonsensical framework through successive reflections?*

Possible in theory (bad reflection reasoning, poor substrate, model errors). Mitigated by: evidence-citation requirement (each change must cite data), revision chain (operator can diff + revert), and operator-set rate limit (gives time for drift to surface before cascade). Not prevented categorically — this is where operator audit is the safety floor.

### ST6 — Rotation inherits stale evolution

*If the seat rotates human → AI → AI-v2, does the new occupant inherit the prior persona's state?*

Yes, by design. ADR-217 D8 says rotation doesn't touch operator-authored substrate; this doc extends that to persona-evolved substrate. A new occupant inherits the fully-evolved persona. If the operator wants reset-on-rotation, they author it explicitly (operator revision of IDENTITY + principles before or after rotation).

### ST7 — Reflection against corrupted _performance.md

*If outcome reconciliation is broken, does reflection produce bad framework updates?*

Possible: garbage-in-garbage-out. Mitigated by: reconciliation task has its own correctness gates per ADR-195; the reflection task depends on it but doesn't re-verify. If reconciliation is broken, other workspace behaviors break too; reflection is downstream of that problem, not a unique source of it.

### ST8 — Operator can always revert to a known-good state

*If reflection produces an unacceptable persona, can the operator undo?*

Yes: ADR-209 revision chain preserves every prior revision. Operator opens Files tab, finds the last `authored_by="operator"` revision, reverts. Future reflections continue from that point.

---

## 9. Open questions (deferred to ADR, not this doc)

1. **Threshold declaration location.** Should reflection triggers be in `principles.md` (operator declares "reflect when X condition holds") or in a separate file? Leaning principles.md because it's framework-adjacent, but ADR will decide.

2. **Domain Agent reflection.** This doc scopes V1 to Reviewer only. Domain Agents (user-authored per ADR-216 D9) have single-file AGENT.md carrying both persona + framework. Whether + how they reflect is a later ADR when the Reviewer pattern is proven.

3. **Reflection-mode prompt model.** Does reflection use the same Sonnet model as verdict-mode, or a deeper-reasoning model for the heavier meta-cognitive task? Cost vs quality tradeoff. ADR decides.

4. **Reflections.md rollup.** Does reflections.md accumulate forever (full audit trail) or does an older "reflections-archive" pattern emerge? Probably forever initially; compaction task later if length becomes a prompt-cost concern.

5. **Cross-persona reflection.** If multiple persona-bearing Agents exist in a workspace (future: Auditor, Advocate, etc.), can they reflect on each other's decisions? Not scoped here. Each persona reflects on its own substrate; cross-persona observation is noise-monitoring at most, not reflective rewriting.

---

## 10. Cross-references

- **FOUNDATIONS v6.0** — Axiom 7 (Recursion) is what this doc operationalizes at the persona layer.
- **ADR-195 v2** — Money-truth accumulation via reconciliation. Reflection is the symmetric pattern at the persona layer: accumulated reality shapes declared substrate.
- **ADR-209** — Authored Substrate. Revision chain + `authored_by` attribution is the mechanism that makes reflection safe (visible, revertible, audit-trailed).
- **ADR-212** — Layer mapping. Reviewer is the sole persona-bearing systemic Agent per ADR-216; this doc is about how that Agent self-maintains.
- **ADR-216** — YARNNN reclassification + persona wiring. Seeded IDENTITY at scaffold; reflection is what makes it evolve.
- **ADR-217** — Workspace autonomy substrate. AUTONOMY.md is explicitly outside the reflection scope ceiling — delegation is operator-only, reflexive writes cannot widen it.
- **PRECEDENT.md** (commit `fd4917a`, 2026-04-24) — The operator-authored sibling to reflection. Durable interpretations that compound across future decisions. Precedent declares (operator-authored); reflection evolves (persona-authored). Both accumulate inside MANDATE + AUTONOMY boundaries. When the implementing ADR for reflection lands, the Reviewer's reflection prompt should explicitly read PRECEDENT.md so that persona-authored evolutions respect operator-declared interpretations.
- **`docs/architecture/agent-composition.md`** — Canonical composition reference. Reflection adds a new execution mode (reflection-mode) distinct from verdict-mode; agent-composition.md amended accordingly when reflection ADR lands.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-24 | v1 — initial draft. Thesis (persona-as-accumulator), reflective vs non-reflective substrate boundary, reflection loop (six steps), scope + invariants (five rules + authorship), operator visibility + override, supersedes + amends prior ADRs, implementation staging (five stages), stress tests (eight), open questions (five deferred to ADR), cross-references. Written before the implementing ADR to pin the thesis; that ADR will cite + amend this doc in the same commit per the discipline declared in `agent-composition.md` §5.3. |
| 2026-04-24 | v1.1 — integrated PRECEDENT.md (commit `fd4917a`, landed 2 minutes after v1). Thesis section notes precedent and reflection as operator-sided and persona-sided halves of the same "framework evolves with reality" gap. Operator-owned substrate table adds PRECEDENT row. Cross-references note that the implementing ADR must have reflection-mode prompt explicitly read PRECEDENT.md so persona-authored evolutions respect operator-declared interpretations. No change to scope ceiling, invariants, or staging plan — PRECEDENT is a sibling authorship path, not a new reflection surface. |
