# The recommended agent set — from first principles, against the current code

> **Status**: Recommendation. Builds on `docs/architecture/AGENT-TAXONOMY.md` (the six axes) + the current-state receipts below.
> **The operator's frame**: *"the current agent line-up of scaffolding will be our base agents, meaning, most primitive agents related to different modality like image maker (absorb into designer?), researcher, or alike… from first principles and given our current state of code, what is your recommendation."*
> **Date**: 2026-07-18

---

## 1. The recommendation in one paragraph

**Keep the four base agents exactly as they are — `Sonnet` (think), `Scout` (read), `Critic` (pressure-test), `Designer` (make) — as the permanent base tier, and grow them by DEPTH, never by adding a fifth character for a modality.** "Image maker" is not a base agent; it is a *modality of `make`*, and it belongs *inside* Designer — some of it (SVG charts/diagrams) is already there, the rest (raster images) attaches as a rented capability when it returns. The base tier is the *verbs*; modality lives within a verb; a fifth base agent is warranted only when a member's unmet reach names a genuinely new **verb**, which — from first principles — there is a strong case is **already complete at four**. Above the base tier sit two *different tiers* that are not base agents and must not be confused with them: the **systemic seat** (Freddie, live) and **hired persona agents** (Rung-2, doc-only, deferred).

## 2. Current state — what actually exists (receipts)

| Tier | What it is | State in code today |
|---|---|---|
| **Base agents** (member hands) | the four verbs | **LIVE** — `KERNEL_AGENTS` = {sonnet, scout, critic, designer}, all `member:` attribution |
| **Systemic seat** (management) | Freddie — one per workspace | **LIVE** — `invoke_freddie()`, kernel constants (ADR-414) |
| **Hired persona agents** (judgment) | Rung-2, program hires | **DOC-ONLY** — ADR-382: *"Do NOT build against this… everything that would make a persona agent exist at runtime is still TBD"* |
| **Systemic judgment archetypes** | Auditor / Advocate / Custodian | **NAMED, NEVER SHIPPED** — placeholders across canon, none registered |

**The operator's instinct is correct and the code agrees**: the base tier is the four scaffolding agents. The recommendation is about what that tier *is* and how it grows — not about reaching up into the deferred tiers.

## 3. First principles — why the base agents are VERBS, not modalities

From `AGENT-TAXONOMY.md`: a base agent is typed by *the reason a member reaches for a colleague* — a verb. This is the single axis that survived six revisions, and it survived because it is the only one that is **irreducible**: you cannot decompose "think" into "think about X" without smuggling a domain back in (the ADR-176 error), and you cannot merge "read" and "pressure-test" without losing the distinct *reach* (a member asks Scout to *find*, asks Critic to *break* — different intents, same possible engine).

**Modality is not a reason. It is a *how*, downstream of a verb.** "Make a deck" and "make an image" are the same reach — *make me the thing* — differing only in output format. Typing them as separate agents is **Axis 1 (output shape)**, the very first axis the codebase abandoned (ADR-019→082), because it conflates *what you want done* with *what comes out*.

So the first-principles test for "should image-maker be its own agent?" is one question: **is "make an image" a different REASON a member reaches for a colleague than "make a deck"?** No — it is the same reason (`make`), different modality. Therefore it is a **capability of Designer**, not a fifth agent.

## 4. On "absorb image maker into Designer" — the sharper answer

The operator's instinct is right, and the code makes it *sharper than "absorb"*:

**"Image making" is not one capability — it splits on the text/binary line, and half of it is ALREADY in Designer** (ADR-440:71, verbatim):

> *"HTML-native visual assets — SVG charts, diagrams, icons — are plain-text authoring and therefore IN scope today: the lane writes `./assets/chart.svg` and cites it… RASTER image generation is a rented engine (ADR-417: generation is rented, not owned) — demand-gated, and when wired it lands as settle-then-cite."*

So the precise picture:

- **SVG charts / diagrams / icons** → *plain-text authoring* → **Designer does this today.** No absorption needed; it is already "make."
- **Raster images (generation)** → *a rented engine, currently non-existent* → when it returns (ADR-417 §2a: *"a member-attached connector, never an in-house engine"*), it attaches to **Designer's `make`** via the ADR-463 §3 capability resolver — the same "capability, not vendor" seam we just built for search. Designer asks for "an image"; the kernel names the server (DALL-E, Imagen, whatever). Designer never learns which.

**This is the key structural payoff**: because we already built the capability-not-vendor resolver (ADR-463), "image maker returns" is not a new agent and not new architecture — it is *one row in `services/capabilities.py`* and Designer's posture gaining a line. The taxonomy and the P1 work compose exactly.

**Do NOT** create an "Image Agent." It would be the output-shape axis returning, and it would strand raster-making in a silo while SVG-making stays in Designer — the same modality split across two agents, which is incoherent.

## 5. Is the verb set complete at four? — the one genuine open question

