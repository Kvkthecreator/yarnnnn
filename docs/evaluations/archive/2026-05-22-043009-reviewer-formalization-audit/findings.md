# findings.md — Reviewer Formalization Audit

**Anchor**: Variant F (see [`PLAYBOOK.md`](PLAYBOOK.md)).

**Verdict legend**:
- **ALIGNED** — codebase reflects Variant F; no Hat-A action required
- **DRIFT** — codebase contradicts or under-reflects Variant F; Hat-A change recommended
- **OPEN-QUESTION** — surfaces a structural ambiguity worth Hat-A discussion before fix-shape decided

---

## Layer 1 — Persona frame (`api/agents/reviewer_agent.py::_PERSONA_FRAME` + `_TRIGGER_FRAMING`)

### L1-F1 — Header missing canonical formalization anchor
**Location**: `api/agents/reviewer_agent.py:371-407` (top of `_PERSONA_FRAME`)
**Verdict**: **DRIFT**

The persona frame opens with "You sit in the operator's chair at the cockpit. The mandate is yours…" — a strong embodiment opener, but it never names what the Reviewer **structurally is** in one canonical sentence. The reader has to assemble the architectural claims (wake-fired, single-lane, paced, mandate-driven, full-substrate-authoring) from 400 lines of prose scattered across 9 sub-sections.

**Recommendation (Hat-A)**: Add a 3-sentence preamble at line ~371 that quotes the Variant F sentence verbatim and cites its canonical location (FOUNDATIONS Derived Principle 21 or equivalent, depending on Hat-A placement). The embodiment opener ("You sit in the operator's chair…") follows it. This gives the LLM the structural anchor before the embodiment register.

### L1-F2 — "Schedule the next mechanical mirror's run" phrasing risks self-invocation misread
**Location**: `api/agents/reviewer_agent.py::_TRIGGER_FRAMING["addressed"]:829-837`
**Verdict**: **ALIGNED** (with caveat)

The current phrasing correctly threads the cadence-author-not-self-invoke distinction:

> Data is stale and a refresh would change the next assessment → author cadence (per ADR-296 v2 D3): either (a) Schedule your next cycle for after the relevant mechanical mirror's next fire, or (b) WriteFile to /workspace/review/standing_intent.md declaring interest in the substrate transition that would unblock you. […] Do NOT invoke the upstream mirror directly from your loop — that is operator + cron territory; your authority is over cadence preference and standing intent, not over commissioning unit-of-work fires.

This is correct and ADR-296 v2-aligned. The caveat: the Variant F sentence makes "wake-fired" the single canonical word for this property. Persona frame should align by using the term explicitly.

**Recommendation (Hat-A)**: Once L1-F1's header anchor is in place, the existing prose stands. No edit to this section.

### L1-F3 — Persona frame doesn't name ADR-298 single-lane queue-serialization
**Location**: `api/agents/reviewer_agent.py::_PERSONA_FRAME` (whole file)
**Verdict**: **DRIFT** (minor)

ADR-298 + the wake-queue cutover introduced single-in-flight per workspace. The persona frame doesn't mention this. The Reviewer's mental model is "I am one cycle; another cycle may queue behind me but cannot run alongside me." Useful for the LLM to know — specifically for the "should I leave work for the next cycle vs cram it in?" tradeoff. Pace-yaml is mentioned via wake envelope; queue is not.

**Recommendation (Hat-A)**: In the L1-F1 preamble or in the "Your operating cadence is yours to author" section (line ~566), add one sentence: "Cycles are serialized — only one of you runs at a time per workspace. The wake queue holds any concurrent wake until you exit; trust the queue."

### L1-F4 — `_PERSONA_FRAME` doesn't name pace as Trigger-dimension dial
**Location**: `api/agents/reviewer_agent.py::_PERSONA_FRAME:566-630`
**Verdict**: **DRIFT** (minor)

