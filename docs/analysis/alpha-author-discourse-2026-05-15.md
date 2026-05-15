# Alpha-Author Discourse — Decision Log

**Date**: 2026-05-15
**Status**: Decisions locked, ADRs pending (ADR-282 axiom rename, ADR-283 alpha-author bundle)
**Author**: kvk + claude

## Origin of the discourse

Session began as an audit of write capabilities — the user wanted to remember what non-trading writes existed in the codebase after months of alpha-trader focus. The audit surfaced the kernel/bundle boundary cleanly: `write_slack`, `write_notion`, `write_email` are kernel-side (any program); `write_commerce`, `write_trading`, `write_prediction`, `write_defi` are bundle-side (program-specific). That framing pulled the conversation toward a broader question: what would refocusing on generalized knowledge work look like?

The discourse then walked through a sequence of progressively-sharpened reframings, each one explicitly rejecting the previous step's framing as too broad. The final landing point is a *specific* second bundle (`alpha-author`) with a specific archetype (substrate-continuity, not autonomous-execution), authored against a *renamed* Axiom 8 (`ground-truth substrate`, not `money-truth`).

## Decisions locked

### 1. Second bundle is `alpha-author`

Not `alpha-creator`, not `alpha-operator`, not `alpha-knowledge`. The naming work matters because the slug propagates into MANIFEST identity, filesystem paths, IDENTITY.md framing, Reviewer persona context, and GTM positioning.

Why `alpha-author`:
- Claims a *stance*, not just a job. Authors author. The word is the verb in the mandate.
- Filters the right ICP. Someone churning posts to feed an algorithm wouldn't self-identify as an author; someone building a body of work (newsletter writer, podcaster, video essayist, paid-community curator) would.
- Distances from "creator economy" commodity framing where every AI startup is racing.
- Transcends format (medium-agnostic — written, audio, video, designed).
- Pairs with the mandate sentence (the word *author* appears in both bundle slug and mandate). Same self-referential property `alpha-trader` has.
- Naturally accommodates the Reviewer's role: the Reviewer in this bundle is editor-shaped, and "editor" has a legible analog in the world.

Rejected alternatives:
- `alpha-creator` — broader ICP but commodity positioning; user explicitly identified that broad-stroked archetypes produce broad-stroked results and harder sells.
- `alpha-operator` — recursion problem (operator-operator) was tolerable but the bundle's archetype is more specifically about authoring than about operating-a-domain.
- `alpha-knowledge` — too generic; doesn't tell you what gets done.
- `alpha-publisher` — industrially-coded (drags NYT/Penguin association).
- `alpha-essayist` — archetypally right but ICP too narrow.

### 2. Mandate sentence

*"Convert lived attention into authored corpus that compounds."*

Six words. Structural parallel to alpha-trader's *"convert observation into capital efficiently."*

- **Input** (lived attention): the rare ingredient, the operator's ongoing absorption of their domain filtered through worldview
- **Output** (authored corpus): the compounding substrate, the body of work that becomes ownably the operator's over time
- **Constraint** (that compounds): one phrase carrying the full Reviewer spec — corpus only compounds if voice is consistent, cadence holds, content doesn't drift toward AI-slop, and continuity is preserved

The constraint phrase is doing the same load-bearing work that "efficiently" does in alpha-trader. Every Reviewer principle inherits from it.

### 3. Archetype is substrate-continuity, not autonomous-execution

Two valid bundle archetypes exist within YARNNN's architecture, exercising different parts of the framework:

- **Autonomous-execution archetype** (alpha-trader's shape) — Reviewer-as-decision-maker, fast loop, immediate ground-truth attribution, single-signal calibration. GTM pitch: "agent acts within bounds you authored."
- **Substrate-continuity archetype** (alpha-author's shape) — Reviewer-as-auditor-and-continuity-guardian, slower multi-signal calibration, accumulating-corpus-as-moat. GTM pitch: "persistent seat that grows into your domain and applies your discipline."

This is not a downgrade of alpha-author. It exercises a different (and more defensible long-term) part of the architecture, because the execution-autonomy race is going to be brutally commoditized over 2026–2027, while substrate moats are harder to commoditize.

The Reviewer's role in alpha-author is editor-shaped, not approver-shaped. Voice fingerprint enforcement, continuity audit across corpus, cadence discipline, anti-AI-slop drift detection.

### 4. Axiom 8 rename: `money-truth` → `ground-truth substrate`

The axiom is correct; the noun is restrictive. "Money-truth" overfit to alpha-trader's instantiation (Alpaca P&L) and accidentally locked the kernel-level concept into one domain.

Generalized axiom: **the workspace must touch a substrate that the operator personally bears the consequences of, that flows back into the workspace, and against which judgment can be calibrated.** Three load-bearing properties: consequence-bearing, substrate-grounded, calibratable.

This is consistent with THESIS.md (which already uses "ground-truth" liberally and explicitly does not claim universality of monetary signal) — the rename surfaces a distinction THESIS already holds and propagates it into FOUNDATIONS Axiom 8 vocabulary.

Instance-level preservation: `money-truth` survives as alpha-trader's instance-level term. `_money_truth.md` filename stays. `services/outcomes/*.py` code unchanged. The kernel rename does not cascade into the alpha-trader bundle's domain vocabulary — that vocabulary was always instance-level, not kernel-level.

For alpha-author, the instance-level ground-truth shape is multi-signal:
- **Internal coherence** (always present) — corpus contradictions, voice drift, continuity breaks. The Reviewer's continuity audits *are* the ground-truth signal when no external audience exists yet (e.g., Netflix script workspace).
- **Audience signal** (when present) — engagement deltas, subscriber cohort behavior, comment patterns.
- **Revenue signal** (when present) — MRR, churn, ARPU through Lemon Squeezy or equivalent.

The script workspace was the disconfirming case that exposed the original framing's limit. A workspace authoring a screenplay has zero external ground-truth for months but still needs Axiom 8 to hold. Internal substrate coherence (does scene 12 contradict scene 5?) plays the ground-truth role until external signal arrives (producer interest, reads, sales).

### 5. Two-workspace dogfood plan

The user proposed two concrete workspaces in their actual life:
- **`yarnnn-author` workspace** — founder content / build-in-public / IR-adjacent narrative about YARNNN itself
- **`netflix-script-author` workspace** — screenplay authoring for a side-hobby project

Both workspaces run the same bundle (`alpha-author`) with workspace-specific persona / IDENTITY / principles. Same architectural pattern as alpha-trader supporting Simons-vs-Buffett-vs-Deming personas.

The two workspaces test the bundle's range natively:
- Short-recurring (founder updates) + long-arc-single-output (script) exercises both ends of the authoring spectrum
- Audience-bearing (founder updates) + no-external-audience (script) stress-tests the ground-truth substrate's degradation modes
- Publishing-cadence (founder updates) + revision-cadence (script) tests whether the bundle's cadence shape is genuinely permissive

This is a stronger dogfood signal than any single bundle dogfooded against one workspace. Two workspaces force the bundle to be genuinely *general within its archetype* rather than accidentally tilted toward one shape.

### 6. Sequencing: axiom rename first, bundle second

Two-ADR sequence in order:

1. **ADR-282** — Axiom 8 rename (`money-truth` → `ground-truth substrate`). FOUNDATIONS + GLOSSARY + LAYER-MAPPING. Alpha-trader instance terms preserved. No code rename.
2. **ADR-283** — alpha-author bundle. Authored against the corrected axiom. Mandate locked. Reviewer-as-editor archetype. Two-workspace dogfood plan documented.

Sequencing rationale: if the bundle ships before the rename, alpha-author either inherits the legacy money-truth framing (which the script workspace would immediately disconfirm) or implicitly contradicts the axiom (which creates inconsistency the next architect would have to clean up). Fixing the axiom first means alpha-author inherits the corrected version natively. Same Singular Implementation discipline as elsewhere in the architecture.

It also gives the axiom rename its own discoverable ADR. Someone searching `docs/adr/` for "ground-truth" six months from now should land on the rename ADR directly, not on alpha-author's MANIFEST.

## Open rounds (deferred for the bundle ADR)

These were named in the discourse spine but not yet decided. They benefit from being authored *against* the renamed axiom:

1. **Instance-level ground-truth name + shape** for alpha-author — likely multi-signal substrate (corpus-coherence + audience-engagement + revenue-when-present). Canonical filename TBD (`_signal.md`? `_corpus_state.md`? compound shape?).

2. **Cadence shape** — bundle must accommodate ship-pulse and revision-pulse gracefully. Recurrences probably stay *capability-shaped* (ship-check, voice-audit, continuity-audit) rather than *schedule-shaped*, with workspace-level config picking schedules.

3. **Cockpit faces** — four-face structure parallel to alpha-trader, but the third face must degrade gracefully when external signal is absent. Speculative: Mandate · Corpus state · Voice consistency · Pipeline (drafts → shipped → audience).

4. **Capability menu** — permissive: declare a menu of useful capabilities, let workspace-level activation pick the subset that matters. For audience-bearing workspaces: publishing-platform writes (LinkedIn, X, newsletter platform). For script-shape workspaces: document-heavy reads/writes. Expanded Notion writes (page-level, not just comments) likely useful across both.

5. **Reviewer principles starter set** — editorial discipline, voice fingerprint enforcement, continuity audit, anti-AI-slop drift detection, cadence enforcement. Operator authors workspace-specific persona/principles on top.

## Discipline reminders carried forward

A few principles emerged from the discourse that should propagate into how the alpha-author bundle gets authored:

- **The dogfooder's edge cases ≠ the median ICP's needs.** When the architect is the dogfooder, the bundle can accidentally optimize for the dogfooder's atypical work patterns. Ask repeatedly: "does the median author care about this, or just me?"
- **Specificity is value.** Broad-stroked archetypes produce broad-stroked results. The user's own thesis. Carry it into bundle authoring — every Reviewer principle should be sharp enough that someone could disagree with it.
- **One bundle, multi-workspace instantiation.** The bundle is medium-agnostic and cadence-agnostic at the mandate level. Workspace-specific persona/principles do the differentiation. Don't accidentally fork the bundle to accommodate edge cases the persona could absorb.
- **Honest naming of failure modes.** Substrate-continuity archetype is slower and less viscerally measurable than autonomous-execution archetype. Be honest in GTM materials — the pitch is "compounds over time" not "agent does X for you."

## Cross-references for downstream ADR drafting

- **FOUNDATIONS Axiom 8** at `docs/architecture/FOUNDATIONS.md:476-502` — the current axiom text to be amended.
- **GLOSSARY entries** `Outcome`, `_money_truth.md`, `Loop`, `Substrate-canonical world` at `docs/architecture/GLOSSARY.md` — money-truth references to re-cite (not necessarily rename — they're talking about alpha-trader's instance-level term).
- **THESIS commitment 3** at `docs/architecture/THESIS.md:90-94` — already framed as "ground-truth evaluation — money-truth as the spine, universality not claimed". No edit needed; the rename ADR can cite this as supporting evidence that THESIS already holds the distinction.
- **Bundle reference**: `docs/programs/alpha-trader/` (existing canonical example), `docs/programs/alpha-commerce/` (status: deferred, useful as deferred-bundle pattern).
- **ADR-230** (Persona-Program Registry Unification) — the activation flow alpha-author plugs into.
- **ADR-226** (Reference-Workspace Activation Flow) — the bundle-fork mechanics alpha-author inherits.
- **ADR-223** (Program Bundle Specification) — the bundle layout alpha-author conforms to.

## Status

Memo complete. ADR-282 + ADR-283 drafting next.
