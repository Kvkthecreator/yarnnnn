# The supervisor and the room — it holds the memory and routes the threads

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

> **YARNNN has never had parallel work to supervise.** There was no set of concurrent threads, no shared context between them, and no routing question. A supervisor over *one desk's declarations* is a face on a filing cabinet. The deletion was correct for that, and says nothing about a supervisor over many live threads.

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
| Who you brief | the main project chat | the chief-of-staff bot | **the supervisor** |
| Where work happens | a thread (own session, own branch) | a specialist bot's turn | **the thread** |
| What persists across both | shared memory | shared memory files | **the commons of the concern** |
| Where outputs land | the project library | — | **the library** |

⭐ **The load-bearing verb is "routes."** The supervisor does not do the work and holds no authority over the workers. It decides *which thread this belongs to*, opens one when none fits, and keeps the context that stops the member re-briefing. **A dispatcher with memory** — which is a much smaller object than "a manager," and crucially a different one.

### 2.2 What is NOT in either benchmark

Worth stating, because the word "chief of staff" imports it and the architecture must not:

- **No authority over the specialists.** Nothing says the supervisor may grant, promote, silence or over-rule a worker. It assigns *work*, never *rights*.
- **No autonomy of its own.** It routes when briefed. Neither product describes a supervisor that wakes up and decides something unprompted.
- **No second identity layer.** The specialists are the same kind of thing whether a supervisor is present or not.

**This is the whole reason the pattern is architecturally admissible here**, and §7.1 shows it is the distinction ADR-603 D3 already drew and got right.

---

## 3. What YARNNN already has — measured, not assumed

Every number below is from live production data, 2026-09-18.

| The benchmark's primitive | YARNNN's | State |
|---|---|---|
| thread | **the lane** (a bound conversation with a cast) | ✅ built and in use |
| the room is multi-party | **ADR-626 / ADR-495** — cast is principal-agnostic | ✅ ratified + built; **effectively unused** |
| library | **`workspace_files`** — attributed, versioned, revertible | ✅ built, and **stronger than the benchmark's** |
| shared memory | `agents/{slug}/memory/` | 🔴 **address only — no writer, no reader** |
| the supervisor / routing | — | 🔴 **nothing** |

### 3.1 Threads exist, in quantity, and they are a flat list

⚠️⚠️ **§13.1 RETIRES THIS SECTION'S NUMBERS AS EVIDENCE.** They are the operator's own workspace — a developer building the product, not a member using it. They can diagnose a defect; they cannot establish demand, and this section used them for demand. Read §13.1 before citing anything below.

178 conversations across 9 workspaces. **139 in a single workspace.** By binding:

```
text 71 · (unbound) 96 · images 5 · radar 3 · slides 2 · blogger 1
```

⭐⭐⭐ **96 of 178 carry no app stamp.** ⚠️ **§12.5 CORRECTS THIS: the query counted the STAMP, not the BINDING.** By binding the split is **138 artifact-bound / 41 unbound** product-wide — an artifact-bound lane can legitimately carry no `app` stamp (ADR-602 D7). The sentence below survives for the 41, not for 96.

**This is the benchmark's problem statement, arrived at independently by usage.** Projects' answer is that each request opens a thread *under a project*, and the project is what you brief. YARNNN has the threads and no container above them.

⚠️ **§11.1 CORRECTS THIS READING.** Driven further, over half of these conversations hold **zero messages** and the median live one is **four**. They are not 96 orphaned concerns awaiting a container — a large share are not concerns at all, and that difference is what splits this into two projects rather than one.

### 3.2 The room is already multi-party, and nobody is using it

ADR-626 (Ratified 2026-09-01) made the room principal-agnostic — humans and agents in one cast, and the agent can *see* who is in it. ADR-495 made the cast the single authority on who replies. Both are live.

Reached for rarely: multi-agent rooms are a small minority of conversations. ⚠️ **The exact ratio is retired as evidence (§13.1)** — it is the operator's own traffic. What stands without it is the qualitative fact, visible by inspection: **the mechanism is built and almost nothing enters it.**

The primitive the operator asks to "re-surface" is therefore **not missing — it is unused**, and the distinction matters enormously for what to build:

> **A capability nobody reaches for is a discoverability problem or a purpose problem, never a mechanism problem.** Building a second multi-party mechanism beside this one would be the ADR-562 second-home drift.

⚠️ Two agents in a room is *possible* today and has no *reason*. The supervisor supplies the reason: a room where the chief of staff and a specialist are both present is the routing conversation made visible.

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