The "Your operating cadence is yours to author" section (566-630) doesn't mention `_pace.yaml`. It mentions `_preferences.yaml` but not pace. Variant F names "paced by operator-declared pace + autonomy" as a primary claim. The Reviewer needs to know pace is the dial the operator turns, and that Schedule() calls land within the pace budget.

**Recommendation (Hat-A)**: In the "cadence" section, add one paragraph: pace is the operator's Trigger-dimension dial (`_pace.yaml`); pre-loaded in your wake envelope; Schedule() calls are pace-gated at declaration time; if your proposed cadence would exceed pace, surface a Clarify rather than fight the gate.

### L1-F5 — Frame's "Standing down is structurally rare" + "default is action" coexist with "Default posture: audit, then act" hook prompts — internal consistency check
**Location**: `_PERSONA_FRAME:387-400` + `_TRIGGER_FRAMING["addressed"]:824-851`
**Verdict**: **ALIGNED**

Both messages reinforce the same priority ordering: act before stand. No drift.

### L1-F6 — Frame mentions "judgment_log" but standing-intent contract is the cycle-closer
**Location**: `_PERSONA_FRAME:436-491` (standing intent section)
**Verdict**: **ALIGNED**

The trigger-aware standing-intent contract (proposal wakes call ReturnVerdict first; recurrence + addressed + heartbeat wakes write standing_intent.md every cycle) is well-articulated and matches the post-Option-D model. No drift.

---

## Layer 2 — Wake envelope (`api/services/reviewer_envelope.py::load_reviewer_governance_envelope`)

### L2-F1 — Universal envelope matches the corrected awareness picture
**Location**: `api/services/reviewer_envelope.py:76-98` (`_UNIVERSAL_ENVELOPE_DECLS`)
**Verdict**: **ALIGNED**

All 9 universal slots are present and load-bearing:
- `identity_md` (REVIEW_IDENTITY_PATH)
- `principles_md` (REVIEW_PRINCIPLES_PATH)
- `precedent_md` (SHARED_PRECEDENT_PATH)
- `mandate_md` (SHARED_MANDATE_PATH)
- `autonomy_md` (SHARED_AUTONOMY_PATH)
- `preferences_yaml` (SHARED_PREFERENCES_PATH)
- `pace_yaml` (SHARED_PACE_PATH) ✓ ADR-298 Phase 2 addition
- `occupant_md` (REVIEW_OCCUPANT_PATH)
- `standing_intent_md` (REVIEW_STANDING_INTENT_PATH)

No pre-cutover paths surviving. `pace_yaml` is present. Program-shaped envelope reads from bundle MANIFEST `substrate_abi.reviewer_wake_envelope` per ADR-281 D2. Singular-implementation discipline honored (one helper, both addressed + reactive paths call it).

### L2-F2 — Envelope helper does not surface single-lane / queue-depth as substrate
**Location**: `api/services/reviewer_envelope.py:105-225`
**Verdict**: **OPEN-QUESTION**

Should the envelope tell the Reviewer "there are N wakes queued behind you" or "no concurrent wakes pending"? Per Variant F it's queue-serialized. Today the queue is kernel-internal (operators don't read it; Reviewer doesn't either). Surfacing queue depth might let the Reviewer reason about "cram-vs-leave-for-next-cycle" more deliberately. But it might also invite the Reviewer to over-optimize for queue empty-ness, which is anti-fiduciary.

**Recommendation (Hat-A)**: Don't surface in Commit 2. Keep queue kernel-internal. The L1-F3 persona-frame note ("Cycles are serialized — trust the queue") gives the Reviewer the conceptual model without runtime visibility into the queue itself.

---

## Layer 3 — Primitive registry (`api/services/primitives/registry.py::REVIEWER_PRIMITIVES` + `workspace_paths.py::DEFAULT_REVIEWER_WRITE_LOCKS`)

### L3-F1 — REVIEWER_PRIMITIVES matches ADR-296 v2 + ADR-298 commitments exactly
**Location**: `api/services/primitives/registry.py:385-424`
**Verdict**: **ALIGNED**

