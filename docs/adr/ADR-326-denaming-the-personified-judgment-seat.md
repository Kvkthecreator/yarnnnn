# ADR-326 — De-naming the Personified Judgment Seat: from "Reviewer" to a Name for the Detachment

> **Status**: **DRAFT — awaiting operator ratification.** NOT Implemented. No code, no canon edit, no rename executes from this ADR until the sequencing gate (§7) opens and the operator ratifies the chosen name.
> **Date**: 2026-06-07
> **Authors**: KVK, Claude
> **Upstream discourse**: [personified-judgment-seat-vs-task-harness-2026-06-05.md](../analysis/personified-judgment-seat-vs-task-harness-2026-06-05.md) §4 (the de-naming argument — the axiom is detachment + personification; "Reviewer" names only the first Purpose) + §7 (naming explicitly left open).
> **Companion analysis**: [reviewer-rename-blast-radius-2026-06-07.md](../analysis/reviewer-rename-blast-radius-2026-06-07.md) — the full touchpoint map this ADR's migration plan rests on.
> **Reuses migration shape from**: [ADR-201](ADR-201-team-rename-and-cross-linking.md) (layered-naming-by-audience + redirect-stub) · [ADR-265](ADR-265-activity-surface-rename-and-mode-discriminator.md) (surface rename + PROTECTED_PREFIXES + redirect) · [ADR-282](ADR-282-axiom-8-ground-truth-rename.md) (canon cascade + discipline-rule + grep-gate + historical-ADR exemption).
> **Depends on**: ADR-320 (`persona/` re-root — done; makes substrate paths name-neutral) + ADR-319 (stewardship elevation — done; makes the name matter more). **Blocked by**: ADR-321–325 (primitive-evolution arc) + the self-writing E2E validation must land first (§7).
> **Dimensional classification**: **Identity** (Axiom 2 — who the entity is) + **Channel** (Axiom 6 — the operator-facing label is a legibility surface).

---

## The one-sentence thesis

"Reviewer" names the entity's *first Purpose* (independent judgment on proposed writes); the entity itself is a **detached, personified judgment seat that owns the operator's mandate as their installed principal** — and after ADR-319 promoted ownership to the entity's job, the name now actively under-describes its canonical authority. This ADR proposes a name for the *detachment*, classifies every touchpoint as LABEL-rename / code-slug-stays / canon-doc-edit, and sequences the execution behind the in-flight backend arc.

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

### What the name must satisfy (the test, derived from the axiom)

A candidate must:
1. **Be plain, everyday language a non-technical person grasps instantly** (operator directive, 2026-06-07). The ICP is "content product operators / domain experts," not engineers; the name appears in the cockpit, in nav, in marketing. It must read like a word the mass-market already owns — not jargon (`Arbiter`), not term-of-art (`Principal` in principal-agent theory), not a word whose lay meaning fights its technical one (`Steward` as passive caretaker). **This is the dominant constraint** — it re-ranks the candidates below the elevated-vocabulary set considered in the v1 draft.
2. **Name the on-your-behalf judgment + ownership**, not the *review* function. (Independence and ownership both *fall out of* being a detached, mandate-holding entity judged against ground truth — discourse §4 + ADR-319.) In plain terms: *the one who watches over your operation and makes the calls you'd make.*
3. **Survive occupant rotation** (Derived Principle 14). The name is the *seat*, not who fills it. Reads coherently whether a human, an AI, or an external service occupies it.
4. **Compose with `persona/`** (the dir ADR-320 D7 chose to be de-name-compatible) and the seat≠occupant split — the occupant's *persona name* ("Simons") is a different, already-named thing the operator authors.
5. **Carry the post-ADR-319 weight** — *owns and tends* the operation, not just *checks* proposals.
6. **Distinguish cleanly from YARNNN** (the orchestration chat surface / brand) and from the occupant persona name.

### The plain-language reframe