This is the only real first-principles decision left, and the honest answer is: **four is defensible as complete, and the burden of proof is on adding a fifth.**

The candidate verbs, tested against "is this a distinct REACH, or a modality/domain of an existing one?":

| Candidate | A new verb? | Verdict |
|---|---|---|
| **think** | ✅ | Sonnet — reason, judge, hard calls |
| **read** | ✅ | Scout — find, retrieve, with sources |
| **pressure-test** | ✅ | Critic — break it before it costs you |
| **make** | ✅ | Designer — produce the artifact, all modalities |
| ~~research~~ | ❌ | This is `read` + `think` composed, or just `read` with web. Scout already has `WebSearch`. Not a fifth reach — the operator's own "researcher, or alike" resolves *into* Scout. |
| ~~summarize / write~~ | ❌ | `make` (it produces prose) or `think` (it decides what matters). ADR-176's `writer` collapsed for this reason. |
| ~~image-maker~~ | ❌ | modality of `make` (§4) |
| ~~plan / coordinate~~ | ❌ | This is `think` applied to a sequence. ADR-138 deleted `pm` outright for exactly this. |
| ~~monitor / track~~ | ⚠️ | The one *arguable* fifth verb — "watch this and tell me when it changes" is a distinct reach (standing attention, not addressed). BUT: it requires **standing intent** (a wake source), which base agents deliberately do NOT have (they are addressed-only, `member:` hands). A watching agent is therefore **not a base agent** — it is closer to the systemic/judgment tier. So even the strongest candidate resolves *out* of the base set. |

**Conclusion**: the four verbs are the complete set of *addressed member-hand reaches*. Every proposed fifth either (a) composes from the four, (b) is a modality of `make`, or (c) requires standing intent and thus belongs to a different tier. **The base set is complete at four by construction** — not by taste, but because "addressed + member-attributed + no-standing-intent" is a bounded space and these four fill it.

The operator's "researcher, or alike" is the proof of the method working: *researcher* felt like a fifth agent, and on inspection it is `read` (Scout, already web-enabled). The instinct to name it was Axis-4 muscle memory (the ADR-176 roster); the taxonomy resolves it into an existing verb.

## 6. So how does the base tier grow? — DEPTH, on three planes

Not by new characters. By making the four verbs *deeper*:

1. **Capability (the tools plane)** — the ADR-463 P2/P3 work. Scout got `QueryKnowledge` + `WebSearch`; Designer gets raster-image generation when it returns; each verb's *reach* grows within its identity. This is where "image maker" actually lands.
2. **Skill (the instruction plane)** — ADR-464. A member teaches Designer their house style, teaches Scout which sources to trust. The verb stays four; the *competence* accumulates per workspace.
3. **Identity (the member plane)** — the personified widening (already built). A member names their own `make` agent "Maya" with a playful tone. Same verb, member's character. This is the roster growing in *instances*, never in *kinds* — exactly ADR-205's "palette that does not accumulate identity," inverted for the member.

## 7. What NOT to do (the anti-recommendations, from the history)

- **No fifth base character for a modality** (image/video/audio "maker") — Axis 1, abandoned first.
- **No fifth base character for a domain** ("trading agent", "marketing agent") — Axis-4/ICP error (ADR-140), the sharpest-superseded.
- **No base character with standing intent** (a "monitor" that fires unaddressed) — that is a different tier; base agents are addressed hands.
- **Do not reach into the deferred tiers** to populate the base set. Freddie is management, not a member colleague; persona agents are judgment-accountable and gated by the ADR-380 clock. Rendering either as a base agent is the exact category error `LAYER-MAPPING.md` §"Specific clarifications" warns against — *"Same chrome must never imply same kind."*

## 8. The recommended set, stated as canon

**Base tier (member hands, addressed-only, `member:` attribution) — COMPLETE at four:**
- `Sonnet` — **think**
- `Scout` — **read** (the "researcher" reach, web-enabled)
- `Critic` — **pressure-test**
- `Designer` — **make** (all modalities; SVG today, raster when rented returns)

**Growth = depth, not breadth**: capability (tools) · skill (instructions) · identity (member-named instances).

**Above the base tier, NOT base agents** (named here only to keep the boundary sharp):
- Freddie — the systemic management seat (live)
- Persona agents — hired judgment, Rung-2 (deferred, do-not-build)

**A fifth base agent requires**: a member's unmet reach that is a genuinely new *verb* — not a modality, not a domain, not a persona, not a watch. The bar is high on purpose; §5 argues the space is already full.

## 9. One-line statement

**Keep the four verbs as the permanent base tier and grow them by depth — "image maker" is a modality of `make` that belongs inside Designer (SVG already there, raster as a rented capability under the ADR-463 resolver when it returns), "researcher" is `read` and already lives in Scout, and the base set is complete at four not by taste but by construction, because "addressed member-hand with no standing intent" is a bounded space these four verbs fill — while Freddie and hired persona agents remain deliberately above the base tier, different kinds the same chrome must never imply.**