21 tools registered:
- All reads (13): READ_FILE / LIST_FILES / SEARCH_FILES / LIST_REVISIONS / READ_REVISION / DIFF_REVISIONS / GET_SYSTEM_STATE / SEARCH_ENTITIES / LOOKUP_ENTITY / LIST_ENTITIES / LIST_INTEGRATIONS / WEB_SEARCH / QUERY_KNOWLEDGE
- Self-substrate write (1): WRITE_FILE (lock-gated)
- Direction (1): PROPOSE_ACTION
- Self-scheduling (2): SCHEDULE + MANAGE_HOOK ✓ ADR-296 v2 D2 + D3
- Composition (1): COMPOSE
- Specialist (1): DISPATCH_SPECIALIST
- Substrate refresh (1): SYNC_PLATFORM_STATE
- Conversation (1): CLARIFY

ReturnVerdict is wired in the tool-use loop, not in REVIEWER_PRIMITIVES (correct — it's the verdict-emission contract, not a primitive).

**`FireInvocation` correctly absent** per ADR-296 v2 D3 (Reviewer does not self-invoke).

### L3-F2 — DEFAULT_REVIEWER_WRITE_LOCKS matches operator-control-trifecta exactly
**Location**: `api/services/workspace_paths.py:187-206`
**Verdict**: **ALIGNED**

Five paths locked:
- `AUTONOMY.md` + `_autonomy.yaml` (Mechanism-dimension dial)
- `_token_budget.yaml` (compute-resource dial)
- `_preferences.yaml` (operator deliverable cadence preferences, ADR-275 D6)
- `_pace.yaml` (Trigger-dimension dial, ADR-298 Phase 4)

Matches Variant F structural claim #6 exactly. No drift.

---

## Layer 4 — Tool-use loop nudges + exit contract

### L4-F1 — Option D nudge-deletion held; no `_round >= N` patterns survived
**Location**: `api/agents/reviewer_agent.py:1522-1549`
**Verdict**: **ALIGNED**

Confirmed: the only mid-loop nudge is signal-based (`clarify_called_this_round`). The deleted counter-based nudge is appropriately gravestone-commented at line 1532-1540, with rationale citing the population audit. No regressions.

### L4-F2 — Text-only fallback at line 1409-1422 remains a real exit branch with no structural binding upstream
**Location**: `api/agents/reviewer_agent.py:1409-1422`
**Verdict**: **DRIFT**

The text-only fallback converts the response text into `stand_down` reasoning when no tool is called. This was the canary v3 failure mode for `pre-ship-audit`. Today the only upstream protection against text-only response is **prose in the hook/recurrence prompt** asking the model to call ReturnVerdict (see L5 findings). There is no tool-side `tool_choice={"type": "any"}` re-engagement after round-1, no structural ReturnVerdict requirement bound to the verdict-emission language in the prompt.

The current tool_choice logic (`reviewer_agent.py:1370`):
```python
tool_choice = {"type": "any"} if _round == 0 else {"type": "auto"}
```
forces a tool call at round 0 only. After that the model can freely emit text-only.

**Recommendation (Hat-A)**: Two complementary moves:
- (a) Tighten hook + recurrence prompts (L5 candidate) so they structurally bind verdict-emission to ReturnVerdict — the cleanest fix.
- (b) Consider whether the text-only fallback should log to `judgment_log.md` as "TEXT_ONLY_FALLBACK" rather than `stand_down`. Different verdict shape distinguishes "I chose to stand down" from "I didn't reach a verdict." Today they collapse to identical substrate.

The latter is out of scope for Commit 2's Variant-F-alignment sweep — record as follow-on observation if (a) doesn't fully resolve the symptom.

### L4-F3 — Loop-exhaustion fallback (`if verdict_raw is None`) at line 1567-1591 is structurally correct
**Location**: `api/agents/reviewer_agent.py:1567-1591`
**Verdict**: **ALIGNED**

This is the safety net for the budget-exhausted-but-no-verdict case. Logged as warning, produces a low-confidence stand_down. Correct shape for the rare case it's meant to catch.

### L4-F4 — `_validate_context_shape` enforces the corrected envelope contract
**Location**: `api/agents/reviewer_agent.py:1108-1178`
**Verdict**: **ALIGNED**

The validator rejects malformed context bags at the wake gateway, preventing silent inert stand_down (the 2026-05-13 fix). Aligned with the wake-fired commitment.

---

## Layer 5 — Hook + recurrence prompts (`alpha-author` + `alpha-trader` reference workspaces)

### L5-F1 — alpha-author `pre-ship-audit` hook: verdict-emission is prose-bound, not structurally bound
**Location**: `docs/programs/alpha-author/reference-workspace/_hooks.yaml:42-83`
**Verdict**: **DRIFT** (canary v3 root cause)

The prompt says "Decide and emit one of: APPROVE / DEFER / REJECT" but does not say "Call ReturnVerdict(verdict='approve'|'reject'|'defer', …)". The model interprets this as a prose-shape request, not a tool-call request. Canary v3 produced a text-only response that the framework auto-converted to `stand_down` with the prose as reasoning.

**Recommendation (Hat-A)**: Edit the hook prompt's "Decide and emit one of" section to bind verdict-emission to ReturnVerdict explicitly:

> Decide and emit verdict via ReturnVerdict (the framework requires a tool call to close the cycle):
>   - **ReturnVerdict(verdict='approve', reasoning='[persona-voice summary]', confidence='high')** — all checks pass; piece may ship. If _autonomy.yaml delegation is bounded AND piece_type matches ceiling_categories, this binds publication via ExecuteProposal. Otherwise approve surfaces to operator Queue.
>   - **ReturnVerdict(verdict='defer', reasoning='[persona-voice summary including specific defect path:line]', confidence='medium')** — some checks pass, some need operator iteration. Also: WriteFile to /workspace/review/judgment_log.md with structured defect (e.g., "para 3 sentence 2: hedge stack 'I think it's worth considering'"). Operator iterates and resubmits.
>   - **ReturnVerdict(verdict='reject', reasoning='[persona-voice summary citing the violated principles.md rule]', confidence='high')** — hard rejection rule fires per principles.md. Also: WriteFile to judgment_log.md with structured reasoning.
>
> Silent stand-down without writing audit reasoning is forbidden. Text-only response without ReturnVerdict will be auto-converted to inert stand_down with no substrate write — that is a discipline failure, not a valid cycle close.

### L5-F2 — alpha-author `corpus-coherence-check` recurrence: same prose-binding issue
**Location**: `docs/programs/alpha-author/reference-workspace/_recurrences.yaml:47-87`
**Verdict**: **DRIFT** (same pattern as L5-F1)

The prompt says "Stand down silently if no findings cross thresholds — AND update standing_intent.md" but doesn't structurally bind to ReturnVerdict. The "AND" pattern is correct for the standing-intent contract, but the verdict-emission for the "no findings" case is implicit. Reviewer may emit text-only "no findings, standing down" which falls through to text-only fallback.

**Recommendation (Hat-A)**: Add explicit ReturnVerdict binding at the close:

> When findings cross thresholds: emit Clarify proposals AND ReturnVerdict(verdict='defer', reasoning='[persona-voice naming the specific drift]', confidence='high').
>
> Otherwise: WriteFile to standing_intent.md with what corpus drift patterns you're watching for, THEN ReturnVerdict(verdict='stand_down', reasoning='[persona-voice noting no findings + what's being watched]', confidence='medium'). Text-only "no findings" responses are forbidden.

### L5-F3 — alpha-author `revision-audit` recurrence: same pattern
**Location**: `docs/programs/alpha-author/reference-workspace/_recurrences.yaml:97-153`
**Verdict**: **DRIFT** (same pattern)

Step 7 ("When no drafts have revisions in window: write one-line stand_down entry to judgment_log.md, exit silently") doesn't bind to ReturnVerdict.

**Recommendation (Hat-A)**: Add ReturnVerdict to all three exit branches (concerning-drift / notable-changes / no-drafts).

### L5-F4 — alpha-author `outcome-reconciliation` recurrence: same pattern
**Location**: `docs/programs/alpha-author/reference-workspace/_recurrences.yaml:162-208`
**Verdict**: **DRIFT** (same pattern)

### L5-F5 — alpha-trader `signal-evaluation` recurrence: same pattern, possibly more severe
**Location**: `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml:136-208`
**Verdict**: **DRIFT** (high-severity because this fires every market-open + carries capital judgment)

The prompt asks for inline ProposeAction emission and stand-down narration but doesn't bind to ReturnVerdict structurally. The exit clause says:

> Otherwise, when neither entries nor exits fire, stand down with reasoning. The universal every-cycle standing_intent.md write contract is governed by your kernel persona frame.

**Recommendation (Hat-A)**: Tighten the close clause:

> Otherwise, when neither entries nor exits fire: WriteFile standing_intent.md per kernel persona frame, THEN ReturnVerdict(verdict='stand_down', reasoning='[persona-voice noting no entries/exits + what you're watching for]', confidence='medium'). Text-only response without ReturnVerdict is forbidden — the cycle does not close cleanly without it.

### L5-F6 — alpha-trader `outcome-reconciliation` recurrence: same pattern
**Location**: `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml:257-289`
**Verdict**: **DRIFT** (same pattern)

### L5-F7 — Mechanical recurrences correctly excluded
**Location**: `alpha-trader _recurrences.yaml:39-76, 90-126, 218-231`
**Verdict**: **ALIGNED**

Mechanical-mode recurrences (track-positions, track-account, track-orders, track-regime, track-universe, mirror-signal-state) do not wake the Reviewer; they execute deterministic Python primitives. No ReturnVerdict needed. Correct.

### L5-F8 — Hook + recurrence count summary

Across alpha-author + alpha-trader bundles:
- **6 judgment-mode prompts with DRIFT** (1 hook + 5 recurrences) — all need ReturnVerdict structural binding
- **0 judgment prompts ALIGNED** at the structural-binding level
- **6 mechanical recurrences ALIGNED** (don't wake Reviewer)

The drift is uniform — the same shape across every judgment prompt. This suggests the issue is template-level, not per-prompt. A single Hat-A pass touching all 6 prompts is the right shape.

---

## Layer 6 — ADR-trace cross-cutting drift

### L6-F1 — Reviewer-amending ADRs broadly aligned with Variant F
**Locations**: ADR-194 v2, ADR-216, ADR-247, ADR-252, ADR-253, ADR-256, ADR-258 revised, ADR-260, ADR-261 D4, ADR-274, ADR-275, ADR-276, ADR-281, ADR-289, ADR-296 v2, ADR-298
**Verdict**: **ALIGNED** (with supersession-banner discipline already in place)

Spot-checked the highest-risk ADRs for pre-cutover prose (`continuously-running`, `self-invoke`, `background process`, `always-on Reviewer`). All matches were either:
- Inside ADR-296 v2's own historical context (correctly named as the framing being corrected)
- Inside `docs/architecture/adr296-canon-and-runtime-audit.md` (the audit document, by design)
- Inside FOUNDATIONS Axiom 2 hardening's "Acts continuously while the human sleeps" phrasing (operator-axis claim about standing intent applied continuously, not runtime-axis claim about continuous cycle)

ADR-256 + ADR-253 + ADR-258 + ADR-261 + ADR-274 all carry forward-pointing supersession banners citing ADR-296 v2. ADR-256's banner explicitly names the Phase 1/2/3 changes. No straggling pre-cutover commitments.

### L6-F2 — FOUNDATIONS Axiom 4 wake-source taxonomy + Derived Principle 20 are the structural canon for Variant F claim #5
**Location**: `docs/architecture/FOUNDATIONS.md:322-405` + Derived Principle 20
**Verdict**: **ALIGNED**

FOUNDATIONS canonizes:
- Five wake sources (`cron_tick | addressed | proposal_arrival | substrate_event | manual_fire`)
- Singular invocation gateway `services/wake.py::submit_wake_proposal()`
- "Mid-loop continuation is not a wake" clause
- Wake sources are kernel-internal; Reviewer reasons against worldview not wake source

This is the structural backbone of Variant F's "wake-fired" claim.

### L6-F3 — FOUNDATIONS has no Reviewer-formalization derived principle that lifts Variant F to canonical anchor status
**Location**: `docs/architecture/FOUNDATIONS.md` (no entry yet)
**Verdict**: **DRIFT**

Variant F itself does not appear as a single canonical sentence in FOUNDATIONS today. The seven structural claims are each canonized individually (Axiom 2 for persona-bearing seat; Axiom 4 + DP20 for wake-fired; Axiom 1 + ADR-209 for filesystem-native; ADR-298 for queue-serialized + pace; etc.) but no single principle assembles them into the one-sentence formalization.

This is exactly the operator's stated session goal: "the codebase's Reviewer framing either aligns with Variant F or has an authored finding explaining the drift + Hat-A recommendation… when a new operator (or new contributor) reads any one Reviewer-framing artifact, they get the same answer to 'what is the Reviewer.' Variant F is that answer."

**Recommendation (Hat-A)**: Add Variant F as a new FOUNDATIONS **Derived Principle 21** ("Reviewer formalization") that quotes the sentence verbatim and points to its seven structural claims with ADR/Axiom citations. Place it near Derived Principle 20 (wake-as-irreducible-unit) since they compose.

### L6-F4 — GLOSSARY Reviewer entry is structurally correct but doesn't cite Variant F
**Location**: `docs/architecture/GLOSSARY.md:179`
**Verdict**: **DRIFT** (minor)

Current entry:
> | **Reviewer** | The systemic Agent that occupies the independent judgment seat. One per workspace. Substrate at `/workspace/review/` (seven canonical files — see separate entry). The seat (role) persists; the occupant rotates (human operator / AI reviewer / external service / impersonated admin). All occupant classes render verdicts through the same dispatch flow; the difference is which occupant is currently filling the seat per `OCCUPANT.md`. | An **Agent** in the sharp sense. […] **Distinctness:** Reviewer is not distinguished from other Agents by Identity class (the seat is occupant-swappable). It is distinguished by its Purpose + Trigger cell — independent judgment (Purpose) on Axiom 4 wake events (Trigger; fires when the evaluation funnel escalates across any of the five wake sources per ADR-296 v2 D1). See ADR-194 v2 + ADR-211 + [reviewer-substrate.md](reviewer-substrate.md). |

This is correct but verbose and doesn't carry the Variant F anchor.

**Recommendation (Hat-A)**: Prepend the Variant F sentence to the entry as a `**Canonical formalization**:` first paragraph. Existing prose stays as elaboration.

---

## Summary

### Total findings: 18 items across 6 layers
- **ALIGNED**: 9 (L1-F2, L1-F5, L1-F6, L2-F1, L3-F1, L3-F2, L4-F1, L4-F3, L4-F4, L5-F7, L6-F1, L6-F2)
- **DRIFT**: 9 (L1-F1, L1-F3, L1-F4, L4-F2, L5-F1 through L5-F6, L6-F3, L6-F4)
- **OPEN-QUESTION**: 1 (L2-F2 — queue depth in envelope)

### Drift is narrower than the stub forecast

The stub predicted broad drift across ~6 layers; actual drift is concentrated in **two thematic clusters**:
1. **Variant F never anchored** (L1-F1, L6-F3, L6-F4) — the formalization sentence doesn't exist as a single canonical place in code or canon. Operator-stated session goal directly addresses this.
2. **Verdict-emission prose-bound not structurally bound** (L4-F2 + L5-F1 through L5-F6) — every judgment hook/recurrence prompt asks for verdict shape in prose; the LLM has discretion to emit text-only; the text-only fallback converts to inert stand_down. Same root cause as the canary v3 finding.

Layers 2, 3, 4 (envelope, primitives, loop nudges) are **substantively aligned** with Variant F — the architectural cutover for ADR-296 v2 + ADR-298 left them clean.

### Recommended Hat-A scope (Commit 2)

**Cluster 1 — Anchor Variant F**:
- FOUNDATIONS: add Derived Principle 21 quoting Variant F (L6-F3)
- GLOSSARY: prepend Variant F to Reviewer entry (L6-F4)
- `_PERSONA_FRAME` header: add 3-sentence preamble quoting Variant F + citing FOUNDATIONS DP21 (L1-F1)
- `_PERSONA_FRAME` cadence section: add pace + queue-serialization sentences (L1-F3, L1-F4)

**Cluster 2 — Bind verdict-emission structurally**:
- alpha-author `_hooks.yaml`: tighten `pre-ship-audit` prompt close (L5-F1)
- alpha-author `_recurrences.yaml`: tighten 3 prompts (L5-F2, L5-F3, L5-F4)
- alpha-trader `_recurrences.yaml`: tighten 2 prompts (L5-F5, L5-F6)

**Regression test** (`api/test_reviewer_formalization.py`):
- Greps `_PERSONA_FRAME` for banned phrases ("continuously running", "self-invoke", "background process", "self-pacing process")
- Greps `_PERSONA_FRAME` for required phrases (the Variant F sentence verbatim; "wake-fired"; "single-lane"; "operator-declared pace + autonomy"; "operator-authored mandate")
- Greps every judgment-mode prompt in alpha-author + alpha-trader for required structural binding (regex `ReturnVerdict\(verdict=`)
- Confirms `FireInvocation` NOT in `REVIEWER_PRIMITIVES`
- Confirms `ManageHook` + `Schedule` IN `REVIEWER_PRIMITIVES`
- Confirms `DEFAULT_REVIEWER_WRITE_LOCKS` contains exactly the 5 paths

**CHANGELOG entry**: `[2026.05.22.1]` per Prompt Change Protocol.

### Out of scope for Commit 2 (record as residual)

- L2-F2 (queue depth in envelope) — recommend NOT surfacing; record as deliberate non-action
- L4-F2 (text-only fallback verdict-shape distinction) — defer until L5 prompt tightening lands; revisit if symptom persists
- Any drift in domains beyond alpha-author + alpha-trader — no other bundles ship judgment prompts today

---

## Cross-references

- Predecessor stub: [`2026-05-21-021204-reviewer-prompt-strategy-audit-stub/findings.md`](../2026-05-21-021204-reviewer-prompt-strategy-audit-stub/findings.md)
- Canary v3 (text-only fallback empirical trigger): [`2026-05-21-014009-reviewer-round-budget-population-audit/findings.md`](../2026-05-21-014009-reviewer-round-budget-population-audit/findings.md) §"Resolution addendum"
- ADR-296 v2 (wake architecture canon): [`docs/adr/ADR-296-continuous-judgment-cycle.md`](../../../docs/adr/ADR-296-continuous-judgment-cycle.md)
- ADR-298 (wake queue + pace): [`docs/adr/ADR-298-wake-queue-pace.md`](../../../docs/adr/ADR-298-wake-queue-pace.md) (or whatever the canonical filename is — verify at Hat-A time)
- FOUNDATIONS Derived Principle 20: [`docs/architecture/FOUNDATIONS.md`](../../../docs/architecture/FOUNDATIONS.md) (the structural neighbor for the proposed DP21)
- Reviewer persona frame: [`api/agents/reviewer_agent.py::_PERSONA_FRAME`](../../../api/agents/reviewer_agent.py)
- Reviewer wake envelope: [`api/services/reviewer_envelope.py`](../../../api/services/reviewer_envelope.py)
- REVIEWER_PRIMITIVES: [`api/services/primitives/registry.py:385-424`](../../../api/services/primitives/registry.py)
- DEFAULT_REVIEWER_WRITE_LOCKS: [`api/services/workspace_paths.py:187-206`](../../../api/services/workspace_paths.py)
