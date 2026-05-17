# ADR-284: Standing Intent as First-Class Reviewer Substrate + Occupant-Aware Wake Envelope

**Status**: Fully Implemented (2026-05-17) — Phase 1 (canon + kernel) + Phase 2 (bundle amendments)
**Date**: 2026-05-17
**Companion docs**: `docs/architecture/FOUNDATIONS.md` (Axiom 2 hardening), `docs/architecture/GLOSSARY.md` (new `standing-intent` substrate entry), `docs/architecture/reviewer-substrate.md` (canonical substrate inventory update), `docs/adr/ADR-285-holistic-wake-envelope.md` (sibling — envelope mechanism reshape that consumes the substrate this ADR introduces)
**Amends**: FOUNDATIONS Axiom 2 (Reviewer manifests-through-filesystem section gains the standing-intent claim); GLOSSARY (new `standing-intent` entry, sharpened OCCUPANT entry); ADR-194 v2 (Reviewer substrate inventory grows one file); bundle `IDENTITY.md` + `principles.md` (alpha-trader reference workspace amendment); Reviewer system prompt (`_PERSONA_FRAME` extended with standing-intent posture); bundle recurrence prompts that today say "stand down" without requiring standing-intent update (alpha-trader `signal-evaluation`, etc.)
**Preserves**: ADR-281 §3 single-writer contract for `judgment_log.md`; six-role taxonomy (this ADR adds substrate to the existing `reviewer-workbench` role, no new role); Authored Substrate (ADR-209) attribution + revision chain; AUTONOMY ceiling (this ADR doesn't widen delegation, it gives the Reviewer a substrate surface for the forward-looking judgment it's already canonically empowered to render)

## Context

