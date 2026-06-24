# Finding — ADR-359 impl probe: the occasion posture WORKS; the agent then calls Clarify instead of producing

**Date**: 2026-06-24
**Hat**: B (external-developer / evaluation) — feeds ADR-359 (Proposed)
**Subject**: the ADR-359 §8 validation probe run LOCALLY against the real implementation (D1 computed occasion fact + D2 produce-close/non_performance + D3 occasion-leads), neutral prompt, netflix-author empty-corpus owed-scene substrate. Probe script: `api/scripts/operator/probe_adr359_occasion_local.py` (local invoke_reviewer so THIS working tree's code runs, not the deployed scheduler).
**Verdict**: **FAIL on the artifact (no content.md) — but the failure mode MOVED, and the trace localizes the true root cause.** The occasion posture WORKED (the agent explicitly decided to compose); the agent then called **Clarify** instead of producing. The blocker is the **ask-vs-produce seam at the moment of origination**, not the occasion concept.

---

## What the implementation achieved (real progress, receipt-grounded)

D1 computed the occasion fact correctly and it led the envelope:
> `OWED this tenure: scene (weekly). PRODUCED so far: 0. OCCASION = NOW. The first owed scene has never been originated, and nothing external gates originating it... A future wake would face this SAME state... so deferring is circular... Producing the scene is the work of THIS runtime.`

And the agent's round-by-round trace (captured via temporary instrumentation, since reverted) shows the occasion posture **changed the agent's intent** — it no longer schedules-and-closes "routine heartbeat":
- Round 1-2: reads substrate (voice, editorial, spec, entities/jaewon, signal) — normal prep.
- **Round 3 (run A): "Now I understand the situation. Let me read the principles file... and then compose the first scene."** ← explicit intent to compose. The prior probes NEVER reached this.
- **Round 3 then calls `Clarify`** (not WriteFile).
- Run B, round 3: *"there's no series-bible file yet... This is a meaningful constraint I need to surface"* → round 6 `Clarify` (success=True — the ask-gate ALLOWED it, i.e. classified it `structural_gap`).
- Close: ReturnVerdict → stand_down. Zero content.md.

So D1/D2/D3 are NOT wrong — they advanced the agent from "schedule a future producer wake and close routine" (the 5 prior falsifications) to **"I should compose the first scene"**. That is the occasion posture working as designed.

## The true root cause (localized by the trace)

**At the moment of origination, the agent reaches for `Clarify` instead of `WriteFile`.** It finds a reason to ask the operator — "there's no series bible yet" — and classifies that as a **structural gap only the operator can close** (the ask-gate allowed the Clarify, so it passed the ADR-352 `structural_gap` test). But it is NOT a structural gap: the agent HAS the character (Jaewon, full voice fingerprint), the editorial principles, the composition spec, and a declared mandate. **A first scene does not need a series bible — it can be composed from what exists, and composing it is reversible (a draft).** The agent is treating "I don't have everything I'd ideally want" as "I cannot proceed without the operator."

This is the **ask-vs-produce seam** — the same family as ADR-344 (B) / ADR-352 / ADR-354 §8 ("under autonomous you author, you do NOT ask permission"). The prior arc fixed asking-permission-to-author-the-organ; this is one layer in: asking-permission-to-originate-the-first-artifact, justified by "missing ideal context." The agent originates an *ask* where it should originate the *work*.

## What this falsifies / confirms

- **CONFIRMS** the occasion-of-work thesis + D1 (computed occasion fact): it provably moved the agent from defer-and-schedule to intend-to-compose. Keep D1/D2/D3.
- **FALSIFIES** "the occasion posture alone is sufficient": it is necessary but not sufficient — the Clarify escape at origination defeats it.
- **FALSIFIES** my mid-investigation escape-hatch theory (that the *existence* of `compose-screenplay-scene` causes deferral): removing that recurrence and re-firing STILL failed (15 rounds, stand_down, 0 content.md) — the producer-recurrence existence was not the cause. (6th theory killed; tested cheaply before canon, per discipline.)

## The fix the evidence now points to (for ADR-359, added decision)

The ask-gate (ADR-352) must NOT classify "missing ideal/secondary context" as a `structural_gap` when the agent holds enough to produce a first draft. Two candidate levers (decide with operator):
1. **Tighten the structural_gap classification**: a gap is structural only when the agent CANNOT produce a floor-clearing draft with present substrate — not when richer context would be nice. "No series bible, but I have character+voice+principles+spec" → produce the draft; the bible emerges from drafts, not before them.
2. **Occasion-fact precedence over Clarify**: when the occasion fact says owed-and-unproduced + nothing external gates it, a Clarify whose stated reason is "missing context I could compose around" is denied (it is the ask-in-costume), and the agent is pushed to produce. The one legitimate Clarify at an owed do-wake is a genuine capability/floor/mandate block, not "I'd like more background."

Either lands as an ADR-359 decision (D6) + the ADR-352 ask-gate classification. NOT a frame-prose nudge (5 prose theories already falsified).

## Implementation state (uncommitted, on this working tree)

D1/D2/D3 implemented across 5 files (reviewer_envelope.py, occupant_contract.py, reviewer_agent.py, reviewer_audit.py, CHANGELOG) + ADR-359 (Proposed, committed 827c843) + probe script. Bug fixes landed during the probe: `non_performance` added to ReturnVerdict enum + `_VALID_VERDICTS` + `_META_OUTCOME_VERDICTS`; budget_exhausted path also synthesizes non_performance on owed-and-unproduced. Trace instrumentation reverted. The substrate `_recurrences.yaml` was mutated during the probe (compose-screenplay-scene removed for the confirmatory test) — note for substrate hygiene; it is the netflix dev workspace.

## Bottom line

The occasion-of-work implementation is on the right track — it provably moved the agent to *intend* to compose, which five prose probes never achieved. The remaining blocker is the **Clarify-instead-of-produce seam at origination**: the agent asks the operator (citing "missing series bible") rather than composing the first scene from the substantial substrate it holds, and the ask-gate wrongly allows it. The fix is in the ADR-352 structural_gap classification (tighten it / make the occasion fact take precedence), not more frame prose. ADR-359 gains a D6 for this; the §8 probe re-runs after.
