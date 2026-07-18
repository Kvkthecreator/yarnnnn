# The base agent roster, derived from axioms

> **Status**: First-principles derivation. **Method constraint (operator)**: *"think in a very axiomatic approach, not using prior agent configurations as a benchmark… step back from existing convention and thus given the current multi-LLM routers, multi-principal (both humans and agents) workspace and chatrooms considered, what is the actual base agents roster."*
> **Discipline**: the four-agent roster and the six historical axes are set aside. The base set must **fall out of the axioms + the current substrate**, and land wherever they land — four, three, five, or a different shape.
> **Date**: 2026-07-18

---

## 1. What a base agent IS, reduced to its irreducible facts

Before asking *how many* or *which*, fix *what one is* — from the fact-vector (ADR-460 / LAYER-MAPPING), not from a job title. A **base agent** is the specific point in the fact-vector where:

- **Attribution** = `member:{id} via {model}` — it is *the member's hands*, not a principal (ADR-460: *"a named preset that runs as the member's hands does not become a principal by acquiring a name"*).
- **Standing intent** = none — it acts *only when addressed*. It has no wake source; it never fires on its own.
- **Governance files** = none — no mandate, no persona-of-its-own beyond a posture.
- **Consequential authority** = none — the cliff is off the entity, at the ADR-307 gate. A base agent **cannot cross the read_only→consequential line into the world** (it can write the commons, which is member-attributed and reversible; it cannot take consequential *external* action).

**So the irreducible definition, axiomatically:**

> **A base agent is an ADDRESSED, MEMBER-ATTRIBUTED actor whose entire action space is (a) reading the commons and the world, and (b) producing revisions into the commons — nothing consequential-external, nothing standing.**

Everything else — persona, mandate, tenure, standing attention, outward action — is a *different fact-cluster* (judgment agents, Freddie) and therefore **cannot be a base agent by construction**. This is not a taste boundary; it is the fact-vector's own cut.

## 2. The move the operator's reframe forces: derive from the ACTION SPACE, not from personas

The historical error (all six axes) was typing agents by *some property of the worker* — its output, its platform, its domain, its cognitive style. The axiomatic move is to type the base set by **the irreducible operations an addressed member-hand can perform over the commons**, because *that* is what the fact-vector fixed and everything else varies.

The substrate names its own operations. Axiom 1's revision ledger (`revision_kind`, ADR-423/448) records exactly three kinds of act on the commons:

| `revision_kind` | The act | What it is |
|---|---|---|
| **`observation`** | a raw arrival is retained | reality *enters* — attributed, un-rewritten (DP32) |
| **`authored`** | an ordinary revision | the member/agent *produces* new state |
| **`derivation`** | a derived act citing its sources | the workspace *makes sense of* what entered (DP31/DP32) |

**This is the substrate telling us the base action space.** An addressed member-hand, acting over this ledger, can do exactly a bounded set of things — and the base roster is the set of *irreducible reasons to invoke one*, where "irreducible" means: cannot be decomposed into the others, and cannot be merged with another without losing a distinct member intent.

## 3. The derivation — the irreducible operations

Start from the fact that a base agent touches the commons and the world through the `read_only` / `authored` / `derivation` operations, and ask: **what are the distinct member INTENTS these serve that cannot collapse into each other?**

Run the four axes that actually vary for an addressed member-hand (the six dimensions, minus the two the fact-cluster fixes — Identity is `member:`, Trigger is addressed):

- **Substrate (what it touches)**: the commons (files/revisions) · the world (perception, `WebSearch`/watches) · a *specific claim* (verify against source).
- **Purpose (why)**: to *acquire* understanding · to *test* understanding · to *produce* state.
- **Mechanism (how)**: retrieve (deterministic-leaning) · reason (judgment) · compose (production).
- **Channel (where output lands)**: back to the member (narration) · into the commons (a revision).

Crossing these, the **irreducible member intents** — the ones that survive "can this be decomposed or merged?" — are:

### The derivation yields FOUR primitive operations, and they are NOT the current four

