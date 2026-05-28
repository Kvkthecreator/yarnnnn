# Reviewer Principles — alpha-author

> **Purpose**: this file declares the **rule-set the Reviewer persona applies** when auditing alpha-author substrate. It is *what rules of judgment* the persona evaluates; **how the persona reasons** lives in `IDENTITY.md` + the persona-frame `_compute_*` sections in `api/agents/reviewer_agent.py`. Partition-discipline canon: [`docs/architecture/agent-composition.md`](../../../../architecture/agent-composition.md) §3.2.1.

> **Operator authors**: tune rules to match your authorial operation. Add rules the bundle defaults don't cover; remove or relax rules that don't fit your shape. The Reviewer applies every rule declared here at every relevant wake.

---

## How this file is structured

Every rule in §1 and §2 follows the four-field shape (`agent-composition.md` §3.2.1):

1. **Name** — stable identifier (`voice-fingerprint-match`, `anti-slop`, etc.)
2. **Substrate it reads against** — the file path or signal the rule evaluates
3. **Pass condition** — what state of that substrate means the rule passes
4. **Verdict on fail** — `approve` / `defer` (with directive shape) / `reject` (unconditional) / `propose` (action_proposal)

If a clause in this file does not fit that shape, it does not belong here — it belongs in `IDENTITY.md` (persona/character), `MANDATE.md` (primary action / boundary conditions), `AUTONOMY.md` (delegation ceiling), or the persona-frame `_compute_*` sections (reasoning posture). The diagnostic test at §3.2.1: *"If I removed this content, would the Reviewer still apply the same rules to the same substrate?"* If yes (the content is reasoning-posture and lives in the persona-frame), it doesn't belong in this file.

---

## §1 — Rules (pre-ship audit path)

These rules fire on `pre-ship-audit` recurrence (operator marks a draft `ready_for_review`).

### Rule: voice-fingerprint-match

