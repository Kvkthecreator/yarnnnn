# ADR-283: alpha-author — Second Operator Bundle, Substrate-Continuity Archetype

**Status**: Proposed (scope-locked; deferred-round detail TBD)
**Date**: 2026-05-15
**Companion docs**: `docs/analysis/alpha-author-discourse-2026-05-15.md`, `docs/adr/ADR-282-axiom-8-ground-truth-rename.md` (prerequisite)
**Depends on**: ADR-222 (OS framing), ADR-223 (Program Bundle Specification), ADR-224 (Kernel/Program Boundary), ADR-225 (Compositor Layer), ADR-226 (Reference-Workspace Activation Flow), ADR-230 (Persona-Program Registry Unification), ADR-282 (Axiom 8 rename — must land first)
**Preserves**: kernel boundary (no kernel changes), alpha-trader bundle unchanged, all existing canon axioms

## Context

After alpha-trader stabilized as the first consequential dogfood program, the architecture needed a second bundle to (a) validate that the kernel/bundle boundary genuinely generalizes beyond a single vertical, (b) exercise a different bundle archetype than autonomous-execution, and (c) ship value into a domain where the architect can dogfood honestly.

The 2026-05-15 discourse (`docs/analysis/alpha-author-discourse-2026-05-15.md`) walked through eight progressively-sharpened candidate framings before landing on `alpha-author`. Key turning points captured in the memo:

