# ADR-460 — Agents: One Concept, Independent Facts, One Gate

> **Status**: **Accepted** (2026-07-15, operator-ratified in the chat(think) discourse). **Doc-first — no code, no schema, no migration in this commit.** It dissolves a taxonomy (the three AI altitudes), replaces it with independent facts, and relocates the one boundary that was riding on the taxonomy to the gate that already enforces it. The kernel Agent registry it makes buildable is its own commit, gated on the ADR-457 D3 settle verb landing first (§8).
> **Date**: 2026-07-15
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — what an agent *is*) + **Mechanism** (Axiom 5 — the configuration that was masquerading as identity). The correction is itself an Axiom-0 act: a bundle spanning three dimensions is dissolved into the dimensions it spanned.

**Amends**:
- [ADR-408](ADR-408-the-coworking-contract.md) **D2** — the three-altitude table is retired. A1/A2/A3 dissolve into one concept with independent facts. D2's *load-bearing* claim (a member's helper is not a principal) is **preserved and strengthened** — it becomes a fact on the vector, not a rung on a ladder.
- [ADR-411](ADR-411-chat-lanes-and-the-lane-tool-surface.md) **D1/D5** — a lane's `model` pin is re-read as one value of the **configuration** fact, not a property of the container. `LANE_MODELS` is the seed of the Agent registry (§5).
- [ADR-382](ADR-382-persona-agent-seats-the-rung-2-judgment-layer.md) — re-pointed. It is no longer "the Rung-2 *seat*" (an entity class); it is **the consequential-authority fact and its exogenous clock** (§4). Its §3 accountability decision (DP24/DP30 attach to the agent that holds a production mandate) is preserved verbatim — that decision was never about altitude, it was about mandate-holding.
- [ADR-380](ADR-380-the-activation-ladder-and-the-judgment-deferral-line.md) **D1** — the *rung ladder as Identity taxonomy* retires; **D2 (the deferral line) is preserved exactly and promoted**: it was always a statement about the [ADR-307](ADR-307-unified-permission-taxonomy.md) gate, not about a class of entity.

**Preserves** (load-bearing, untouched): ADR-307 (the one consequential gate — this ADR *strengthens* its role), ADR-380 D2 (reversible ships / consequential defers), ADR-380 D4 (the exogenous-clock dogfood discipline), ADR-382 §3 (accountability attachment), ADR-383 (the consistent agent framework — this ADR is its completion, §3), ADR-373/386/431 (principals + grants — an Agent is not a principal unless it attributes as itself), ADR-405 (the witness dial), ADR-402/450 (routing + recipes as kernel data — the pattern this ADR makes its third instance).

---

## 1. Context — the correction

The chat(think) discourse (`docs/analysis/chat-think-three-axes-discourse-2026-07-15.md` §4–8) proposed multi-model orchestration as chat's differentiator, and hedged it with a guard: *"designations are routing facts, never identities — anything more backdoors A3 and unwinds the Rung-2 deferral."* The operator then made two corrections in sequence, and both are the reason this ADR exists.

**Correction 1 — LLM routing is not a layman concept; pre-configured Agents are.**

> "LLM-routing is simply NOT a laymen intuitive concept. Pre-configured Agents IS. thus, we need, per workspace, the registry of agents management where the LLM-routing or model and configuration is out-of-box... Agents are agents, chat rooms are chat rooms, Agent configurations are separate. I think i was diluting the concerns and confusing and creating gray, ambiguous interpretations of that which should be clearly separated and gated."

This is an Axiom-0 diagnosis, not a product preference. The live `lane_meta` bag proves it — `api/routes/lanes.py::create_lane` builds:

```python
lane_meta = {"name": name, "model": req.model}          # ← Mechanism (which engine)
if artifact_path:  lane_meta["artifact_path"] = ...     # ← Substrate/Purpose (ADR-440 D3)
if derive_recipe:  lane_meta["derive_recipe"] = ...     # ← Purpose (ADR-450 D3)
                   lane_meta["derive_source"] = ...
```

Three dimensions in one bag on a Channel-dimension object. The muddiness is structural.

**Correction 2 — question the altitudes themselves.**

> "is that separation and altitude necessary now? A2, A3, can they be dissolved? and thus, we have Agents (that's it), and they may or may not have personas, they may or may not have other governance files, etc."

Yes — with one exception that this ADR spends most of its length protecting (§4).

## 2. D1 — The three altitudes dissolve

**ADR-408 D2's A1/A2/A3 table is retired.** "Altitude" is not a dimension; it is a **bundle** of four facts that vary independently:

