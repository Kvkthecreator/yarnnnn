# Invocation and Narrative

> **Status**: Canonical (v2 — ADR-296 wake-architecture alignment, 2026-05-20)
> **Date**: 2026-04-25 (v1); 2026-05-20 (v2 — pulse aligned to wake sources)
> **Authors**: KVK, Claude
> **Ratified by**: FOUNDATIONS v6.8 (Axiom 9) + GLOSSARY v1.9 + ADR-296 v2 (2026-05-20)
> **Scope**: The atom of action in YARNNN and the narrative surface where that atom becomes legible to the operator.
> **Surface-home amendment (2026-06-25 — [ADR-370](../adr/ADR-370-context-surface-the-operations-boundary.md))**: the narrative's operator-facing surface is the **Context boundary surface's Flow lens** (`/context?context.pane=flow`) and, redundantly, **Notifications → Activity** (deliberate tiered access — ADR-367 D3). The standalone `/feed` route dissolved into Context's Flow lens (the renderer, grammar, and `session_messages` substrate are unchanged — only the launcher home moved); references below to `/chat` / `/feed` as "the narrative surface" name that same narrative — now the Flow lens. The *definition* (narrative ⊇ chat; every invocation logs; Channel-axis legibility closes Derived Principle 12) is unchanged.

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

### Invocations compose into the Loop (hardening, 2026-05-11)

Per FOUNDATIONS v8.4 (Axiom 1 fourth sub-clause + Axiom 2 two-embodiments sub-section), invocations are the atom *of* a runtime construct named **the Loop** — the synchronous Reviewer session canonized by [ADR-260](../adr/ADR-260-real-time-reviewer-loop.md).

A single Loop wake-up is composed of multiple invocations:

- **One Reviewer invocation** — the LLM session with `trigger="addressed"` (operator messaged the feed) or `trigger="reactive"` (a `judgment`-mode recurrence fired, or a proposal arrived). Identity = `reviewer:{occupant}`.
- **Zero or more System Agent invocations** — each tool call the Reviewer makes (`FireInvocation`, `Schedule`, `WriteFile`, `ProposeAction`) dispatches as a separate invocation by the System Agent acting on the Reviewer's behalf. Identity = `system:agent`.
- **Zero or more nested specialist invocations** — `DispatchSpecialist` calls produce `headless`-mode specialist invocations whose substrate writes are read by the Reviewer in the same Loop cycle. Identity = `specialist:{role}`.

All these invocations land in the universal narrative (§3 below), each as its own entry. The narrative is the operator-legible surface of the Loop; the substrate writes are the Loop's medium of action. There is no parallel control-flow channel between Reviewer and System Agent — the channel *is* substrate revisions (per ADR-209 attribution), with per-action narration on the feed (per ADR-258 revised) as a Channel-axis legibility affordance.

**Mechanical recurrences are not part of the Loop.** A `mechanical`-mode recurrence fire (per ADR-263 D5) emits one System Agent invocation that executes a primitive deterministically and writes substrate. It does not wake the Reviewer; it does not enter the Loop. Mechanical recurrences are the deterministic end of the same operating architecture — they keep substrate fresh between Loop wake-ups so the Loop has truth to read from when it next wakes. Same operator (operator-as-standing-intent → mandate authoring → cron schedule), different runtime composition.

