# ADR-303 — Reviewer Posture Taxonomy + Per-Posture Substrate Contracts

**Status**: **Proposed** (2026-05-26). Drafted from Hat-B evaluation findings; defines what postures the Reviewer can take per wake and what substrate-visibility contract each posture must honor. No code/prompt changes yet.
**Date**: 2026-05-26 (Proposed)
**Supersedes / amends**: Implicitly amends the persona-frame standing_intent contract in `api/agents/reviewer_agent.py::_PERSONA_FRAME` §392–§411 (current contract: "every reactive recurrence cycle produces a standing_intent.md write"). The current contract is over-broad — it conflates several distinct postures into one rule and forces silent-exits when the rule doesn't fit the cell.
**Builds on**: ADR-194 v2 (Reviewer substrate), ADR-258 revised (REVIEWER_PRIMITIVES + per-action narration), ADR-289 D4 (verdict-of-record substrate), ADR-293 (governance/operational taxonomy), ADR-295 (self-amendment evidence patterns), ADR-298 (trifecta), and ADR-302 (prompt-envelope discipline — drafted same session).
**Preserves**: FOUNDATIONS Axiom 1 (substrate is filesystem), Axiom 2 (judgment seat), Axiom 4 (Trigger), Axiom 8 (money-truth), ADR-209 attribution model, ADR-256 unified invoke_reviewer entry point, `DEFAULT_REVIEWER_WRITE_LOCKS`.

---

## 1. Problem statement

The Reviewer persona-frame asserts: *"Reactive recurrence fires + addressed turns + heartbeats: every cycle produces a standing_intent.md write."* (`_PERSONA_FRAME` §395). Population audit at `docs/evaluations/2026-05-25-053951-reviewer-behavior-population-audit/findings.md` measured ~48% adherence (N=27 judgment-shape wakes, range 33%–67% by slug class). The audit treated <100% as a discipline gap. Operator review identified that the criterion itself is under-specified: several legitimate Reviewer postures could rationally exit without writing standing_intent.md, in which case ~48% is the model correctly distinguishing material from immaterial wakes against an over-broad criterion.

Render Scheduler trace verification at `docs/evaluations/2026-05-26-145500-silent-wake-hypothesis-verification/findings.md` confirmed the silent-exit failure mode at code-log level (`WARNING:agents.reviewer_agent:[REVIEWER] text-only response round N`). Structural deepening at `docs/evaluations/2026-05-26-152500-failed-action-substrate-blindspot/findings.md` surfaced **two distinct substrate-surfacing blindspots**:

1. Failed Reviewer actions are filtered out of narrative substrate at `services/reviewer_chat_surfacing.py::surface_reviewer_actions:408` (`if not action.get("success", True): continue`). Every failed WriteFile, ProposeAction, SyncPlatformState is invisible to operator surfaces — even though the Reviewer DID try, DID spend tokens, DID encounter substrate constraints worth knowing about.
2. The Reviewer's final prose at silent-exit is captured in memory inside `invoke_reviewer` as `verdict_raw.reasoning` but never reaches canonical substrate (only `ReturnVerdict`-sourced verdicts land in `judgment_log.md`). Prose exists transiently in Render logs (capped retention) and nowhere persistent.

And the failed-WriteFile pattern audit identified a structural cause: the persona-frame canon contradiction over write-capability (addressed by [ADR-302](ADR-302-prompt-envelope-discipline.md)) leaves the Reviewer attempting locked operator-substrate writes, getting refused, with no clean recovery path. Falls back to Clarify, eventually text-only-exits.

**Together these findings produce the operator-experience symptom**: "I'm not seeing real information and updates on feed, cockpit information that feels like reviewer agent is really working." The Reviewer IS working; the substrate is structurally biased to show only its successes and only its formal verdicts. The operator can structurally see only ~52% of Reviewer cycles. The remaining ~48% is plumbing-healthy but substrate-invisible by design.

**The root issue**: the persona-frame's standing_intent contract is one-size-fits-all across what are actually distinct cognitive postures. A taxonomy is needed before any per-cell contract can be defined.

## 2. Decisions

