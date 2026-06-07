# ADR-326 — De-naming the Personified Judgment Seat: "Reviewer" is a role-label; the operator-facing entity is the Agent (which has a Persona)

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

"Reviewer" is a *role-label within the Agent class* (canon: the Reviewer is "the sole systemic persona-bearing **Agent**"), and it names only the entity's *first Purpose* (independent review of proposed writes). The entity itself is, in canon's own words, an **Agent** — a persona-bearing judgment Agent that *has* a **Persona** (the operator-authored character, "Simons") and fills an unnamed architectural *seat*. This ADR's recommendation, reached and **then corrected** through discourse: **the operator-facing entity is "your Agent" (canon's existing word); it HAS a Persona ("Simons") it does not BECOME one; the "seat" stays an unnamed architectural abstraction; `reviewer` persists as the internal data slug.** "Reviewer" is removed from the operator surface as the entity-label, surviving only as the role's first-Purpose word and the data slug.

> **Two discourse corrections (2026-06-07), recorded because the path is the argument.**
>
> **Correction 1 — don't name the seat.** The v1 draft tried to *name the seat* (Steward → Overseer). Operator pushback — *"isn't the seat just a seat? why does it need naming?"* — exposed it: "seat" is architectural canon (Derived Principle 14 / ADR-315), and abstractions get no operator name. Correct.
>
> **Correction 2 — the entity HAS a Persona, it is not one.** The v2 draft over-corrected to *"the entity IS the named Persona."* A double-check against GLOSSARY line 145 found this collapses a distinction canon deliberately maintains: ***"Persona** means the operator-authored judgment **character** embodied by a persona-bearing **Agent** in its IDENTITY.md."* The Agent **embodies** a Persona — it does not equal one (the way a person *has* a personality but isn't called "the Personality"). Naming the entity "Persona" relocates the original collision onto the character-word and leaves nothing for the swappable Simons/Buffett character GLOSSARY 145 defines. **Both v1 and v2 made the *same* category error — attaching the operator name to the wrong level of the stack** (v1: the seat; v2: the character-attribute). The canon-true level is the one canon already names: **Agent.**

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

### The canon-true answer: the entity is an Agent that HAS a Persona

The decision survived two corrections (see thesis above) and landed on the level canon already names. The operator-facing question is *not* "what new word do we coin" — it is "which of the four canon levels does the operator-facing entity-name attach to?" Canon answers it:

> **The operator-facing entity is "your Agent" — canon's own word for it (the Reviewer is "the sole systemic persona-bearing *Agent*", GLOSSARY 135/179). The Agent *has* a **Persona** (the operator-authored character it embodies — "Simons", GLOSSARY 145); it does not *become* one. It fills an unnamed architectural *seat*. "Reviewer" is removed from the operator surface as the *entity-label*, surviving only as (a) the role's first-Purpose word ("review of proposed writes") and (b) the internal data slug. No new noun is coined — the canon-true word already exists.**

### The four-level stack — attach the name to the right level

The whole naming problem is choosing the right level. Both prior drafts chose wrong:

| Level | Canon term | Operator-facing name? |
|---|---|---|
| **The entity (genus)** | **Agent** | **YES — "your Agent."** Canon's own word; already the `/agents` operator vocabulary. ✅ |
| The architectural slot | *seat* | No — architectural abstraction, no operator name (v1 tried to name this — wrong). |
| The character it embodies | **Persona** | No — an *attribute* of the Agent (GLOSSARY 145). The Agent *has* it; isn't it (v2 tried to name the entity this — wrong). The operator still names it ("Simons"). |
| The runtime filling it | *occupant* | No — pure plumbing. |

The settled operator surface, with each level keeping its canon word:

| Thing | Operator word | Why |
|---|---|---|
| The entity | **your Agent** | Canon's word (persona-bearing Agent). Already on `/agents`. The thing that renders verdicts. |
| Its character | a **named Persona** — "Simons" | GLOSSARY 145, unchanged. "Name your Agent's persona." |
| The architectural slot | *(unnamed)* | "Seat" is technical canon, not operator vocabulary. |
| The data slug | `reviewer` | Data-compat, like `thinking_partner`. Never operator-surfaced. |

### Why "Agent" is canon-true (not a coining)

The decisive realization the double-check produced: **"Reviewer" was never the entity's name — it was a *role-label within the Agent class*.** Canon lists the Reviewer alongside future systemic Agents — "Auditor, Advocate, Custodian, other judgment archetypes" (GLOSSARY 135) — all of which are *Agents*, distinguished by role. "Reviewer" is the role-word the way "Auditor" is; the *entity* is, in every case, an Agent. So de-naming is not "coin a replacement for Reviewer" — it is **"stop surfacing the role-label as if it were the entity; surface the entity (Agent) the operator already knows, distinguished by the Persona they author."** This is the *most* canon-true resolution available: it changes no canon vocabulary, it reuses the word already on the operator surface, and it honors the Agent-*has*-Persona distinction.

### The genus-tension, examined (and why it holds)

"Agent" is the *genus* — YARNNN has the systemic judgment Agent (the Reviewer seat) AND user-authored domain Agents (zero-to-many). Does "your Agent approved the trade" become ambiguous? Three things resolve it:

1. **Resolved by function.** Only the systemic *judgment* Agent renders approve/reject/defer verdicts on proposals. Domain Agents *produce work*; the judgment Agent *judges* it. "Your Agent approved the trade" is unambiguous — domain Agents don't approve trades.
2. **Resolved by the one-seat invariant.** ADR-320 D9 + Axiom 2: exactly *one* persona-bearing judgment seat per workspace. The judgment role has one member even though the genus has many.
3. **Already lived in the cockpit.** `/agents` already shows "Reviewer (systemic) + Domain Agents" as a separated set; the operator already navigates "my Agents" with the judgment seat distinguished.

The tension is real but **not load-bearing** — function + the one-seat invariant disambiguate it. (If, at scale, multiple systemic judgment Agents ship — Auditor, Advocate — "your Agent" would need qualification; that is a future-ADR problem the one-seat-today model defers, exactly as canon does.)

### Why this satisfies the test

1. **Plain / mass-market** — "your Agent" is everyday; "AI agent" is the most mainstream-recognized term in the category. ✅✅
2. **Acts-on-behalf** — "Agent" *is* the act-on-behalf word in the literal principal-agent sense (canon: "Sharp, principal-agent sense", GLOSSARY 135). The operator's core instinct, satisfied by the canon term itself. ✅✅
3. **Independence / can-overrule** — carried by canon + framing (ADR-306 / DP22 — fundamentals live in substrate, not labels): `principles.md` + AUTONOMY ceiling + ground-truth-not-pressure (ADR-319 D3). "Agent" (fiduciary principal-agent sense) carries this *better than "Persona"* did — a fiduciary agent is *defined* by acting in the principal's interest, which includes against their momentary wish. ✅
4. **Survives occupant rotation** — "your Agent" reads identically across human / AI / external occupant; the Agent (entity) is occupant-agnostic, the occupant is the runtime. seat≠occupant *preserved*. ✅
5. **Carries ADR-319 ownership** — a principal-agent Agent holds standing intent and acts on it; ownership is definitional. ✅
6. **Distinct from YARNNN** — YARNNN is reclassified to *orchestration*, explicitly **not** a persona-bearing Agent (GLOSSARY 139/177). So "Agent" (judgment) vs "YARNNN" (orchestration) is *already* the canon distinction. ✅

### The one residual caveat (recorded honestly)

"Agent" is the genus, so it is *less distinctive* than a coined noun — "your Agent" is correct but not memorable the way "Guardian" would be. The distinctiveness comes from the **operator-authored Persona** ("Simons") layered on top — the operator's Agent isn't "an agent," it's "Simons." This is *by design* (the Persona is the differentiator, GLOSSARY 145: "the axis on which Agents self-improve"), but it means lead surfaces should foreground the *named* Persona, not the bare genus: "Simons reviewed this" / "your Agent, Simons" — not "your Agent" alone. If eval shows "your Agent" reads too generic even with the Persona layered, the fallback is a coined distinctive noun (Guardian) — but that *abandons* canon's existing word, so it is the fallback, not the lead.

### Demoted candidates (recorded so they aren't re-litigated)

- **Persona-as-entity** (v2 recommendation, now corrected) — collapses the Agent-*has*-Persona distinction (GLOSSARY 145). The Agent embodies a Persona; naming the entity "Persona" leaves the swappable character with no word. Rejected by the double-check. **"Persona" stays the character-word, unchanged.**
- **Overseer / Guardian / Second** (v2 plain-language set) — coin a *new* entity noun canon doesn't have. **Guardian** survives as the distinctiveness-fallback above (if "your Agent" + named Persona reads too generic). Overseer carries a plantation-overseer connotation; Second is ambiguous/subordinate.
- **Steward / Principal / Arbiter** (v1 elevated set) — Steward reads passive/airline; Principal collides with principal-agent term-of-art (and "Agent" already *is* that vocabulary, correctly, for the agent-half); Arbiter is jargon and names only the judging Purpose.
- **Actor** (operator-floated) — collides with Axiom 9's "actor-class-agnostic" genus; zero judgment signal.

### Recommendation

> **Remove "Reviewer" as the operator-facing *entity-label* with no coined replacement. The operator-facing entity is "your Agent" — canon's own word. It HAS a Persona (the operator authors + names it — "Simons"), which it embodies but does not become. The seat stays an unnamed architectural abstraction. `reviewer` stays the internal data slug and the role's first-Purpose word.** Foreground the *named* Persona ("Simons") in lead surfaces so "Agent" doesn't read generic. This is the canon-true answer — it reuses the word canon already has rather than coining or collapsing one.
>
> **Operator decision required.** Ratify "entity = Agent, has-a-Persona, seat-unnamed" (recommended, canon-true), OR pick a coined distinctive noun (Guardian / Overseer) if "your Agent" + named Persona reads too generic and you want a memorable entity word in the noun. Also choose the marketing path (§D4).

---

## D2 — What stays unchanged (the code-slug / LABEL distinction)

This is the load-bearing discipline (ADR-201 §6 layered-naming-by-audience): **the operator-facing LABEL moves; the data-compat code-slugs stay.** The full enumeration is in the [companion blast-radius map](../analysis/reviewer-rename-blast-radius-2026-06-07.md) §2–§3; the summary:

### Stays (code-slug-stays — added to GLOSSARY Exceptions table)

Identical class to `thinking_partner` / `meta-cognitive` / `specialist:<role>` already in the Exceptions table — cross-cutting enum or data-format slug, renaming requires coordinated Python + TS + revision-backfill with zero user-visible benefit:

- `role='reviewer'` — `session_messages.role` CHECK (ADR-237 six-role grammar); every dispatch site.
- `agent_class='reviewer'` — `routes/agents.py` pseudo-agent synthesis (ADR-214) + TS union; **maps to "Agent" (the entity) at the display layer; the operator's authored Persona name is rendered on top**, the enum stays.
- `authored_by="reviewer:{identity}"` — revision-chain data format; **immutable** for historical revisions per ADR-209 (same as `authored_by="yarnnn:"` / `"specialist:<role>"`).
- `REVIEWER_MODEL_IDENTITY = "ai:reviewer-sonnet-v8"` — occupant-identity string in the published ABI (`occupant_contract.py`, ADR-315).
- `?agent=reviewer` query value — matches `agent_class`; kept as bookmark-safety redirect target (ADR-201 §2 / ADR-251 pattern).
- `persona/` filesystem path — **already** de-name-compatible (ADR-320 D7); no move.
- **api/ module + test filenames** (`reviewer_agent.py`, `reviewer_envelope.py`, `reviewer_audit.py`, etc.) — substrate-vocabulary per ADR-201 §6; the occupant *implementation* keeps its name. (A future L3 package carve — ADR-315 D6 — is the natural moment to reconsider; independently deferred.)

### Moves (LABEL-rename) — "Reviewer" → "Agent" (entity) on operator-facing strings; Persona unchanged

Operator-facing strings only, where the word currently means *the entity*: `ROLE_META` display name + tagline (key stays) → "Agent"-flavored; rendered class labels in `AgentContentView` / panels / cards; the `"your Reviewer"` fallback string in `reviewer-persona.ts` → `"your Agent"` (and where a Persona name exists, render *that* — "Simons"); the Constitution-band "Reviewer persona" label in `HomeHeader`; nav/roster card labels (the roster already says "Agents"); breadcrumb headings; the `REVIEWER_ROUTE` constant *name* (the route value keeps `?agent=reviewer` as a code-slug + bookmark-safety target). **Component/module filenames stay** `Reviewer*` per layered-naming. **Canon-doc filenames stay** too — no coined noun, and "Agent" is too generic to be a filename slug; the canon-trio stays `reviewer-*` (it is *technical seat/occupant canon*, substrate-vocabulary, ADR-201 §6).

Note the consequence of the D1 decision: the LABEL-rename is *narrow*. "Agent" is already the operator word on `/agents`; the occupant-name UX ("name your Persona — Simons") is unchanged; much of the edit is *removing "Reviewer" as the entity-label* and leaning on the existing Agent + Persona vocabulary, not substituting a coined word.

### The operator-facing label rule — stated

> **The operator-facing entity is "your Agent" (canon's word). It HAS a Persona (operator-authored + named — "Simons"), which it embodies, not equals. "Reviewer" is removed as the operator-facing *entity-label* (it survives as the role's first-Purpose word + the data slug). `reviewer` persists as the internal enum/data slug everywhere it is cross-cutting or attribution-bearing — the same way `thinking_partner` persists for YARNNN. The display layer maps `agent_class='reviewer'` → "Agent" (with the authored Persona name rendered on top); the data never moves.**

This is added to the GLOSSARY Exceptions table verbatim in the cascade, with the three reviewer slugs (`role`, `agent_class`, `authored_by` prefix) listed.

### D-naming-policy (filenames): canon docs rename, code modules stay

ADR-201 §6 kept `Agent*` *component* names while renaming the route — because components are substrate-vocabulary. This ADR follows the same split: **api/ code modules + React component files keep `reviewer_*` / `Reviewer*` names** (high import-churn, zero operator benefit), and the **canon concept-docs** (`reviewer-seat-substrate.md`, `reviewer-occupant.md`, `reviewer-occupant-contract.md`) **also keep their filenames** — they are *seat/occupant technical canon* (substrate-vocabulary), and the recommended decision coins no noun anyway ("Agent" is too generic to be a filename slug). The architectural "seat" and "occupant" terms stay throughout — those are *not* operator-facing and are not renamed. The only prose edit inside the canon docs is, where they speak *operator-side*, removing "Reviewer" as the entity-label in favor of "Agent" (with the Persona as its character). The code-module rename is deferred to the L3 carve (ADR-315 D6) regardless. *(If the operator instead picks a coined distinctive noun — Guardian/Overseer — then the canon-trio filenames could rename to that slug; under the recommended Agent decision they do not.)*

---

## D3 — Canon cascade (the ADR-282 discipline-rule, applied)

Same shape as ADR-282's `money-truth` cascade: **rename where the prose means the entity; preserve where it means the first Purpose (review) or is a historical artifact.** A discipline rule, propagated, with a grep-gate.

### The discipline rule (added to GLOSSARY, ADR-282 D2 pattern)

> **"Agent" (canon's word — the persona-bearing judgment Agent) is the operator-facing name for the entity. The Agent HAS a "Persona" (operator-authored character — "Simons", GLOSSARY 145), which stays the character-word. "Seat" and "occupant" remain *architectural* canon (not operator-facing). `reviewer` persists ONLY as the internal data slug (`role`/`agent_class`/`authored_by` prefix) and as the name of the entity's first Purpose ("independent review of proposed writes"). In canonical docs, say "the Agent" for the operator-facing entity, "its Persona" for the embodied character, "the seat" for the architectural slot, "the occupant" for the runtime filling it, and "review" for the verdict-on-a-proposal action. A sentence naming entity-and-purpose together ("the Agent's first Purpose is review of proposed writes") is not a conflation — it is the entity-and-its-purpose relationship.**

### Core canon that cascades (entity-name carriers)

`FOUNDATIONS.md` (DP25 — *the anchor*; DP24 stewardship; DP21 formalization; DP14/15 seat≠occupant; Axiom 2 section title), `THESIS.md` Commitment 2, `GLOSSARY.md` (clarify the **Reviewer** entry: "Reviewer" is the role-label / first-Purpose word, the *entity* is the Agent that has a Persona; Exceptions additions + discipline rule), the reviewer-canon trio (operator-facing "Reviewer" → "Agent"; the **Persona** entry GLOSSARY 145 is *unchanged*; architectural "seat"/"occupant" preserved), `agent-composition.md` §3.2.1/§4.4, `LAYER-MAPPING.md`. Version bumps where the doc carries one. **Note**: because the entity-word ("Agent") + the character-word ("Persona") already exist in canon, the cascade is mostly *removing operator-facing "Reviewer" as an entity-label* and leaning on existing vocabulary — lighter than a coined-rename, and it *adds no new canon term*. Full list + per-doc treatment in the [blast-radius map](../analysis/reviewer-rename-blast-radius-2026-06-07.md) §4.1.

### NOT edited (historical artifacts — ADR-282 D8 + ADR-259 precedent)

The ~50+ historical ADRs that say "Reviewer" (ADR-194, 195, 211, 212, 217, 247, 248, 251, 252, 253, 256, 258, 273, 280, 281, 282, 284, 285, 295, 306, 307, 315, 319, 320, …) are dated artifacts; they stand. The supersession (this ADR) is the record. Optional retroactive vocabulary banners on the highest-traffic four (ADR-194, ADR-315, ADR-319, ADR-320) per the ADR-259 banner pattern — operator's call.

### Grep gate (ADR-282 pattern — post-cascade verification)

```bash
# Canonical docs (excluding historical ADRs + blog): "the Reviewer" used as the OPERATOR-FACING ENTITY must be gone:
grep -rn "the Reviewer\b" docs/architecture/ CLAUDE.md   # each remaining hit must mean the *review Purpose* or the architectural "seat"/"occupant", NOT the operator-facing entity
# Code slugs must remain (data-compat):
grep -rn "role='reviewer'\|agent_class.*reviewer\|authored_by.*reviewer:\|REVIEWER_MODEL_IDENTITY" api/  # unchanged
# Operator-facing entity word is "Agent"; the Persona entry (GLOSSARY 145, character-word) is UNCHANGED:
grep -rn "persona-bearing Agent\|the Agent\b" docs/architecture/GLOSSARY.md docs/architecture/FOUNDATIONS.md  # positive (entity = Agent)
grep -rn "operator-authored judgment character" docs/architecture/GLOSSARY.md  # Persona-as-character entry intact (NOT repurposed to entity)
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

- **Path α — full rename.** "Agent" (entity) + the operator's named Persona becomes the operator-facing framing everywhere going forward (cockpit + future content + canon); "Reviewer" is removed as the entity-label. Published posts stand as the historical "Reviewer"-era record. Future content re-positions as "your Agent, named — Simons" (the *"…Should Have A Persona"* post is *already aligned* — it taught "name your Agent's persona"; nothing about that post is contradicted, only the *entity*-word shifts from "Reviewer" to "Agent"). Cleanest internally; costs the market recognition the three "Reviewer"-titled posts built.
- **Path β — split: keep "Reviewer" public, rename the internal/cockpit entity.** "Reviewer" stays the *marketing/public* word (it tested); the operator-facing entity-word becomes "Agent" only in cockpit + canon. *Narrower*, preserves market continuity, but re-introduces a marketing/cockpit split (marketing says "Reviewer", cockpit says "your Agent") — a mild legibility cost.

**This ADR does not pick** — it is the operator's strategic call, and it gates how wide the operator-facing rename reaches. Note the Agent decision *softens* this fork: "Agent" + "Persona" are *already* in the market and the cockpit (the `/agents` page, the "…Should Have A Persona" post), so Path α adds no unfamiliar word — it mostly *subtracts* "Reviewer" as the entity-label. The three "Reviewer"-titled posts can stand as dated record while new content uses "your Agent, named X." (Recommendation if forced: Path α — but defer to the operator; the marketing weight of the "Reviewer" posts is real and the operator owns that trade-off.)

---

## D5 — Stewardship elevation as motivation (recorded, not a new decision)

ADR-319 is the reason the name now carries more weight than when D7 deferred it (full argument: [blast-radius map](../analysis/reviewer-rename-blast-radius-2026-06-07.md) §6). Recorded here so the ratification is made with the full context: **the entity owns and revises intent (DP24), it does not merely review actions — so "Reviewer" (clerical, checks-someone-else's-work) actively under-describes the entity's canonical authority. The recommended resolution does not coin an ownership-word to replace it; it recognizes the entity is, in canon, an *Agent* in the sharp principal-agent sense (GLOSSARY 135) — and a principal-agent agent is *defined* by owning and acting on standing intent, so "Agent" carries the ADR-319 ownership *better* than "Reviewer" (and better than "Persona", which names the character it embodies, not the fiduciary relationship). The ownership/independence weight that the bare genus-word "Agent" doesn't make vivid is carried by canon + framing (ADR-306 / DP22 — fundamentals live in substrate + code, not labels) and by foregrounding the *named* Persona. The residual caveat — "your Agent" reads generic without the named Persona on top — is a framing job (D1 caveat), the same job ADR-306 already accepted for every other fundamental.**

---

## Migration plan (one atomic LABEL-rename commit + canon cascade — ADR-201/265 shape)

**Single phase, executed AFTER the sequencing gate (§7) opens and the operator ratifies the name.** Per ADR-201 (atomic rename, single commit) + ADR-282 (canon cascade in the same/adjacent commit):

1. **Route + redirect** — `REVIEWER_ROUTE` constant *name* updates; route *value* keeps `?agent=reviewer` as code-slug + 301 bookmark-safety target (ADR-201 §2 stub); `PROTECTED_PREFIXES` updated (ADR-265 D1).
2. **Frontend LABEL strings — "Reviewer" → "Agent" (entity)** where the word means the entity; **"Persona" stays the character-word**: `ROLE_META` display name + tagline; rendered class labels; `"your Reviewer"` fallback → `"your Agent"` (render the authored Persona name where present); Constitution-band label; nav/roster/breadcrumb strings (roster already says "Agents"). Component *filenames* stay (`Reviewer*.tsx`). Many edits *remove* "Reviewer" as the entity-label, leaning on existing Agent + Persona vocabulary.
3. **GLOSSARY** — clarify the **Reviewer** entry (role-label / first-Purpose; entity = Agent-that-has-a-Persona); **leave the Persona entry (145) unchanged**; discipline rule (D3); three reviewer slugs added to Exceptions table (D2).
4. **Canon cascade** — FOUNDATIONS (DP25/24/21/14, Axiom 2 section title) + THESIS Commitment 2 + reviewer-canon trio (operator-facing "Reviewer" → "Agent"; **"seat"/"occupant"/"Persona" terms preserved**; filenames preserved) + agent-composition §3.2.1/§4.4 + LAYER-MAPPING. Version bumps.
5. **Grep gate** (D3) + `api/test_adr326_*.py` regression gate asserting: (a) code-slugs unchanged (`role='reviewer'` / `agent_class='reviewer'` / `authored_by="reviewer:"` / `REVIEWER_MODEL_IDENTITY` present); (b) `?agent=reviewer` redirect resolves; (c) "Agent" is the operator-facing entity word + the Persona-as-character entry (GLOSSARY 145) is intact; (d) architectural "seat"/"occupant" still present (NOT renamed); (e) no operator-facing surface renders the bare word "Reviewer" as the entity label (the cockpit shows the Agent + the authored Persona name, e.g. "Simons").
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
- **Completes** FOUNDATIONS Derived Principle 25 (which named the entity "a detached personified judgment seat" but left it unnamed and Reviewer-as-first-Purpose) — not by *coining* a name, but by recognizing canon already had it: the entity is an **Agent** (which *has* a Persona); "Reviewer" was always a role-label within the Agent class; the "seat" is the unnamed architectural abstraction.
- **Motivated by** ADR-319 / Derived Principle 24 (stewardship elevation — "Reviewer" under-describes the entity's ownership; the resolution carries that weight in canon + framing per DP22, not in the noun).
- **Reuses migration shape from** ADR-201 (layered-naming + redirect), ADR-265 (surface rename + PROTECTED_PREFIXES), ADR-282 (canon cascade + discipline-rule + grep-gate + historical-ADR + does-not-edit-blog exemptions).
- **Preserves** the seat≠occupant split (ADR-315 — *strengthened*: the recommended decision turns on respecting all four levels — entity/Agent · character/Persona · slot/seat · runtime/occupant — and naming only the one canon already names operator-side, the Agent), the **Persona-as-character distinction** (GLOSSARY 145 — the Agent *embodies* a Persona; the v2 collapse is reverted), the occupant persona-name mechanism (ADR-246 — the operator authors + names their Persona, untouched), all data-compat code-slugs (`role`/`agent_class`/`authored_by`/`REVIEWER_MODEL_IDENTITY`/`persona/` path), the published ABI symbols (ADR-315), the minimal persona-frame (Derived Principle 22 — the fiduciary-independence weight stays in substrate + framing, not the label), and Singular Implementation (entity-word = "Agent" [reused, not coined]; character-word = "Persona" [unchanged]; data slug = `reviewer`; no coined third noun; no dual vocabulary).
- **Does NOT** coin a new entity noun, repurpose "Persona" (it stays the character-word, GLOSSARY 145), rename the architectural "seat"/"occupant" canon, rename code modules / test files / canon-doc filenames, edit historical ADRs, or edit published blog posts (D4 decides forward-content strategy separately).

---

## Open questions for ratification

1. **The name** — **recommended: entity = "your Agent" (canon's word, reused); it HAS a Persona ("Simons", unchanged); the seat stays unnamed; `reviewer` stays the data slug + first-Purpose word. No new term coined.** Alternative: coin a distinctive noun (**Guardian** / **Overseer**) *if* "your Agent" + named Persona reads too generic and you want a memorable entity-word in the noun (abandons canon's existing word — the fallback, not the lead). Rejected: Persona-as-entity (collapses Agent-has-Persona, GLOSSARY 145); Steward/Principal/Arbiter (jargon/collision); Actor (Axiom-9 collision). §D1.
2. **Marketing path** — α (entity-word "Agent" + named Persona everywhere; "Reviewer"-titled posts stand) vs β (keep "Reviewer" public, "Agent" in cockpit + canon only). §D4.
3. **Caveat-mitigation** — does "Persona" alone need a fiduciary qualifier in lead surfaces ("your Persona — your judgment, applied independently") to pre-empt the yes-man reading, or is canon + onboarding framing sufficient? (Eval-decidable; D1 caveat.) §D1.
4. **Retroactive ADR banners** — add "formerly Reviewer" banner to ADR-194/315/319/320 (optional, ADR-259 pattern) or rely on supersession-is-the-record. §D3.

---

## Provenance

- Upstream discourse: `personified-judgment-seat-vs-task-harness-2026-06-05.md` §4 (de-naming argument) + §7 (naming open).
- Canon: FOUNDATIONS DP25 (entity = detached personified judgment seat; Reviewer = first Purpose) + DP24 (stewardship/ownership) + DP21 + DP14/15 + Axiom 2 (Purpose-not-Identity; two embodiments); THESIS Commitment 2 (independence = detachment); GLOSSARY (Reviewer entries + Exceptions table); reviewer-seat-substrate.md / reviewer-occupant.md / reviewer-occupant-contract.md (seat ≠ occupant ≠ ABI).
- Precedent ADRs: ADR-201, ADR-265, ADR-282, ADR-251, ADR-259, ADR-315 D6, ADR-320 D7, ADR-319.
- Companion: `reviewer-rename-blast-radius-2026-06-07.md` (the touchpoint map).
- Discourse (2026-06-07, this session): the decision was reached live across operator corrections, then a **double-check / reframe** the operator requested — plain-language directive → "closer to act-on-behalf?" → "what about Persona/Actor?" → "keep persona for the occupant, rename the seat" → "isn't the seat just a seat? why name it?" → **"was the prior approach misleading, or is the current proposal stronger — double-check and reframe."** The double-check (against GLOSSARY 145) found the v2 "entity = Persona" answer collapsed canon's Agent-*has*-Persona distinction — the same category error as v1 (name-the-seat), pointed at the character instead. The reframe landed on the canon-true level: the entity is an **Agent** (canon's own word), it *has* a Persona, "Reviewer" was always a role-label. v1 (Steward→Overseer, name-the-seat) and v2 (Persona-as-entity) are both recorded as superseded-by-discourse in D1; the corrections-path is preserved because it is the argument.