**Tasks are not the same as the Loop, either.** Tasks are legibility wrappers (§4 below) over categories of invocations; the Loop is the runtime construct that produces invocations. A single Loop wake-up may produce invocations attributed to multiple tasks (Reviewer reads several recurrences' outputs, fires one, ProposeActions another) or no tasks at all (operator addresses with an inline question).

---

## 2. Pulse — the actor-scoped shape of Trigger

**Pulse**: the named wrapper around Axiom 4 Trigger when the trigger pertains to a specific actor. Pulse is not a separate dimension; it is Trigger viewed through the Identity lens.

Per **ADR-296 v2 (2026-05-20)**, the architecture's irreducible Trigger-axis unit is **wake**. Five wake sources contribute proposals to one evaluation funnel; the Reviewer fires only on `escalate`. Pulse is the actor-facing lens onto that wake.

### Wake sources and their pulse mapping

| Wake source (ADR-296 v2 D1) | Reviewer pulse (sub-shape) | Wake-warrant |
|---|---|---|
| **`cron_tick`** | Reactive | Recurrence's `schedule` declared a moment to consider |
| **`proposal_arrival`** | Reactive | A `action_proposals` row landed; creation is itself a wake-warrant |
| **`substrate_event`** | Reactive | A `workspace_file_versions` revision matched a `_hooks.yaml` declaration |
| **`addressed`** | Addressed | Operator (or external MCP caller) wrote to the feed surface |
| **`manual_fire`** | Addressed | Operator's explicit `FireInvocation` in chat |

The Reviewer's pulse sub-shapes (`reactive | addressed`) are the **internal viewpoint** — the user-message envelope shape the Reviewer assembles around the wake. The wake source is the kernel-internal primary vocabulary. Pulse is not a separate dimension; it is the wake source's actor-facing projection.

### Wake routes through one singular gateway (ADR-296 v2 D1)

Every Reviewer invocation routes through `services/wake.py::submit_wake_proposal(source, payload)` (or `stream_addressed_wake(...)` for SSE-streaming addressed). No other path invokes the Reviewer. Each wake source has a source-side module at `services/wake_sources/{name}.py` that builds the source-specific payload and routes through the gateway.

### The funnel decides which wakes propagate (ADR-296 v2 D2)

Each wake proposal passes through `services/wake_evaluation.py::evaluate()`. Five funnel decisions:

| Funnel decision | Meaning | Reviewer fires? |
|---|---|---|
| `skip` | Tier 1 kernel gate failed (balance/spend/cap/min-interval) | No |
| `tier_2_wait` | Tier 2 Haiku said wait | No |
| `tier_2_observe` | Tier 2 Haiku said observe | No |
| `escalate` | Tier 1 deterministic or Tier 2 Haiku said yes | Yes |
| `mechanical` | `cron_tick` on `mode: mechanical` recurrence | No (deterministic primitive runs) |

Operator-addressed, proposal-arrival, manual-fire, and substrate-event wakes auto-escalate at Tier 1. Cron-tick judgment recurrences pass kernel gates first; mechanical recurrences bypass.

### Heartbeat is deleted as a pulse sub-shape

The previous taxonomy named four pulse sub-shapes (Periodic / Reactive / Addressed / Heartbeat). Under ADR-260 D2 + ADR-256 supersession + ADR-296 v2, heartbeat is deleted — mid-loop continuation is the natural shape of a real-time tool-use loop, not a separate trigger. Periodic collapses into the `cron_tick` wake source. The two surviving pulse sub-shapes (reactive + addressed) are the Reviewer's internal viewpoint on the five wake sources.

### Pulse is on actors and on tasks

An Agent has a pulse. Reviewer is wake-pulsed (fires on any of the five wake sources). YARNNN is addressed-pulsed (fires when the operator sends a feed message). A user-authored domain Agent has whatever pulse its assigned tasks give it.

A task is a **scheduled pulse with a nameplate and a contract** (§4). When YARNNN creates a task with `schedule: daily`, it is attaching a `cron_tick`-source pulse to the work. When a task is reactive (no schedule, listening for an event), the pulse is `proposal_arrival` or `substrate_event`. When a task has no schedule (run-now default per ADR-205), the initial firing is an `addressed`-source pulse and no persistent recurrence is authored.

### Singular invocation gateway (Axiom 4 Derived; hardened by ADR-296 v2 D1)

There is exactly **one** Reviewer-invocation mechanism: `services/wake.py`. Pre-ADR-296 vocabulary spoke of "dispatchers per trigger sub-shape" — that framing is superseded. Every wake source's module routes through the singular gateway. If a new mechanic seems to need a new dispatcher, it is almost always an existing wake source in a new cell — route it through `wake_sources/{name}.py` and move on.

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
- **Provenance** — pointers into substrate (output folder path, decision.md line, `_money_truth.md` section) so a curious operator can drill in.

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

- **Amends FOUNDATIONS Axiom 4** (Trigger) — introduces *pulse* as the actor-scoped vocabulary wrapper; under ADR-296 v2 (2026-05-20) the irreducible unit is *wake*, with five wake sources mapping to two Reviewer pulse sub-shapes.
- **Amends FOUNDATIONS Axiom 6** (Channel) — names the narrative as a first-class Channel, not just "chat UX."
- **Amends ADR-138** (Agents as Work Units) — tasks are nameplate + pulse + contract rather than independent work units. Schema and implementation unchanged.
- **Supersedes implicit drift in ADR-163 / ADR-198 surface framing** — `/work` and `/chat` are not parallel substrates.
- **Aligns with ADR-296 v2** — pulse sub-shapes (reactive / addressed) map to wake-source taxonomy (cron_tick + proposal_arrival + substrate_event → reactive; addressed + manual_fire → addressed). Heartbeat as a pulse sub-shape is deleted.

### Preserves

- **FOUNDATIONS Axioms 1 / 2 / 3 / 5 / 7 / 8** — substrate, identity, purpose, mechanism, recursion, ground-truth substrate are unchanged.
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
| 2026-05-20 | v2 — §2 Pulse amended for ADR-296 v2: five wake sources (cron_tick + addressed + proposal_arrival + substrate_event + manual_fire) map to two Reviewer pulse sub-shapes (reactive + addressed). The wake source is the kernel-internal primary vocabulary; pulse is its actor-facing projection. Singular invocation gateway at `services/wake.py`. Five funnel decisions (skip / tier_2_wait / tier_2_observe / escalate / mechanical) stamp every `execution_events` row. Heartbeat sub-shape deleted. |