### D1 — Five posture cells, axiomatically derived

The Reviewer's possible exit shapes from a judgment cycle, exhaustively enumerated:

| # | Posture | Trigger | Exit shape today | Operator-visible today? |
|---|---|---|---|---|
| **P1** | **Fired-correctly** | Material substrate change warrants action | `ReturnVerdict` with verdict + reasoning + actions taken | Yes — verdict in `judgment_log.md`, actions narrated via `surface_reviewer_actions` |
| **P2** | **Decided-nothing-material** | Substrate read complete, model concludes nothing warrants action | `ReturnVerdict("stand_down")` if model wraps it, OR text-only exit if model doesn't | Partially — wrapped stand_down visible, text-only invisible |
| **P3** | **Tried-was-gated** | Model attempted substrate write to locked path (or other primitive refused) | Failed action discarded; model continues; often Clarify; often text-only exit | **No — failed action filtered at surfacing layer; silent on substrate** |
| **P4** | **Budget-exhausted** | Loop hit `max_rounds` without ReturnVerdict | Dispatcher constructs synthetic `stand_down` with last text snippet | **No — no `judgment_log` entry, no `standing_intent` write** |
| **P5** | **Confused** | Model genuinely unable to synthesize against the envelope | Indistinguishable from P4 in current code; surfaces as text-only exit | **No — same as P4** |

The five are exhaustive over the current `invoke_reviewer` execution paths. P1 is the happy path. P2 is the optimal-selectivity path. P3 is the canon-contradiction-driven path that ADR-302 addresses upstream. P4 + P5 are runtime degenerate paths.

The taxonomy is the unit of analysis. Each cell needs:
- A **declared expected posture** in canon (what the Reviewer SHOULD do in this cell)
- A **substrate side-effect contract** (what MUST be written to be considered a complete cycle, from the operator-visibility perspective)
- A **surfacing policy** (how the per-cell substrate reaches operator-facing surfaces)

### D2 — Per-cell substrate side-effect contract

Each cell MUST produce at minimum one operator-readable substrate artifact. The artifact may be slot-filled differently per cell but operator-visibility is non-negotiable per cell.

| Cell | Required substrate side-effect | Surfacing site |
|---|---|---|
| **P1 Fired-correctly** | `ReturnVerdict` → `judgment_log.md` entry (existing) + per-action narrative via `surface_reviewer_actions` (existing) | Feed (existing) + cockpit Decision surface (existing) |
| **P2 Decided-nothing-material** | `standing_intent.md` revision recording "I looked, evaluated against [evidence], no action warranted because [reason]." Distinct from P1 because no `judgment_log` entry. | Feed (per `standing_intent.md` revision attribution) + cockpit Standing-Intent surface |
| **P3 Tried-was-gated** | A new structured narrative entry "Reviewer attempted write to {path}, blocked by {gate}. Reasoning: {prose snippet}." Sourced from the in-memory `actions_taken` failed-action records. **This is a new substrate visibility class — currently filtered.** | Feed (new event-kind, see D3) |
| **P4 Budget-exhausted** | A `standing_intent.md` revision recording "Cycle hit budget without converging. Last reasoning: {prose snippet}. Substrate may need refresh or recurrence prompt may need tightening." Mechanically synthesized by the dispatcher. | Feed (per `standing_intent.md` revision attribution) + telemetry flag |
| **P5 Confused** | Indistinguishable from P4 at exit — same substrate side-effect. Differentiation happens at re-occurrence pattern (P5 recurs across diverse triggers; P4 recurs on specific complex recurrences) — operator surfaces handle the differentiation, not the cell contract. | Same as P4 |

**Key shape**: the contract is operator-visibility, not "model authored intent." A mechanically-synthesized `standing_intent.md` revision (P3, P4, P5) is honest substrate — it carries the model's last-prose snippet, an `authored_by: dispatcher:silent_exit_fallback` attribution that distinguishes it from `authored_by: reviewer:...` revisions, and a clear "what happened" framing. The substrate doesn't pretend the model authored intent it didn't; it surfaces what the model produced.

