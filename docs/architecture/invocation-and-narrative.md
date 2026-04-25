# Invocation and Narrative

> **Status**: Canonical
> **Date**: 2026-04-25
> **Authors**: KVK, Claude
> **Ratified by**: FOUNDATIONS v6.8 (Axiom 9) + GLOSSARY v1.9
> **Scope**: The atom of action in YARNNN and the narrative surface where that atom becomes legible to the operator.

---

## Purpose

FOUNDATIONS v6.0 named the six dimensions the system must separately decide (Substrate, Identity, Purpose, Trigger, Mechanism, Channel). Axiom 7 named what happens when the six compose over time (Recursion). This document names what happens when they compose **once** — the **invocation** — and where each invocation becomes legible to the operator — the **narrative**.

The architecture has long had invocations and chat entries, but without a canonical frame the two drifted against each other. `/work` was designed as a parallel substrate of "tasks and their runs" while chat was designed as "what I said to YARNNN and what YARNNN said back." The operator intuition — *"chat is where I come back to see what was done while I wasn't watching"* — exposed the drift: chat is not only a conversation log, it is the universal log of *every* act the system took. Tasks are not a parallel substrate; they are **named filters** over that universal log.

This doc ratifies that framing and makes four things precise:

1. **Invocation** is one cycle of the six dimensions — the atom of action.
2. **Pulse** is the named, actor-scoped shape of Axiom 4 Trigger.
3. **Narrative** is the single chat-shaped log where every invocation surfaces.
4. **Task** is a legibility wrapper — nameplate + pulse + contract — over a subset of the narrative.

---

## 1. Invocation — the atom of action

**Invocation**: one cycle through the six dimensions. One actor, one firing, one bounded set of reads and writes.

