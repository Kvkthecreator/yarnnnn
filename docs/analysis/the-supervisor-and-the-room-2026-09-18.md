# The supervisor and the room — a coordinator holds the memory and routes the threads

*What a member briefs, where parallel work lives, and why the room we already built has two tenants.*

> **Status**: Analysis (2026-09-18). **No ADR rides this document.** It records a discourse and derives a frame; it decides nothing about mechanism, schema or surface. An implementation ADR would cite it.
> **Authors**: KVK (operator) + Claude (collaborator)
> **Hat**: A (system canon). Vocabulary: operator, member, workspace, substrate, agent, lane, cast, grant, declaration.
> **Method**: derived from the member's chair and from two named market benchmarks, then collision-checked against the record in §7 — including two prior deletions this frame reopens.
> **Origin**: the operator's re-sequencing call, 2026-09-17→18: *"i think i made a mistake in the prioritization… instead of a app builder, i've should've focused efforts in scaffolding a supervisor agent and its respective app"*, with the explicit instruction that **prior deletions are not a reason not to try again**, and a follow-on naming the room: *"if we can actually re-surface similar group chat concept here."*

---

## 1. The correction this document starts from

An earlier pass in this discourse (2026-09-17) assessed the same proposal and concluded *"the thing you're describing needs no being at all."* It reached that by reading the deletion record — ADR-610, ADR-639 — and treating it as settled.

**That was the wrong move, and naming why is the beginning of the frame.**

ADR-639 deleted a Supervisor that was, in its own words, *"a posture string — no code branched on its slug."* The audit found strings was **seven things wearing one name** and that none of them dissolved into an agent. Every word of that is still true.

But it is a verdict on a **mechanism**, not on a **concept**. And the mechanism it judged had nothing to coordinate:

> **YARNNN has never had parallel work to supervise.** There was no set of concurrent threads, no shared context between them, and no routing question. A supervisor over *one desk's declarations* is a face on a filing cabinet. The deletion was correct for that, and says nothing about a coordinator over many live threads.

⭐ **The rule this yields, and it generalises past this document**: a deletion closes the mechanism it measured. Re-opening requires new evidence, not a new mood — and the evidence here is that the thing to be coordinated now exists and did not before (§3).

---

## 2. The two benchmarks, read for structure rather than features

The operator named two, and their convergence is the signal — they are different companies solving the same shape.