This is a deliberate departure from the substrate-honoring fallback hotfix `9e7c1c7` (reverted in same session, see CHANGELOG `[2026.05.26.2]`). That fallback attributed silent-exit substrate as `reviewer:{model}` — falsely conflating model authorship with mechanical dispatch. This ADR's substrate uses a distinct `dispatcher:...` attribution class so the operator and future evaluations can distinguish authored intent from mechanical safety-net writes.

### D3 — Failed-action narrative surfacing: visibility-first default with explicit noise denylist (source-grounded refinement, 2026-05-26)

The `success=True` filter in `services/reviewer_chat_surfacing.py::surface_reviewer_actions:408` is uniformly success-biased. It is inverted: **default-surface for all failures; explicit denylist for known-noise classes.**

This is the first-principles position derived from Claude Code's tool-error handling (`docs/analysis/src_claudeCC/query.ts:140`, where every tool failure produces a `tool_result` with `is_error: true` and is surfaced to the user without filter). The principle the source enacts: all tool outcomes are operator-visible because the operator's judgment requires the substrate-receipt of *what actually happened*, not a curated view of *what succeeded*.

YARNNN's prior success-bias filter was a design choice that didn't survive contact with the failed-WriteFile pattern. Operator-visible Reviewer cognition is non-negotiable per Derived Principle 21 ("full-substrate-authoring … paced by operator-declared pace + autonomy"). A filter that hides cognition contradicts the canon.

Concretely:

```python
# api/services/reviewer_chat_surfacing.py — replacing the success=True filter

# Default: every Reviewer action — success OR failure — produces narrative.
# Failures explicitly listed in SILENCE_FAILURE_REASONS are filtered as
# known-noise; ALL other outcomes surface to the feed.

SILENCE_FAILURE_REASONS: frozenset[str] = frozenset({
    "rate_limited",                   # transient platform-API throttle
    "transient_network",              # retriable network failure
    "retried_successfully_in_cycle",  # superseded by a same-tool same-args success in same wake
})

def should_surface_action(action: dict) -> bool:
    if not isinstance(action, dict):
        return False
    if action.get("success", True):
        # successful actions surface per existing folding logic (D2 P1 contract)
        return True
    reason = (action.get("failure_reason") or "").strip()
    if reason in SILENCE_FAILURE_REASONS:
        return False
    return True  # visibility-first default
```

Failed actions that surface produce narrative entries with a new event-kind `reviewer_action_blocked` carrying tool + path/target + failure_reason + the model's prose context if available. The narrative entry is authored as `dispatcher:reviewer_action_blocked` per D6 attribution discipline (the dispatcher reports the failure; the Reviewer didn't author the report).

The asymmetry favoring surfacing is structural: the cost of false-surfacing is one extra feed entry the operator can ignore. The cost of false-filtering is invisible Reviewer cognition that the operator can't react to. The denylist grows only when a specific noise class is identified through observation — never preemptively.

**Failure-reason taxonomy is open at this ADR**: tools produce failures with reasons that are not yet structurally enumerated. Phase 4 implementation surfaces the natural taxonomy from production; the denylist may expand from the initial three entries above as transient-noise classes are identified. Operator-relevant classes (path_locked, capability_required_missing, schema_validation_failed, permission_denied, etc.) NEVER enter the denylist — they are exactly the substrate signals the operator needs.

### D4 — Posture-frame disambiguation in persona-frame

The persona-frame standing_intent section (`_PERSONA_FRAME` §392–§411) gets rewritten per ADR-302's discipline + this ADR's posture distinctions:

- Replace the single rule ("every reactive recurrence cycle produces a standing_intent.md write") with the five-cell taxonomy explicitly named.
- Each cell paragraph names the cell, describes when it applies, and declares the substrate contract the model is responsible for vs the contract the dispatcher fills in mechanically.
- The dispatcher's mechanical writes are named in the prompt as the safety net — model is encouraged to author intent itself when warranted (P1, P2), and informed that the dispatcher will surface (P3, P4, P5) silent-exits to the operator with a distinct attribution so the model knows silent-exit is operator-visible.