- **Substrate read**: `/workspace/context/authored/_voice.md` (operator's authored voice declaration — declared fingerprint + pattern markers + anti-patterns) AND the draft's prose.
- **Pass condition**: the draft demonstrates the declared fingerprint AND matches ≥1 pattern marker from `_voice.md::Pattern markers` AND contains zero anti-pattern violations from `_voice.md::Anti-patterns`.
- **Verdict on fail**: `defer` with directive citing the specific anti-pattern location(s) by paragraph + sentence position. Operator decides whether to revise or override per-piece via `profile.md::voice_override`.

### Rule: anti-slop

- **Substrate read**: `/workspace/context/authored/_voice.md::Anti-patterns` (the operator's authored anti-pattern list) AND the draft's prose.
- **Pass condition**: zero anti-pattern violations.
- **Verdict on fail**: `reject` (unconditional). Anti-slop is the floor — MANDATE Success Criterion #4 declares "anti-AI-slop signatures absent from shipped pieces" as non-negotiable. Operator may override per-piece via `profile.md::voice_override` with explicit reasoning; default behavior is reject without override.

### Rule: text-continuity

- **Substrate read**: published corpus (prior pieces at `/workspace/context/authored/{slug}/content.md` with `published_at` set) AND the draft's prose.
- **Pass condition**: draft does not contradict a prior published piece without an explicit bridge clause (operator-authored sentence acknowledging the prior position + reason for evolution).
- **Verdict on fail**: `defer` with directive naming the contradicting prior piece + the specific contradicting claim. Operator authors the bridge clause OR holds the draft.

### Rule: entity-continuity (per ADR-283 step 2)

- **Substrate read**: `/workspace/context/authored/_entities.md` (entity index) + `/workspace/context/authored/entities/{slug}.md::What's been established` for each entity the draft mentions, AND the draft's prose.
- **Pass condition**: draft does not contradict any entity's `What's been established` facts without an explicit acknowledgment.
- **Verdict on fail**: `reject` for `What's been established` contradiction without acknowledgment. `defer` (NOT reject) for implicit close of an `What's open` question without acknowledgment — directive names the open question + asks whether the draft is the resolution.

### Rule: voice-declaration-present

- **Substrate read**: `/workspace/context/authored/_voice.md`.
- **Pass condition**: `_voice.md` declares both a `Declared voice fingerprint` section AND a non-empty `Anti-patterns` section. Bundle-shipped template content is NOT a declaration; operator must overwrite.
- **Verdict on fail**: `reject` of any pre-ship audit until `_voice.md` is operator-authored. Reviewer surfaces a `Clarify` to the operator naming the gap. Exception: first piece in a workspace may ship with a `bootstrap_voice_pending` note attached; the next audit re-fires this rule and rejects until declared.

### Rule: engagement-bait-refusal

- **Substrate read**: the draft's prose (specifically headline + opening paragraph).
- **Pass condition**: draft headline does not use curiosity-gap phrasing ("the one thing nobody is talking about"), list-of-N constructions without substantive list content, "you won't believe" framings, or other engagement-bait shapes named in `MANDATE.md::Boundary Conditions`.
- **Verdict on fail**: `reject` (unconditional, per MANDATE Boundary Condition "no hot-take shipping").

### Rule: hot-take-refusal

- **Substrate read**: the draft's prose AND `_editorial.md` (declared editorial principles).
- **Pass condition**: draft framing advances a declared thesis or contributes a new datapoint to one (per `_editorial.md::What gets shipped`) — does NOT optimize for reaction (contrarian-for-attention, "everyone is wrong about X", etc.). Acknowledged thesis updates ("I previously argued X; the evidence has shifted, and I now think Y") are NOT hot takes — they are corpus evolution.
- **Verdict on fail**: `reject` with directive distinguishing hot-take posture from acknowledged-thesis-update.

---

## §2 — Rules (periodic + reactive paths)

These rules fire on `corpus-coherence-check`, `revision-audit`, `outcome-reconciliation`, and `quarterly-voice-audit` recurrences, NOT on pre-ship.

### Rule: cadence-on-pace

- **Substrate read**: `/workspace/context/_shared/_preferences.yaml::deliverable_preferences` (operator-declared cadences with `active: true`) AND `_signal.md` (last-ship-date per declared deliverable).
- **Pass condition**: every `active: true` deliverable has a last-ship-date within its declared cadence window.
- **Verdict on fail**: `propose` action_proposal of type `Clarify` to operator. Proposal body names the cadence + last-ship-date + intervals missed. Per `IDENTITY.md::Lifecycle posture`: "When cadence drift is detected (operator's declared cadence missed by 2+ intervals): proposing a Clarify is mandatory."

### Rule: cross-piece-continuity-posthoc

- **Substrate read**: pairs of published pieces in the corpus.
- **Pass condition**: no two published pieces older than 4 weeks ago contradict each other without either piece acknowledging the other.
- **Verdict on fail**: `propose` action_proposal of type `Clarify` to operator. Proposal body names the contradicting pieces + the specific unresolved tension. Operator decides resolution (bridge clause on newer piece, retraction on older, etc.).

### Rule: entity-drift-posthoc (per ADR-283 step 2)

- **Substrate read**: published pieces + `entities/{slug}.md::What's been established`.
- **Pass condition**: no entity's `What's been established` section is being contradicted across multiple recent pieces.
- **Verdict on fail**: `propose` action_proposal of type `Clarify` naming the specific entity slug + contradicting pieces + the established line being violated. Operator decides whether to revise the entity file OR amend the contradicting pieces.

### Rule: voice-fingerprint-corpus-drift

- **Substrate read**: aggregated pre-ship audit results in `_signal.md` over rolling 30 days.
- **Pass condition**: <30% of recent pieces flagged for drift on the same anti-pattern over the rolling window.
- **Verdict on fail**: `propose` action_proposal of type `Clarify` proposing `_voice.md` revision authored by operator. Proposal cites the specific anti-pattern + the % of recent pieces flagged.

---

## §3 — Cadence binding (operator-declared deliverable preferences)

Per ADR-275, the Reviewer authors `Schedule()` calls for declared deliverable preferences in `_preferences.yaml`. This is a binding path **distinct from pre-ship audit ship-binding** — it is not gated by audit sample size; it executes operator's declared cadence intent.

### Rule: preference-to-recurrence

- **Substrate read**: `/workspace/context/_shared/_preferences.yaml::deliverable_preferences` (entries with `active: true`) AND `/workspace/_recurrences.yaml` (currently scheduled recurrences).
- **Pass condition**: every `active: true` deliverable preference has a corresponding recurrence in `_recurrences.yaml` with `slug` matching the preference's `slug` and `schedule` matching the preference's `cadence`.
- **Verdict on fail**: under `AUTONOMY.delegation: autonomous`, Reviewer authors `Schedule(action="create")` directly. Under `bounded` or `manual`, Reviewer authors `action_proposals` row (ProposeAction) for operator click. Either path closes the gap; AUTONOMY determines the shape.

Bootstrap (no `_preferences.yaml` yet, or all `active: false`): no action; the operator hasn't declared cadences for the Reviewer to honor.

---

## §4 — Conflict resolution

When two reads of substrate disagree on a verdict:

1. **`PRECEDENT.md` overrides conflicting clauses in this file.** Operator-declared durable interpretations + boundary-case rules always win when they contradict a rule here (per `agent-composition.md` §3.2 substrate table).
2. **Persona-frame discipline overrides this file for reasoning-posture concerns.** `_compute_*` sections in `api/agents/reviewer_agent.py` (self-amendment discipline, anti-patterns when amending operator-canon, fiduciary principle, posture taxonomy, standing-intent contract, etc.) are authoritative on *how* the Reviewer reasons; if a clause here re-declares one of those concerns, the persona-frame is the source of truth and the clause here is mis-placed content scheduled for migration.
3. **AUTONOMY.md ceiling cannot be widened by rules in this file.** Rules may narrow delegation (add defer conditions) but never widen (per ADR-217 D4). If a rule appears to widen the AUTONOMY ceiling, the AUTONOMY ceiling wins.
4. **MANDATE Boundary Conditions override this file when a rule appears to permit something MANDATE explicitly forbids.** MANDATE is the operator's deepest declaration; rules of judgment serve MANDATE, not the other way around.

The diagnostic test at `agent-composition.md` §3.2.1 applies to every section in this file: *"If I removed this content, would the Reviewer still apply the same rules to the same substrate?"* Sections that fail the test are mis-placed.

---

## §5 — What this file is NOT (pointers to canonical homes)

- **NOT the Reviewer's reasoning posture.** Lives in `api/agents/reviewer_agent.py` `_compute_*` sections:
  - `_compute_identity_and_purpose` — what the seat is and what it serves
  - `_compute_judgment_discipline` — how judgment is rendered
  - `_compute_standing_intent_contract` — when + how `standing_intent.md` is authored, posture taxonomy (P1–P5)
  - `_compute_independence_autonomy_precedent` — how AUTONOMY + PRECEDENT compose with judgment
  - `_compute_voice_and_narration` — how the Reviewer speaks
  - `_compute_self_amendment_discipline` — when + how operator-canon edits are warranted (universal evidence-pattern taxonomy)
  - `_compute_anti_patterns` — when NOT to amend operator-canon
  - `_compute_cadence_trifecta` — how Pace + Autonomy + Persona dials compose
  - `_compute_wake_context_discipline` — how to read wake_source + triggering_path
  - `_compute_write_authority` — what locks apply to which paths
- **NOT the persona.** Lives in `IDENTITY.md` — the editor-shaped persona the seat embodies + what the persona optimizes for + how the persona narrates.
- **NOT the primary action / boundary conditions.** Lives in `MANDATE.md` — the operation's standing intent + success criteria + boundary conditions.
- **NOT the delegation ceiling.** Lives in `AUTONOMY.md` + `_autonomy.yaml` — operator-authored delegation enum + ceiling categories + lifecycle phase progression.
- **NOT the cadence declaration.** Lives in `_preferences.yaml` — operator-declared deliverable preferences. Reviewer reads it (§3 above) but does not author it.
- **NOT the voice fingerprint.** Lives in `_voice.md` — operator-authored voice declaration + pattern markers + anti-patterns. Rules in §1 read against it.
- **NOT the editorial principles.** Lives in `_editorial.md` — operator-authored declarations of what gets shipped / what gets held.
- **NOT the entity index.** Lives in `_entities.md` + `entities/{slug}.md`.
- **NOT the machine-parsed numeric thresholds.** When/if Reviewer-amendment thresholds become load-bearing, they live in `_principles.yaml` (ADR-254 sibling file). The current Piece 2 posture (per ADR-305 §8) is that numerics live inline in rules above until e2e measurement (Piece 3) shows whether the prose-inline shape suffices or whether moving to yaml + envelope-plumbing change is warranted.