- who the act attributes as,
- what engine/tools/posture runs,
- whether it holds standing intent (fires unaddressed),
- whether it may take consequential action without a witness.

A concept that is *partly* Identity, *partly* Mechanism, *partly* Trigger and *partly* Purpose is not a dimension — it is a bundle, and reasoning about the ordinal instead of the facts is the drift Axiom 0 names.

**The evidence that the runtime never had altitudes.** `services/primitives/workspace.py::_caller_class` — the function the ADR-320 lock table branches on — does not know what an altitude is. It branches on the **author prefix**, and for the member's helper it does this:

```python
if caller_identity.startswith("member:"):
    # ADR-411 D4: a lane helper is the MEMBER's embodiment (ADR-408 D2)
    return "operator"
```

**A2 is already dissolved in the gate.** A lane helper is not a class of caller — it resolves to `operator` because it *is* the member. Meanwhile `agent:` *is* a distinct class with its own locked-prefix set. The runtime has always had **two things distinguished by one question**: *does this write attribute to a human, or to itself?* The three-altitude table was a doc-layer fiction over a two-valued fact.

**Ordinals do not compose.** There is no answer to "what is A2.5?" — a helper with a persona but no mandate; a named preset that may schedule itself. Those are coherent configurations with no rung to sit on. Independent facts compose; ladders do not.