This closes the model's "I exited silently and nothing happened" assumption. Silent exits are still possible but they reach operator-visible substrate via the dispatcher's mechanical write with `dispatcher:silent_exit_fallback` attribution, plus the failed-action narrative entries from D3.

### D5 — Author-class vs trader-class persona-frame question

The failed-WriteFile concentration on author-class personas (korea-thriller-shorts, netflix-script-author) but not trader-class (kvk, alpha-trader, alpha-trader-2, yarnnn-author) is real signal worth naming, but **this ADR does NOT resolve it**.

Resolution hypothesis surfaced for future investigation:
- Author-class bundles may have `_autonomy.yaml` content that more often invites attempted amendment.
- Author-class persona-frame guidance (currently uniform) may not match author-work cognitive patterns.
- Author-class `_locks.yaml` (if it exists) may differ across these personas.

ADR-302 remediation may resolve this implicitly by eliminating the canon contradiction that drives the attempted-amendment behavior in the first place. If post-ADR-302 the concentration persists, a separate ADR addresses per-bundle persona-frame overlay mechanism. Out of scope here.

## 3. Acceptance criteria

After all phases land:

1. **Cell-level adherence**: re-run population audit against the new criterion (per-cell contract honored, not "every cycle writes standing_intent"). Target: 95%+ adherence per cell, where adherence means "the cell's substrate contract per D2 was honored." Pre-fix baseline is unmeasured because the contract didn't exist; post-fix baseline becomes the discipline check.
2. **Operator-visibility ratio**: the fraction of Reviewer wakes that produce SOME operator-visible substrate (any of: judgment_log entry, standing_intent revision, action narrative, blocked-action narrative) should approach 100%. Currently ~52%. Target: 95%+ post-fix.
3. **No silent class regression**: P3 + P4 + P5 cells must produce dispatcher-attributed substrate in 100% of cases by structural enforcement. Verified by Hat-B sampling.
4. **Failed-action signal quality**: D3 surfacing produces operator-relevant entries (sample-verify at Phase 4 — surfaced entries should resolve to actual constraint hits, not noise).

## 4. What this ADR does NOT do