Strip the product names, and strip the row counts with them (§13.1). A member doing ongoing work across more than one thread has four wants, and none of them needs a population to be true:

1. *"I don't want to re-explain the context every time."* → **memory**
2. *"I don't want to decide which of my threads this belongs in."* → **routing**
3. *"I want to see everything about this concern in one place."* → **the container** (which ADR-653 built and called an app)
4. *"I want someone who knows what's going on across it."* → **the supervisor**

⭐ **Items 3 and 4 are the same object seen from two sides.** The container is where the work is; the supervisor is who holds it. That is not a coincidence — it is why both benchmarks ship them together and neither ships one without the other.

**A container with no supervisor is a folder.** (This is ADR-653 §9.8's "generic apps are worse than none", restated: the app frame shipped the container and left the resident resting.)
**A supervisor with no container is a chatbot with opinions about your other chats.**

---

## 5. The frame

> **A supervisor is an app's resident once the app has threads and memory. It holds the shared memory of one concern, it routes work into threads, and it is met in a room that may hold anyone. It does the work of no thread and holds authority over no one; what it decides is WHERE work goes, never WHO may do what.**

Unpacked into the four claims the mechanism must honour:

**5.1 The supervisor is not a species.** It is a member app's agent (ADR-653 D2/R4) that has gained two things: memory to hold and threads to route into. No new row shape, no new register, no `kernel` variant. ⭐ This is what makes the frame admissible against ADR-610's *"a being is someone a member MEETS"* — the member meets their app's resident, and always did.

**5.2 The thread is the lane, unchanged.** A thread is a bound conversation with a cast. Under this frame it gains one thing: **a container it belongs to.** The 96 unbound conversations are the evidence that the container is the missing edge.

**5.3 Memory is the concern's, not the being's.** Projects says *"every thread adds to and draws from a shared memory"* — the memory belongs to the **project**, and threads share it. YARNNN's address is `agents/{slug}/memory/`, per-BEING. Under R4 (one member app, one agent, both directions) those coincide exactly. ⚠️ **That coincidence is load-bearing and should be examined rather than relied on** — §8.2.

**5.4 Routing is authority over DECLARATIONS AND LANES, never over beings.** *"Supervisor hires Editor"* is authority over a being — forbidden, unrepresentable (ADR-460 D3.a). *"The supervisor opens a thread about X, and that thread's resident does the work"* is the sentence ADR-603 D3 already ruled admissible. The cliff is untouched, and §7.1 shows this is a re-application of an existing ruling rather than a new exception.

---

## 6. Why the room is the right surface for it

The operator's second instruction — re-surface the group-chat concept — lands exactly here, and the benchmark supports it.

**Grok's shape is the tell**: several bots *in the same thread*, passing work between one another. Not a dispatcher UI. Not a queue. **A room where more than one party is present.**

YARNNN has that room already (§3.2) and it is idle. The supervisor gives it its first real tenant:

- the member briefs **in the room**, the way they already talk to any resident;
- the supervisor routes, and the routing is **visible as conversation** rather than as a hidden dispatch;
- a specialist can be present in the same room when the work needs two.

⭐ **The design consequence**: there is no new "supervisor UI" to invent. There is a room that already renders multi-party casts, and an app surface (ADR-653 D3.c, shipped 2026-09-17) whose band 3 shows the concern's state. The container's pane and its room are the two halves of one screen — which is the shape ADR-653 §9.2 already ruled for an app's bound lane.

⚠️ **And the honest risk**: ADR-626 shipped a multi-party room and it is barely entered. A frame that assumes members will want several parties in one room is making a bet that has not yet paid — and (§13.1) one that **cannot be settled from this product's current traffic at all.** Only a member settles it. §8.4.

---

## 7. The collision check — what this reopens

**Two deletions and one sequencing call.** Each is named with the reason, per the operator's instruction that prior deletes are not themselves an argument.

### 7.1 ADR-639 (and ADR-610) — the Supervisor seat

**What was deleted**: a Supervisor that was a `resident` field's value over the strings desk; a Keeper that was an executor slot wearing a character.

**Why the deletion still stands**: both were *"a being is someone a member MEETS"* violations — rows that promised a concept and delivered a slot. ADR-610's reasoning is worth preserving verbatim: *the name promised the concept; the row delivered an executor slot, and that gap recruits responsibilities the row cannot hold.*

**What is different now, and it is a fact rather than a preference:**

| | The deleted Supervisor | The supervisor |
|---|---|---|
| What it coordinates | declarations on **one desk** | **threads** — a live, growing set |
| Does the member meet it? | no — it was a receipt-signer | **yes** — it is the app's resident, briefed in a room |
| What it holds | nothing (a posture string) | **the concern's memory** |
| Its authority | none, and nothing to have authority over | none — routing is over lanes, not beings |

⭐⭐⭐ **The deleted Supervisor failed the "does a member meet it" test. This one passes it by construction**, because it is the resident of an app the member opened. That is not a workaround; it is the rule doing its job.

⚠️ **The name should be re-examined, and ADR-603 D3 said so first**: *every other resident is named for a CRAFT (Editor · Designer · Blogger) while a manager-word names a role over others — the exact reading D3.a forbids, taught by the name itself.* Under R4 a member names their own agent, so this may resolve itself: the member calls theirs whatever they like, and the kernel never ships a row called "Supervisor." **Open (§8.5).**

### 7.2 ADR-653 — the sequencing, not the architecture

**What the operator is re-sequencing**: the app-builder as the headline. That call is correct and ADR-653 says so itself — §8/D6 ranks the origins **derived > chosen > authored** and notes *"the builder as a surface someone visits is the smallest part of this"*; the origin that shipped is authored, the least important.

**What is NOT re-sequenced, and the distinction matters:**

> **The app-builder was the vehicle; the composition surface is the asset.**

ADR-653's §1 correctly identified the surface layer as the demolished one, and the FE half (shipped `e15ae7f`, 2026-09-17) rebuilt it: a validated `composition` register, a data-driven kind dispatch, one generic surface, and a member app whose agent resolves and runs a turn. **Every one of those is what a supervisor's container needs.** Re-deriving them under a new name would be the ADR-562 second-home drift.

⭐ **So the re-sequencing is: demote step 4 (the builder as an app) and put the supervisor in its place.** Step 4 was always the design's self-test, never a member's need. The supervisor is the member's need, and it reuses the same three bands.

### 7.3 ADR-596 / ADR-460 D3.a — untouched, and this is the test of the frame

An agent is identity ⊕ character ⊕ engine. Authority, clock, purpose and judgment live on grants, declarations and gates.

The supervisor adds **memory** and **routing**. Neither is authority:
- **memory** is what a being knows, and ADR-624 already ruled it belongs in the being's home;
- **routing** decides which lane work enters — and a lane is a declaration-shaped thing, not a being.

⚠️ **The one place this could breach, and it must be watched**: if the supervisor's routing ever became *"assign this to Editor"* rather than *"open a thread about X, whose resident derives,"* it would be authority over a being. **The derivation must stay the mechanism** (ADR-597 D1: the resident follows the registration). Named here so an implementation cannot drift into it quietly.

---

## 8. What is open

Named so a later session does not mistake an open question for a settled one.

1. ✅ **Can an agent open a lane? — ANSWERED 2026-09-18, driven. NO, and it should not. See §10.**
2. ⭐⭐ **Whose memory is it?** §5.3 notes that per-being and per-concern coincide under R4. They diverge the moment a kernel agent (Editor, serving two apps) needs memory, and ADR-624 **already ruled for flat per-being** on a scaling argument. Whether that ruling survives contact with a *shared* memory that threads write is unexamined.
3. ⭐⭐ **What is a thread's relationship to its container?** A lane carries an `app` stamp today. Is a thread's membership in a concern the same edge, or a new one? (⚠️ An earlier draft motivated this with a count of unbound conversations; §13.1 retires that. The question stands on its own — a thread with no concern is unroutable whether there are three of them or three hundred — and it includes the retroactive case.)
4. ⭐ **Will members want a multi-party room?** ADR-626 shipped it and it is, by inspection, reached for rarely. ⚠️ How rarely is not knowable here (§13.1) — and it does not need to be: the mechanism is built either way, and the frame's bet is that the supervisor supplies a *reason* to enter a room with two parties in it. **That bet is unproven and only a member can settle it.**
5. ✅ **The name — CLOSED 2026-09-18 (§13.3).** The concept is **supervisor**, by operator ruling. ADR-603 D3's warning is answered by the FRAME (§5.4, §7.3 — routing is over declarations and lanes, no verb takes an agent slug), not by avoiding the word. A MEMBER's own agent is still named by them (R4), and the kernel ships no row called Supervisor: the concept has a name; a being does not inherit it.
6. **How does the supervisor know what the threads did?** Routing out is easy; knowing what came back is the harder half, and it is what makes memory *shared* rather than one-directional. The benchmark asserts it and does not say how.
7. **Does this leave the standing/unattended half behind?** Measured 2026-09-17: **zero live standing declarations**, and a source predicate that structurally cannot name a workspace region — unattended work can only watch the outside world. That is a real gap and it is **a different one**: the supervisor routes *attended* work. Naming it here so the two are not merged by accident.

---

## 9. The one-line statement

**A supervisor is not a new kind of being and not a manager — it is an app's resident once that app has threads to route into and a memory to hold, met in the multi-party room YARNNN already built and has never had a reason to use; the container it presides over is the one the app frame shipped, the threads are the lanes that already exist, the library is the filesystem and is the half we are ahead on, and the two things genuinely missing — accumulation and routing — are the two the canon had already named and deferred.**


---

## 10. §8.1 answered — can an agent open a lane?

> **Driven against live code and the live database, 2026-09-18. The answer is NO, it is a CLIFF question rather than a plumbing one, and the frame survives it — because routing never needed an agent to hold the pen.**

### 10.1 What was measured

| Question | Finding | Receipt |
|---|---|---|
| Who writes a conversation row? | **Exactly ONE site** | `routes/lanes.py:1250` — `auth.client.table("chat_sessions").insert(row)` |
| Behind what auth? | `UserClient` — a decoded human JWT | `create_lane(req, auth: UserClient)`; `get_user_client` requires the `Authorization` header |
| Can the unattended path do it? | **No — toolless by construction** | `run_bounded_derive_turn` never passes `tools=` (`derive_turn.py:69-97`) |
| Is there a lane verb in the tool set? | **No** | driven: `lane_tool_names()` → the 7 file verbs + `QueryKnowledge` · `WebSearch` · `list_integrations` · `GenerateImage`. Nothing conversational. |
| Does the ADR-603 D3 precedent survive? | **No** | `Schedule` is GONE from `services/primitives/` — the tool ADR-603 D3 cited as *"already in CHAT_PRIMITIVES"* no longer exists. |
| Could an agent hold the grant? | **No — refused at the DATABASE** | `is_workspace_member` (mig 221) is `role IN ('owner','member') AND principal_id = auth.uid()`, and its own COMMENT reads: *"Membership = a HUMAN role only (AI principals are not members)."* |
| Does `own-agent` exist as a role? | Legal in ADR-373, **0 live rows** | 28 active grants: 22 owner · 5 foreign-llm · 1 member |

### 10.2 The refusal is three-deep, and the deepest one is the DB

This is what makes it a cliff question. The door is not merely unbuilt — it is refused at three independent layers, and the bottom one is not application code:

1. **The route** takes `UserClient`; there is no agent-shaped auth that reaches it.
2. **`is_agent_caller`** (ADR-577 D1.a) exists precisely to separate *an agent acting on its own* from *a member's hands*, and **fails toward refusal** for agents.
3. **RLS** ANDs `is_workspace_member(workspace_id)` on the `chat_sessions` SELECT policy. An AI principal cannot satisfy it — by a comment that states the rule as law rather than as configuration.

⭐⭐⭐ **A session would have to change a SECURITY DEFINER function whose comment says "AI principals are not members" to let a supervisor open a thread on its own.** That is the clearest possible signal that the naive mechanism is the wrong one.

### 10.3 The distinction that rescues the frame

`is_agent_caller`'s docstring draws the line the frame needs, and it was written for a different purpose three months ago:

> *"False for a member, and **false for a member's chat LANE** — a lane stamps `member:{id} via {model}` and **is the member's hands**, so it correctly reads that member's account store even though an AI is driving it."*

So the architecture already distinguishes:

| | Who acts | Admissible? |
|---|---|---|
| An agent, on its own initiative | `specialist:{role}` / headless | ❌ refused at three layers |
| **A member's lane, driven by an AI** | `member:{id} via {model}` | ✅ **this is how every lane turn already works** |

⭐ **Routing happens inside a turn the member started.** The member briefs the supervisor; the supervisor, *in that turn, as the member's hands*, opens a thread. Nothing wakes on its own initiative (the kernel rule, ADR-603/618/639) and no agent holds a grant.

The corroborating precedent is the MCP surface: it find-or-creates a `chat_sessions` row (`mcp_server/server.py:1775`), and does it under **the connecting human's `user_id`** — a foreign LLM writing as the member's hands, never as itself. **The pattern the supervisor needs is already shipped, for a different tenant.**

### 10.4 What this costs, stated honestly

It is not free, and the cost is a real one:

⚠️ **A lane verb would be the first conversational primitive.** Every tool a lane holds today acts on FILES. `OpenThread` would act on the workspace's own conversation graph — a new *class* of primitive, not a new member of an existing one. That deserves its own ruling.

⚠️ **The demand bar is not met yet.** `primitives-matrix.md` marks **8** registered primitives *"none — registered, no live surface"*, and records the discipline on `cp`: *"excluded (demand-pull; no demonstrated need — ADR-337 D6)"*. The demand behind `OpenThread` today is one analysis document. **By this repo's own rule that is a located gap, not demand** — the same verdict ADR-653 §10.11 reached about the projection verb, and for the same reason.

⭐ **The cheap intermediate exists and should be tried first**: the member briefs in a room, and the supervisor *proposes* the split — naming the threads it would open — while **the member's click opens them**.

The machinery for that shape is built and live: `ProposeAction`/`ExecuteProposal`/`RejectProposal` (ADR-193), `action_proposals` (**5 live rows**), and a member-facing execute surface on Reach + Notifications (`primitives-matrix.md:89` — *"an agent ProposeActions; the member executes or rejects"*, and the verdict-giver is the member, ADR-632 D2).

⚠️ **It is NOT free, and an earlier draft of this section said it was.** Driven: `'ProposeAction' in lane_tool_names(False)` → **False**. The primitive exists with live rows but is **not in the lane's tool set** — its callers today are the trading emit contract and the Hat-B operator harness. So the click path costs *admitting an existing primitive to the lane surface*, which is strictly smaller than declaring a new conversational verb, but it is still a payload line and still needs the ADR-467 D4 three-way agreement. The honest ordering is: **admit a built primitive before declaring a new one**, and measure demand with the cheaper of the two.

### 10.5 The ruling this suggests

> **The supervisor routes as the member's hands, inside a turn the member began — never on its own initiative, and never holding a grant.** Whether it opens a thread directly (a new `OpenThread` primitive) or proposes the split for a click is a demand question, not an authority question, and the click version should ship first because it is free and it measures the demand the verb would need.

**The cliff is untouched either way.** Routing decides where work goes; the thread's resident still DERIVES from the app registration (ADR-597 D1). No being gains authority over another, and §7.3's named drift — *"assign this to Editor"* — stays unrepresentable because no verb takes an agent slug.

### 10.6 One correction to §3 this investigation forced

§3 lists routing as simply "missing". That is true of the verb and **false of the mechanism**: a lane turn already writes to the substrate as the member's hands, and the MCP surface already creates conversation rows that way. What is missing is narrower than "routing" — it is **one primitive, or one proposal shape, inside a capability that already exists.**


---

## 11. The split — chat handling is a SEPARATE project, and the measurement is why

> **Operator call, 2026-09-18**: *"i think i may be over-reaching in my request and scope to try and evolve the chat associated handling alongside or within the supervisor and orchestration premise… should we just clear gate and thus scaffold this separately."* **Agreed, and the data argues it harder than the instinct did.**

### 11.1 The measurement that forced it

§3.1 read *178 conversations, 96 unbound* as evidence of parallel work needing coordination. **Driven further, it is not that.** In the busiest workspace (`d5b9029b`, 139 conversations), of the first 100 sampled:

| | |
|---|---|
| conversations with **zero** messages | **55** |
| conversations with any messages | 45 |
| median messages among the live ones | **4** |
| longest | 53 |

⭐⭐⭐ **Over half of all conversations are empty, and the median live one is four messages long.** That is not a set of durable work units awaiting a dispatcher. It is a **list accumulating abandoned rows** — something opens a conversation, it gets four messages or none, and nothing ever reclaims it.

**This corrects §3.1's reading of its own number.** The 96 unbound conversations are not 96 orphaned concerns; a large share are not concerns at all.

### 11.2 Why that makes them two projects

> **The chat layer has its own defect, and it is UPSTREAM of the supervisor rather than a component of it.**

Routing presumes threads are durable units worth dispatching to. Here, over half are not units of anything. Building routing on this list would put a dispatcher on top of destinations that are mostly empty, and the supervisor would read as useless for a reason that has nothing to do with coordination.

Three further reasons the separation is right, in ascending weight:

1. **Different evidence.** The chat question is answerable by reading ONE code path — a lane is created with its artifact, before anyone speaks — which needs no population. The supervisor question waits on shared memory, which has zero writers and zero readers: there is no mechanism to examine, let alone use.
2. **Different risk.** Chat handling is a contained surface concern. The supervisor reopens two deletions and sits against the ADR-460 D3.a cliff. Bundling makes the cheap, safe work wait on the expensive, contested work.
3. ⭐ **The separation is itself a test of the frame.** If the supervisor turns out to *require* the chat layer rebuilt first, that is evidence the frame is weaker than §5 claims — it would mean the supervisor only works on a chat model that does not exist. Better found by building them independently than by assuming they are one thing.

### 11.3 What Project A inherits — a clean SCOPE, not a clean slate

The chat work is separate; it is **not** unconstrained. Three findings bind it:

- **A lane is created only by a member's act** (§10). That is now a ruled position rather than an accident of the route, and any chat rework inherits it.
- **The room is already multi-party** (ADR-626 / ADR-495, ratified, 2 of 164 conversations using it). A chat rework that introduces a second multi-party mechanism is the ADR-562 second-home drift, and must argue against this one explicitly.
- **The container edge must stay NAMEABLE.** Whatever a conversation comes to belong to, the supervisor would later route *into* that edge. Project A need not build routing, but it must not foreclose the edge.

### 11.4 The two projects, and their next gates

| | **Project A — the chat layer** | **Project B — the supervisor** |
|---|---|---|
| The question | *Why do 55% of conversations die empty, and what should a conversation belong to?* | *Can an app's resident hold a concern's memory and route work into threads?* |
| State | audit not yet run | frame derived (§§1–10); §8.1 answered |
| Next gate | **the audit**: which gesture creates a conversation · is an empty one a defect or a draft · do the 96 unbound want a container or a reaper | **§8.2 — whose memory is it?** Accumulation has no mechanism, and the supervisor is not worth designing until it does. |
| Blocked on | nothing | Project A's answer to *what does a conversation belong to* — **possibly**; see §11.5 |

### 11.5 What stays undecided, deliberately

⚠️ **ADR-653's disposition is HELD until the audit reports** (operator call, same conversation). Steps 1–3 stay shipped and green; step 4 (the builder as an app) stays demoted. The reason for holding rather than amending now is exact: **what a conversation belongs to may change what an app IS.** Amending ADR-653 to describe its surface layer as supervisor infrastructure, before knowing whether the container is the app or something the chat audit names, would be deciding the load-bearing question in a status line.

⚠️ **Do not re-merge these two projects without new evidence.** The merge is intuitive — both are "conversations" — and §11.1 is the receipt for why the intuition is wrong at this moment. If the audit finds the empty conversations are a *routing* artifact after all, that is exactly the new evidence that would justify re-merging, and it should be recorded as such.


---

## 12. Project A, first pass — what the empty conversations actually are

⚠️⚠️ **§13.1 RETIRES THE DEMAND HALF OF THIS SECTION.** What survives is the DEFECT half — artifact-bound conversations are created eagerly, before anyone speaks — which is a fact about a code path and reproducible from one member opening one deck. The re-weighting of the supervisor's motivation in §12.5 is withdrawn.

> **Driven 2026-09-18, immediately after the split. It corrects §11.1's own reading, which corrected §3.1's.** Three passes over one number, each narrowing it; the third is the one to build on.

### 12.1 The census

One workspace (`d5b9029b`, the busiest), all 139 conversations, joined against `session_messages`:

| | count |
|---|---|
| conversations | 139 |
| **never spoken to (zero messages)** | **69** |
| live (≥1 message) | 70 |

And the empties, decomposed — this is the finding:

| empties by BINDING | | empties by STATUS | |
|---|---|---|---|
| **artifact-bound** | **65** | active | 53 |
| unbound | 4 | archived | 16 |

All 69 carry a `model` and **none carries a summary** — created at the door, never named, never spoken to.

### 12.2 What that means, and it is not what §3.1 or §11.1 guessed

⭐⭐⭐ **The empties are not abandoned chats. They are authoring lanes nobody talked in.**

**65 of 69 are artifact-bound.** An artifact-bound lane is created *with* its artifact — the Studio/Text shape, a conversation beside a canvas (`StudioSurface.tsx:4965`, `:4986`, `:5023`). The member opened a deck or a document, worked **on the canvas**, and never used the chat beside it. The conversation row is a **fixture of the authoring surface**, not a thing the member chose to start.

Compare the live half: 45 of 70 live conversations are *also* artifact-bound. So the canvas-side chat is used about **41% of the time** (45 of 110 artifact-bound lanes), and the other 59% are the residue of simply having opened an artifact.

**The 4 unbound empties are the only ones that match the "abandoned chat" story**, and four is noise.

### 12.3 The harm, measured rather than assumed

⚠️ **My first inference here was WRONG and is corrected in place.** Seeing 24 unbound active lanes against `_MAX_ACTIVE_LANES = 20`, I inferred the empties were consuming the cap and blocking new chats. Driven:

| | |
|---|---|
| cap (`_MAX_ACTIVE_LANES`, unbound only) | 20 |
| unbound ACTIVE lanes in this workspace | **24 — already over** |
| of those 24, **empty** | **2** |
| of those 24, real conversations | 22 |

**The cap pressure is real conversations, not the empties** — the cap counts unbound lanes only, and the empties are overwhelmingly bound. Two separate problems wearing one number:

1. **A cap that a real member has already exceeded** (24 > 20) — the 409 in `ChatSurface.tsx`'s own comment is live for this workspace. That is a UX bound (ADR-408 D6) meeting a member who outgrew it.
2. **65 empty artifact-bound rows** — which cost nothing against the cap and instead cost *legibility*: they pad any list, count, or future routing surface that reads conversations without asking whether anyone spoke.

### 12.4 The question this reframes

§11.4 set Project A's question as *"why do 55% of conversations die empty, and what should a conversation belong to?"* The first half is now answered and the second half is unchanged:

> **They die empty because a conversation is CREATED BY OPENING AN ARTIFACT, not by deciding to talk.** The gesture that makes the row is not a gesture about conversing.

So the live design question is narrower and better:

⭐ **Should an artifact-bound conversation exist before its first message?**

Three shapes, none yet argued:
- **eager** (today) — the row exists when the canvas opens; 59% are never used.
- **lazy** — the row is created on the first message; the canvas holds an intent until then.
- **eager but not counted** — the row exists, and every consumer that lists or counts conversations asks "has anyone spoken?" first.

⚠️ **This is not obviously a defect.** An eagerly-created lane may be load-bearing for the authoring surface's own wiring (the pane needs a lane id to mount against), and lazy creation would move that work to the first keystroke. **Which it is must be driven before it is changed** — `_lane_agent`, the cast seeding, and the pane's mount path all read a lane id. The audit's next step is that dependency walk, not a fix.

### 12.5 What this does to the supervisor (Project B)

It **strengthens the split** and removes one of Project B's assumed inputs:

- §3.1's *"96 unbound conversations = 96 orphaned concerns"* is now doubly corrected, and the cause is a **query that answered a different question**. It counted `lane.app` — rows with no APP STAMP — not rows with no BINDING. Driven across every workspace:

  | by `lane.app` (§3.1's query) | | by actual BINDING |  |
  |---|---|---|---|
  | `text` | 71 | **artifact-bound** | **138** |
  | *(none)* | **97** | **unbound** | **41** |
  | `images` · `radar` · `slides` · `blogger` | 11 | | |

  ⚠️ **An artifact-bound lane can carry no `app` stamp** — ADR-602 D7 records exactly this (56 bound `.html` lanes with no stamp, derived at read time). So §3.1's 96 was ~97 *unstamped* lanes, most of them bound, and the true unbound population product-wide is **41**.
- ⚠️ **So the "flat list of orphaned threads" problem the supervisor was partly motivated by is smaller than stated.** 25 live unbound conversations in the busiest workspace is a list a person can read. It is not nothing, and it is not the crisis §3.1 implied.
- **The routing motivation therefore rests on the OTHER two legs** — shared memory (no mechanism at all) and the container (what an app frame already builds) — not on thread sprawl. §5's frame survives; one of its supports does not.


---

## 13. Two corrections to this document's method — 2026-09-18

> **Operator call, closing the arc**: *"stop using the existing statistics as a measure for our reasoning. we're still essentially pre users (or just friends and family) and so none of existing chats should influence our decision and assessment here. rather, first principled approach is better"* — and *"i notice you keep using coordinator but i want to use supervisor."* **Both accepted. The first is the more damaging of the two and this section states it against the author of §§3, 11 and 12.**

### 13.1 The statistics were the operator's own traffic, and they are RETIRED as evidence

Every number in §3.1, §11.1 and §12 came from workspace `d5b9029b` — **the operator's own workspace** — plus a development rig. **That is a developer building the product, not a member using it.**

⭐⭐⭐ **This document used that traffic to argue DEMAND, twice, in opposite directions.** First §3.1: *96 orphaned threads justify routing.* Then §12: *no — 65 empty artifact lanes are the real story, and routing's motivation shrinks.* Both readings were of the operator using their own system while building it. A number that can be turned to argue a thesis and then its negation, from the same source, was never evidence for either.

**This is the trap this repo's own canon names, taken in the other direction.** ADR-653 §10.11 refused the projection verb because the demand behind it was *"one synthetic probe, in a workspace holding five CSVs totalling under 2KB, prompted by a hypothetical"* — a **located gap, not demand.** Twelve sections later, the same author let 139 rows of the operator's development sessions argue for a supervisor. Same error, opposite conclusion, and the discipline that would have caught it was already written down.

**What the numbers can and cannot do**, kept because the distinction is reusable:

| | |
|---|---|
| ✅ **Can** diagnose a DEFECT | an empty conversation row is empty whoever made it; a query keyed on `app` really did answer a different question than one keyed on binding |
| ❌ **Cannot** establish DEMAND | how many concerns a member has, whether threads sprawl, whether anyone wants routing — none of that is observable in a pre-user product |

**So the following claims are WITHDRAWN as support for the frame** (not deleted — a withdrawn claim that vanishes is a claim that can be made again):

- §3.1's *"the benchmark's problem statement, arrived at independently by usage"* — **no.** There is no usage. It was arrived at by the operator's own building.
- §12.5's *"the routing motivation now rests on the other two legs"* — the re-weighting was itself statistical, and is withdrawn with the rest.
- §11.1's *"55% empty"* as a reason the projects split. ⚠️ **The SPLIT survives**, because §11.2's three reasons are architectural (different risk, different evidence-availability, and the split is a test of the frame) — but it must not be justified by a number from the operator's own chats.

⚠️ **What survives from §12 is only the DEFECT half**: artifact-bound conversations are created eagerly, before anyone speaks, and 65 such rows exist in one workspace. That is a fact about a code path (`StudioSurface.tsx` creates a lane with its artifact), reproducible from one member opening one deck. **Its design question stands and needs no population** — *should an artifact-bound conversation exist before its first message?* — and it is answered by driving the dependency walk, never by counting rows.

### 13.2 The first-principles standard this document must be held to

With the statistics retired, **§§4–6 carry the frame alone** — and they should, because they were derived from the member's chair rather than from a table:

- a member does not want to re-explain context → **memory**
- a member does not want to choose among many threads → **routing**
- a member wants one place per concern → **the container**
- a member wants someone who knows what is going on → **the supervisor**

⭐ None of those four needs a row count to be true. They are claims about what ongoing work *is*, and the test for each is whether a member recognises it — which is the same standard the app frame was held to, and the reason that frame survived contact with its own collision check.

**The honest statement of the evidence base is therefore**: two market benchmarks converging on one shape (§2), a substrate audit of what exists versus what does not (§3's table, which is a CAPABILITY census and stands), and one member sentence — the operator's sister — that started the app arc. **No usage data. None is available, and a pre-user product that reasons from its own operator's traffic is reading its own reflection.**

### 13.3 The word is SUPERVISOR

Every instance of "coordinator" in this document is replaced. The operator's word governs, and the reasons are three:

1. **It is the member's word.** It is what the operator says, what the market says (*chief of staff*), and what a member would call the thing. The product does not get to prefer an internal noun.
2. ⭐ **Avoiding it was the wrong move, and worth naming.** This document reached for "coordinator" because ADR-603 D3 warned that a manager-word *"names a role over others — the exact reading D3.a forbids, taught by the name itself."* That warning is real. But routing around a name is not answering it: **if a name carries a risk, the FRAME must make the name safe, not the vocabulary make the risk unsayable.** §5.4 and §7.3 do exactly that work — routing is over declarations and lanes, never over beings; no verb takes an agent slug. With those in place the word is safe to use.
3. **A second word for one concept is the drift this repo spends ADRs deleting.** "Supervisor" and "coordinator" naming one thing would be the vocabulary split ADR-610 and ADR-639 each had to clean up.

⚠️ **§8.5 (the name) is therefore CLOSED for this document's purposes**: internally the concept is **supervisor**. What a MEMBER's own agent is called stays theirs under ADR-653 R4 — a member names the being that lives in their app — and the kernel still ships no row called Supervisor. **The concept has a name; a being does not inherit it.**

