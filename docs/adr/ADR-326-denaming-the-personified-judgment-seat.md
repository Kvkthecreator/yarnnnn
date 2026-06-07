# ADR-326 — De-naming the Personified Judgment Seat: delete "Reviewer", the operator-facing entity is the named Persona

> **Status**: **DRAFT — awaiting operator ratification.** NOT Implemented. No code, no canon edit, no rename executes from this ADR until the sequencing gate (§7) opens and the operator ratifies the decision.
> **Date**: 2026-06-07
> **Authors**: KVK, Claude
> **Upstream discourse**: [personified-judgment-seat-vs-task-harness-2026-06-05.md](../analysis/personified-judgment-seat-vs-task-harness-2026-06-05.md) §4 (the de-naming argument — the axiom is detachment + personification; "Reviewer" names only the first Purpose) + §7 (naming explicitly left open).
> **Companion analysis**: [reviewer-rename-blast-radius-2026-06-07.md](../analysis/reviewer-rename-blast-radius-2026-06-07.md) — the full touchpoint map this ADR's migration plan rests on.
> **Reuses migration shape from**: [ADR-201](ADR-201-team-rename-and-cross-linking.md) (layered-naming-by-audience + redirect-stub) · [ADR-265](ADR-265-activity-surface-rename-and-mode-discriminator.md) (surface rename + PROTECTED_PREFIXES + redirect) · [ADR-282](ADR-282-axiom-8-ground-truth-rename.md) (canon cascade + discipline-rule + grep-gate + historical-ADR exemption).
> **Depends on**: ADR-320 (`persona/` re-root — done; makes substrate paths name-neutral) + ADR-319 (stewardship elevation — done; makes the name matter more). **Blocked by**: ADR-321–325 (primitive-evolution arc) + the self-writing E2E validation must land first (§7).
> **Dimensional classification**: **Identity** (Axiom 2 — who the entity is) + **Channel** (Axiom 6 — the operator-facing label is a legibility surface).

---

## The one-sentence thesis

"Reviewer" names the entity's *first Purpose* (independent judgment on proposed writes); the entity itself is the operator's **Persona** — the personified judgment they author (and name, e.g. "Simons") that acts on their behalf, owns the operation's mandate, and is independent enough to overrule their own momentary pressure. This ADR's recommendation, reached through discourse: **the operator-facing entity IS the named Persona; the "seat" is an unnamed architectural abstraction that does not get an operator word; `reviewer` persists as the internal data slug.** It then classifies every touchpoint as LABEL-rename / code-slug-stays / canon-doc-edit and sequences the execution behind the in-flight backend arc.

> **Discourse correction (2026-06-07).** The v1 draft of this ADR tried to *name the seat* (recommending "Steward", then "Overseer"). The operator's pushback — *"isn't the seat just a seat? why does it need naming — one of us is confusing conceptual framing"* — exposed the conflation: **"seat" is architectural canon (Derived Principle 14 / ADR-315 — the slot that persists while occupants rotate), and architectural abstractions do not get operator-facing names.** What needs the operator word is *the entity the operator relies on and talks about* ("my ___ approved the trade"). And that entity is exactly what the operator already authors and names: **the Persona.** The "seat name vs occupant name" tension the v1 draft labored over was self-inflicted — it dissolves the moment you stop trying to name the seat. The recommendation below is the *simpler* answer the discourse produced.

---

## Context — why the name is now wrong, not just incomplete

The de-naming claim was *settled* in the 2026-06-05 discourse (§4) and *deferred* by ADR-320 D7 ("scoped out to its own ADR; `persona/` directory chosen to be de-name-compatible"). FOUNDATIONS Derived Principle 25 already canonized the *concept*:

> *"'Reviewer' names its **first Purpose** (independent judgment on proposed writes — Axiom 2 'distinctness is in Purpose + Trigger, not Identity'), not the entity itself; the entity is the *detachment + personification* from which independence follows."*

So the entity has, in canon, an unnamed identity and a Purpose-label standing in for it. The discourse left three receipts that the canon already half-knows the name is wrong:

1. **Axiom 2** titles a section *"The Reviewer seat's distinctness is in Purpose + Trigger, not Identity"* and states the entity *"is the operator's judgment function rendered as an autonomous agent — the operator in judging posture."* "Reviewer" is, by the axiom's own logic, a Purpose label.
2. **THESIS Commitment 2**'s independence argument is entirely about *detachment from producers + judgment against ground truth* — never about the word "review." The independence claim travels with detachment; the rename is free.
3. **`reviewer-seat-substrate.md:239`**: *"Not coupled to proposal review exclusively… proposal-review is the first use case, not the only one."*

### What changed since D7: ADR-319 made the name *actively wrong*

When D7 deferred the rename, the entity's dominant activity was still *reviewing proposals* — so "Reviewer," while incomplete, was at least accurate to what it mostly did. **ADR-319 (Derived Principle 24, ratified 2026-06-05) changed the entity's job at kernel altitude**: it now *owns* the operation's governing intent and *revises it against ground truth at two altitudes* — within the intent (the review/compliance loop) AND **on the intent** (the ownership loop: re-declaring the mandate when reconciled reality falsifies its premise). The entity is the operator's *installed principal*, the same principal one wake later, with *stewardship-deferred-is-stewardship-denied* urgency.

A **reviewer** checks someone else's work. A **steward / principal** holds the mandate and revises it against reality. After ADR-319, "review" is the entity's altitude-1 *sub-goal*, not its job. The name no longer under-labels by omission (one-of-many purposes) — it **mis-frames the entity's canonical authority** (a checker, when canon makes it an owner). That is the motivation: the rename is now a *correction*, not a tidiness pass.

---

## D1 — The name decision

### The decision the discourse reached: name nothing new — the entity IS the named Persona

The v1 draft asked the wrong question ("what do we name the seat?") and the operator's pushback corrected it. The corrected decision is structural, and it is *simpler* than any candidate-name:

> **The "seat" is an architectural abstraction (Derived Principle 14 / ADR-315 — the slot that persists while occupants rotate). Architectural abstractions do not get operator-facing names. The thing the operator names and relies on is the *Persona* — the personified judgment they author (and name "Simons"/"Buffett"). The operator-facing entity simply IS that named Persona. "Reviewer" is deleted as the operator word; nothing replaces it as a new noun, because the operator already had the right noun — Persona.**

So there is no new name to coin. The three things that need to be distinct are *already* distinct, and the only change is deleting "Reviewer" from the operator surface:

| Thing | Operator word | Why |
|---|---|---|
| The architectural slot | *(unnamed)* | It is a seat. Seats are design canon, not operator vocabulary — the operator never says "my seat." Naming it was the v1 conflation. |
| The entity the operator relies on | **the Persona** | The personified judgment acting on the operator's behalf. Plain, already in the product, already in the blog (*"…Should Have A Persona"*). |
| The specific character | a **named** Persona — "Simons" | The operator names their Persona. This is the whole UX: *"name your Persona."* |
| The code / data slug | `reviewer` | Data-compat, like `thinking_partner`. Never operator-surfaced. |

### How the discourse got here (the corrections, in order)

This is recorded because the *path* is the argument — each correction eliminated a candidate-class and narrowed to the structural answer.