- Rejected `alpha-creator` for commodity positioning ("creator economy" race-to-bottom)
- Rejected `alpha-operator` (recursion with the existing operator term) and `alpha-knowledge` (too broad)
- Identified that broad-stroked archetypes produce broad-stroked Reviewers and harder sells (Kevin's thesis)
- Identified that the substrate-continuity archetype is more defensible long-term than autonomous-execution as the latter commoditizes
- Validated `alpha-author` against two concrete dogfood workspaces in the architect's actual life (YARNNN founder content + Netflix screenplay side project)
- Used the screenplay workspace's lack of external audience signal as a disconfirming case to surface the Axiom 8 rename (ADR-282)

This ADR ratifies the bundle's identity, mandate, archetype, and dogfood plan. Detail rounds (instance-level ground-truth substrate shape, cadence shape, cockpit faces, capability menu, Reviewer principles starter set) are explicitly deferred to follow-up commits — they benefit from being designed *after* the kernel rename (ADR-282) lands and *before* the bundle's reference-workspace is forked into any live workspace.

## Decision

### D1. Bundle slug: `alpha-author`

The bundle is registered as `docs/programs/alpha-author/` with status `active` per ADR-223 vocabulary.

Naming rationale (full discourse in companion memo): `alpha-author` claims a stance (author-shaped operator authoring a corpus), not just a job (creator producing content). The word filters the right ICP — operators who self-conceive as building a body of work, regardless of medium. The word also pairs with the mandate sentence (the verb `author` appears in both), giving the bundle the same self-referential property `alpha-trader` has. Medium-agnostic and cadence-agnostic at the bundle level; workspace-level persona absorbs medium and cadence specifics.

### D2. Mandate (canonical sentence)

> *"Convert lived attention into authored corpus that compounds."*

Structural parallel to alpha-trader's *"convert observation into capital efficiently."*

- **Input** (lived attention): the rare ingredient — the operator's ongoing absorption of their domain, filtered through worldview
- **Output** (authored corpus): the compounding substrate — the body of work that becomes ownably the operator's over time
- **Constraint** (that compounds): one phrase carrying the full Reviewer spec. The corpus only compounds if voice is consistent, cadence holds, content doesn't drift toward AI-slop, and continuity is preserved. Every Reviewer principle inherits from this phrase, the same way every alpha-trader Reviewer principle inherits from "efficiently."

This sentence becomes the `default_objective` in the bundle's MANIFEST.yaml and the lead clause in the bundle's reference-workspace MANDATE.md.

### D3. Archetype: substrate-continuity (not autonomous-execution)

Within YARNNN's architecture, two bundle archetypes are valid and exercise different parts of the framework:

**Autonomous-execution archetype** (alpha-trader's shape):
- Reviewer-as-decision-maker
- Fast loop (minutes to hours)
- Immediate, attributable ground-truth
- Single-signal calibration
- GTM pitch: *"agent acts within bounds you authored"*

**Substrate-continuity archetype** (alpha-author's shape, this ADR):
- Reviewer-as-auditor-and-continuity-guardian
- Multi-speed loop (continuous coherence + slower external signal)
- Multi-signal ground-truth, attribution often cohort-level
- Calibration via patterns over time, not credit-assignment per verdict
- GTM pitch: *"persistent seat that grows into your domain and applies your discipline"*

The substrate-continuity archetype is the more defensible long-term position. The autonomous-execution race is going to be brutally commoditized over 2026–2027 (every agent platform pitches autonomy). Substrate accumulation + operator-authored judgment compounding is structurally harder to commoditize because the moat is operator's accumulated work product + operator's authored principles, not vendor IP.

The Reviewer's role in alpha-author is editor-shaped — voice fingerprint enforcement, continuity audits across corpus, cadence discipline, anti-AI-slop drift detection. "Editor" has a legible analog in the world, which makes the Reviewer's job operator-comprehensible without architectural explanation.

### D4. Ground-truth substrate is multi-signal (per ADR-282 instance 3)

alpha-author's instance of FOUNDATIONS Axiom 8 (Ground-Truth Substrate, per ADR-282) is multi-signal:

1. **Internal substrate coherence** (always present). The Reviewer's continuity audits across corpus are themselves the ground-truth signal. Detected contradictions, voice drift, broken arcs, stale framings. This signal exists from day one in any alpha-author workspace, regardless of audience or revenue presence.

2. **Audience signal** (when present). Engagement deltas, subscriber cohort behavior, comment patterns, reply velocity. Flows from publishing-platform integrations declared in the bundle's capability menu (see D7).

3. **Revenue signal** (when present). MRR, churn, ARPU through Lemon Squeezy or equivalent. Inherits ADR-183 (Commerce Substrate) + ADR-184 (Product Health Metrics) mechanics natively.

The bundle's reference-workspace seeds all three signal types; workspace-level activation determines which are populated. A pre-monetization newsletter workspace exercises (1) + (2). A Netflix-screenplay workspace exercises (1) only until the script ships. A monetized paid-newsletter workspace exercises all three.

**Disconfirming-case test**: the Netflix-screenplay workspace, with zero external audience signal for months, must still satisfy Axiom 8. It does, because internal substrate coherence (Reviewer-detected continuity audits) is the ground-truth signal until external signal arrives. This was the case that surfaced ADR-282 and validates that the kernel rename was necessary, not cosmetic.

The instance-level filename + substrate shape is **deferred to a follow-up commit** (probably `_signal.md` or compound per-signal files at `/workspace/context/{domain}/`). The decision is intentionally deferred until the bundle's reference-workspace is being authored end-to-end, so the filename serves the actual usage shape rather than being speculative.

### D5. Two-workspace dogfood plan

The architect (kvk) commits to activating `alpha-author` in two concrete personal workspaces:

1. **`yarnnn-author` workspace** — founder content authoring (build-in-public posts, IR-adjacent narrative about YARNNN itself, LinkedIn/blog/newsletter cadence). Exercises: short-recurring publishing cadence, audience signal present (followers/subscribers), eventual revenue signal as YARNNN monetizes.

2. **`netflix-script-author` workspace** — screenplay authoring for a side-hobby project. Exercises: long-arc single-output cadence, revision-pulse rather than ship-pulse, no external audience until shipped, internal-coherence as sole ground-truth for the bulk of authoring time.

The two workspaces are deliberately different shapes so the bundle's claim to medium-agnosticism and cadence-agnosticism is stress-tested natively rather than asserted. If alpha-author works in both, it works across the bundle's claimed range. If it works in only one, the bundle is accidentally tilted and needs to either narrow its claims or generalize further.

This dogfood plan is documented here in the bundle ADR (not in `docs/alpha/personas.yaml`) until ADR-230's persona registry is updated to host the two new persona slots. Persona-level overrides at `docs/alpha/personas/alpha-author/{yarnnn-author,netflix-script-author}/overrides/` per ADR-230 D6 will hold workspace-specific content.

### D6. Reviewer-as-editor

The Reviewer's seat in alpha-author workspaces is editor-shaped, distinct from alpha-trader's capital-EV-approver-shape. Principle structure (deferred detail to follow-up commit) covers at minimum:

- **Voice fingerprint enforcement** — detect AI-slop drift, generic-content drift, recycled-stale-framings; flag drafts that don't pass operator's authored voice criteria
- **Continuity audit** — read against the corpus, detect contradictions, broken arcs, factual drift across pieces
- **Cadence discipline** — detect shipping-pulse breaks; surface "you said you'd ship weekly, you haven't shipped in 12 days"
- **Anti-overclaim** — detect stance inflation, hedged claims masquerading as strong ones, audience-betrayal patterns
- **Substrate honesty** — detect when a draft makes claims the corpus or external substrate doesn't support

The persona occupying the seat is operator-authored per ADR-230 (Simons / Buffett / Deming / operator-character analog for alpha-trader maps to e.g. specific editor archetypes for alpha-author — could be a specific historical editor figure or operator-authored original). The seat structure is fixed; the persona is swappable. Two workspaces under one operator can run identical seat structure with distinct editor personas.

### D7. Capability menu (permissive, not prescriptive)

alpha-author bundle declares a *menu* of useful capabilities in MANIFEST.yaml. Workspace-level activation determines which subset matters. Bundle does not force capability requirements at the bundle level — that's a workspace-shape concern.

Tentative menu (final list deferred to follow-up commit):

**Kernel-side (inherited, no new code)**:
- `read_slack` / `write_slack` (operator's own Slack, audience comms if applicable)
- `read_notion` / `write_notion` (drafts, accumulated reading notes, corpus organization)
- `write_email` (transactional sends, audience-facing emails via Resend)
- `read_uploads` (operator-contributed documents, reference materials)
- `websearch` (research, source-finding)

**Bundle-declared additions (likely needed, code TBD per ADR-224 bundle-side capability pattern)**:
- Expanded Notion writes (page creation + page update, not just comment). Currently `write_notion` is comment-only per the 2026-05-15 audit. Most-load-bearing capability gap. Likely a kernel extension once authored, not a bundle-private capability — generalizes beyond alpha-author.
- Publishing-platform writes — at least one of (LinkedIn schedule-and-publish, X schedule-and-publish, newsletter-platform compose+send). Most-load-bearing for the `yarnnn-author` workspace; not needed for the `netflix-script-author` workspace.
- `read_commerce` / `write_commerce` (inherited from alpha-commerce bundle pattern per ADR-183; gated on Lemon Squeezy connection if applicable to the workspace).

**Explicitly out-of-scope (for v1)**:
- Calendar (was sunset per ADR-131; not load-bearing for alpha-author's core loop)
- GitHub (irrelevant for most author workspaces; YARNNN-author workspace already has architect-level GitHub via direct cockpit, not bundle-needed)
- Trading / DeFi / Prediction (off-archetype)

### D8. Cockpit faces (program-specific composition per alpha-trader precedent)

**Correction note (2026-05-15 audit)**: An earlier draft of this ADR claimed alpha-author should *"compose four faces per the ADR-228 four-face cockpit pattern."* The audit verified this is structurally incorrect. ADR-228's kernel-default four faces (`MandateFace`, `MoneyTruthFace`, `PerformanceFace`, `TrackingFace`) were **deleted in ADR-273 Phase 2** as dead kernel fallbacks. The current cockpit pattern is: each bundle composes its own program-specific face component set via `SURFACES.yaml::cockpit.{key}` bindings, with no kernel-level four-face floor enforced. alpha-trader exemplifies this — it ships **seven** program-specific face components (`TraderRegime`, `TraderPortfolio`, `TraderMoneyTruth`, `TraderExpectancy`, `TraderPositions`, `TraderSignals`, `TraderOrders`) at `web/components/library/programs/alpha-trader/`, not four kernel-aligned faces.

**Corrected framing**: alpha-author's cockpit composes program-specific face components per the alpha-trader precedent. Count, naming, and structure are determined by the bundle's `SURFACES.yaml` cockpit binding map, not by a kernel-imposed archetype.

Speculative starter set (final detail deferred to step 1 reference-workspace authoring + SURFACES.yaml composition):

| Face | Substrate read | Purpose |
|---|---|---|
| **AuthorMandate** | `MANDATE.md` + `AUTONOMY.md` | Standing intent + autonomy posture (parallel to TraderRegime's role) |
| **AuthorCorpus** | Instance-level ground-truth substrate (filename TBD per D4) | Multi-signal corpus state: coherence metrics + audience signal when present + revenue signal when present. Must degrade gracefully when external signal absent (Netflix-screenplay case) — internal-coherence prominent, external slots show empty-state |
| **AuthorVoice** | Reviewer-authored voice-drift logs + recent revision attribution per ADR-209 | Voice fingerprint consistency over time, anti-AI-slop scoring, principle-fitness audit results |
| **AuthorPipeline** | `/workspace/_recurrences.yaml` + draft/published substrate manifest | Drafts → scheduled → published, comment-debt, audience-signal queue, cadence-health indicator |

Additional faces may emerge during reference-workspace authoring (alpha-trader's `TraderSignals` + `TraderOrders` emerged from the work, not from kernel pattern). Bundle author has full latitude per `SURFACES.yaml::cockpit` shape.

Per ADR-273 these live at `web/components/library/programs/alpha-author/` once authored.

### D9. Cadence shape is permissive

The bundle's reference-workspace declares recurrences (per ADR-261) that are *capability-shaped* (ship-check, voice-audit, continuity-audit, corpus-coherence-rebuild) rather than *schedule-shaped*. Workspace-level configuration in `_recurrences.yaml` picks schedules.

This accommodates both ship-pulse workspaces (daily/weekly publishing cadence — `yarnnn-author` shape) and revision-pulse workspaces (continuous revision, episodic ship — `netflix-script-author` shape) without forking the bundle.

Reviewer's `_preferences.yaml` (per ADR-275) takes operator's declared cadence preferences and authors corresponding Schedule primitive calls. The bundle ships capability specs at `/workspace/specs/{capability}.md` for the canonical author capabilities; the Reviewer composes them into operator's chosen cadence.

### D10. Bundle dependencies on prerequisite ADRs

Hard prerequisites:

- **ADR-282 (Axiom 8 rename)** — must land first. alpha-author's multi-signal ground-truth shape requires the renamed axiom to be axiomatically legitimate, not a special case bolted onto the alpha-trader-locked framing.
- **ADR-230 (Persona-Program Registry Unification)** — already implemented. alpha-author plugs into the canonical activation path (`activate_persona.py --persona alpha-author --workspace <yarnnn-author|netflix-script-author>`).
- **ADR-226 (Reference-Workspace Activation Flow)** — already implemented. alpha-author's reference-workspace ships under `docs/programs/alpha-author/reference-workspace/` and gets forked via `_fork_reference_workspace`.
- **ADR-223 (Program Bundle Specification)** — already implemented. alpha-author conforms to MANIFEST.yaml + SURFACES.yaml + reference-workspace shape.
- **ADR-224 (Kernel/Program Boundary)** — already implemented. alpha-author's bundle-side capabilities (publishing-platform writes, expanded Notion writes if scoped bundle-private) live in MANIFEST, not in kernel registries.

No new ADR-shaped infrastructure required. alpha-author is the second concrete bundle riding the abstractions ADR-222 → ADR-230 built.

## Implementation roadmap (deferred follow-up commits)

This ADR ratifies scope. Implementation lands across multiple commits, each one its own discourse + ADR-or-amendment as needed.

1. **Reference-workspace authoring** — `docs/programs/alpha-author/{MANIFEST,README,SURFACES}.yaml` + `docs/programs/alpha-author/reference-workspace/**`. Tier frontmatter (`tier: canon | authored | placeholder`) per ADR-226 may be applied to reference-workspace files as soft annotation, but note that the tier system is **operationally dissolved per ADR-261/262 Phase D.2** — `fork_reference_workspace` strips frontmatter and does not gate behavior on tier values anymore. The annotation remains useful as documentation of authorial intent for the operator-vs-bundle authorship boundary. Most substantive single commit. Decisions: instance-level ground-truth filename + substrate shape (D4 deferred), Reviewer principles starter set (D6 deferred), capability menu finalization (D7 deferred), cockpit faces (D8 deferred — see corrected framing above).
2. **Capability extensions** — expanded Notion writes (kernel extension), publishing-platform writes (bundle-side or kernel — decided during commit). Code work in `api/integrations/core/` + `api/services/platform_tools.py`.
3. **Cockpit face components** — `web/components/library/programs/alpha-author/Author{Mandate,Corpus,Voice,Pipeline}.tsx` per ADR-273 convention.
4. **Persona registry update** — `docs/alpha/personas.yaml` gains `yarnnn-author` and `netflix-script-author` rows with `program: alpha-author`. Persona-specific override directories scaffolded.
5. **Activation harness** — `activate_persona.py` smoke-test against alpha-author bundle. Validates fork mechanics, capability resolution, recurrence registration.
6. **Dogfood activation** — kvk runs `activate_persona.py --persona yarnnn-author` and `--persona netflix-script-author` against the live workspace. First-wake observations recorded as `docs/alpha/observations/2026-XX-XX-adr283-alpha-author-*.md`.

Each step is its own commit + (where architecturally consequential) own ADR. The roadmap is not committing to a timebox — depth-first authoring, not breadth-first.

## What this ADR explicitly does not do

- Does not declare alpha-author "implemented." Status is Proposed. Implementation is the roadmap above.
- Does not specify instance-level filenames for ground-truth substrate. That decision lands when the reference-workspace is being authored end-to-end.
- Does not commit to specific publishing-platform integrations (LinkedIn vs X vs newsletter-platform). That decision lands when capability extension work begins.
- Does not finalize Reviewer principles. D6 lists categories; specific principles get authored during reference-workspace commits and refined through dogfood.
- Does not modify alpha-trader bundle. alpha-trader is unchanged.
- Does not amend kernel architecture. alpha-author is purely additive — new bundle under `docs/programs/`, no kernel touch.

## Status check

- **Implementation effort (this ADR)**: scope-only, ~zero hours beyond drafting.
- **Implementation effort (full roadmap)**: substantial. Reference-workspace authoring is the heaviest single commit. Capability extensions (especially Notion page-writes) are non-trivial. Cockpit face components are FE work proportional to alpha-trader's face component effort. Persona registry + activation harness are small.
- **Risk**: low at the scope-ratification level (this ADR). Implementation risk is normal-engineering-shaped, with the substrate-continuity archetype's slower-feedback-loop being the main novelty to be honest about (the bundle's value won't be felt in a single dogfood session).
- **Blocks on**: ADR-282 (Axiom 8 rename) must land first.
- **Unblocks**: alpha-author reference-workspace authoring + subsequent roadmap steps.

## Closing note on discipline

The 2026-05-15 discourse memo captures a discipline that should propagate into how alpha-author gets authored:

> **The dogfooder's edge cases ≠ the median ICP's needs.** When the architect is the dogfooder, the bundle can accidentally optimize for the dogfooder's atypical work patterns. Ask repeatedly: "does the median author care about this, or just me?"

alpha-author is the first bundle in YARNNN's history where the architect's personal use case is unambiguously load-bearing on the design. alpha-trader had this risk too but kvk-the-trader-persona overlapped heavily with the median trader-shape. For alpha-author, kvk's two workspaces (founder-of-YARNNN content + Netflix screenplay) are *somewhat* atypical for the bundle's ICP. This is acceptable, but it requires the discipline above to hold during reference-workspace authoring and capability-menu decisions.

Singular Implementation discipline also holds at the bundle level: don't add bundle-level mechanisms to serve dogfooder edge cases that the median operator wouldn't need. Push edge-case accommodation into the workspace-level persona/principles layer wherever possible.

## Discovery note

This ADR was patched in place on 2026-05-15 after a codebase audit verified 11 of 12 architectural claims and surfaced one structural mistake:

- **D8 corrected** — Original draft claimed alpha-author should *"compose four faces per the ADR-228 four-face cockpit pattern."* Audit revealed ADR-228's kernel-default four faces (`MandateFace`, `MoneyTruthFace`, `PerformanceFace`, `TrackingFace`) were deleted in ADR-273 Phase 2 as dead kernel fallbacks. Current pattern is bundle-specific face composition via `SURFACES.yaml::cockpit.{key}` bindings, with no kernel-imposed four-face floor. alpha-trader ships seven program-specific face components, not four. D8 rewritten to describe program-specific composition per alpha-trader precedent with a speculative AuthorMandate / AuthorCorpus / AuthorVoice / AuthorPipeline starter set that bundle authoring may extend or modify.
- **D2 caveat added** — Tier frontmatter (`tier: canon | authored | placeholder`) per ADR-226 still parses in reference-workspace files but is operationally dissolved per ADR-261/262 Phase D.2 — `fork_reference_workspace` strips frontmatter and does not gate behavior on tier values. Annotation remains useful as authorial-intent documentation but is not load-bearing on activation behavior.

Other audited claims (bundle structure, activation path, persona registry with `program:` field, recurrences + preferences shape, capability specs convention, Notion-write-comment-only, tasks table state, ADR-282 cascade landed) all verified clean. No other ADR-283 claims require correction.

This patch supersedes the affected sections in place per Singular Implementation. No v1/v2; the corrected text is the ADR.