**Precedent — this is the third instance of a move this codebase has made twice and been right both times:**
- **ADR-383** ruled Freddie and persona agents are *the same kind of construct* — one universal file structure, differing only in file **content**, not schema. It refused to make MANDATE conditional (every agent has a purpose; Freddie's is the kernel steward-mandate). That is this ADR's model, one order up, already ratified.
- **ADR-380 D2** narrowed "judgment" (too coarse — it was deferring things that were safe to ship) to "autonomy over consequential action" (precise). This ADR performs the same narrowing on `never identities` (§4).

**The new statement:**

> **An Agent is a named, configured entity. Its facts are independent and optional: it may or may not carry a persona; may or may not carry governance files; may or may not hold standing intent. There is no ordinal. Configuration is a vector, not a rung.**

## 3. D2 — The five independent facts

| Fact | Dimension | Range | Where it lives |
|---|---|---|---|
| **Attribution** | Identity (Axiom 2) | `member:{id} via {model}` **or** `agent:{slug}` | `VALID_AUTHOR_PREFIXES`; branched by `_caller_class` |
| **Configuration** | Mechanism (Axiom 5) | engine · tools · posture · token profile | the Agent registry (§5) |
| **Standing intent** | Trigger (Axiom 4) | none (addressed-only) → wake sources | ADR-296 wake sources |
| **Governance files** | Substrate (Axiom 1) | none → persona/mandate/principles | ADR-383 (same schema, different content) |
| **Consequential authority** | **the gate, not the entity** | **witness-first → autonomous** | **[ADR-307](ADR-307-unified-permission-taxonomy.md) `execute_primitive()`** — §4 |

**Attribution is the fact everything correlates with**, because it is the fact the gate already branches on. It is a genuine either/or, not a rung:

- `member:{id} via {model}` — **the member's hands.** Acts under the member's grant; the member's accountability; `_caller_class` → `operator`; the ADR-373 grant consult narrows by the member's `principal_id`. **Not a principal** — no `principal_grants` row, never on the ADR-431 roster.
- `agent:{slug}` — **attributes as itself.** Its own caller class, its own locks, its own accountability (ADR-382 §3: DP24/DP30 attach here).

**"Principal" stays a gated word.** In this codebase a principal is a `principal_grants` row — an entity that attributes as itself, holds its own grant, is subject to the powerbox (ADR-434). ADR-431 is explicit that the chat model is not a principal and never appears on the roster. A named preset that runs as the member's hands **does not become a principal by acquiring a name.** The face is an Agent; the fact is your hands. The room shows `Scout · Gemini` as a participant chip; the ledger says `member:kvk via gemini/gemini-2.5-pro`.

## 4. D3 — The one thing that does not dissolve: the cliff

Among the five facts, four are **dials**. One is a **cliff**:

> *May this Agent take consequential external action without a witness?*

**Every other fact ships on engineering time. This one ships on a clock we do not control.** ADR-380 D2's argument is preserved here verbatim because it was never a taxonomy claim — it is a claim about *what kind of time a thing ships on*:

> Rung 0–1 ship on **engineering time** and have reversible blast radius; Rung 2 has **irreversible blast radius and an uncontrollable clock**... "can a persona be trusted with autonomous capital action" is answered by months of accruing record **that can come out negative; it cannot be compressed by writing better code.**

**So: dissolve the ladder, keep the cliff — and relocate it to where it already lives.** Consequential authority was never an Identity property. It is the **ADR-307 gate** — one gate at `execute_primitive()`. ADR-380 D2 says this outright: *"The line is drawn precisely at the ADR-307 consequential boundary."* The altitude was a shadow that gate cast onto the Identity dimension. **This ADR deletes the shadow, not the gate.** The boundary stays exactly where it is enforced; it stops being duplicated in the wrong dimension.

**D3.a — The cost of dissolution, paid explicitly.** The ladder made the cliff *visible in the vocabulary*. "A3 is deferred" is a sentence a tired engineer at 2am understands; "consequential authority is a field with a range" is a sentence they can fill in wrong. The flat model must buy that safety back **structurally, not documentarily**:

> **The kernel Agent registry row shape has NO field for consequential authority.** Kernel Agents are addressed-only hands *by construction*. The authority is not omitted from the row — it is **unrepresentable** in it. An Agent that would take consequential action is not a registry row with a flag flipped; it requires the ADR-307 gate, a mandate, an autonomy dial, and the record. Make the cliff structural.

**D3.b — The exogenous clock survives (ADR-380 D4).** The dogfood track (alpha-trader, alpha-author) stays running off the critical path so the record accrues. Dissolving the ladder does not stop the clock; it removes the *entity class* the clock was mis-attached to. **The clock attaches to the authority, not to a rung.**

**D3.c — ADR-382 re-pointed.** ADR-382 is no longer "the Rung-2 seat" (an entity class that must be built before persona agents exist). It is **the consequential-authority fact and its clock**. Its §3 accountability decision stands verbatim — that decision attached DP24/DP30 to *the agent that holds a production mandate*, which is a mandate-holding fact, never an altitude fact. Its §4 deferrals (lifecycle, trust model, per-seat substrate) remain deferred and are now readable as *"what must be true before the cliff is crossed"* rather than *"what must be built before an entity class exists."* **ADR-380 §5's vision boundary is unchanged**: consequential autonomy is scoped out of the vision, not merely the build.

## 5. D4 — The Agent registry: kernel-internal first, per-workspace later

The operator's sequencing:

> "yarnnn's internal system and codebase is about providing the base-default agents. we could, if the separation of per-workspace, to common agent config is confusing at first, yarnnn-internalize this for initial codebase and architecture, than expand out further for workspace specific customizations."

This is the ADR-222 kernel-names-the-category discipline and the ADR-450 sequencing, independently re-derived. It is adopted verbatim.

**The registry is the third instance of a twice-ratified pattern.** `LANE_MODELS` (ADR-411 D5) and `DERIVE_RECIPES` (ADR-450) are both kernel-constant registries of pre-configured work-shapes. ADR-450: *"recipes are data, not sub-processes... versioned in this codebase, refined by yarnnn; when [agent-composed] arrives it composes beside kernel recipes, never replacing them."* ADR-402: model routing is *"kernel data, not identity."* **An Agent registry is not new architecture — it is the convergence of two registries the codebase already ratified.** `LANE_MODELS` grows a row shape:

```
{ name, icon, model, posture, tools, token_profile }   # + NO authority field (D3.a)
```

**Cardinality and ownership** (the "may or may not" made concrete): kernel Agents ship as constants — every workspace gets the same base set, out-of-box, zero configuration. Per-workspace customization is a **later widening**, forward-compatible by construction (a workspace-scoped registry composes *beside* the kernel set, never replacing it — ADR-450's rule).

**The layman consequence, which is the point:** nobody routes. You talk to someone. This collapses the capture's routing ladder (§4): rungs (b) *remembered designations* and (d) *auto-routing* largely dissolve — **the Agent is the designation.** What survives is (a) pick who answers and (c) gestures ("have them cross-check"). The ladder's own guard — *deterministic before intelligent* — is satisfied by a registry, not by a classifier.

## 6. D5 — The three objects, separated

The operator's cut, mapped to the axioms and to what exists:

| Object | Dimension | What it is |
|---|---|---|
| **Agent configuration** | Mechanism (Axiom 5) | a registry row — engine, tools, posture, token profile |
| **Agent** | Identity (Axiom 2) | a named, addressable entity — a row instance |
| **Room** (conversation) | Channel (Axiom 6) | the meeting. Its `cast` = which Agents are in it |

**The Conversation object gains justification, and a cleaner field.** The capture's proposed `{scope, cast, bindings}` re-reads as: `cast` is **a list of Agent ids**, not an inline `model → designation` map — an id into a registry beats a map in a bag. **But this ADR does not create that object** (§7): `lane_meta` already carries bindings and has absorbed two extensions (ADR-440, ADR-450) without a migration. The object is the correct end-state *description*; `cast` cannot be specified before the registry exists and `scope: shared` cannot be specified before rooms. **Concrete before abstract** — the deterministic-before-intelligent guard applied to schema.

## 7. What this ADR does NOT do

- **No code, no schema, no migration.** It retires a taxonomy and relocates a boundary. Both are doc-layer facts.
- **It does not create the unified Conversation object.** ADR-411's session-row-plus-metadata is the conversation substrate; it gets amended in place a third time (as ADR-412 and ADR-413 already amended it), when and if `cast` and `scope` are specifiable from evidence.
- **It does not build the Agent registry.** §5 makes it buildable and names its shape; the build is its own commit, sequenced in §8.
- **It does not move the ADR-307 gate**, weaken the witness dial (ADR-405), or grant any Agent consequential authority. It makes that authority *unrepresentable* in the kernel registry (D3.a).
- **It does not make any Agent a principal.** No `principal_grants` change; the ADR-431 roster is untouched.
- **It does not re-open ADR-380 §5's vision boundary.** Consequential autonomy stays out of the vision.

## 8. Sequencing — why the registry is not next

The registry is cheap, high-intuition, and crosses no gate. **It is still not next**, and the reason is the discourse's central finding: **Phase A shipped five parity features; settle — the flagship named by ADR-457 D3, the missing derive organ ADR-401's audit found the connector chain breaks at, the fix for the P4 grounding debt — is still unbuilt.**

A room full of named Agents producing transcripts that never become record is **a better-decorated parity trap.** Pre-configured Agents are a *chassis-class* instinct — they make the surface usable and intuitive, which is right and is Axis-1 work applied to Axis-2's object. They are not the moat. The moat is that the room's output lands in the commons attributed and traceable, and that verb is settle.

**Settle and Agents compose in one direction only.** "Keep this" from a room where two Agents cross-checked each other produces a derived note whose `derived_from` cites a conversation with **multiple attributed voices** — a trace no single-vendor host can render. Settle-then-Agents makes the second more valuable; Agents-then-settle makes the first decorative.

The order:

1. **W0 — instrument the ADR-457 D8 falsifiers.** The chassis no longer contaminates them, and instrumenting *after* settle ships destroys the pre-settle baseline for falsifier 2 ("settle unused → don't GTM-lead with it"). An unbuilt verb reads null; null is not evidence of non-adoption.
2. **Settle** (ADR-457 D3/D4) — the flagship, the derive organ, the P4 fix.
3. **The Agent registry** (§5) — kernel constants, addressed-only, `member:` attribution, no authority field.
4. **Cast in a room** — private scope first (the operator's "single user's cohesive experience"); rooms are the same grammar at shared scope, rehearsed solo.
5. **The Conversation object ADR** — written from evidence, with `cast: [agent_id]`.

## 9. Consequences

- **A vocabulary retires.** "A2 helper" / "A3 agent" / "Rung-2 seat" stop being entity classes. Say instead: *an Agent that attributes as the member* vs *an Agent that attributes as itself*; *an Agent with a mandate* vs *without*; *behind the gate* vs *past it*. Canon that says "Altitude 2 helpers are not principals" re-states as "an Agent attributing as `member:` is not a principal" — same fact, on the vector.
- **The gate gains its proper weight.** ADR-307 was already the one gate; it now carries the deferral line explicitly rather than by proxy through a taxonomy. This is a *concentration* of the safety property, not a dilution.
- **Three ADRs' worth of taxonomy becomes one entity plus one gate that already exists.**
- **The risk, named:** a flat model is easier to fill in wrong than an ordinal. D3.a is the mitigation and it is structural (no authority field in the row) rather than documentary. **A future session that adds an authority field to the kernel Agent registry has violated this ADR** — that is the CI-ratchet-shaped statement, and the ratchet lands with the registry build (§8 step 3), not here.

## 10. One-line statement

**An Agent is a named, configured entity whose facts are independent — attribution, configuration, standing intent, governance files — and there is no ladder; the one fact that is not a dial is consequential authority, which is not a property of the entity at all but the ADR-307 gate, unrepresentable in the kernel registry and gated by a clock we do not own.**