For the non-technical operator, the entity is best described in one sentence: **"the part of YARNNN that watches over your operation and makes the calls the way you would — even when you're not looking."** The name should be the everyday word for *that someone*. Candidates are now ranked by how naturally a non-technical person reads them, with the elevated-vocabulary options (Steward / Principal / Arbiter) explicitly demoted.

### Candidate names

#### Candidate A — **Overseer** *(recommended)*

Plain English for *the one who watches over and is responsible for an operation.*

1. **Layman-friendly** — everyone knows "oversee / overseer" from ordinary speech ("who's overseeing this?"). No technical baggage, no dictionary trip. ✅✅ (the dominant test)
2. **On-your-behalf judgment + ownership** — "oversee" means *watch over with responsibility for outcomes* — it carries both the judging (watches) and the owning (responsible for) that ADR-319 elevated, without the clerical narrowness of "review." It reads as active and accountable, not passive. ✅
3. **Survives rotation** — "your Overseer" / "the Overseer seat" reads identically for human / AI occupant. ✅
4. **`persona/` + seat≠occupant** — clean three layers: `persona/` is *how the Overseer reasons*; "Simons" is *who it's embodied as*; "Overseer" is *the role*. ✅
5. **Post-319 weight** — "watches over the whole operation" is exactly two-altitude ownership in plain words (it minds the trades *and* the strategy). ✅
6. **Distinct from YARNNN / persona name** — YARNNN does the work; the Overseer watches over it and makes the calls; the persona name embodies the Overseer. Clear three-way. ✅

**Risk**: "overseer" has a historical slavery connotation in some markets (the plantation overseer). Real, must be weighed — but the dominant modern usage is neutral managerial ("project overseer," "oversight"), and the connotation attaches to *overseeing people under coercion*, not *overseeing your own operation on your behalf*. Mitigant: if the connotation is judged too live for the target markets, fall to Candidate B. **Operator should weigh this explicitly.**

#### Candidate B — **Guardian**

Plain English for *the one who protects and acts in your interest.*

1. **Layman-friendly** — universally understood, warm, zero jargon. ✅✅
2. **On-your-behalf + ownership** — "guardian" carries *acts in your interest, with authority, protecting what's yours* — which maps to the fiduciary independence (THESIS Commitment 2: the entity protects the operator even from their own momentary pressure — ADR-319 D3). Strong fit to "makes the calls you'd make, in your interest." ⚠️ leans *protective* more than *owning/driving* — slightly under-weights the altitude-2 *grow-the-operation* ownership (it guards more than it drives).
3. **Survives rotation** — "your Guardian" reads fine. ✅
4. **`persona/` + seat≠occupant** — clean. ✅
5. **Post-319 weight** — carries the *protect-the-mandate-against-pressure* half of ADR-319 well; carries the *revise-the-mandate-to-grow* half less naturally. ⚠️
6. **Distinct** — clean; no overload with YARNNN or persona name. ✅

**Verdict**: the safest plain-language pick (no connotation risk, warm, instantly clear). Slightly under-weights the *ownership-that-drives-improvement* half of ADR-319 — guards more than it grows. **Recommended fallback if Overseer's connotation is judged too live.**

#### Candidate C — **Second** (as in *your second-in-command* / *your right hand*)

Plain English for *the trusted one who acts for you when you're not there.*