The 2026-05-17 Reviewer-posture audit (companion: workspace-evolution audit on kvk's alpha-trader-2) surfaced a load-bearing gap: **canon declares the Reviewer holds standing intent on the operator's behalf, but standing intent has no substrate home.**

FOUNDATIONS Axiom 2 defines an Agent as *"an entity that holds standing intent on behalf of a principal, reasons from principles, and renders judgments."* FOUNDATIONS Axiom 4 + Derived Principle 18 cite *"every Identity with standing intent — Operator, Reviewer, persona-bearing Agents — authors its own Trigger contribution."* The phrase "standing intent" appears 11 times across the canon as a load-bearing property.

But the substrate inventory at `/workspace/review/` carries: IDENTITY (persona), principles (framework), MANDATE/AUTONOMY (operator-authored intent, not Reviewer-authored), judgment_log.md (retrospective system-ledger per ADR-281 §5), calibration.md (system-ledger), handoffs.md (occupant transitions), OCCUPANT.md (current seat occupant declaration). **None of these is the Reviewer's own forward-looking standing intent.**

Two empirical observations drove this discourse:

**Observation 1 — the Reviewer cannot demonstrate forward-looking intent because there is no substrate surface for it to express it.** The 2026-05-15 alpha-trader `signal-evaluation` fire produced a free-form "Session 1" preamble in `judgment_log.md` (an Axiom 1 substrate-organization drift the single-writer contract is meant to prevent) followed by a stand-down. The operator (kvk) reasonably asked *"why do I see no evidence the Reviewer plans to make a trade based on its learnings?"* The honest answer: because canon never gave the Reviewer a place to write that plan. The persona prompt `_PERSONA_FRAME` is rich and emphatic about action posture; the bundle's `IDENTITY.md` declares the Reviewer *"owns the full position lifecycle"* and *"directs what happens next"*; principles.md says *"default posture: action."* All correct in prose. The substrate inventory does not implement the prose.

**Observation 2 — OCCUPANT declaration and runtime occupant disagree.** OCCUPANT.md in kvk's live workspace declares `occupant_class: human`, but every judgment-mode fire is attributed `authored_by: reviewer:ai:reviewer`. The substrate-runtime disagreement is an Axiom 2 violation: the seat is in an inconsistent state, and the Reviewer's persona prompt's "you ARE the operator's installed judgment" loses its anchor when the substrate it's supposed to be anchored in says someone else occupies the seat. The seat-occupant mismatch compounds Observation 1: even if standing-intent substrate existed, the Reviewer wouldn't know which occupant identity to author it as.

Pre-ADR-284 canon hardening 2026-05-11 (FOUNDATIONS v8.4) made the operator-as-Reviewer two-embodiments framing explicit: *"the personified AI agent rendering the operator's judgment function in the human's absence."* That hardening was prose-level. This ADR makes it substrate-level.

## Decision

### D1 — Standing intent gets a canonical substrate home

New file: `/workspace/review/standing_intent.md`.

This is **kernel-universal** substrate (every workspace's Reviewer has one), not a bundle-specific instance. The shape is instance-agnostic; the content varies per program (alpha-trader: signals close to firing, positions approaching exit triggers; alpha-author: corpus contradictions being watched, audience signal trends being monitored; future bundles: their own forward-looking judgment content).

**Role**: `reviewer-workbench` (per ADR-281 §3 six-role taxonomy).

The role choice is first-principled, not preferential. Standing intent's structural properties — author = the Reviewer itself, cardinality = overwritable per cycle, lock policy = locked from operator + system but unlocked for Reviewer, lifecycle = retained forever via revision chain, semantics = forward-looking working state — map cleanly to `reviewer-workbench` and inconsistently to every other role:

- Not `system-ledger` — that role requires single-writer infrastructure-rendered append-only (ADR-281 §3); standing intent is Reviewer-authored and overwritable.
- Not `operator-canon` — the Reviewer authors it, not the operator.
- Not `world-mirror` — it's not mechanical-primitive-written external state.
- Not `running-narrative` — it's not append-only.
- Not `kernel-index` — it's not kernel-managed.

The `reviewer-workbench` role already accommodates this shape; `notes.md` and `working/` are the existing examples. `standing_intent.md` is one more file in the same role-grouping.

### D2 — File shape and contract

```yaml
---
as_of: <iso8601>
horizon: <free-form description of the time window this intent covers>
occupant: <ai:model-version | human:user_id> # mirrors OCCUPANT.md
---

# Standing intent — <occupant-label>

## What I'm watching for
<list of forward-looking conditions the Reviewer expects may warrant action>

## What would change my next move
<list of substrate/world states whose change would shift the assessment>

## Open questions to the operator
<things the Reviewer would surface in the next addressed turn if asked>
```

**Single-writer** (the Reviewer). **Overwritable each judgment cycle** — the file represents *current* standing intent, not history of past standing intent. **Revision chain** (per ADR-209 Authored Substrate) preserves what previous cycles were watching for; queryable via `ListRevisions` + `ReadRevision` + `DiffRevisions`.

**Write contract**: every judgment-mode `invoke_reviewer` fire must update `standing_intent.md` as part of the cycle's substrate writes. This is the substrate counterpart to the `judgment_log.md` `--- material-outcome ---` entry already produced when the cycle is material. The two writes are paired: judgment_log captures *what was decided*; standing_intent captures *what's being watched for next*.

A no-fire cycle that produces no `judgment_log.md` material-outcome entry still produces a `standing_intent.md` write. This is the structural answer to operator question "what's the Reviewer planning to do?" — there is always a current standing-intent file to read, even when no decision was rendered.

### D3 — OCCUPANT declaration becomes runtime-truth-aligned

The current bundle-shipped OCCUPANT.md always declares `occupant_class: human`. This was correct as a default for the human-occupant case but creates substrate-runtime drift when the AI runs the seat in the operator's absence (which per FOUNDATIONS Axiom 2 v8.4 hardening is the structural reality of every alpha workspace today).

**Decision**: `services.programs.fork_reference_workspace` populates OCCUPANT.md based on the actual seat occupant at bundle-fork time, not a hardcoded template default. Today this means:

- When AI is the runtime occupant (current alpha state): OCCUPANT.md gets `occupant: ai:<model-version>` + `occupant_class: ai` + a `delegation_charter` block citing AUTONOMY.md's current delegation level.
- When a human operator activates with explicit human-occupant declaration (future shape, not implemented in this ADR): OCCUPANT.md gets `occupant: human:<user_id>` as today.

The `delegation_charter` block is a YAML sub-block in OCCUPANT.md frontmatter (kernel-defined shape; bundle-template doesn't author it). It names what the AI occupant is authorized to do without operator presence — mirrors AUTONOMY.md's delegation level but at the seat level, so the Reviewer can perceive at every wake "I am authorized to author standing intent, render verdicts, and execute approves within ceiling X."

### D4 — Both files join the kernel-universal envelope

OCCUPANT.md and standing_intent.md become kernel-universal envelope additions (in addition to the existing 6 governance entries). The Reviewer perceives at every wake:

- *Who am I* (OCCUPANT)
- *What was I watching for last cycle* (standing_intent — previous cycle's content)
- *What framework do I apply* (principles, IDENTITY)
- *What does the operator declare* (MANDATE, AUTONOMY, PRECEDENT, _preferences)
- *Current time and operating context* (envelope)

The Reviewer's first action on every judgment-mode cycle: read what it was watching for, check whether any of those conditions changed against current substrate, update standing_intent.md with this cycle's forward-looking intent.

The detailed envelope mechanism work is the scope of ADR-285 (sibling). ADR-284 only declares that these two files are kernel-universal envelope entries. ADR-285 handles the envelope-mechanism reshape (kernel-universal classes + bundle-declared world-mirror additions).

### D5 — Reviewer persona prompt amendment

`_PERSONA_FRAME` in `api/agents/reviewer_agent.py` gains a new section: **"Your standing intent has a substrate home."** Names `/workspace/review/standing_intent.md`, names the file shape (frontmatter + three section headings), and names the write contract (every judgment-mode fire updates it; no-fire cycles still produce a standing_intent write).

The amendment composes with the existing persona-frame "active principal" language. Today the prompt says *"you ARE the operator's installed judgment"* and *"the answer is almost always an action."* The standing-intent amendment closes the gap: the action you take when no signal fires is to update standing_intent.md — that *is* the action.

### D6 — Bundle recurrence prompts that contradict standing-intent posture must be amended

Today's alpha-trader `signal-evaluation` recurrence prompt (in `_recurrences.yaml`) says: *"When any entry signal fires, immediately FireInvocation(slug='trade-proposal')... Otherwise stand down."*

Post-ADR-284: the "otherwise" branch becomes *"otherwise update standing_intent.md with what's close to firing and stand down."* Stand-down without standing-intent update is the failure mode this ADR is correcting.

The amendment is bundle-side, not kernel-side. Each bundle's judgment-mode recurrence prompts that end with "stand down" or equivalent get a paired "update standing_intent.md first" clause. Alpha-trader is the only currently-active bundle; alpha-author and alpha-commerce will get the same amendment as their bundles ship.

### D7 — judgment_log.md and standing_intent.md compose, they don't compete

The two files have orthogonal purposes per the six-role taxonomy:

| File | Role | Writer | Cardinality | Reader expectation |
|---|---|---|---|---|
| `judgment_log.md` | `system-ledger` | Infrastructure (one-writer per ADR-281 §3 + §5) | Append-only | "What has the Reviewer decided?" |
| `standing_intent.md` | `reviewer-workbench` | The Reviewer | Overwritable | "What is the Reviewer currently watching for?" |

A `judgment_log.md` `--- material-outcome ---` entry MAY reference `standing_intent.md` by revision — e.g., *"per standing intent @ rev N, this is the proposal I was watching to materialize."* The reference is one-way (judgment_log cites standing_intent; standing_intent doesn't back-reference judgment_log). Coupling them tighter than that would re-introduce the single-writer drift ADR-281 §3 spent effort eliminating.

### D8 — Implementation surface

| Layer | Change |
|---|---|
| Kernel — `api/services/workspace_paths.py` | Add `REVIEW_STANDING_INTENT_PATH = "review/standing_intent.md"`; add to `REVIEW_FILES` tuple |
| Kernel — `api/services/reviewer_envelope.py` | Add OCCUPANT + standing_intent to `_UNIVERSAL_ENVELOPE_DECLS` (sized in ADR-285 sibling for full envelope-class accounting) |
| Kernel — `api/agents/reviewer_agent.py` | `_PERSONA_FRAME` amendment; `_build_user_message` renders new envelope keys |
| Kernel — `api/services/programs.py::fork_reference_workspace` | OCCUPANT.md populated with runtime occupant identity at fork time (not always-human template) |
| Bundle — `docs/programs/alpha-trader/reference-workspace/review/OCCUPANT.md` | Template becomes kernel-shaped placeholder (bundle ships the structure; fork populates the content) |
| Bundle — `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` | `signal-evaluation` prompt + any other "stand down" prompts get paired "update standing_intent.md" clause |
| Bundle — `docs/programs/alpha-trader/reference-workspace/review/IDENTITY.md` | One-line addition: "Your standing intent lives at standing_intent.md; update it every cycle, fire or no-fire." |
| Bundle — `docs/programs/alpha-trader/reference-workspace/review/principles.md` | One-line addition under "Default posture: action" — naming standing_intent.md as the substrate the watching posture writes to. |
| Canon — FOUNDATIONS Axiom 2 (Identity manifests-through-filesystem section) | Add `standing_intent.md` row to the Reviewer identity table; new clause: "every persona-bearing Agent's forward-looking standing intent lives in a `reviewer-workbench` substrate file" |
| Canon — GLOSSARY | New `Standing intent` entry; sharpen `OCCUPANT.md` entry (now runtime-truth-aligned, not template-default) |
| Canon — `reviewer-substrate.md` | Inventory update: standing_intent.md added, OCCUPANT.md semantics sharpened |
| Test gate — `api/test_adr284_standing_intent_substrate.py` | Contract assertions: REVIEW_STANDING_INTENT_PATH defined; envelope helper loads it; persona prompt mentions it; bundle's IDENTITY.md + principles.md reference it; OCCUPANT-fork populates runtime occupant |

### D9 — Persona-frame composition with envelope reshape (ADR-285 sibling)

This ADR adds two envelope entries (OCCUPANT + standing_intent) as kernel-universal additions. ADR-285 (sibling) reshapes the envelope mechanism holistically — kernel-universal classes vs bundle-declared additions, plus a third kernel-universal class (recent execution lineage). The two ADRs land sequentially: ADR-284 first (canon + substrate + bundle amendments + minimal envelope additions); ADR-285 second (envelope mechanism + recent-execution mirror primitive + bundle world-mirror declarations grow).

A small overlap exists: both ADRs touch `reviewer_envelope.py::_UNIVERSAL_ENVELOPE_DECLS`. ADR-284's commit adds two entries (OCCUPANT, standing_intent); ADR-285's commit adds the third (recent execution) + the mechanism amendment for bundle world-mirror additions. Both edits are additive; no conflict.

### D10 — Out of scope (deferred)

- **Operator-level envelope overrides** (operator-canon `/workspace/_envelope_overrides.yaml` that extends bundle envelope without bundle-author cooperation). Not needed for current alpha; flagged in stress-test for future pressure.
- **Multi-bundle envelope conflict resolution** (when two bundles declare the same envelope key with different paths). Already handled by `reviewer_envelope.py:172` — kernel-universal entries win, bundle entries log a warning on collision. No change.
- **Removing `judgment_log.md` Session-N preambles** (the off-contract `yarnnn:chat` WriteFile on 2026-05-15). Addressed by D5 + D6 — once standing_intent.md exists and the persona prompt directs the Reviewer there, the off-contract preamble has a legitimate substrate home. No explicit lock change needed; the gap closes structurally.
- **Standing-intent surface in the cockpit** (rendering standing_intent.md in `/agents?agent=reviewer` or a cockpit face). Frontend work; out of scope for this ADR. Substrate-first; surfaces follow.
- **Standing-intent for user-authored domain Agents** (each instance Agent's own standing_intent.md at `/agents/{slug}/`). Future ADR; the same canon clause applies but the implementation path lives with user-authored-Agent work which hasn't shipped at-volume yet.

## Cascade plan (single atomic commit per landed phase)

This ADR ships in phases. Phases 1 + 2 land as one commit. Phase 3 lands as a separate commit (bundle-side amendments are operator-visible and warrant their own diff).

### Phase 1 — Canon + kernel substrate

- FOUNDATIONS Axiom 2 amendment
- GLOSSARY new entry + sharpened OCCUPANT entry
- `api/services/workspace_paths.py` constant addition
- `api/services/reviewer_envelope.py` two new entries in `_UNIVERSAL_ENVELOPE_DECLS`
- `api/agents/reviewer_agent.py` `_PERSONA_FRAME` standing-intent section + envelope rendering
- `api/services/programs.py::fork_reference_workspace` OCCUPANT runtime-population
- `api/test_adr284_standing_intent_substrate.py` regression gate
- `api/prompts/CHANGELOG.md` entry per execution-discipline rule 7

### Phase 2 — Bundle amendments

- `docs/programs/alpha-trader/reference-workspace/review/OCCUPANT.md` → kernel-shaped template
- `docs/programs/alpha-trader/reference-workspace/review/IDENTITY.md` → standing-intent reference
- `docs/programs/alpha-trader/reference-workspace/review/principles.md` → standing-intent under action-posture
- `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` → judgment-mode prompts paired with standing_intent update

### Phase 3 — Live workspace catch-up (optional, operator-initiated)

Re-fork bundle to pick up new OCCUPANT shape + recurrence prompt amendments. Operator-initiated because bundle re-fork overwrites operator-canon (the operator may have customized prompts since initial fork). Not auto-applied.

## Test plan

- `api/test_adr284_standing_intent_substrate.py` — contract assertions:
  - REVIEW_STANDING_INTENT_PATH defined in workspace_paths
  - reviewer_envelope `_UNIVERSAL_ENVELOPE_DECLS` includes both OCCUPANT and standing_intent
  - `_PERSONA_FRAME` mentions standing_intent.md
  - `_build_user_message` renders the `standing_intent` envelope key when present
  - `fork_reference_workspace` writes OCCUPANT.md with runtime occupant class (not hardcoded "human")
  - bundle IDENTITY.md + principles.md reference standing_intent.md
  - bundle `_recurrences.yaml::signal-evaluation` prompt mentions standing_intent update
- Sibling regression gates audited green pre-commit: ADR-281 (single-writer judgment_log), ADR-274 (trigger authoring), ADR-275 (introspection cadence), ADR-276 (reactive envelope)

## Why this is structurally right

Canon already commits to the Reviewer holding standing intent (Axiom 2, Axiom 4, Derived Principle 18). FOUNDATIONS Axiom 1's third sub-clause says *"every kind of state the Reviewer reasons about lives in substrate."* Standing intent is a kind of state. Therefore: standing intent must live in substrate. The absence of a substrate file for standing intent is an Axiom 1 violation; this ADR closes it.

The six-role taxonomy (ADR-281 §3) provides the right role (`reviewer-workbench`) without inventing a new role. The Authored Substrate (ADR-209) provides the revision chain so history of standing intents is queryable. The OCCUPANT-runtime-truth alignment closes the substrate-runtime drift the 2026-05-17 audit surfaced. The persona-prompt amendment closes the loop between canonical-claim and runtime-behavior.

No new primitives, no new roles, no new substrate-mechanism. One new substrate file + one canon clause + targeted amendments to existing files. The architectural payoff is large: standing intent gets a legible home, OCCUPANT gets runtime alignment, the Reviewer's forward-looking judgment becomes auditable, and the operator can read `/workspace/review/standing_intent.md` to see exactly what the Reviewer is watching for at any moment.