- Does not change the model's in-loop decision behavior (no tool_choice forcing, no mid-loop nag, no behavioral pressure on what verdict to produce).
- Does not introduce per-bundle persona-frame variants (D5 explicitly defers).
- Does not change `DEFAULT_REVIEWER_WRITE_LOCKS` (lock policy still ADR-293's).
- Does not address operator-side cockpit rendering of the new substrate classes — UI changes are downstream of substrate availability, addressed when surfacing data exists to render.

## 5. Implementation phases

- **Phase 1**: ratify this ADR + ADR-302 together. Both proposals land.
- **Phase 2**: ADR-302 D5 remediation pass on `_PERSONA_FRAME`. Resolves the canon contradiction class. Predicted to reduce P3 frequency at the source.
- **Phase 3**: D2 substrate contracts — dispatcher-side mechanical writes for P2/P3/P4/P5 cells. Single file changes in `reviewer_agent.py` (replace the existing fallback paths with the new contract-honoring writes, with `dispatcher:silent_exit_fallback` attribution that's distinct from model authorship).
- **Phase 4**: D3 failed-action surfacing relaxation. Single file change in `reviewer_chat_surfacing.py` to relax the `success=True` filter against the `SURFACE_FAILURE_REASONS` set. New event-kind addition to narrative schema.
- **Phase 5**: D4 persona-frame posture-taxonomy rewrite. Single file change in `reviewer_agent.py::_PERSONA_FRAME`. CHANGELOG entry per ADR-302 D4.
- **Phase 6**: re-run population audit against new criterion (D2 contract per cell, not single rule). Confirms or refutes whether the structural fix carries.

Phase order is deliberate: ADR-302 first (cause), then substrate visibility (D2 + D3), then prompt update (D4) so the model knows about the new substrate it can author into, then re-measurement.

## 6. Why dispatcher attribution matters

A subtle but load-bearing point: the rejected hotfix `9e7c1c7` wrote silent-exit substrate as `authored_by="reviewer:{model}"`. That is structurally dishonest — the Reviewer did NOT author that substrate; the dispatcher did, on the Reviewer's behalf, because the Reviewer exited without authoring. Conflating dispatcher fallback writes with model-authored substrate would:

- Contaminate future evaluation data (evaluator can't distinguish "Reviewer wrote thoughtful intent" from "dispatcher slot-filled an exit trace")
- Inflate persona-frame adherence metrics dishonestly
- Make `reviewer:` attribution semantically meaningless over time

This ADR's `dispatcher:silent_exit_fallback` attribution preserves the distinction. Future evaluations that ask "what did the Reviewer actually author?" still get a clean answer. Future evaluations that ask "did the cycle produce operator-visible substrate?" also get a clean answer. Two different questions, two different attribution classes, no conflation.

The same principle applies to D3 failed-action narratives: they're authored by `dispatcher:reviewer_action_blocked`, not by `reviewer:...`. The dispatcher is reporting what happened; the model didn't author the report.

## 7. Cross-references

- Predecessor finding chain:
  - `docs/evaluations/2026-05-25-053951-reviewer-behavior-population-audit/findings.md` (the 48% adherence measurement)
  - `docs/evaluations/2026-05-26-145500-silent-wake-hypothesis-verification/findings.md` (text-only-fallback confirmed)
  - `docs/evaluations/2026-05-26-152500-failed-action-substrate-blindspot/findings.md` (two structural blindspots named)
- Source-grounded refinement basis: `docs/analysis/src_claudeCC/query.ts:140` (Claude Code's `is_error: true` always-surface pattern) + `docs/analysis/src_claudeCC/query.ts:674` (`toolChoice: undefined` validating no-in-loop-intervention stance) — first-principles compatibility documented in `docs/analysis/claude-code-prompt-discipline-comparison-2026-05-26.md`
- Sibling ADR: ADR-302 (prompt-envelope discipline) — drafted same session
- Reverted hotfix: commit `9e7c1c7` + CHANGELOG `[2026.05.26.2]` (revert rationale)
- Related canon: ADR-194 v2 (Reviewer substrate), ADR-258 revised (REVIEWER_PRIMITIVES + narration), ADR-289 D4 (judgment_log substrate-of-record), ADR-293 (write-authority), ADR-295 (self-amendment evidence patterns), ADR-298 (trifecta), ADR-302 (prompt discipline)
- Source: `api/agents/reviewer_agent.py::invoke_reviewer` (text-only fallback + budget-exhausted fallback), `api/services/reviewer_chat_surfacing.py::surface_reviewer_actions:408` (success-bias filter)

## 8. Open questions

- **Failure-reason denylist evolution**: D3's `SILENCE_FAILURE_REASONS` starts with three known transient-noise classes (rate_limited, transient_network, retried_successfully_in_cycle). The denylist may expand if Phase 4 observation surfaces other natural noise classes. Operator-relevant failure reasons NEVER enter the denylist — they are exactly the substrate signals the operator needs. ADR amendment expected only if a noise class is identified that the initial three don't cover.
- **Operator-side noise tolerance**: D3 surfaces all failed actions by default with operator-side filtering deferred. If real-world feed becomes too noisy post-Phase-4, a per-operator suppress mechanism may be needed. Deferred until evidence justifies.
- **Cell P5 detection**: P5 ("genuinely confused") is currently indistinguishable from P4 ("budget-exhausted") at exit. Differentiating at re-occurrence pattern requires substrate-level telemetry that doesn't yet exist. Deferred to operator-driven future work if the distinction becomes load-bearing.
- **Whether the substrate-honoring "dispatcher write" approach IS itself a hotfix in disguise**: arguable. The structural alternative would be in-loop intervention (force ReturnVerdict on terminal rounds, or push system-message reminder when model exits text-only). The dispatcher-write approach is chosen because it preserves model autonomy in-loop (no behavioral pressure) while honoring operator visibility — but is functionally similar to the rejected hotfix `9e7c1c7` at the substrate-result layer. The honest distinction: this ADR's dispatcher writes have explicit `dispatcher:` attribution + are grounded in a per-cell taxonomy where they slot into a defined posture rather than papering over a uniform contract. If this distinction proves too thin in practice, future ADR revisits.