1. **Layman-friendly** — "my second" / "second-in-command" / "right hand" is everyday business speech. ✅
2. **On-your-behalf + ownership** — captures *the same principal, one step removed, acting with your authority* (Axiom 2's two-embodiments) better than any other plain word — a "second" IS you when you're absent. ✅✅ on faithfulness to the axiom.
3. **Survives rotation** — "your Second" reads fine. ✅
4. **`persona/` + seat≠occupant** — clean. ✅
5. **Post-319 weight** — a "second-in-command" *runs the operation in your stead*, which carries ownership well. ✅ ⚠️ but "Second" as a bare noun is ambiguous (the number, the unit of time) — needs "your Second" / "Second-in-command" framing to disambiguate, which is wordier in nav/labels.
6. **Distinct** — ⚠️ mild: it positions the entity as *subordinate to* the operator, which is *true* (the operator's veto is supreme — ADR-319 D2) but slightly undersells the *independent-judgment-even-against-your-pressure* property (THESIS Commitment 2). A "second" obeys; the entity is independent.

**Verdict**: most faithful to the two-embodiments plain-language intuition, but the bare-noun ambiguity (number/time) and the "subordinate" lean make it weaker as a cockpit label than Overseer/Guardian.

### Elevated-vocabulary options (demoted by the layman directive)

For the record, the v1 draft recommended **Steward** and considered **Principal** / **Arbiter**. Under the plain-language directive all three are demoted: **Steward** (right meaning — it *is* DP24's word — but "steward" reads as airline/estate-caretaker to a lay audience and leans passive); **Principal** (term-of-art collision with principal-agent theory; "the AI principal" confuses); **Arbiter** (jargon; and names only the judging Purpose, not the post-319 ownership). They remain available if the operator prefers canon-word-fidelity over mass-market plainness, but they fail constraint #1.

### Operator-suggested candidates (2026-06-07): **Persona** and **Actor** — both rejected for collision

The operator floated **Persona** and **Actor**. Both are plain words (they pass constraint #1's *accessibility* test) but both fail on collision with load-bearing existing vocabulary — and collision is worse than jargon, because it makes *two* concepts ambiguous instead of one.

- **Persona — REJECTED (triple collision).** "Persona" is already three load-bearing things in this exact architecture: (1) the `persona/` directory — the seat's substrate home (ADR-320), chosen *specifically* to be de-name-compatible *because it names where the seat lives, not the seat*; (2) the **occupant persona name** — the operator authors "Simons"/"Buffett" in `persona/IDENTITY.md`, and the blog post *"Name Your Reviewer: Why AI Judgment Should Have A Persona"* makes "persona" mean *the occupant's character* in published marketing; (3) the **persona-frame** — the system-prompt layer (`reviewer_agent.py` `_PERSONA_FRAME`, Derived Principle 22). Naming the *entity* "Persona" collapses the entity, its directory, its occupant-character, and its prompt-frame into one ambiguous word — the exact opposite of the legibility the rename is *for*. It would also break the seat≠occupant split (ADR-315): "Persona" most naturally reads as *the occupant* ("which persona is filling the seat?"), not the *seat*. Hard reject.
- **Actor — REJECTED (axiom collision + too generic).** "Actor" is already a kernel term: FOUNDATIONS Axiom 9 declares invocations *"actor-class-agnostic"* — an **actor** is *anything that emits an invocation* (the operator, YARNNN, the entity, an external MCP caller all are "actors"). ADR-257 calls the orchestration *system* "a different actor." So "Actor" names the *genus*, not this *species* — it's the broadest possible word for "thing that does something in the system," which makes it useless as the name for the *specific* detached-judgment entity (it would be like naming one employee "Employee"). It also carries zero signal about judgment/ownership/detachment — an actor just *acts*. Plain, yes; but it names everything and therefore nothing. Reject.

The lesson both share: a plain word that *collides* with existing canonical vocabulary is less legible than a plain word that doesn't (Overseer/Guardian collide with nothing in YARNNN's vocabulary). Accessibility (constraint #1) is necessary but not sufficient — non-collision is the gate that eliminates Persona and Actor despite their plainness.

### Recommendation: **Overseer** (fallback **Guardian**)

**Overseer** is the plainest everyday word that carries *watches over + responsible for + makes the calls on your behalf* — the post-ADR-319 entity in mass-market language. It survives rotation, composes cleanly with `persona/` + the occupant persona-name, and is distinct from YARNNN. Its one real risk is the historical connotation; if the operator judges that too live for the target markets, **Guardian** is the safe fallback (warmer, zero connotation risk, slightly under-weights the drive-to-improve half of ownership).

> **Operator decision required.** This ADR recommends **Overseer** (fallback **Guardian**), both chosen for plain-language accessibility per the 2026-06-07 directive. The name is the operator's to ratify — including the option to keep "Reviewer" as the *public/marketing* word (§D4) while renaming only the internal/cockpit entity.

---

## D2 — What stays unchanged (the code-slug / LABEL distinction)

This is the load-bearing discipline (ADR-201 §6 layered-naming-by-audience): **the operator-facing LABEL moves; the data-compat code-slugs stay.** The full enumeration is in the [companion blast-radius map](../analysis/reviewer-rename-blast-radius-2026-06-07.md) §2–§3; the summary:

### Stays (code-slug-stays — added to GLOSSARY Exceptions table)

Identical class to `thinking_partner` / `meta-cognitive` / `specialist:<role>` already in the Exceptions table — cross-cutting enum or data-format slug, renaming requires coordinated Python + TS + revision-backfill with zero user-visible benefit:

- `role='reviewer'` — `session_messages.role` CHECK (ADR-237 six-role grammar); every dispatch site.
- `agent_class='reviewer'` — `routes/agents.py` pseudo-agent synthesis (ADR-214) + TS union; **maps to the new label at the display layer**, the enum stays.
- `authored_by="reviewer:{identity}"` — revision-chain data format; **immutable** for historical revisions per ADR-209 (same as `authored_by="yarnnn:"` / `"specialist:<role>"`).
- `REVIEWER_MODEL_IDENTITY = "ai:reviewer-sonnet-v8"` — occupant-identity string in the published ABI (`occupant_contract.py`, ADR-315).
- `?agent=reviewer` query value — matches `agent_class`; kept as bookmark-safety redirect target (ADR-201 §2 / ADR-251 pattern).
- `persona/` filesystem path — **already** de-name-compatible (ADR-320 D7); no move.
- **api/ module + test filenames** (`reviewer_agent.py`, `reviewer_envelope.py`, `reviewer_audit.py`, etc.) — substrate-vocabulary per ADR-201 §6; the occupant *implementation* keeps its name. (A future L3 package carve — ADR-315 D6 — is the natural moment to reconsider; independently deferred.)

### Moves (LABEL-rename)

Operator-facing strings only: route-constant `REVIEWER_ROUTE` name, `ROLE_META` display name + tagline (key stays), rendered class labels in `AgentContentView` / panels / cards, the `"your Reviewer"` fallback string in `reviewer-persona.ts`, the Constitution-band "Reviewer persona" label in `HomeHeader`, nav/roster card labels, breadcrumb headings. **Component/module filenames stay** `Reviewer*` per layered-naming (recommend); **canon-doc filenames** (`reviewer-seat-substrate.md` et al.) the ADR may rename since they are concept docs, not code (recommend rename — see §D-naming-policy below).

### The operator-facing label rename vs the code-slug — stated as the rule

> **The new name (`Overseer`, if ratified per §D1) is the operator-facing label for the entity. `reviewer` persists as the internal enum/data slug everywhere it is cross-cutting or attribution-bearing — the same way `thinking_partner` persists for YARNNN. The display layer maps the slug to the label; the data never moves.**

This is added to the GLOSSARY Exceptions table verbatim in the cascade, with the three reviewer slugs (`role`, `agent_class`, `authored_by` prefix) listed.

### D-naming-policy (filenames): canon docs rename, code modules stay

ADR-201 §6 kept `Agent*` *component* names while renaming the route — because components are substrate-vocabulary. This ADR follows the same split with one refinement: **api/ code modules + React component files keep `reviewer_*` / `Reviewer*` names** (high import-churn, zero operator benefit), but **canon concept-docs** (`reviewer-seat-substrate.md`, `reviewer-occupant.md`, `reviewer-occupant-contract.md`) *may* rename to the new-name slug (e.g., `overseer-*`) since they are prose, low-churn, and their filenames *are* read by humans navigating canon. Recommend renaming the canon trio; deferring the code-module rename to the L3 carve. The operator confirms at ratification.

---

## D3 — Canon cascade (the ADR-282 discipline-rule, applied)

Same shape as ADR-282's `money-truth` cascade: **rename where the prose means the entity; preserve where it means the first Purpose (review) or is a historical artifact.** A discipline rule, propagated, with a grep-gate.

### The discipline rule (added to GLOSSARY, ADR-282 D2 pattern)

> **The ratified entity name (`Overseer` recommended, §D1) is the operator-facing name of the personified judgment seat — the detached entity that owns the operator's mandate and judges against ground truth. `reviewer` persists ONLY as the internal data slug (`role`/`agent_class`/`authored_by` prefix) and as the name of the entity's first Purpose ("independent review of proposed writes"). In canonical docs, say "the Overseer" for the entity, "review" for the verdict-on-a-proposal action. A sentence naming both legitimately ("the Overseer's first Purpose is review of proposed writes") is not a conflation — it is the role-and-its-purpose relationship.**

### Core canon that cascades (entity-name carriers)

`FOUNDATIONS.md` (DP25 — *the anchor*; DP24 stewardship; DP21 formalization; DP14/15 seat≠occupant; Axiom 2 section title), `THESIS.md` Commitment 2, `GLOSSARY.md` (new entity entry + Exceptions additions + discipline rule), the reviewer-canon trio, `agent-composition.md` §3.2.1/§4.4, `LAYER-MAPPING.md`. Version bumps where the doc carries one. Full list + per-doc treatment in the [blast-radius map](../analysis/reviewer-rename-blast-radius-2026-06-07.md) §4.1.

### NOT edited (historical artifacts — ADR-282 D8 + ADR-259 precedent)

The ~50+ historical ADRs that say "Reviewer" (ADR-194, 195, 211, 212, 217, 247, 248, 251, 252, 253, 256, 258, 273, 280, 281, 282, 284, 285, 295, 306, 307, 315, 319, 320, …) are dated artifacts; they stand. The supersession (this ADR) is the record. Optional retroactive vocabulary banners on the highest-traffic four (ADR-194, ADR-315, ADR-319, ADR-320) per the ADR-259 banner pattern — operator's call.

### Grep gate (ADR-282 pattern — post-cascade verification)

```bash
# Canonical docs (excluding historical ADRs + blog) must use the new entity name for the entity:
grep -rn "the Reviewer\b" docs/architecture/ CLAUDE.md   # each remaining hit must mean the *review Purpose*, not the entity
# Code slugs must remain (data-compat):
grep -rn "role='reviewer'\|agent_class.*reviewer\|authored_by.*reviewer:\|REVIEWER_MODEL_IDENTITY" api/  # unchanged
# New entity name appears in canon:
grep -rn "Overseer" docs/architecture/FOUNDATIONS.md docs/architecture/GLOSSARY.md  # positive (ratified entity name)
```

---

## D4 — The published-content / marketing decision (must be made explicitly)

Three **published** blog posts carry "reviewer" in title + slug and are *active positioning*, not just labels:
- *"Name Your Reviewer: Why AI Judgment Should Have A Persona"*
- *"You Don't Need More Models. You Need A Reviewer."*
- *"The Reviewer Seat Is What Single-Agent Architectures Can't Add"*

Per ADR-282 (does-not-edit blog) + ADR-259 (historical-artifact): **published posts are not edited.** They stand as the public record at their date. But they are *evidence about the name itself* — "Reviewer" is the word that already tested in market. Two coherent paths, **the operator must pick one at ratification**:

- **Path α — full rename.** The ratified name (e.g., "Overseer") becomes the entity word everywhere going forward (cockpit + future content + canon). Published posts stand as the historical "Reviewer"-era record. Future blog posts re-position under the new name (or under both — "the Overseer, formerly the Reviewer seat"). Cleanest internally; costs the market recognition the three posts built.
- **Path β — split: keep "Reviewer" public, rename the internal/cockpit entity.** "Reviewer" stays the *marketing/public* word (it tested; the blog narrative is coherent); the rename applies only to the cockpit label + canon. This is *narrower* and preserves market continuity, but re-introduces a LABEL/marketing split (the operator sees one word, the marketing says another) — a mild legibility cost.

**This ADR does not pick** — it is genuinely the operator's strategic call, and it gates how wide the LABEL-rename bucket is. The blog is the single highest-signal input: it is the only place "Reviewer" was *chosen for positioning weight* rather than inherited. (Recommendation if forced: Path α with the canon trio renamed and a one-line "formerly Reviewer" gloss in the GLOSSARY + the highest-traffic blog post's intro updated *as new content, not an edit of the dated post* — but defer to the operator.)

---

## D5 — Stewardship elevation as motivation (recorded, not a new decision)

ADR-319 is the reason the name now carries more weight than when D7 deferred it (full argument: [blast-radius map](../analysis/reviewer-rename-blast-radius-2026-06-07.md) §6). Recorded here so the ratification is made with the full context: **the entity owns and revises intent (DP24), it does not merely review actions — so the name must denote watching-over-and-owning, which is why "Overseer" (watches over + responsible for) is recommended over both the clerical "Reviewer" and the sharper-but-still-judging "Arbiter."**

---

## Migration plan (one atomic LABEL-rename commit + canon cascade — ADR-201/265 shape)

**Single phase, executed AFTER the sequencing gate (§7) opens and the operator ratifies the name.** Per ADR-201 (atomic rename, single commit) + ADR-282 (canon cascade in the same/adjacent commit):

1. **Route + redirect** — `REVIEWER_ROUTE` constant relabel; new deep-link resolves; `?agent=reviewer` 301-redirects (ADR-201 §2 stub); `PROTECTED_PREFIXES` updated (ADR-265 D1).
2. **Frontend LABEL strings** — `ROLE_META` display name + tagline; rendered class labels; `"your Reviewer"` fallback; Constitution-band label; nav/roster/breadcrumb strings. Component *filenames* stay (`Reviewer*.tsx`).
3. **GLOSSARY** — new entity entry; discipline rule (D3); three reviewer slugs added to Exceptions table (D2).
4. **Canon cascade** — FOUNDATIONS (DP25/24/21/14, Axiom 2 section title) + THESIS Commitment 2 + reviewer-canon trio (+ optional filename rename per D-naming-policy) + agent-composition §3.2.1/§4.4 + LAYER-MAPPING. Version bumps.
5. **Grep gate** (D3) + `api/test_adr326_*.py` regression gate asserting: (a) code-slugs unchanged (`role='reviewer'` / `agent_class='reviewer'` / `authored_by="reviewer:"` / `REVIEWER_MODEL_IDENTITY` present); (b) `?agent=reviewer` redirect resolves; (c) new entity name present in FOUNDATIONS + GLOSSARY; (d) no operator-facing surface renders the bare word "Reviewer" as the entity label (the cockpit shows the new name + the occupant persona name).
6. **CHANGELOG** — `api/prompts/CHANGELOG.md` entry (the persona-frame / cockpit-awareness prose that names the entity is a prompt-layer touch).
7. **Marketing decision (D4)** executed per the operator's Path α / β choice — separate from the code commit if Path α (new content, not edits to dated posts).

**Code-module rename** (`reviewer_agent.py` → e.g. `overseer_agent.py`) is **NOT in this migration** — deferred to the ADR-315 D6 L3 package carve, where the import-churn is already being paid.

---

## §7 — Sequencing gate (the explicit dependency)

> **This rename does NOT execute until BOTH of the following have landed on `main`:**
> 1. **The primitive-evolution arc ADR-321–325** — path-native file primitives (321), entity-layer pruning (322), persona-frame collapse finish (323), InferContext dissolution (324), Embed primitive (325). These saturate `reviewer_agent.py`, the primitives registry, `REVIEWER_PRIMITIVES`, the persona-frame sections, and `InferContext`'s identity-inference (which targets `persona/IDENTITY.md`). A rename commit landing mid-arc collides on the same files.
> 2. **The self-writing E2E validation** — saturates the eval core + the reviewer invocation path.

Until the gate opens, this ADR is a settled *design* awaiting a clear runway — the ADR-236 Rule 8 "draft → land just-in-time" discipline applied to a high-blast-radius rename. The [blast-radius map](../analysis/reviewer-rename-blast-radius-2026-06-07.md) §7 re-runs the grep sweep at gate-open time (counts drift). The execution is then a known-quantity single commit + cascade.

---

## What this ADR supersedes / amends / preserves

- **Closes** ADR-320 D7 (de-naming scoped out, deferred to its own ADR — this is that ADR).
- **Completes** FOUNDATIONS Derived Principle 25 (which named the entity "a detached personified judgment seat" but left it unnamed and Reviewer-as-first-Purpose) by giving the entity a name.
- **Motivated by** ADR-319 / Derived Principle 24 (stewardship elevation — the name must now denote ownership).
- **Reuses migration shape from** ADR-201 (layered-naming + redirect), ADR-265 (surface rename + PROTECTED_PREFIXES), ADR-282 (canon cascade + discipline-rule + grep-gate + historical-ADR + does-not-edit-blog exemptions).
- **Preserves** the seat≠occupant split (ADR-315), the occupant persona-name mechanism (ADR-246 — "Simons approved" is *occupant* naming, untouched), all data-compat code-slugs (`role`/`agent_class`/`authored_by`/`REVIEWER_MODEL_IDENTITY`/`persona/` path), the published ABI symbols (ADR-315), the minimal persona-frame (Derived Principle 22), and Singular Implementation (the LABEL moves once; the slug stays once; no dual vocabulary).
- **Does NOT** rename code modules / test files (deferred to ADR-315 D6 L3 carve), edit historical ADRs, or edit published blog posts (D4 decides forward-content strategy separately).

---

## Open questions for ratification

1. **The name** — **Overseer** (recommended) / **Guardian** (fallback, zero connotation risk) / **Second** / operator's own. Elevated options (Steward / Principal / Arbiter) demoted by the plain-language directive. Operator-suggested **Persona** and **Actor** both rejected for collision (§D1 "Operator-suggested candidates"). §D1.
2. **Marketing path** — α (full rename, posts stand) vs β (keep "Reviewer" public, rename internal). §D4.
3. **Canon-trio filename rename** — rename `reviewer-seat-substrate.md` et al. to the new-name slug (e.g. `overseer-*`, recommended) or keep filenames + relabel prose only. §D2 D-naming-policy.
4. **Retroactive ADR banners** — add "formerly Reviewer" banner to ADR-194/315/319/320 (optional, ADR-259 pattern) or rely on supersession-is-the-record. §D3.

---

## Provenance

- Upstream discourse: `personified-judgment-seat-vs-task-harness-2026-06-05.md` §4 (de-naming argument) + §7 (naming open).
- Canon: FOUNDATIONS DP25 (entity = detached personified judgment seat; Reviewer = first Purpose) + DP24 (stewardship/ownership) + DP21 + DP14/15 + Axiom 2 (Purpose-not-Identity; two embodiments); THESIS Commitment 2 (independence = detachment); GLOSSARY (Reviewer entries + Exceptions table); reviewer-seat-substrate.md / reviewer-occupant.md / reviewer-occupant-contract.md (seat ≠ occupant ≠ ABI).
- Precedent ADRs: ADR-201, ADR-265, ADR-282, ADR-251, ADR-259, ADR-315 D6, ADR-320 D7, ADR-319.
- Companion: `reviewer-rename-blast-radius-2026-06-07.md` (the touchpoint map).