1. **ACQUIRE** — *bring the world/commons into view.* Read files, search the commons semantically, search the web, resolve a source. Substrate: world+commons. Purpose: acquire. Output: narration + `observation`/`authored` into the commons. **Irreducible**: nothing else brings external state in; every other operation presupposes state is already in view.

2. **REASON** — *turn state into judgment.* Think a problem through, decide what matters, weigh, conclude. Substrate: what's in view. Purpose: acquire *understanding* (not state). Output: narration. **Irreducible**: it produces no artifact and touches nothing external — it is the pure judgment operation, and it is what everything else is *for* or *checked by*.

3. **PRODUCE** — *turn judgment into an artifact in the commons.* Compose the deck, the doc, the note; author the revision; make the thing. Substrate: the commons. Purpose: produce state. Output: `authored` revisions. **Irreducible**: it is the only operation that lands new authored state; every artifact the member keeps came through it.

4. **DERIVE** — *turn raw arrivals into cited understanding.* Take what `observation` brought in and make the `derivation` that cites it — the settle-shaped act, the distillation, the "what does this mean and where did it come from." Substrate: raw→derived on the ledger. Purpose: make-sense-of. Output: `derivation` revisions with `derived_from`. **Irreducible — and this is the one the current roster MISSES**: it is neither pure reasoning (it lands cited state) nor pure production (its input is *raw arrivals*, and its contract is *citation*, DP31/DP32). It is the operation the whole perception→substrate cycle (DP27·DP32·DP31·DP34) exists to perform, and ADR-401's audit found *"the connector chain breaks at derive."*

## 4. Where this lands — and why it is NOT "the current four re-derived"

Mapping the derivation onto the current roster:

| Axiomatic operation | Current agent | Match? |
|---|---|---|
| **ACQUIRE** | Scout (read) | ✅ clean |
| **REASON** | Sonnet (think) | ✅ clean |
| **PRODUCE** | Designer (make) | ✅ clean |
| **DERIVE** | — | ❌ **absent** |
| — | Critic (pressure-test) | ⚠️ **not a primitive operation** |

**Two findings the operator's pushback predicted:**

**(a) The roster is MISSING a base operation: DERIVE.** Settle is *the* member-facing instance of it (ADR-457 D3 made it a member gesture, not a primitive) — but there is no *agent* whose reason-to-exist is "make sense of what came in, with citations." The substrate has the `derivation` revision-kind, the `derived_from` edge, and the DP31/DP32 citation contract, and **no colleague you address to do it.** This is not a nice-to-have; it is the operation the entire perception field was built to serve, and its absence is why "the connector chain breaks at derive." **The axioms say there should be a DERIVE agent, and the substrate is already shaped for it.**

**(b) Critic is NOT a primitive operation — it is REASON pointed adversarially.** "Pressure-test" decomposes: it is REASON (judgment) with a *stance* (find the hole). Axiomatically, a stance is a **posture/skill**, not a distinct operation — it touches nothing REASON doesn't, produces nothing REASON doesn't. Critic is a *specialization of think*, exactly as "researcher" was a specialization of read. It earns its place on the roster **as a character, not as a base operation** — which is a real distinction: the base OPERATIONS are four (acquire/reason/produce/derive), and Critic is a *fifth roster entry that is a posture over an operation*, not a fifth operation.

## 5. The multi-LLM / multi-principal / room facts — do they change the answer? (No — and that is load-bearing)

The operator named three substrate facts to derive against. Tested each:

- **Multi-LLM routers** — changes *which engine* serves an operation, never *what operations exist*. ACQUIRE served by Gemini or GPT is still ACQUIRE. The router is a Mechanism-dimension fact; the base operations are Purpose-dimension. **Orthogonal — confirmed by the whole ADR-463 capability-not-vendor work: the agent asks for an operation, the kernel picks the engine.**
- **Multi-principal (humans + agents)** — changes *who attributes*, never the operation. A base agent is `member:` by construction (§1); a *different* principal (a hired judgment agent) is a different fact-cluster with its own operations (it can go consequential-external). **The multi-principal fact defines a tier ABOVE the base set, it does not add or remove base operations.** A second human's base agents are the same four operations under their grant.
- **Chatrooms** — ADR-460 is explicit: *"Agents are agents, chat rooms are chat rooms."* A room is a **Channel-dimension** object (its members = which agents are in it). Putting Scout in a room with two humans does not change what Scout *does* — it changes *where the conversation happens*. **A room composes base agents; it does not define new ones.** The room is the meeting; the base agents are who you can invite; the operations are what each does when addressed.

