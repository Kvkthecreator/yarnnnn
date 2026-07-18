# The base agent roster, derived from axioms

> **Status**: First-principles derivation. **Method constraint (operator)**: *"think in a very axiomatic approach, not using prior agent configurations as a benchmark… step back from existing convention and thus given the current multi-LLM routers, multi-principal (both humans and agents) workspace and chatrooms considered, what is the actual base agents roster."*
> **Discipline**: the four-agent roster and the six historical axes are set aside. The base set must **fall out of the axioms + the current substrate**, and land wherever they land — four, three, five, or a different shape.
> **Date**: 2026-07-18

> **⚠ Correction (2026-07-18, operator) — DERIVE is an operation but NOT an agent.** The derivation below concluded "add a DERIVE base agent." **Withdrawn.** The flaw: §1 defines a base agent as an **ADDRESSED** member-hand, but DERIVE is produced by an *un-addressed gesture* — settle is `POST /api/lanes/{id}/settle`, *"the member's gesture, NOT a model capability… fires only on a human act"* (ADR-457 D3 / settle-spec, verbatim). You do not *talk to* a Distiller; you hit "keep this" on a conversation and the kernel derives. I mapped the substrate's three revision-kinds to agents 1:1, but `derivation` is produced by a **gesture the member performs ON a lane**, not by an addressee. So the operation is real (and the roster's coverage of it — via settle — is real); the *agent* is not. **Corrected roster: THREE addressed base agents (Acquire · Reason · Produce) + settle as the derive gesture + Critic as a posture over Reason.** The "four operations" analysis was right about the operation *space* and wrong about which operations are *agents* — the addressed/un-addressed line (a Trigger-dimension fact §1 fixed but §3 forgot to apply) is the cut. See §4 + §7, corrected inline.

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

4. **DERIVE** — *turn raw arrivals into cited understanding.* Take what `observation` brought in and make the `derivation` that cites it. Substrate: raw→derived on the ledger. Purpose: make-sense-of. Output: `derivation` revisions with `derived_from`. **Real operation, but NOT an addressed one** (see the correction banner): it is performed by **settle — a member GESTURE on a lane**, not by a colleague you address. The perception→substrate cycle (DP27·DP32·DP31·DP34) needs this operation and ADR-401 found *"the connector chain breaks at derive"* — but the fix is the **settle gesture** (ADR-457 D3), which exists, not a Distiller *agent*, which would violate the addressed-only base-agent definition (§1). The operation is covered without an agent.

## 4. Where this lands — and why it is NOT "the current four re-derived"

Mapping the derivation onto the current roster:

| Axiomatic operation | Addressed? | Current coverage | Verdict |
|---|---|---|---|
| **ACQUIRE** | yes | Scout (→ **Researcher**) | ✅ agent |
| **REASON** | yes | Sonnet (→ **Thinker**) | ✅ agent |
| **PRODUCE** | yes | Designer | ✅ agent |
| **DERIVE** | **NO — a gesture** | **settle** (`POST /lanes/{id}/settle`) | ✅ covered, but NOT an agent |
| — | (posture over Reason) | Critic | ⚠️ not an operation — a character |

**Two findings, corrected:**

**(a) DERIVE is covered — by a gesture, not an agent (operator correction).** The original draft said "the roster is MISSING a DERIVE agent." Wrong: DERIVE is *un-addressed*, so it is not an agent-shaped operation at all. It is performed by **settle** — a member gesture on a lane (ADR-457 D3), which exists. The perception cycle's derive stage being broken (ADR-401) is a reason to *finish settle's wiring*, not to add a Distiller colleague. The three revision-kinds do NOT map to three agents 1:1: `observation` and `authored` are produced by *addressed* acts (agents), `derivation` by an *un-addressed* one (a gesture). The addressed/un-addressed line is the cut the 1:1 mapping missed.

**(b) Critic is NOT a primitive operation — it is REASON pointed adversarially.** "Pressure-test" decomposes: it is REASON (judgment) with a *stance* (find the hole). Axiomatically, a stance is a **posture/skill**, not a distinct operation — it touches nothing REASON doesn't, produces nothing REASON doesn't. Critic is a *specialization of think*, exactly as "researcher" was a specialization of read. It earns its place on the roster **as a character, not as a base operation** — which is a real distinction: the base OPERATIONS are four (acquire/reason/produce/derive), and Critic is a *fifth roster entry that is a posture over an operation*, not a fifth operation.

## 5. The multi-LLM / multi-principal / room facts — do they change the answer? (No — and that is load-bearing)

The operator named three substrate facts to derive against. Tested each:

- **Multi-LLM routers** — changes *which engine* serves an operation, never *what operations exist*. ACQUIRE served by Gemini or GPT is still ACQUIRE. The router is a Mechanism-dimension fact; the base operations are Purpose-dimension. **Orthogonal — confirmed by the whole ADR-463 capability-not-vendor work: the agent asks for an operation, the kernel picks the engine.**
- **Multi-principal (humans + agents)** — changes *who attributes*, never the operation. A base agent is `member:` by construction (§1); a *different* principal (a hired judgment agent) is a different fact-cluster with its own operations (it can go consequential-external). **The multi-principal fact defines a tier ABOVE the base set, it does not add or remove base operations.** A second human's base agents are the same four operations under their grant.
- **Chatrooms** — ADR-460 is explicit: *"Agents are agents, chat rooms are chat rooms."* A room is a **Channel-dimension** object (its members = which agents are in it). Putting Scout in a room with two humans does not change what Scout *does* — it changes *where the conversation happens*. **A room composes base agents; it does not define new ones.** The room is the meeting; the base agents are who you can invite; the operations are what each does when addressed.

**The load-bearing conclusion**: none of the three named facts touches the base-operation derivation, because all three live on dimensions the base-agent fact-cluster holds fixed or orthogonal (Mechanism, Identity-as-tier, Channel). **The base roster is derived purely from Purpose × Substrate for an addressed member-hand — and that is a small, closed space.**

## 6. The answer — the axiomatic base roster

**Four operations — but only three are ADDRESSED (agents); the fourth is a gesture:**

| Operation | Reason to address it | Substrate contract |
|---|---|---|
| **ACQUIRE** | "find / bring into view" | reads commons + world; may land `observation` |
| **REASON** | "think this through / judge" | reads only; narration out; no artifact |
| **PRODUCE** | "make the thing" | lands `authored` revisions |
| **DERIVE** | "make sense of what came in, with citations" | lands `derivation` revisions + `derived_from` |

**Plus N POSTURES over those operations (roster entries that are characters, not operations):**
- **Critic** = REASON + adversarial stance. Legitimate roster entry; not a base operation.
- Any future "researcher who knows my book", "editor", etc. = a posture/skill over an operation (ADR-464 skills, member-authored).

Note DERIVE has no "reason to address it" cell that reads naturally — because you don't address it; you gesture it (settle). That absence in the table *is* the tell that it is not an agent.

**So the honest axiomatic answer to "what is the actual base agent roster":**

> **There are FOUR base OPERATIONS but only THREE are ADDRESSED, and only addressed operations are agents: Acquire · Reason · Produce. The fourth operation, Derive, is real but un-addressed — it is the settle GESTURE, not a colleague. So the base AGENT roster is THREE (Acquire/Reason/Produce), the current registry ships exactly those three (as Scout/Sonnet/Designer), and its fourth entry Critic is a posture over Reason, not a base agent. The registry's cardinality was wrong in BOTH directions: it listed Critic (a posture) as a base agent and it would have been wrong to add Derive (a gesture) as one. The clean count is three agents + one gesture + open-ended postures.**

## 7. What this says to do (and what it does not)

**The recommendation that falls out** (corrected per the operator, 2026-07-18):

1. **Do NOT add a Derive agent.** Derive is covered by settle (a gesture); adding a Distiller colleague would violate the addressed-only base-agent definition. What the perception-cycle break (ADR-401) calls for is *finishing settle's wiring*, not a new agent. **The base agent roster is complete at THREE addressed operations** — Acquire · Reason · Produce.
2. **Re-understand Critic as a posture, not a base agent.** It stays on the roster surface (a member reaches for "break this" as readily as "think this"), but canon should record it as *Reason adversarially postured* — so the next "should we add X?" is asked correctly: is X an addressed *operation*, an un-addressed *gesture*, or a *posture* over an operation?
3. **The base AGENT set is closed at three; operations are four (one is a gesture); postures are open.** This is the clean version of the completeness question earlier docs botched: *addressed operations* are closed and derivable (three); *gestures* are their own category (settle); *postures* are unbounded and member-owned (Critic + skills, ADR-464).

**What it does NOT say**: it does not touch the judgment tier (persona agents can go consequential-external — a different fact-cluster) or Freddie (management, kernel-constituted). Those are not base agents and their roster is a separate axiomatic question.

## 8. One-line statement

**Deriving from the axioms rather than the roster: a base agent is an ADDRESSED, member-attributed hand, so the base AGENT roster is the addressed operations — Acquire (read in) · Reason (judge) · Produce (write out) — which is exactly THREE, and the current registry ships exactly those three (Scout→Researcher · Sonnet→Thinker · Designer); the fourth operation, Derive (make sense of what came in, cited), is REAL but UN-ADDRESSED — it is the settle gesture, not a colleague — and Critic is not an operation at all but a posture over Reason; so the clean answer is three base agents + the settle gesture + open-ended postures, and the multi-LLM, multi-principal, and room facts change engine, tier, and channel respectively and touch this not at all, because the base agents live on Purpose×Substrate-for-an-addressed-hand while those three live on the dimensions the base fact-cluster holds fixed.**