**Claude Projects, redesigned** ([claude.com/blog/projects-redesigned](https://claude.com/blog/projects-redesigned)). The copy is unusually precise about the architecture:

- *"brief Claude in the project the way you'd brief a **chief of staff** and it **routes** work to new or pre-existing threads"*
- each thread is *"a full Claude Code cloud session working on its own branch and copy of the repo"*
- *"every thread now adds to and draws from a **shared memory**, reducing the need for complex prompt engineering"*
- a **project library** *"collects the files you add and the artifacts produced by Claude"*
- *"One project across a week. Each request opens a thread on the right; the memory, the decisions, and the results build underneath."*

**Grok Bot** ([x.ai/news/introducing-grok-bot](https://x.ai/news/introducing-grok-bot)). A chief-of-staff bot delegates to named specialists with permanent narrow roles; several bots sit **in the same thread** and pass work between one another; *"shared memory files keep everyone aligned."*

### 2.1 The four primitives both have

| | Claude Projects | Grok Bot | The generic name |
|---|---|---|---|
| Who you brief | the main project chat | the chief-of-staff bot | **the coordinator** |
| Where work happens | a thread (own session, own branch) | a specialist bot's turn | **the thread** |
| What persists across both | shared memory | shared memory files | **the commons of the concern** |
| Where outputs land | the project library | — | **the library** |

⭐ **The load-bearing verb is "routes."** The coordinator does not do the work and holds no authority over the workers. It decides *which thread this belongs to*, opens one when none fits, and keeps the context that stops the member re-briefing. **A dispatcher with memory** — which is a much smaller object than "a manager," and crucially a different one.

### 2.2 What is NOT in either benchmark

Worth stating, because the word "chief of staff" imports it and the architecture must not:

- **No authority over the specialists.** Nothing says the coordinator may grant, promote, silence or over-rule a worker. It assigns *work*, never *rights*.
- **No autonomy of its own.** It routes when briefed. Neither product describes a coordinator that wakes up and decides something unprompted.
- **No second identity layer.** The specialists are the same kind of thing whether a coordinator is present or not.

**This is the whole reason the pattern is architecturally admissible here**, and §7.1 shows it is the distinction ADR-603 D3 already drew and got right.

---

## 3. What YARNNN already has — measured, not assumed

Every number below is from live production data, 2026-09-18.

| The benchmark's primitive | YARNNN's | State |
|---|---|---|
| thread | **the lane** (a bound conversation with a cast) | ✅ built, **178 live** |
| the room is multi-party | **ADR-626 / ADR-495** — cast is principal-agnostic | ✅ ratified + built; **effectively unused** |
| library | **`workspace_files`** — attributed, versioned, revertible | ✅ built, and **stronger than the benchmark's** |
| shared memory | `agents/{slug}/memory/` | 🔴 **address only — no writer, no reader** |
| the coordinator / routing | — | 🔴 **nothing** |

### 3.1 Threads exist, in quantity, and they are a flat list

178 conversations across 9 workspaces. **139 in a single workspace.** By binding:

```
text 71 · (unbound) 96 · images 5 · radar 3 · slides 2 · blogger 1
```

⭐⭐⭐ **96 of 178 are bound to nothing at all** — more than half. A conversation with no binding is a thread with no concern: it cannot be grouped, cannot be routed to, and is findable only by scrolling a list that is 139 long in the workspace that uses the product most.

**This is the benchmark's problem statement, arrived at independently by usage.** Projects' answer is that each request opens a thread *under a project*, and the project is what you brief. YARNNN has the threads and no container above them.

### 3.2 The room is already multi-party, and nobody is using it

ADR-626 (Ratified 2026-09-01) made the room principal-agnostic — humans and agents in one cast, and the agent can *see* who is in it. ADR-495 made the cast the single authority on who replies. Both are live.

Measured: **302 cast rows over 164 conversations. Exactly 2 conversations hold more than one agent.**

The primitive the operator asks to "re-surface" is therefore **not missing — it is unused**, and the distinction matters enormously for what to build:

> **A capability nobody reaches for is a discoverability problem or a purpose problem, never a mechanism problem.** Building a second multi-party mechanism beside this one would be the ADR-562 second-home drift.

⚠️ Two agents in a room is *possible* today and has no *reason*. The coordinator supplies the reason: a room where the chief of staff and a specialist are both present is the routing conversation made visible.

### 3.3 Shared memory is the one genuine hole, and it was already named

`agents/{slug}/memory/` is declared (`workspace_paths.py`), protected (`_is_foreign_agent_home`), and served as an address on the `/agents` payload. **Nothing writes it and nothing reads it into a turn.**

This is not a new finding — ADR-653 §1.5 and §9.1 say it in the operator's own canon, and flag it as *"the load-bearing open question"*:

> *"The frame promises an agent that accumulates judgment about this specific work. That accumulation does not exist today."*

Projects makes exactly this the headline feature — *"reducing the need for complex prompt engineering"* — which is the market confirming the gap YARNNN's own ADR had already identified and deferred.

### 3.4 The library is the half we are ahead on

Claude's project library *"collects the files you add and the artifacts produced by Claude."* That is `workspace_files` with attribution, version history, revert, `derived_from` edges and export — shipped since ADR-209/427.

⭐ **Worth stating plainly because it inverts the usual posture**: on three of four primitives YARNNN is level or ahead. The missing pieces are **memory** and **routing**, and neither is a substrate question.

---

## 4. What the member actually wants, from the chair

Strip the product names. A member with 139 conversations has a real problem and it is not "I need an agent":

1. *"I don't want to re-explain the context every time."* → **memory**
2. *"I don't want to decide which of 139 chats this belongs in."* → **routing**
3. *"I want to see everything about this concern in one place."* → **the container** (which ADR-653 built and called an app)
4. *"I want someone who knows what's going on across it."* → **the coordinator**

⭐ **Items 3 and 4 are the same object seen from two sides.** The container is where the work is; the coordinator is who holds it. That is not a coincidence — it is why both benchmarks ship them together and neither ships one without the other.

**A container with no coordinator is a folder.** (This is ADR-653 §9.8's "generic apps are worse than none", restated: the app frame shipped the container and left the resident resting.)
**A coordinator with no container is a chatbot with opinions about your other chats.**

---

## 5. The frame

> **A supervisor is an app's resident once the app has threads and memory. It holds the shared memory of one concern, it routes work into threads, and it is met in a room that may hold anyone. It does the work of no thread and holds authority over no one; what it decides is WHERE work goes, never WHO may do what.**

Unpacked into the four claims the mechanism must honour:

**5.1 The coordinator is not a species.** It is a member app's agent (ADR-653 D2/R4) that has gained two things: memory to hold and threads to route into. No new row shape, no new register, no `kernel` variant. ⭐ This is what makes the frame admissible against ADR-610's *"a being is someone a member MEETS"* — the member meets their app's resident, and always did.

**5.2 The thread is the lane, unchanged.** A thread is a bound conversation with a cast. Under this frame it gains one thing: **a container it belongs to.** The 96 unbound conversations are the evidence that the container is the missing edge.

**5.3 Memory is the concern's, not the being's.** Projects says *"every thread adds to and draws from a shared memory"* — the memory belongs to the **project**, and threads share it. YARNNN's address is `agents/{slug}/memory/`, per-BEING. Under R4 (one member app, one agent, both directions) those coincide exactly. ⚠️ **That coincidence is load-bearing and should be examined rather than relied on** — §8.2.

**5.4 Routing is authority over DECLARATIONS AND LANES, never over beings.** *"Supervisor hires Editor"* is authority over a being — forbidden, unrepresentable (ADR-460 D3.a). *"The coordinator opens a thread about X, and that thread's resident does the work"* is the sentence ADR-603 D3 already ruled admissible. The cliff is untouched, and §7.1 shows this is a re-application of an existing ruling rather than a new exception.

---

## 6. Why the room is the right surface for it

The operator's second instruction — re-surface the group-chat concept — lands exactly here, and the benchmark supports it.

**Grok's shape is the tell**: several bots *in the same thread*, passing work between one another. Not a dispatcher UI. Not a queue. **A room where more than one party is present.**

YARNNN has that room already (§3.2) and it is idle. The coordinator gives it its first real tenant:

- the member briefs **in the room**, the way they already talk to any resident;
- the coordinator routes, and the routing is **visible as conversation** rather than as a hidden dispatch;
- a specialist can be present in the same room when the work needs two.

⭐ **The design consequence**: there is no new "coordinator UI" to invent. There is a room that already renders multi-party casts, and an app surface (ADR-653 D3.c, shipped 2026-09-17) whose band 3 shows the concern's state. The container's pane and its room are the two halves of one screen — which is the shape ADR-653 §9.2 already ruled for an app's bound lane.

⚠️ **And the honest risk**: ADR-626 shipped a multi-party room and 2 of 164 conversations use it. A frame that assumes members will want several parties in one room is making the same bet that has not yet paid. §8.4.

---

## 7. The collision check — what this reopens

**Two deletions and one sequencing call.** Each is named with the reason, per the operator's instruction that prior deletes are not themselves an argument.

### 7.1 ADR-639 (and ADR-610) — the Supervisor seat

**What was deleted**: a Supervisor that was a `resident` field's value over the strings desk; a Keeper that was an executor slot wearing a character.

**Why the deletion still stands**: both were *"a being is someone a member MEETS"* violations — rows that promised a concept and delivered a slot. ADR-610's reasoning is worth preserving verbatim: *the name promised the concept; the row delivered an executor slot, and that gap recruits responsibilities the row cannot hold.*

**What is different now, and it is a fact rather than a preference:**

| | The deleted Supervisor | The coordinator |
|---|---|---|
| What it coordinates | declarations on **one desk** | **threads** — 178 live, 96 unbound |
| Does the member meet it? | no — it was a receipt-signer | **yes** — it is the app's resident, briefed in a room |
| What it holds | nothing (a posture string) | **the concern's memory** |
| Its authority | none, and nothing to have authority over | none — routing is over lanes, not beings |

⭐⭐⭐ **The deleted Supervisor failed the "does a member meet it" test. This one passes it by construction**, because it is the resident of an app the member opened. That is not a workaround; it is the rule doing its job.

⚠️ **The name should be re-examined, and ADR-603 D3 said so first**: *every other resident is named for a CRAFT (Editor · Designer · Blogger) while a manager-word names a role over others — the exact reading D3.a forbids, taught by the name itself.* Under R4 a member names their own agent, so this may resolve itself: the member calls theirs whatever they like, and the kernel never ships a row called "Supervisor." **Open (§8.5).**

### 7.2 ADR-653 — the sequencing, not the architecture

**What the operator is re-sequencing**: the app-builder as the headline. That call is correct and ADR-653 says so itself — §8/D6 ranks the origins **derived > chosen > authored** and notes *"the builder as a surface someone visits is the smallest part of this"*; the origin that shipped is authored, the least important.

**What is NOT re-sequenced, and the distinction matters:**

> **The app-builder was the vehicle; the composition surface is the asset.**

ADR-653's §1 correctly identified the surface layer as the demolished one, and the FE half (shipped `e15ae7f`, 2026-09-17) rebuilt it: a validated `composition` register, a data-driven kind dispatch, one generic surface, and a member app whose agent resolves and runs a turn. **Every one of those is what a coordinator's container needs.** Re-deriving them under a new name would be the ADR-562 second-home drift.

⭐ **So the re-sequencing is: demote step 4 (the builder as an app) and put the coordinator in its place.** Step 4 was always the design's self-test, never a member's need. The coordinator is the member's need, and it reuses the same three bands.

### 7.3 ADR-596 / ADR-460 D3.a — untouched, and this is the test of the frame

An agent is identity ⊕ character ⊕ engine. Authority, clock, purpose and judgment live on grants, declarations and gates.

The coordinator adds **memory** and **routing**. Neither is authority:
- **memory** is what a being knows, and ADR-624 already ruled it belongs in the being's home;
- **routing** decides which lane work enters — and a lane is a declaration-shaped thing, not a being.

⚠️ **The one place this could breach, and it must be watched**: if the coordinator's routing ever became *"assign this to Editor"* rather than *"open a thread about X, whose resident derives,"* it would be authority over a being. **The derivation must stay the mechanism** (ADR-597 D1: the resident follows the registration). Named here so an implementation cannot drift into it quietly.

---

## 8. What is open

Named so a later session does not mistake an open question for a settled one.

1. ⭐⭐⭐ **Can an agent open a lane?** Routing means the coordinator creates a thread. `create_lane` is a member-authenticated route today. Whether an agent may open one — and under whose grant, with what attribution — is **the load-bearing mechanism question**, and it may be a cliff question rather than a plumbing one. Nothing should be designed past it until it is answered.
2. ⭐⭐ **Whose memory is it?** §5.3 notes that per-being and per-concern coincide under R4. They diverge the moment a kernel agent (Editor, serving two apps) needs memory, and ADR-624 **already ruled for flat per-being** on a scaling argument. Whether that ruling survives contact with a *shared* memory that threads write is unexamined.
3. ⭐⭐ **What is a thread's relationship to its container?** A lane carries an `app` stamp today. Is a thread's membership in a concern the same edge, or a new one? The 96 unbound conversations need an answer either way, including the retroactive one.
4. ⭐ **Will members want a multi-party room?** ADR-626 shipped it; 2 of 164 conversations use it. This frame bets that the coordinator supplies the missing *reason*. That bet is unproven and the frame should not pretend otherwise.
5. **The name.** ADR-603 D3 flagged that a manager-word teaches the wrong reading. Under R4 the member names their own; the kernel may never need to ship one. Unsettled.
6. **How does the coordinator know what the threads did?** Routing out is easy; knowing what came back is the harder half, and it is what makes memory *shared* rather than one-directional. The benchmark asserts it and does not say how.
7. **Does this leave the standing/unattended half behind?** Measured 2026-09-17: **zero live standing declarations**, and a source predicate that structurally cannot name a workspace region — unattended work can only watch the outside world. That is a real gap and it is **a different one**: the coordinator routes *attended* work. Naming it here so the two are not merged by accident.

---

## 9. The one-line statement

**A supervisor is not a new kind of being and not a manager — it is an app's resident once that app has threads to route into and a memory to hold, met in the multi-party room YARNNN already built and has never had a reason to use; the container it presides over is the one the app frame shipped, the threads are the lanes that already exist 178-strong and half of them belonging to nothing, the library is the filesystem and is the half we are ahead on, and the two things genuinely missing — accumulation and routing — are the two the canon had already named and deferred.**