**The load-bearing conclusion**: none of the three named facts touches the base-operation derivation, because all three live on dimensions the base-agent fact-cluster holds fixed or orthogonal (Mechanism, Identity-as-tier, Channel). **The base roster is derived purely from Purpose × Substrate for an addressed member-hand — and that is a small, closed space.**

## 6. The answer — the axiomatic base roster

**Four primitive OPERATIONS (the irreducible base — derived, not assumed):**

| Operation | Reason to address it | Substrate contract |
|---|---|---|
| **ACQUIRE** | "find / bring into view" | reads commons + world; may land `observation` |
| **REASON** | "think this through / judge" | reads only; narration out; no artifact |
| **PRODUCE** | "make the thing" | lands `authored` revisions |
| **DERIVE** | "make sense of what came in, with citations" | lands `derivation` revisions + `derived_from` |

**Plus N POSTURES over those operations (roster entries that are characters, not operations):**
- **Critic** = REASON + adversarial stance. Legitimate roster entry; not a base operation.
- Any future "researcher who knows my book", "editor", etc. = a posture/skill over an operation (ADR-464 skills, member-authored).

**So the honest axiomatic answer to "what is the actual base agent roster":**

> **The base roster is the FOUR PRIMITIVE OPERATIONS — Acquire · Reason · Produce · Derive — of which the current registry ships three (Scout/Sonnet/Designer) and MISSES one (Derive), while its fourth entry (Critic) is a posture over Reason, not a primitive operation. The count "four" was accidentally right and structurally wrong: it had the right cardinality with the wrong members.**

## 7. What this says to do (and what it does not)

**The recommendation that falls out** (distinct from the prior doc's — this is derived, not defended):

1. **Add a DERIVE base agent.** Its reason-to-exist is the operation settle performs, personified: "make sense of what came in, cite the source." The substrate is already built for it (`revision_kind='derivation'`, `derived_from`, DP31/DP32); ADR-401's audit says the chain breaks exactly here. This is the missing primitive, and it is the one with the strongest first-principles claim of anything on the board.
2. **Re-understand Critic as a posture, not a peer.** It stays on the roster (a member reaches for "break this" as readily as "think this"), but canon should record it as *REASON adversarially postured* — so the next "should we add X?" question is asked correctly (is X an operation, or a posture over one?).
3. **The base OPERATIONS are closed at four** — Acquire/Reason/Produce/Derive exhaust "addressed member-hand over the commons" (read-in / judge / write-out / make-sense-of-what-came-in). **Postures are open-ended** (Critic, and member-authored ones via skills). This is the clean version of the completeness question the prior doc botched: *operations* are closed and derivable; *postures* are unbounded and member-owned.

**What it does NOT say**: it does not touch the judgment tier (persona agents can go consequential-external — a different fact-cluster, a different derivation) or Freddie (management, kernel-constituted). Those are not base agents and their roster is a separate axiomatic question.

## 8. One-line statement

**Deriving from the axioms rather than the roster: a base agent is an addressed, member-attributed hand whose action space is exactly the substrate's own three revision-kinds plus reasoning, so the base roster is the four PRIMITIVE OPERATIONS an addressed member-hand can perform — Acquire (read in) · Reason (judge) · Produce (write out) · Derive (make sense of what came in, cited) — and the current registry has the right count for the wrong reason: it ships three of these, misses Derive (the operation settle performs and the connector chain breaks at), and lists Critic, which is not a primitive operation at all but a posture over Reason; the multi-LLM, multi-principal, and room facts change engine, tier, and channel respectively and touch the base-operation derivation not at all, because operations live on Purpose×Substrate while those three live on the dimensions the base fact-cluster holds fixed.**