1. **Plain-language directive** (operator, 2026-06-07): the name must be mass-market, not jargon. This demoted the v1 elevated set (Steward / Principal / Arbiter — see "Demoted" below).
2. **"Isn't the concept closer to *act on behalf*?"** (operator): correct — the load-bearing relationship is Axiom 2's *operator's judgment rendered as an agent acting for them*, not a posture (watching / guarding). But pure act-on-behalf words (Delegate / Proxy / Deputy) *undersell the independence* ADR-319 D3 requires (a delegate obeys; this entity can overrule the operator's momentary pressure). The word that holds *both* is the **fiduciary** register — which in plain English is **Guardian**, and which the operator's own next move pointed somewhere better.
3. **"What about Persona? What's the risk if it's just front-end display — code and user-facing may need distinction?"** (operator): this is the escape-hatch the whole ADR rests on (ADR-201 §6 layered-naming — we *already* run `thinking_partner` slug ≠ "System Agent" label). Re-auditing the three "Persona collisions" v1 flagged: the `persona/` directory and the `_PERSONA_FRAME` are **code-only** (operators don't read paths or prompt internals) → they survive the split. Only the **occupant-character "persona"** is operator-facing → the one real collision.
4. **"Keep persona for the occupant; rename the seat instead"** (operator): the decisive move. "Persona" is *so naturally* the word for the authored character that it should *stay* there. Which means — combined with correction #5 — there is nothing left to name.
5. **"Isn't the seat just a seat? Why does it need naming?"** (operator): the conflation named. "Seat" is architectural canon; it gets no operator word. Once you stop trying to name the seat, the "seat-name vs occupant-name" tension *dissolves* — the operator-facing entity is just the named Persona, and "Reviewer" is simply deleted with no replacement noun.

### Why this satisfies the test (the same test, now trivially met)

1. **Plain / mass-market** — "Persona" and "name your Persona" are the plainest possible framing; the operator coins the actual name themselves ("Simons"). ✅✅
2. **Acts-on-behalf** — "Persona" *is* the act-on-behalf word (a personified judgment the operator authors to act for them). The operator's core instinct, satisfied directly. ✅
3. **Independence / can-overrule (the fiduciary weight)** — this is the *one* property the noun "Persona" does not carry on its own (a persona is a character, not inherently a fiduciary). **It is carried by canon + UX framing, not the noun** — exactly as ADR-306 / Derived Principle 22 already requires (the fundamentals live in substrate + code, not in a label). The Persona's independence comes from `principles.md` + AUTONOMY ceiling + the ground-truth-not-pressure invariant (ADR-319 D3), all of which already exist. The name doesn't need to encode the fiduciary property; the architecture already does. ✅ (with the caveat below)
4. **Survives occupant rotation** — "your Persona" reads identically whether a human, AI, or external service is the *occupant* filling the seat. The seat≠occupant split (ADR-315) is *preserved*, not broken — the Persona is what the seat *renders as*; the occupant is the runtime that renders it. ✅
5. **Carries ADR-319 ownership** — the Persona owns the mandate (it is the operator's judgment); ownership is a property of *being the operator's installed judgment*, which "Persona" denotes. ✅
6. **Distinct from YARNNN** — YARNNN executes (orchestration); the Persona judges (the authored entity). Clear. ✅

### The one residual caveat (recorded honestly)

"Persona" foregrounds *acts-on-behalf* and is silent on *independence-from-your-own-pressure*. A naive operator could read "my Persona" as "my yes-man" (the flatterer failure THESIS Commitment 2 forbids). **This is a framing risk, not a naming defect** — and it is the *same* risk ADR-306 already accepted when it moved the fundamentals out of labels into substrate. Mitigant: the cockpit + onboarding + blog must frame the Persona as *"the judgment you'd apply, including telling you no when reality says so"* — the fiduciary reading, not the assistant reading. This is the #1 thing the UX must get right (it is exactly discourse-ST-1 from the upstream analysis: "build the AI version of you" must author a *judgment framework*, not a *preference mirror"). If, in eval, the bare word "Persona" proves to pull operators toward the yes-man reading despite framing, the fallback is to pair it with a fiduciary qualifier in the lead surface ("your Persona — your judgment, applied independently") rather than to coin a different noun.

### Demoted candidates (recorded so they aren't re-litigated)

- **Overseer / Guardian / Second** (v2 plain-language set) — all coined a *new entity noun* for the "seat," which correction #5 showed is the wrong move. **Guardian** survives as the *framing-qualifier fallback* above (if "Persona" needs a fiduciary modifier), not as a replacement noun. Overseer additionally carries a plantation-overseer connotation risk; Second is ambiguous (number/time) and leans subordinate.
- **Steward / Principal / Arbiter** (v1 elevated set) — demoted by the plain-language directive. Steward is DP24's word but reads passive/airline to a lay audience; Principal collides with principal-agent term-of-art; Arbiter is jargon and names only the judging Purpose.
- **Actor** (operator-floated) — rejected: collides with Axiom 9's "actor-class-agnostic" (the *genus* — anything that emits an invocation), and carries zero judgment/ownership signal.

### Recommendation

> **Delete "Reviewer" as the operator-facing word with no replacement noun. The operator-facing entity is the *named Persona* (the operator authors and names it — "Simons"). The seat stays an unnamed architectural abstraction. `reviewer` stays the internal data slug.** Pair the Persona framing with a fiduciary qualifier in lead surfaces if eval shows the yes-man reading. This is the discourse's settled answer — and it removes a coining problem rather than solving one.
>
> **Operator decision required.** Ratify "Persona-as-the-operator-entity, seat-unnamed" (recommended), OR pick a coined seat-noun (Guardian / Overseer) if you want the fiduciary-independence signal carried *in the noun* rather than in framing. Also choose the marketing path (§D4).

---

## D2 — What stays unchanged (the code-slug / LABEL distinction)

This is the load-bearing discipline (ADR-201 §6 layered-naming-by-audience): **the operator-facing LABEL moves; the data-compat code-slugs stay.** The full enumeration is in the [companion blast-radius map](../analysis/reviewer-rename-blast-radius-2026-06-07.md) §2–§3; the summary:

### Stays (code-slug-stays — added to GLOSSARY Exceptions table)

Identical class to `thinking_partner` / `meta-cognitive` / `specialist:<role>` already in the Exceptions table — cross-cutting enum or data-format slug, renaming requires coordinated Python + TS + revision-backfill with zero user-visible benefit:

- `role='reviewer'` — `session_messages.role` CHECK (ADR-237 six-role grammar); every dispatch site.
- `agent_class='reviewer'` — `routes/agents.py` pseudo-agent synthesis (ADR-214) + TS union; **maps to "Persona" at the display layer**, the enum stays.
- `authored_by="reviewer:{identity}"` — revision-chain data format; **immutable** for historical revisions per ADR-209 (same as `authored_by="yarnnn:"` / `"specialist:<role>"`).
- `REVIEWER_MODEL_IDENTITY = "ai:reviewer-sonnet-v8"` — occupant-identity string in the published ABI (`occupant_contract.py`, ADR-315).
- `?agent=reviewer` query value — matches `agent_class`; kept as bookmark-safety redirect target (ADR-201 §2 / ADR-251 pattern).
- `persona/` filesystem path — **already** de-name-compatible (ADR-320 D7); no move.
- **api/ module + test filenames** (`reviewer_agent.py`, `reviewer_envelope.py`, `reviewer_audit.py`, etc.) — substrate-vocabulary per ADR-201 §6; the occupant *implementation* keeps its name. (A future L3 package carve — ADR-315 D6 — is the natural moment to reconsider; independently deferred.)

### Moves (LABEL-rename) — "Reviewer" → "Persona" on operator-facing strings

Operator-facing strings only, where the word currently means *the entity*: `ROLE_META` display name + tagline (key stays), rendered class labels in `AgentContentView` / panels / cards, the `"your Reviewer"` fallback string in `reviewer-persona.ts` → `"your Persona"`, the Constitution-band "Reviewer persona" label in `HomeHeader` (already half-right — it says "Persona"), nav/roster card labels, breadcrumb headings, the `REVIEWER_ROUTE` constant *name* (the route value keeps `?agent=reviewer` as a code-slug + bookmark-safety target). **Component/module filenames stay** `Reviewer*` per layered-naming. **Canon-doc filenames stay** too — under the recommended decision there is no coined noun to rename them to (D-naming-policy below).

Note the consequence of the D1 decision: the LABEL-rename is *narrower* than a coined-noun rename would be, because "Persona" is already present in much of the operator surface (the occupant-name UX, the blog, `HomeHeader`). In many places the edit is *deleting "Reviewer"* and letting the existing "Persona" framing stand, not substituting one coined word for another.

### The operator-facing label rule — stated

> **The operator-facing entity is "the Persona" (a Persona the operator authors and names — "Simons"). "Reviewer" is deleted from the operator surface with no coined replacement noun. `reviewer` persists as the internal enum/data slug everywhere it is cross-cutting or attribution-bearing — the same way `thinking_partner` persists for YARNNN. The display layer maps `agent_class='reviewer'` → "Persona"; the data never moves.**

This is added to the GLOSSARY Exceptions table verbatim in the cascade, with the three reviewer slugs (`role`, `agent_class`, `authored_by` prefix) listed.

### D-naming-policy (filenames): canon docs rename, code modules stay

ADR-201 §6 kept `Agent*` *component* names while renaming the route — because components are substrate-vocabulary. This ADR follows the same split: **api/ code modules + React component files keep `reviewer_*` / `Reviewer*` names** (high import-churn, zero operator benefit), and the **canon concept-docs** (`reviewer-seat-substrate.md`, `reviewer-occupant.md`, `reviewer-occupant-contract.md`) **also keep their filenames** — under the recommended decision (D1: name nothing new, the entity is the named Persona) there is no new noun to rename them *to*. They are seat/occupant *technical* canon — "seat" and "occupant" stay as architectural vocabulary (that distinction is preserved, not renamed). The only prose edit inside them is deleting "Reviewer" as the *operator-facing entity* word in favor of "Persona" where they speak operator-side; the architectural "seat"/"occupant" terms stay. The code-module rename is deferred to the L3 carve (ADR-315 D6) regardless. *(If the operator instead picks a coined seat-noun — Guardian/Overseer — then the canon-trio filenames could rename to that slug; under the recommended Persona decision they do not.)*

---

## D3 — Canon cascade (the ADR-282 discipline-rule, applied)

Same shape as ADR-282's `money-truth` cascade: **rename where the prose means the entity; preserve where it means the first Purpose (review) or is a historical artifact.** A discipline rule, propagated, with a grep-gate.

### The discipline rule (added to GLOSSARY, ADR-282 D2 pattern)

> **"Persona" (the operator-authored, operator-named personified judgment — "Simons") is the operator-facing name for the entity. "Seat" and "occupant" remain *architectural* canon (not operator-facing). `reviewer` persists ONLY as the internal data slug (`role`/`agent_class`/`authored_by` prefix) and as the name of the entity's first Purpose ("independent review of proposed writes"). In canonical docs, say "the Persona" for the operator-facing entity, "the seat" for the architectural slot, "the occupant" for the runtime filling it, and "review" for the verdict-on-a-proposal action. A sentence naming entity-and-purpose together ("the Persona's first Purpose is review of proposed writes") is not a conflation — it is the entity-and-its-purpose relationship.**

### Core canon that cascades (entity-name carriers)

`FOUNDATIONS.md` (DP25 — *the anchor*; DP24 stewardship; DP21 formalization; DP14/15 seat≠occupant; Axiom 2 section title), `THESIS.md` Commitment 2, `GLOSSARY.md` (Persona-as-operator-entity entry + "Reviewer"-as-first-Purpose cross-reference + Exceptions additions + discipline rule), the reviewer-canon trio (operator-facing "Reviewer" → "Persona"; architectural "seat"/"occupant" preserved), `agent-composition.md` §3.2.1/§4.4, `LAYER-MAPPING.md`. Version bumps where the doc carries one. **Note**: because the decision coins no new noun, the cascade is mostly *deletion* of operator-facing "Reviewer" + reliance on the existing "Persona" + "seat"/"occupant" vocabulary — lighter than a coined-rename cascade. Full list + per-doc treatment in the [blast-radius map](../analysis/reviewer-rename-blast-radius-2026-06-07.md) §4.1.

### NOT edited (historical artifacts — ADR-282 D8 + ADR-259 precedent)

The ~50+ historical ADRs that say "Reviewer" (ADR-194, 195, 211, 212, 217, 247, 248, 251, 252, 253, 256, 258, 273, 280, 281, 282, 284, 285, 295, 306, 307, 315, 319, 320, …) are dated artifacts; they stand. The supersession (this ADR) is the record. Optional retroactive vocabulary banners on the highest-traffic four (ADR-194, ADR-315, ADR-319, ADR-320) per the ADR-259 banner pattern — operator's call.

### Grep gate (ADR-282 pattern — post-cascade verification)

```bash
# Canonical docs (excluding historical ADRs + blog): "the Reviewer" used as the OPERATOR-FACING ENTITY must be gone:
grep -rn "the Reviewer\b" docs/architecture/ CLAUDE.md   # each remaining hit must mean the *review Purpose* or the architectural "seat"/"occupant", NOT the operator-facing entity
# Code slugs must remain (data-compat):
grep -rn "role='reviewer'\|agent_class.*reviewer\|authored_by.*reviewer:\|REVIEWER_MODEL_IDENTITY" api/  # unchanged
# Operator-facing entity word appears in canon as "Persona":
grep -rn "the Persona\b" docs/architecture/GLOSSARY.md docs/architecture/FOUNDATIONS.md  # positive (operator-facing entity = Persona)
# Architectural vocabulary preserved (NOT renamed — these are canon, not operator-facing):
grep -rn "the seat\b\|the occupant\b" docs/architecture/reviewer-seat-substrate.md  # still present
```

---

## D4 — The published-content / marketing decision (must be made explicitly)

Three **published** blog posts carry "reviewer" in title + slug and are *active positioning*, not just labels:
- *"Name Your Reviewer: Why AI Judgment Should Have A Persona"*
- *"You Don't Need More Models. You Need A Reviewer."*
- *"The Reviewer Seat Is What Single-Agent Architectures Can't Add"*

Per ADR-282 (does-not-edit blog) + ADR-259 (historical-artifact): **published posts are not edited.** They stand as the public record at their date. But they are *evidence about the name itself* — "Reviewer" is the word that already tested in market. Two coherent paths, **the operator must pick one at ratification**:

- **Path α — full rename.** "Persona" becomes the operator-facing entity word everywhere going forward (cockpit + future content + canon); "Reviewer" is deleted from the operator surface. Published posts stand as the historical "Reviewer"-era record. Future blog posts re-position under "Persona" (the *"…Should Have A Persona"* post is *already half-aligned* — it taught "Persona" as the character; Path α just promotes Persona from the character-word to the entity-word). Cleanest internally; costs the market recognition the three "Reviewer"-titled posts built.
- **Path β — split: keep "Reviewer" public, rename the internal/cockpit entity.** "Reviewer" stays the *marketing/public* word (it tested; the blog narrative is coherent); the operator-facing rename to "Persona" applies only to the cockpit + canon. *Narrower*, preserves market continuity, but re-introduces a marketing/cockpit split (marketing says "Reviewer", cockpit says "Persona") — a mild legibility cost.

**This ADR does not pick** — it is the operator's strategic call, and it gates how wide the operator-facing rename reaches. Note the Persona decision *softens* this fork relative to a coined-noun rename: because the blog already uses "Persona" for the character, Path α's continuity cost is lower than it would be for an unfamiliar coined word — the market has already met "Persona." (Recommendation if forced: Path α — promote "Persona" to the entity word in canon + cockpit + future content; let the three "Reviewer"-titled posts stand as dated record; optionally publish *new* content reframing "the Persona is your Reviewer, named and embodied" — but defer to the operator.)

---

## D5 — Stewardship elevation as motivation (recorded, not a new decision)

ADR-319 is the reason the name now carries more weight than when D7 deferred it (full argument: [blast-radius map](../analysis/reviewer-rename-blast-radius-2026-06-07.md) §6). Recorded here so the ratification is made with the full context: **the entity owns and revises intent (DP24), it does not merely review actions — so "Reviewer" (clerical, checks-someone-else's-work) actively under-describes the entity's canonical authority. The recommended resolution does not coin an ownership-word to replace it; it recognizes that the entity is the operator's authored *Persona* (their installed judgment, which owns the mandate by *being* their judgment), and that the ownership/independence weight is carried by canon + framing (ADR-306 / DP22 — fundamentals live in substrate + code, not labels), not by the noun. The residual caveat — "Persona" alone reads act-on-behalf, not can-overrule — is a framing job (D1 caveat), the same job ADR-306 already accepted for every other fundamental.**

---

## Migration plan (one atomic LABEL-rename commit + canon cascade — ADR-201/265 shape)

**Single phase, executed AFTER the sequencing gate (§7) opens and the operator ratifies the name.** Per ADR-201 (atomic rename, single commit) + ADR-282 (canon cascade in the same/adjacent commit):

1. **Route + redirect** — `REVIEWER_ROUTE` constant *name* updates; route *value* keeps `?agent=reviewer` as code-slug + 301 bookmark-safety target (ADR-201 §2 stub); `PROTECTED_PREFIXES` updated (ADR-265 D1).
2. **Frontend LABEL strings — "Reviewer" → "Persona"** where the word means the entity: `ROLE_META` display name + tagline; rendered class labels; `"your Reviewer"` fallback → `"your Persona"`; Constitution-band label (already "Persona" in `HomeHeader` — verify); nav/roster/breadcrumb strings. Component *filenames* stay (`Reviewer*.tsx`). Many edits are *deletions* of "Reviewer" leaning on existing "Persona" framing, not substitutions.
3. **GLOSSARY** — Persona-as-operator-entity entry + "Reviewer = first Purpose" cross-reference; discipline rule (D3); three reviewer slugs added to Exceptions table (D2).
4. **Canon cascade** — FOUNDATIONS (DP25/24/21/14, Axiom 2 section title) + THESIS Commitment 2 + reviewer-canon trio (operator-facing "Reviewer" → "Persona"; **"seat"/"occupant" architectural terms preserved**; filenames preserved) + agent-composition §3.2.1/§4.4 + LAYER-MAPPING. Version bumps.
5. **Grep gate** (D3) + `api/test_adr326_*.py` regression gate asserting: (a) code-slugs unchanged (`role='reviewer'` / `agent_class='reviewer'` / `authored_by="reviewer:"` / `REVIEWER_MODEL_IDENTITY` present); (b) `?agent=reviewer` redirect resolves; (c) "Persona" present as the operator-facing entity word in FOUNDATIONS + GLOSSARY; (d) architectural "seat"/"occupant" still present (NOT renamed); (e) no operator-facing surface renders the bare word "Reviewer" as the entity label (the cockpit shows "Persona" + the occupant's authored name, e.g. "Simons").
6. **CHANGELOG** — `api/prompts/CHANGELOG.md` entry (the persona-frame / cockpit-awareness prose that names the operator-facing entity is a prompt-layer touch).
7. **Marketing decision (D4)** executed per the operator's Path α / β choice — separate from the code commit if Path α (new content, not edits to dated posts).

**Code-module rename** (`reviewer_agent.py` etc.) is **NOT in this migration** — there is no coined noun to rename them to under the recommended decision, and module names are substrate-vocabulary anyway; any future rename is deferred to the ADR-315 D6 L3 package carve. **Architectural "seat"/"occupant" canon is NOT touched** — the rename is operator-facing only.

---

## §7 — Sequencing gate (the explicit dependency)

> **This rename does NOT execute until BOTH of the following have landed on `main`:**
> 1. **The primitive-evolution arc ADR-321–325** — path-native file primitives (321), entity-layer pruning (322), persona-frame collapse finish (323), InferContext dissolution (324), Embed primitive (325). These saturate `reviewer_agent.py`, the primitives registry, `REVIEWER_PRIMITIVES`, the persona-frame sections, and `InferContext`'s identity-inference (which targets `persona/IDENTITY.md`). A rename commit landing mid-arc collides on the same files.
> 2. **The self-writing E2E validation** — saturates the eval core + the reviewer invocation path.

Until the gate opens, this ADR is a settled *design* awaiting a clear runway — the ADR-236 Rule 8 "draft → land just-in-time" discipline applied to a high-blast-radius rename. The [blast-radius map](../analysis/reviewer-rename-blast-radius-2026-06-07.md) §7 re-runs the grep sweep at gate-open time (counts drift). The execution is then a known-quantity single commit + cascade.

---

## What this ADR supersedes / amends / preserves

- **Closes** ADR-320 D7 (de-naming scoped out, deferred to its own ADR — this is that ADR).
- **Completes** FOUNDATIONS Derived Principle 25 (which named the entity "a detached personified judgment seat" but left it unnamed and Reviewer-as-first-Purpose) — not by *coining* a name, but by recognizing the operator already had it: the entity is the named **Persona**; the "seat" is the unnamed architectural abstraction.
- **Motivated by** ADR-319 / Derived Principle 24 (stewardship elevation — "Reviewer" under-describes the entity's ownership; the resolution carries that weight in canon + framing per DP22, not in the noun).
- **Reuses migration shape from** ADR-201 (layered-naming + redirect), ADR-265 (surface rename + PROTECTED_PREFIXES), ADR-282 (canon cascade + discipline-rule + grep-gate + historical-ADR + does-not-edit-blog exemptions).
- **Preserves** the seat≠occupant split (ADR-315 — *strengthened*: the recommended decision turns on respecting it, naming neither the seat nor coining a new occupant word, just promoting "Persona" from character-label to operator-facing-entity-label), the occupant persona-name mechanism (ADR-246 — the operator authors + names their Persona, untouched), all data-compat code-slugs (`role`/`agent_class`/`authored_by`/`REVIEWER_MODEL_IDENTITY`/`persona/` path), the published ABI symbols (ADR-315), the minimal persona-frame (Derived Principle 22 — the fiduciary-independence weight stays in substrate + framing, not the label), and Singular Implementation (one operator word — "Persona"; one data slug — `reviewer`; no coined third noun; no dual vocabulary).
- **Does NOT** coin a new entity noun, rename the architectural "seat"/"occupant" canon, rename code modules / test files / canon-doc filenames, edit historical ADRs, or edit published blog posts (D4 decides forward-content strategy separately).

---

## Open questions for ratification

1. **The name** — **recommended: name nothing new; the operator-facing entity is the named Persona; the seat stays an unnamed architectural abstraction; `reviewer` stays the data slug.** Alternative: coin a seat-noun (**Guardian** / **Overseer**) *if* you want the fiduciary-independence signal carried in the noun rather than in canon + framing. Demoted: Steward / Principal / Arbiter (jargon/collision); Actor (Axiom-9 collision). §D1.
2. **Marketing path** — α (promote "Persona" to the entity word everywhere; "Reviewer"-titled posts stand) vs β (keep "Reviewer" public, "Persona" in cockpit + canon only). §D4.
3. **Caveat-mitigation** — does "Persona" alone need a fiduciary qualifier in lead surfaces ("your Persona — your judgment, applied independently") to pre-empt the yes-man reading, or is canon + onboarding framing sufficient? (Eval-decidable; D1 caveat.) §D1.
4. **Retroactive ADR banners** — add "formerly Reviewer" banner to ADR-194/315/319/320 (optional, ADR-259 pattern) or rely on supersession-is-the-record. §D3.

---

## Provenance

- Upstream discourse: `personified-judgment-seat-vs-task-harness-2026-06-05.md` §4 (de-naming argument) + §7 (naming open).
- Canon: FOUNDATIONS DP25 (entity = detached personified judgment seat; Reviewer = first Purpose) + DP24 (stewardship/ownership) + DP21 + DP14/15 + Axiom 2 (Purpose-not-Identity; two embodiments); THESIS Commitment 2 (independence = detachment); GLOSSARY (Reviewer entries + Exceptions table); reviewer-seat-substrate.md / reviewer-occupant.md / reviewer-occupant-contract.md (seat ≠ occupant ≠ ABI).
- Precedent ADRs: ADR-201, ADR-265, ADR-282, ADR-251, ADR-259, ADR-315 D6, ADR-320 D7, ADR-319.
- Companion: `reviewer-rename-blast-radius-2026-06-07.md` (the touchpoint map).
- Discourse (2026-06-07, this session): the name decision was reached live across five operator corrections — plain-language directive → "closer to act-on-behalf?" → "what about Persona/Actor?" → "keep persona for the occupant, rename the seat" → "isn't the seat just a seat? why name it?". The last correction collapsed the question: the seat is unnamed architectural canon, the operator-facing entity is the named Persona, and "Reviewer" is simply deleted. The v1 draft's coined-noun recommendations (Steward → Overseer) are recorded as superseded-by-discourse in D1.