An invocation begins with a **Trigger** (periodic, reactive, or addressed), is carried out by an **Identity** (an Agent, an orchestration surface, or an external caller) for a declared **Purpose** (mandate, task objective, conversational intent, external request), applies some **Mechanism** (code, LLM, or a blend — Axiom 5's spectrum), reads and writes **Substrate**, and emits output to some **Channel**.

When the invocation terminates, the atom is complete. Nothing persists in the actor; state persists only in the substrate it wrote (Axiom 1) and in the narrative entry it emitted (this doc, §3).

### The invocation shape is actor-class-agnostic

Axiom 2 names four classes of actor: persona-bearing Agents (Reviewer + user-authored domain Agents), the orchestration chat surface (YARNNN), orchestration capability bundles (production roles + platform integrations), and external callers (foreign LLMs via MCP, webhook senders). **All four emit invocations of the same shape.** The Identity slot varies; the atom does not.

This is what makes MCP a *fifth caller of `execute_primitive()`* per ADR-164/169 without any parallel dispatch machinery: a foreign LLM calling `pull_context` is an invocation with Identity = `external:<client>`, Trigger = addressed, Mechanism = the primitive, Channel = MCP response. Same atom, different occupant in the Identity cell.

### Invocation is logged universally

Every invocation lands three places:

- **`agent_runs` DB row** — neutral audit ledger (Axiom 1 permitted kind 2). Billing, debugging, forensics. No semantic content.
- **Substrate writes** — whatever files the invocation produced (output folder, context-domain updates, memory scratch, decisions.md entry, etc.).
- **Narrative entry** — a chat-shaped record in the universal log (§3). This is the operator-legible surface.

The first two exist today. The third is the load-bearing commitment this doc adds: **no invocation is silent to the operator by default.** Housekeeping invocations may be rolled up or throttled (§4), but the narrative is the single home where "what happened while I wasn't watching" is answerable.

### Boundary: what is *not* an invocation

Not every function call is an invocation. The boundary is: **an invocation is a cycle that visits the Trigger dimension.** Pure helper code (parsing TASK.md, formatting a prompt, rendering HTML) that runs *inside* an invocation is not itself one. The unified scheduler polling the `tasks` table is not an invocation — it is the *mechanism that produces the Trigger* for the invocations that result.

One firing of one actor. One atom.

---

## 2. Pulse — the actor-scoped shape of Trigger

**Pulse**: the named wrapper around Axiom 4 Trigger when the trigger pertains to a specific actor. Pulse is not a separate dimension; it is Trigger viewed through the Identity lens.

Every actor in YARNNN has at most four pulse sub-shapes. Most actors have one; some have more.

| Pulse sub-shape | Trigger (Axiom 4) | Canonical invocations |
|---|---|---|
| **Periodic** | Scheduled cron | Task heartbeats (daily-update, recurring tasks, back-office tasks, reviewer calibration) |
| **Reactive** | Event-driven | Proposal landed → Reviewer invocation; upload POST → working-memory refresh; platform webhook → sync |
| **Addressed** | User action | Operator sends chat message → YARNNN turn; Approve click → ExecuteProposal; MCP call from foreign LLM |
| **Heartbeat** | Liveness pings | System tasks that fire regardless of load to prove the system is alive (daily-update empty-state template is the archetype) |

The fourth (Heartbeat) is a degenerate case of Periodic — worth naming because ADR-161 (daily-update as "the system is alive") depends on it. If the distinction feels academic, collapse Heartbeat into Periodic. What matters is the first three are structurally distinct; Heartbeat is a design-intent flavor of Periodic.

### Pulse is on actors and on tasks

An Agent has a pulse. Reviewer is reactive-pulsed (fires when a proposal lands). YARNNN is addressed-pulsed (fires when the operator sends a message). A user-authored domain Agent has whatever pulse its assigned tasks give it.

A task is a **scheduled pulse with a nameplate and a contract** (§4). When YARNNN creates a task with `schedule: daily`, it is attaching a periodic pulse to the work. When a task is `reactive`, the pulse is reactive. When a task has no schedule (run-now default per ADR-205), the initial firing is addressed and no persistent pulse is attached.

### No parallel dispatch systems (Axiom 4 Derived)

There is one dispatcher per pulse sub-shape. Periodic → `api/jobs/unified_scheduler.py`. Reactive → event handlers in `api/routes/`. Addressed → user-facing routes + `api/mcp_server/`. If a new mechanic seems to need a new dispatcher, it is almost always an existing sub-shape in a new cell — route it to the existing dispatcher and move on.

This is already FOUNDATIONS Axiom 4 policy. Naming the sub-shapes as *pulse* gives the operator-facing vocabulary a home without introducing new dispatch layers.

---

## 3. Narrative — chat is the universal log

**Narrative**: the single operator-facing chat-shaped record of every invocation. Ordered by time, attributed by Identity, filterable by task-nameplate or Agent.

### Commitment

**Every invocation emits a narrative entry.** The operator returning to the product tomorrow should be able to scroll the narrative and see everything that happened — what YARNNN did, what each Agent did, what the Reviewer decided, what the reconciler computed, what ran in back-office. The chat surface is not "my conversation with YARNNN." It is the workspace's stream of consciousness, of which the operator's conversation is one thread.

This reframes `/chat` from "a chat feature" to **the substrate-consumer view of the entire invocation history.** It is the Axiom 6 Channel that closes FOUNDATIONS Derived Principle 12 (Channel legibility gates autonomy): autonomous invocations become legible by surfacing here.

### Narrative entry shape

Each entry carries:

- **Identity** — who ran (`yarnnn`, `agent:<slug>`, `reviewer:<occupant>`, `system:<role>`, `external:<client>`).
- **Task-nameplate (optional)** — the task slug this invocation was labeled with, if any. Used as a filter key.
- **Pulse** — periodic / reactive / addressed (for narrative stylistic variation and filtering).
- **Summary** — one-line description of what the invocation did (the headline).
- **Body** — optional richer content (LLM output, proposal card, chart, pointer).
- **Timestamp** — when it terminated.
- **Provenance** — pointers into substrate (output folder path, decision.md line, `_performance.md` section) so a curious operator can drill in.

Implementation note: today's `session_messages` table carries operator-authored messages and YARNNN replies. The narrative entry shape is a superset of that. ADR-219 (proposed) will scope the storage layer; the present doc commits to the vocabulary.

### Material vs housekeeping gradient

Not every invocation deserves equal chat weight. A 3am workspace cleanup that deleted four ephemeral files does not warrant a prominent card above the operator's morning review. A reviewer decision on a $5k proposal does.

The gradient is **stylistic, not architectural.** Every invocation still emits an entry. Rendering varies:

| Weight | Example invocations | Narrative rendering |
|---|---|---|
| **Material** | Task output delivered, proposal awaiting review, reviewer verdict, high-impact outcome | Prominent card with body, actions, pointers |
| **Routine** | Recurring task run (already delivered, no new feedback), domain context refresh | Collapsed line, expand to see |
| **Housekeeping** | Back-office cleanup with no work done, heartbeat with no change | Rolled into a daily digest ("12 housekeeping invocations, all clean") |

The gradient is a render-layer decision, not a log-layer one. The log is complete; the UI surfaces it proportionally.

### Every invocation's narrative entry is authored

Per FOUNDATIONS Derived Principle 13 (Authored Substrate), every substrate write carries an `authored_by` identity. Narrative entries inherit this: the Identity cell of the invocation becomes the entry's author. `yarnnn` authored this entry; `reviewer:human:kvk` authored that one; `system:workspace-cleanup` authored the housekeeping digest.

---

## 4. Task — the legibility wrapper

**Task**: a nameplate + pulse + contract attached to a recurring (or goal-bounded, or reactive) category of invocations.

The three components:

- **Nameplate** — a stable slug + TASK.md that names the work. Without the nameplate, the invocations are still valid; they just aren't grouped for the operator.
- **Pulse** — the trigger shape for future invocations of this task. Periodic with a schedule, reactive with a platform event, or goal-bounded with a completion condition.
- **Contract** — DELIVERABLE.md (for `produces_deliverable` tasks) or the context-domain mapping (for `accumulates_context` tasks). Declares what the invocation should produce and against what standard.

### A task does not create a new substrate — it labels invocations

The substrate under a task is standard: an invocation runs, writes to `/tasks/{slug}/outputs/`, writes to context domains, emits a narrative entry. The narrative entry happens to carry the task slug. `/work` is the surface that filters the narrative by task slug.

`/work` is not a parallel log of `agent_runs`; it is a **filtered view of the narrative** scoped to task-labeled invocations. Implementation-wise the filter may be backed by `agent_runs` indexes, but the conceptual model — and therefore the user model — is filter-over-narrative.

### Inline action → task graduation

The mental model of a task as "nameplate + pulse + contract" makes the inline-to-task transition gradient and reversible:

- **Inline action** — operator asks "pull today's revenue." YARNNN invokes `get_revenue` via a primitive. One invocation, one narrative entry, no nameplate, no persistent pulse. Done.
- **Task graduation** — operator says "do that every morning." YARNNN creates a task: slug `morning-revenue`, schedule `daily`, DELIVERABLE.md describing the brief. The *next* invocation is indistinguishable in shape from the inline one — same Identity, same Mechanism, same substrate writes — but now it carries the task slug in its narrative entry, and a pulse fires it again tomorrow.
- **Task dissolution** — operator says "stop doing that." YARNNN archives the task; the pulse stops. The nameplate remains (historical record) but no new invocations fire under it. If operator asks inline again later, it's an inline action again.

The transition is a nameplate-attach or nameplate-detach operation, not a substrate migration. This is why the collapse works: the atom is the same throughout; only the legibility wrapper rotates.

### Task mode is about lifecycle posture, not about invocation

Task modes (`recurring` / `goal` / `reactive` per ADR-149) describe **YARNNN's management posture** over the lifetime of the task — how it evaluates, steers, and completes. The mode is orthogonal to the pulse: a `recurring` task typically carries a periodic pulse; a `reactive` task carries a reactive pulse; a `goal` task carries a periodic pulse bounded by a completion condition.

Mode is the lifecycle layer. Pulse is the invocation layer. An invocation of a goal-mode task and an invocation of a recurring-mode task can be structurally identical — the difference is what YARNNN does *between* firings (evaluate, steer, maybe complete vs keep running forever).

---

## 5. Scope summary: what collapses under this framing

| Previous framing | New framing | Notes |
|---|---|---|
| `/chat` is the conversation with YARNNN | `/chat` is the narrative — the universal invocation log, of which the operator's conversation is one thread | Stylistic rendering of non-conversation invocations is a UI commitment; substrate is already there |
| `/work` is a parallel substrate of tasks and runs | `/work` is a filtered view of the narrative scoped to task-labeled invocations | Data shape unchanged; mental model clarified |
| Tasks are independent work units | Tasks are nameplate + pulse + contract — legibility wrappers over recurring invocations | ADR-138 "agents as work units" survives; this doc refines the definition |
| Inline actions are "chat-only" and different from tasks | Inline actions are invocations without a nameplate; tasks attach a nameplate to future invocations | Transition is gradient and reversible |
| Back-office runs in its own layer | Back-office tasks emit narrative entries too (rolled up into housekeeping digests by default) | ADR-164 stands; narrative rendering is the new commitment |
| Reviewer verdicts live in `/workspace/review/decisions.md` only | Reviewer verdicts also emit narrative entries (material weight) | Substrate unchanged; narrative surfacing added |
| MCP calls are "outside the system" | MCP calls are invocations with Identity = `external:<client>`; they emit narrative entries | Supports the cross-LLM-continuity thesis in ADR-169 |

---

## 6. Relationship to existing canon

### Supersedes / amends

- **Amends FOUNDATIONS Axiom 4** (Trigger) — introduces *pulse* as the actor-scoped vocabulary wrapper; sub-shapes are unchanged.
- **Amends FOUNDATIONS Axiom 6** (Channel) — names the narrative as a first-class Channel, not just "chat UX."
- **Amends ADR-138** (Agents as Work Units) — tasks are nameplate + pulse + contract rather than independent work units. Schema and implementation unchanged.
- **Supersedes implicit drift in ADR-163 / ADR-198 surface framing** — `/work` and `/chat` are not parallel substrates.

### Preserves

- **FOUNDATIONS Axioms 1 / 2 / 3 / 5 / 7 / 8** — substrate, identity, purpose, mechanism, recursion, money-truth are unchanged.
- **ADR-141** (Execution Architecture) — three layers of mechanism are unchanged; invocation is one cycle through them.
- **ADR-164** (Back-office tasks) — YARNNN-owned tasks, narrative rendering is an additive commitment.
- **ADR-169** (MCP as Context Hub) — foreign LLM invocations already fit the atom; this doc names that fit.
- **ADR-194 v2 + ADR-211** (Reviewer seat) — decisions.md is Reviewer substrate; narrative emission is additive.
- **ADR-205** (Workspace Primitive Collapse) — chat-first triggering and run-now-is-default survive cleanly as inline addressed invocations.
- **ADR-209** (Authored Substrate) — narrative entries carry authorship; no new attribution plumbing needed.

### Proposed follow-up

**[ADR-219](../adr/ADR-219-invocation-narrative-implementation.md) (proposed, 2026-04-25)**: Invocation + Narrative — Implementation. Scopes the storage and rendering layer for the narrative commitment in six staged commits: (1) ratification (this ADR), (2) `session_messages` extension + `write_narrative_entry` single-write-path, (3) back-office digest task, (4) `/work` list view as filter-over-narrative, (5) `/chat` weight-driven rendering + inline-to-task graduation affordance, (6) MCP narrative emission + final coverage grep gate. Until ADR-219 lands, this doc is the vocabulary canon; implementation remains in its current shape.

---

## 7. Open questions

1. **Narrative storage** — is the single `session_messages` table the right substrate, or is there a sibling `narrative_entries` table that carries invocations that were never message-shaped? ADR-219 scope.
2. **Housekeeping digest cadence** — daily roll-up, or weekly? How does this interact with the daily-update email (ADR-161)? Likely the digest surfaces *inside* the daily-update when there is little else to say.
3. **External-caller rendering** — an MCP `pull_context` from ChatGPT at 3pm: does this land as a material-weight narrative entry ("ChatGPT pulled 3 competitor profiles"), routine, or housekeeping? Default: routine, with material surfacing only on `remember_this` writes.
4. **Filter affordances on `/chat`** — by task, by Agent, by pulse sub-shape, by time range. UI design question for the ADR-219 frontend phase.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-04-25 | v1 — Initial canonicalization. Invocation as atom, pulse as actor-scoped Trigger wrapper, narrative as universal log, task as legibility wrapper. Ratified by FOUNDATIONS v6.8 (Axiom 9). |
