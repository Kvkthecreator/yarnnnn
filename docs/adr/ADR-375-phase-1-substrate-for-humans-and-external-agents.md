# ADR-375 — Phase 1: YARNNN as the Substrate Operated by Humans and External Agents (the Interop Wedge)

> **Status**: **Accepted; §6 gate Implemented** (2026-06-26). Defines the Phase-1 product positively; the internal-steward gate is a *mechanism in service of it*, not the thesis. The §6 gate (steward-presence resolver `services/agent_gating.py::is_agent_enabled` + the four pre-cut chokepoints + `test_adr375_agent_gating.py` 32/32) is implemented, default ON — `AGENT_ENABLED=false` on a deploy yields the substrate-only Phase-1 product. **Render env-var (API + Unified Scheduler per §6) is a deploy-time step, set when an interop-first deploy is launched** — code defaults ON so current deploys are unchanged until then.
> **Date**: 2026-06-26
> **Authors**: KVK (operator) + Claude (collaborator)
> **Supersedes**: the prior ADR-375 (*"AGENT_ENABLED: Gating the Steward Behind One Flag"*, committed `6ef7b57`). That draft took the word "agent" to mean *the internal Reviewer/steward* and made *gating it off* the definition of the interop product. KVK's 2026-06-26 reframe rejected that whole framing: **the agent in the wedge is the EXTERNAL operator** (a principal that uses YARNNN like a human), **not the internal steward.** This rewrite inverts the subject — the product is defined by *who operates the substrate*, not by *which internal component is switched off*. The gating flag survives as §6, demoted from headline to mechanism.
> **Discourse base**: [`the-three-rung-framework-and-the-multi-principal-wedge-2026-06-26`](../analysis/the-three-rung-framework-and-the-multi-principal-wedge-2026-06-26.md) — §2 D2 (*"a principal is any authenticated caller that reaches the substrate — a human, that human's own agents, other humans, their agents, third-party platforms, foreign LLMs"*) + §4 (the three comparison sets) + [`interop-first-pivot-and-agent-gating-2026-06-25`](../analysis/interop-first-pivot-and-agent-gating-2026-06-25.md) (the GTM sequencing + the code-grounded feasibility audit of the gate).
> **Companion**: [ADR-374](ADR-374-presentation-ia-substrate-face-and-the-steward-posture.md) — the *presentation/IA* side (what the in-app operator lands on when the steward is off). This ADR is the *product definition* + the *switch*; 374 is the *face*. They share one input (steward-presence) and ship together.
> **Preserves**: [ADR-373](ADR-373-multi-principal-workspace-and-the-re-key.md) (the substrate floor + the multi-principal model this product *is* — the external agent is one of ADR-373's principal classes), [ADR-310](ADR-310-judged-substrate-interop-face.md)/[ADR-311](ADR-311-primitive-interop-surface.md)/[ADR-368](ADR-368-memory-first-interop-surface.md) (the interop face the external agent operates through: `remember`/`recall`/`trace` + file primitives), [ADR-296](ADR-296-continuous-judgment-cycle.md)/[ADR-298](ADR-298-reviewer-wake-queue-and-pace.md) (the internal wake architecture — gated at its entry points by §6, never modified), [ADR-307](ADR-307-unified-permission-taxonomy.md) (the gate is untouched; a foreign write still commits and still attributes when the steward is off — it is simply not judged).
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — who acts: the external agent is a first-class *principal*, not a YARNNN component) over **Channel** + **Trigger** (Axiom 6 + Axiom 4 — the secondary gate: whether the internal steward's surfaces appear / its wakes fire).

---

## 1. The two phases (the frame that partitions everything below)

YARNNN's long-frame vision has **two cleanly separable phases**, and the prior ADR-375 blurred them by binding the word "agent" to the wrong one. Naming them apart is the work of this ADR.

### Phase 1 — YARNNN as the file-system-native substrate, operated by humans AND external agents

**This is the wedge. This is what ships first.**

The substrate floor (ADR-209: content-addressed, parent-pointered, attributed, single-head — "git minus branches") + the membrane (ADR-373 multi-principal workspace) + the interop face (ADR-310/311/368: `remember`/`recall`/`trace` + file primitives over MCP) + the connectors that feed it.

An **external agent operator** — OpenClaw, Hermes, a Claude-Code-class autonomous agent, or any agentic caller — uses YARNNN **exactly the way a human operator does**: it connects over the interop face, calls the primitives, attributes as *itself* (a principal, per ADR-373's `principal_grants`), and treats the workspace as durable, attributed, cross-LLM context it reads and writes. **The agent here is a CALLER — a citizen of the multi-principal workspace, on the OUTSIDE, structurally identical in kind to a human except by its grant and its attribution prefix.** It is *not a YARNNN component.*

The relevant analogy: **git → GitHub → Copilot, but the agent in the wedge is the external coding agent hitting the API — not a GitHub-internal reviewer.** The substrate is the product; agents (and humans) are its operators.

### Phase 2 — internal agents (a different topic, deliberately walled off)

Phase 2 is where YARNNN grows its *own* agents that live *inside* the workspace. It has two distinct cuts, **neither of which is this ADR** — both are framed in the forward-vision analysis [`phase-2-internal-agents-freddie-and-user-personas-2026-06-26`](../analysis/phase-2-internal-agents-freddie-and-user-personas-2026-06-26.md) (conceptual; the Phase-2 ADRs cite it):

- **Cut 1 — the internal steward, named Freddie (forward).** The thing today called *"the Reviewer"* has, through the ADR-260→345 arc, become *the* actor — the judgment, the steward, the de-facto "YARNNN agent / system agent." That earned role is fine. But "Reviewer" was a *seat* name (ADR-194: occupant-agnostic) now used for a *specific, hardened, persona-bearing occupant*. The deliberate direction is to **name it Freddie** (Frankenstein → the creature we intentionally built and are hardening) and harden it as the de-facto system agent — slotting cleanly into the ADR-315 seat≠occupant carve (Freddie is a *named occupant*, not a new component). **This is a separate ADR. Not built here.** (§7.)

- **Cut 2 — user-authored independent agent seats (forward, deferred).** A *second* notion of internal agent: an agent **the user authors inside YARNNN** to hold standing intent on their behalf (the original ADR-216 "user-authored domain Agents" / independent seat). This is **not** Freddie (the single system agent) and **not** an external caller-operator. It is its own discourse — different lifecycle, creation surface, trust model. **Explicitly out of scope; named so it stops contaminating the other two.** (§7.)

**The blur this dissolves:** the prior ADR-375 used "agent" for the Phase-2-Cut-1 thing (future-Freddie) and called *gating that off* the definition of the interop product. But the interop product is **Phase 1**, defined by *external agents and humans operating the substrate.* Freddie's presence is a *secondary* Phase-2 concern that merely *happens to be gateable* (§6). The gate is a real lever; it is not what Phase 1 is *about*.

## 2. What the Phase-1 product IS (positively, with zero steward dependency)

The base value loop — **connected tools + principals → attributed substrate → served cross-LLM via the interop face** — closes with **zero internal-agent dependency** (interop-first-pivot §4 invariant). Concretely:

| Capability | Mechanism (live in code) | Steward needed? |
|---|---|---|
| A principal **writes** durable, attributed memory | `remember` → `write_revision()` → `operation/memory/{slug}.md`, attributed `<principal-prefix>` (ADR-368, ADR-209) | **No** — the write commits + attributes regardless |
| A principal **reads** what the workspace knows | `recall` → `QueryKnowledge`/`resolve_memory_path` (ADR-368) | **No** |
| A principal sees **how a fact changed, by whom** | `trace` → the parent-pointered revision chain (ADR-209) — *"which a plain storage connector cannot show"* | **No** — this is the differentiator, and it is substrate-native |
| Reality **flows in** as attributed observation | connectors + `TrackWebSources` (zero-LLM perception, ADR-335/336) + the ledger-intake lane (ADR-376, DP32) | **No** — mechanical intake |
| The **same substrate** is reachable from every room each principal works in | the MCP interop face, one workspace served to Claude / ChatGPT / agents / platforms | **No** |
| **Files / revisions / connectors** are fully legible in-app | the macOS-desktop shell + Files surface + revision history + Context boundary composition (ADR-297/370) | **No** — surfaces mirror substrate |

**The moat sentence (Phase 1 altitude):** *a single attributed substrate — every entry signed by its principal (human, agent, platform, foreign LLM), parent-pointered, single-head — served to every room each principal works in.* YARNNN is git's model for LLM context, multi-principal, served cross-LLM. Not a memory cache, not an MCP filesystem, not a notes app.

The one place Phase 1 *could* lean on an internal agent is the *intelligence of what-to-keep* when distilling raw dumps. ADR-376 (ledger-intake: **raw observation in, derived citing act out, raw never rewritten**) + the mechanical perception primitives already prove the write path is agent-free: a `remember` *dumps* to the inbox; *placement/judgment* is the steward's Phase-2 job, and its absence costs nothing in Phase 1 (the dump is durable and recallable as-is).

## 3. The external agent is a principal, not a component (the load-bearing distinction)

The discourse base already settled this (three-rung §2 D2): **a principal is any authenticated caller that reaches the substrate.** ADR-373 makes it structural — `principal_grants(principal_id, workspace_id, role, scopes)`; the role set is `owner | member | own-agent | foreign-llm | platform | a2a`. An external agent operator is, depending on how it authenticates, an `own-agent` (the operator's own agent), a `foreign-llm` (a model reaching in via a foreign room), or an `a2a` principal (agent-to-agent).

Consequences that make this more than vocabulary:

- **It attributes as itself.** The attribution taxonomy is *already principal-agnostic* (`VALID_AUTHOR_PREFIXES` includes `agent:`, `yarnnn:mcp:<client>`, `a2a:` spec'd per ADR-373/371-D3). `trace` therefore says *"which principal — human, agent, platform, or foreign model — contributed each version"* — load-bearing precisely *because* agents are first-class authors, not anonymous tool-calls.
- **It is authorized by grant, not by being "the agent."** Write-region permission comes from its `principal_grants` row (default: the class floor — `own-agent`/`foreign-llm` get `operation/memory/` only; richer grants opt-in). The same `_caller_class`/`CALLER_WRITE_POLICY` seam serves it as serves a human (ADR-373 §6.2). There is no special "agent path" — there is the *principal* path.
- **It needs no internal steward to be useful.** An external agent operating the substrate is the *complete* Phase-1 customer. Freddie (Phase 2) adds *accountable judgment over the commons*; it is an upgrade, not a prerequisite.

**This is the inversion:** "agent" in Phase 1 is the customer operating the product, on the outside. "Agent" in Phase 2 (Freddie) is a component we run on the inside. The prior ADR-375 conflated them; this ADR holds them apart by construction.

## 4. The three comparison sets (why this framing partitions the launch)

From the three-rung framework §4 — each rung's honest name dictates a different fight, and Phase 1 owns the first two:

| Rung (Phase 1) | Benchmarked against | The fight | Verdict |
|---|---|---|---|
| **Ledger** (Files + `trace`) | storage/memory MCPs — Mem0, Letta, generic MCP filesystems | attribution + parent-pointered history + single enforced write path, served cross-LLM | **Win, provably** — `trace` exposes a structural property no storage connector has. Lead the wedge here. |
| **Membrane** (the multi-principal workspace, served cross-room) | in-room LLM memories — ChatGPT memory, Claude Projects, Gemini context | **neutral**, cross-principal, cross-LLM portable substrate | **Win structurally** — a walled-garden memory cannot be neutral across rivals or across principals (incl. *agent* principals). The lab's strongest incentive is the exact thing it cannot do. |
| **Steward** (Freddie — *Phase 2*) | autonomous-agent / accountable-action products | accountable judgment over the multi-principal commons | **No incumbent** — an *evidence* problem, not a build problem (tenure-rule-revision proven). Demonstrated in the beta, not part of the Phase-1 fight. |

Phase 1 fights the first two fights — both winnable — *without exposing Freddie at all.*

## 5. The decisions

### D1 — Phase 1 is defined by WHO operates the substrate, not by what is switched off

The product is *"the file-system-native, attributed, cross-LLM substrate that humans and external agents operate as principals."* The internal steward's presence/absence is an *implementation variable* of a given deployment (§6), not the definition. **Future sessions: do not describe the Phase-1 product as "YARNNN with the agent turned off." Describe it as "the substrate agents and humans operate."** The first framing buries the customer; the second names it.

### D2 — The external agent is a first-class principal under ADR-373; no special-casing

External agent operators reach the substrate through the **same** interop face, the **same** `principal_grants` authorization, the **same** attribution taxonomy as every other principal. There is no "agent mode," no separate code path, no internal-component coupling. ADR-373 is the load-bearing dependency; this ADR adds *no* new authorization or attribution mechanism for agents — it **names them as the customer the existing model already serves.**

### D3 — The internal steward (Freddie) is gated by ONE flag; OFF degrades to substrate-only, nothing breaks

`AGENT_ENABLED` (resolved through `is_agent_enabled(workspace_id=None)`) gates the internal steward at the four pre-cut chokepoints (§6). **When off:** nothing wakes the internal Reviewer; the steward surfaces vanish from nav; a foreign/agent `remember` still commits + attributes (ADR-307 gate + ADR-209 write path untouched) — it is simply **not placed/judged**. `recall`/`trace`/connectors/files all work fully. The dump waits in the inbox; if the flag later flips on, the steward's first drain picks up the accumulated inbox (graceful, no data loss). **This is the gate the prior ADR-375 built — preserved verbatim as a mechanism, demoted from thesis.**

### D4 — Gating granularity: per-deploy now, per-workspace forward-compatible; DEFAULT = ON

Ship as an **environment flag** (per-deploy). `is_agent_enabled(workspace_id=None)` is the single steward-presence resolver — the same input [ADR-374](ADR-374-presentation-ia-substrate-face-and-the-steward-posture.md) reads to choose the at-rest face. A per-workspace branch is **forward-compatible** (density-gating, interop-first-pivot §5 decision 3) **without touching the four chokepoints**, but not built now.

**Default when unset = ON** (the steward runs). Rationale: the flag is an **isolation seam for a future public launch, not a behavior flip for the current live system.** Defaulting OFF would silently gate the steward on every existing deploy the moment this ships — and risk the exact API/Scheduler drift CLAUDE.md §5 warns about (gate the API but forget the Scheduler → wake_queue rows pile up undrained). Default ON keeps the seam **invisible until invoked**: the off-state is something a specific deploy *sets* (`AGENT_ENABLED=false`), deliberately, for the interop-first launch — and is fully exercisable by the regression gate (§6) regardless. *(Decision: KVK, 2026-06-26 — "the flag's job is isolation, not a behavior flip.")*

### D5 — No deletion; the steward layer is dormant, not removed (Singular-Implementation preserved)

Gating is `if`-guards + a registry filter. The wake architecture, the Reviewer/occupant, the proposal/queue stack all remain in the codebase, untouched, dormant. The fork (the original "freddyy.ai" repo-duplication) is rejected (interop-first-pivot §2): the flag solves the same brand-isolation at a fraction of the cost, with no porting tax. The Phase-2 beta is a **flip, not a re-integration.** *(This is also why the Phase-2 Freddie ADR can be a clean rename-and-harden, not a resurrection — the code never left.)*

## 6. The internal-steward gate — mechanism (the demoted prior-375 body)

The seam was **pre-cut** (interop-first-pivot §6 Finding 2): `write_revision()` contains zero wake/Reviewer calls — the producer (file writes) is decoupled from the consumer (the steward) by a scheduler poll, not a synchronous call. Writing a file fires nothing. DB schema is cleanly partitioned (substrate tables vs agent tables share only the workspace membership; no cross-layer FKs). Frontend nav is 100% backend-driven. So the gate is **~3 flag checks + one list filter**, not a rebuild.

### The steward-presence resolver

`is_agent_enabled(workspace_id: str | None = None) -> bool` — one module, the single source of truth. Reads `AGENT_ENABLED` from env now (default ON per D4); the `workspace_id` parameter is accepted but unused (forward-compatible per-workspace branch, D4). Every chokepoint and ADR-374's IA read consult **this one resolver** — no per-site divergence.

### The four chokepoints (confirmed against live code, 2026-06-26)

| # | Chokepoint | Symbol : line | Action when OFF |
|---|------------|---------------|------------------|
| 1 | Scheduler **due-dispatch + hook-walker + drain** (the cleanest single gate) | [`unified_scheduler.py`](../../api/jobs/unified_scheduler.py): `dispatch_due_invocations` (:317), `walk_hooks` (:335), `drain_all_users_with_pending` (:371) — all inside `run_unified_scheduler` | Wrap the **block** in `if is_agent_enabled():` → nothing ever wakes the Reviewer. **Gate the walker AND the drain as a unit** (interop-first-pivot §7 risk 2: gating only the drain leaves flagged-off workspaces silently accumulating undrained `wake_queue` rows). |
| 2 | Wake **enqueue** gateway (belt-and-suspenders) | [`wake.py:118`](../../api/services/wake.py#L118) `submit_wake_proposal` | Early-return when off. #1 alone suffices; #2 makes the off-state airtight (no row ever enqueued — also covers the MCP→wake adapter, which reaches the queue only via this function and "never raises," so the dump already committed). |
| 3 | Addressed (chat→Reviewer) path | [`feed.py:1126`](../../api/routes/feed.py#L1126) `wake_sources.addressed.stream` (+ manual-fire callers in `routes/agents.py`, `routes/recurrences.py`, `routes/admin.py`) | Per ADR-374 D2 the base product has no native chat → no caller. If a thin assistant ever exists, it must not reach this path when off. Guard the dispatch so it never reaches the addressed stream. |
| 4 | Surface catalog (nav) | [`kernel_surfaces.py:203`](../../api/services/kernel_surfaces.py#L203) `KERNEL_SURFACES`, filtered in `kernel_surface_entries()` | Filter out the steward-coupled surfaces. Backend-driven → zero FE change. |

**Filter at #4 — steward surfaces (off):** `agents`, `queue`, `notifications`, `autonomy`, `program`, `recurrence`, `expected-output`, `activity`.
**Keepers (always on — ledger + membrane + constitution mirrors):** `files`, `context`, `connectors`/`sources`, `settings`/`workspace-settings`, `identity`/`mandate`/`principles`, `home` (substrate-forward empty state per ADR-374 D1/D3), `budget`, plus structural chrome (`top-bar`, `launcher`, `chat-drawer`, `setup`).

### Render parity (CLAUDE.md §5 — load-bearing)

`AGENT_ENABLED` must be set consistently on **API + Unified Scheduler** — chokepoint #1 lives on the scheduler; a drift where the API thinks agent-off but the scheduler still drains is the exact failure mode the parity check exists to catch. MCP server + render gateway hold no wake-trigger and are unaffected.

### Regression gate

`api/test_adr375_agent_gating.py` — off-state: a foreign `remember` still commits + attributes but enqueues **no** wake; `kernel_surface_entries()` excludes the steward surfaces and retains the keepers; a substrate write still works. On-state (default): all surfaces present, wakes enqueue normally.

## 7. What this does NOT do (the deferrals, named so they don't re-blur)

- **Does not rename the Reviewer to Freddie.** Phase-2 Cut 1 is **named as the deliberate direction** (§1) and gets its **own ADR** — the internal-steward naming + hardening. No `reviewer_agent.py` / occupant-canon edits in this commit.
- **Does not build user-authored agent seats.** Phase-2 Cut 2 is **explicitly out of scope** (§1) — a separate discourse (independent seat lifecycle, creation surface, trust model).
- **Does not touch substrate, the gate, the write path, or attribution.** Off-state writes still commit + attribute; they are just unjudged (D3). ADR-373 carries the multi-principal model; this ADR consumes it, does not extend it.
- **Does not decide the in-app IA.** That is ADR-374 (the at-rest face when the steward is off). This ADR decides the *product definition* + the *switch*; 374 decides the *face*. They share `is_agent_enabled` and ship together.
- **Does not build per-workspace density-gating** (D4) — forward-compatible via the resolver, demand-gated.
- **Does not fork the repo** (D5) — rejected (interop-first-pivot §2); the flag is the isolation seam.

## 8. Implementation sequencing (doc-first)

1. This ADR + ADR-374 (they share `is_agent_enabled`).
2. `is_agent_enabled(workspace_id=None)` resolver (one module; env read now, default ON; per-workspace branch deferred).
3. The four chokepoint guards (§6) — #1 (walker+drain+dispatch unit) and #4 (registry filter) are load-bearing; #2 defensive; #3 no-op while base has no chat (ADR-374 D2).
4. **Render parity:** `AGENT_ENABLED` set consistently on API + Unified Scheduler (the interop-first launch deploy sets it `false`; current deploys leave it unset → ON).
5. Regression gate `api/test_adr375_agent_gating.py`.
6. Verify off-state end-to-end: a foreign `remember` commits to `operation/memory/`, attributes `yarnnn:mcp`, and does **not** wake the Reviewer; `recall`/`trace`/connectors/files all work; nav shows only keepers.

The framing (§1–§5) ratifies on this ADR; the gate (§6) is a small, low-risk implementation downstream of it.

## 9. Rejected alternatives

- **Keep the prior ADR-375 framing ("AGENT_ENABLED gates the steward" as the thesis).** Rejected (§Supersedes) — it binds "agent" to the internal steward and buries the actual customer (the external agent operating the substrate). The product is defined by *who operates it*, not by *what is switched off*.
- **Fork the repo (the "freddyy.ai" proposal).** Rejected (interop-first-pivot §2; D5) — a permanent porting tax; the flag solves the same brand-isolation at a fraction of the cost. If an escape hatch is wanted: a tagged git snapshot, not a maintained fork.
- **Delete the steward layer for the base build.** Rejected (D5) — re-integration cost on beta; dormant-behind-a-flag is reversible, and lets the Phase-2 Freddie ADR be a clean rename-and-harden.
- **Default the flag OFF when unset.** Rejected (D4) — would silently flip every existing deploy's behavior on merge and risk API/Scheduler drift. The flag's job is isolation, not a behavior change to the live system; the off-state is *invoked* per-deploy.
- **Special-case the external agent (an "agent mode" / separate code path).** Rejected (D2) — the external agent is a *principal* under ADR-373; the existing interop face + grant model + attribution taxonomy already serve it. A special path would be a second authorization vocabulary (Singular-Implementation violation) and would re-blur agent-as-customer with agent-as-component.
- **Per-workspace gating from day one.** Deferred (D4) — forward-compatible via the resolver; density-gating is demand-gated, not launch-critical.
