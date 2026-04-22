# YARNNN Cognitive Architecture — Foundations

> **Status**: Canonical
> **Date**: 2026-03-25 (v6.0 rewrite 2026-04-20)
> **Authors**: KVK, Claude
> **Scope**: First principles from which all architectural decisions derive.
> **Rule**: ADRs implement these axioms. If an ADR contradicts a foundation, the ADR must justify the deviation or be revised.

---

## Purpose

This document defines the foundational axioms of YARNNN's cognitive architecture. It is not an implementation guide — it is the conceptual substrate from which implementation decisions follow. Everything in `docs/adr/`, `docs/architecture/`, and the codebase should be derivable from or consistent with these axioms.

---

## Axiom 0: Six Dimensions, Not Phases

Every mechanic in YARNNN — every table, every file, every service, every prompt, every surface, every ADR — occupies a cell in **six orthogonal dimensions**. The dimensions are the irreducible questions the system must answer:

| Interrogative | Dimension | What it decides |
|---|---|---|
| **What** | **Substrate** | What persists; what is true between invocations |
| **Who** | **Identity** | Which cognitive layer acts; which identity authors or consumes |
| **Why** | **Purpose** | What intent drives the work; what the objective is |
| **When** | **Trigger** | What invokes execution — periodic, reactive, or addressed |
| **How** | **Mechanism** | By what means the work happens — a spectrum from deterministic code to LLM judgment |
| **Where** | **Channel** | To what location or surface output is addressed |

The six are **dimensions, not phases.** A cron firing is not "in the Trigger stage"; it is *one cell's position along the Trigger dimension*. The same invocation simultaneously occupies cells in Substrate (what it reads/writes), Identity (who is running), Purpose (why this fires now), Mechanism (how the work is done), and Channel (where output lands). Design errors happen when a mechanic is allowed to span a dimension without necessity — conflating Substrate with Identity, or Purpose with Channel, or Mechanism with Trigger.

### The three pairings (mental mnemonic)

As a cognitive aid, the six pair into three natural couplings:

- **Substrate ⟷ Identity** — *what is*, *authored by whom*. Every file has an author; every domain has a reader.
- **Purpose ⟷ Trigger** — *why*, *when*. Intent drives invocation. Trigger without purpose is noise; purpose without trigger is dormant.
- **Mechanism ⟷ Channel** — *how*, *where*. Means produces a targeted artifact. Rendering is Mechanism; addressing the surface is Channel.

The pairings are how humans think about the system. The dimensions are what the system must separately decide. Both frames are useful; they are not the same.

### Why this axiom now

The architecture grew a vocabulary faster than it acquired discipline for that vocabulary. By 2026-04 the repo had dozens of named mechanics — primitives, tool profiles, scheduling, pulse (deleted), proactive review (deleted), compose substrate, reviewer seat, feedback actuation, back-office tasks, MCP surface, surface archetypes, inference hardening, impersonation, outcome reconciliation — each designed, each defended, each ADR-ed. Many were correct. Some were cross-cuts that confused one dimension for another. Without a dimensional test, the mistakes were only caught retroactively (Composer → YARNNN, pulse → dissolved, project layer → collapsed, platform_content → sunset, action_outcomes SQL → filesystem).

Axiom 0 is the architectural conscience that catches these conflations *before* shipped code accretes dependents. The previous Axiom 0 (v5.1, filesystem-is-substrate) is preserved — it is now Axiom 1 below, the Substrate dimension stated axiomatically.

### Test for new features

Before adding a mechanic, answer the six:

1. **What** does it read/write? (Substrate cell)
2. **Who** authors/consumes it? (Identity cell)
3. **Why** does it exist — what intent is served? (Purpose cell)
4. **When** does it fire — periodic, reactive, or addressed? (Trigger cell)
5. **How** does it work — code, LLM, or a blend? (Mechanism cell)
6. **Where** does its output go? (Channel cell)

If two questions have the same answer, the mechanic is conflating dimensions — redesign. If one question has no answer, the mechanic is incomplete — specify before shipping.

---

## Axiom 1: Substrate — Filesystem Is the Persistence Layer

**What persists lives in files. Nothing else persists.**

YARNNN's semantic state lives in the filesystem (`workspace_files` today; storage-agnostic by design per ADR-106). Every other architectural layer — scheduling, reasoning, review, reconciliation, rendering, delivery — is **stateless computation** that operates *over* the filesystem. State lives in files. Components do not hold state; they read files, act, write files, and terminate.

This axiom was introduced in v5.1 (previously Axiom 0). Its content is preserved; only its number changed. It remains the single most load-bearing architectural property: every prior collapse of a parallel substrate happened because semantic content was placed in a DB row when it belonged in a file.

### What this means concretely

- **Semantic content lives in files.** Entities, theses, observations, track records, feedback, decisions, identities, charters — all filesystem. A DB row that holds semantic content is, by default, a violation.
- **Computation is stateless.** The scheduler holds no work-definition state; it reads TASK.md. The pipeline holds no output state; it writes to `/tasks/{slug}/outputs/`. The reconciler holds no performance state; it edits `_performance.md`. The Reviewer holds no judgment state; it writes to `/workspace/review/`. Every component reads the filesystem, acts, writes the filesystem, and terminates. State persists only in files across invocations.
- **Accumulation happens in files across invocations.** Each cycle adds to context. The recursive property (Axiom 7 below) is enabled by the filesystem being the single accumulation target.
- **Mechanism varies; statelessness does not.** Scheduling is periodic (cron); execution is one-shot per invocation (task pipeline); review is reactive (triggered by proposal creation); reconciliation is periodic (daily back-office task); rendering is invocation-scoped (compose engine). Different shapes of Mechanism, one invariant: none retain state of their own.

### Four permitted kinds of database rows

DB rows are not banned — they are narrowly permitted. Every table in the schema must fall into one of four categories:

1. **Scheduling indexes** — what needs to run, when. Examples: `tasks` (schedule + mode + next_run_at), `agents` (identity pointer + role). These are lean pointers at files; the file is the source of truth.
2. **Neutral audit ledgers** — what happened, for billing / debugging / forensics. Examples: `agent_runs`, `token_usage`, `activity_log`, `render_usage`. No semantic content.
3. **Credentials / auth** — encrypted secrets the filesystem cannot hold safely. Examples: `platform_connections`, `mcp_oauth_*`. Opaque to everything except the decryption path.
4. **Ephemeral queues / inboxes** — pending items with hard TTLs awaiting action, not accumulating. Example: `action_proposals` (proposed writes, TTL-bounded, swept by back-office cleanup). The row disappears after acceptance, rejection, or expiration.

Anything that doesn't fit one of these four patterns belongs in the filesystem.

### Secondary benefits of filesystem-first discipline

- **Storage-agnostic** — Postgres today, cloud storage later, no code change (ADR-106).
- **User-legible** — operators can read their own accumulated context. Tables are opaque; markdown is transparent.
- **Agent-legible** — every agent reads files natively. No ORM, no schema coupling.
- **Git-compatible** (future) — filesystem state can be exported, diffed, and version-controlled.
- **Model-agnostic** — files are the universal interface across LLM providers and interoperability protocols (MCP).

### Corollary: Substrate grows from work, not from signup scaffolding (ADR-205)

The filesystem-first commitment is not only about *where* state lives — it is also about *when* state comes into being. Substrate should materialize through user action (tasks writing, conversations resolving, uploads landing), not through framework-level pre-creation at signup. A fresh workspace is textually present (identity, brand, uploads) and structurally empty (zero user-authored Agents, zero context domain directories, zero user-authored tasks beyond the deterministic daily-update heartbeat and back-office tasks). Directory registries exist as *naming conventions* consulted at first-write, not as *pre-creation manifests* run at signup.

This corollary strengthens Axiom 1 rather than extending it: if the substrate is where state lives, then populating the substrate before work exists is itself a Substrate violation. It places content in the persistence layer ahead of the purpose that would justify it.

---

## Axiom 2: Identity — Four Cognitive Layers, Filesystem Author

**Every act has an identity. Every file has an author. Identity is orthogonal to mechanism.**

YARNNN has four distinct cognitive layers. Each develops along a different axis, each carries a different scope of judgment. All four share the same filesystem substrate (Axiom 1) — the distinction is scope and what each serves. See [GLOSSARY.md](GLOSSARY.md) for canonical terminology.

### The four layers in one sentence each

- **YARNNN (meta-cognitive)** — composes the future. Owns attention allocation and workforce health.
- **Specialists (role-cognitive)** — style the craft. Six role-typed capabilities (Researcher, Analyst, Writer, Tracker, Designer, Reporting) with role-scoped stylistic memory.
- **Agents (domain-cognitive)** — execute the work. User-created, identity-explicit, domain-scoped workers.
- **Reviewer (review-cognitive)** — occupies the independent judgment seat. Structurally separate; seat is interchangeable between human and AI without architectural change.

### The Reviewer layer's distinctness is in Purpose + Trigger, not Identity

A subtle but load-bearing clarification enabled by Axiom 0's dimensional model: the Reviewer layer is *not* distinguished from other layers by having a unique Identity. The Reviewer seat is **swappable** across three identities (human user, AI reviewer agent, admin impersonation) *precisely because* Identity is not what makes it distinct. What makes the Reviewer distinct is its Purpose (independent judgment on proposed writes) and its Trigger (reactive to proposal creation). The seat is the Purpose + Trigger cell; the filler is the Identity.

This is why ADR-194 v2 is correct to treat Reviewer as a fourth layer, and why swapping human ↔ AI in that seat requires no architectural change: the dimensions the swap preserves (Purpose, Trigger, Mechanism, Channel, Substrate) are all the same; only the Identity dimension changes.

### Identity manifests through filesystem

Per Axiom 1, identity is carried by substrate, not held in code:

- **YARNNN's identity** — `/workspace/IDENTITY.md`, `/workspace/BRAND.md`, compact index, session memory
- **Specialist identity** — ADR-117 role-keyed style distillation in `/workspace/style/{role}.md`
- **Agent identity** — `/agents/{slug}/AGENT.md` + accumulated domain context
- **Reviewer identity** — `/workspace/review/IDENTITY.md` + `principles.md` + `decisions.md`

A file without a declared author identity is an Axiom 2 violation. An agent acting without a resolvable identity is a bug.

### Development axes

Each layer develops along exactly one axis. Conflating these has been a recurring source of design error (ADR-189 resolved it for the first three; ADR-194 added the fourth):

| Layer | Develops | How |
|---|---|---|
| YARNNN | Upward — judgment about attention allocation | Workspace-level accumulation of what works for this operator |
| Specialist | Outward — stylistic preference | Role-scoped distillation of edits across every task using the specialist |
| Agent | Inward — deeper domain expertise | Accumulated memory, observations, learned preferences in its domain |
| Reviewer | Through reasoning style — capital-EV calibration | Decisions accumulate in `decisions.md`; calibration against reconciled outcomes |

---

## Axiom 3: Purpose — Intent Lives in Substrate

**Every mechanic has a Why. The Why lives in a file.**

Purpose is what intent drives the work. It is declared in substrate files:

- **Workspace purpose** — `/workspace/context/_shared/IDENTITY.md`, `/workspace/context/_shared/BRAND.md`, `/workspace/context/_shared/CONVENTIONS.md` (post-ADR-206 relocation; previously at `/workspace/` root). What the operator is building, how they think, what they care about, and the structural rules all agents honor.
- **Operation purpose** — `/workspace/context/{domain}/_operator_profile.md` + `/workspace/context/{domain}/_risk.md`. Declared rules, signals, limits — the *edge hypothesis* the operator is running. Post-ADR-206 these files are the Intent artifacts that drive the loop.
- **Task purpose** — `/tasks/{slug}/TASK.md` (objective) + `/tasks/{slug}/DELIVERABLE.md` (output specification). Why this task exists, what it produces.
- **Reviewer purpose** — `/workspace/review/principles.md`. How the independent judgment seat should reason; auto-approve thresholds, escalation rules. Post-ADR-206 this is the Reviewer's capital-EV framework the operator authors once, the Reviewer executes per-proposal.
- **Agent purpose** — `/agents/{slug}/AGENT.md`. What domain the agent owns, how it approaches its domain.
- **Domain purpose** — `/workspace/context/{domain}/_domain.md`. What this domain tracks, what entities belong in it.

### Purpose can also be carried by Identity's known context

Not every Purpose needs to be substrate-declared. When an Identity takes a well-defined action (operator uploading a PDF to Context, user clicking Approve on a ProposalCard), Purpose is inferrable from the Identity's role and the interaction shape. The model allows Purpose to be carried by Identity when not substrate-declared — Substrate is preferred for persistent purposes, Identity is sufficient for per-action purposes.

### Rule: a mechanic without Purpose is dead code

Every shipped mechanic must be answerable to the Why question. If a mechanic fires but no substrate or identity declares *why*, it is either dead code or a drift (a mechanic that once had purpose and lost it). Axiom 3 is the conscience that prevents accumulation of purposeless mechanics.

### Corollary: the operator-facing three-layer view (ADR-206)

Purpose, from the operator's perspective, is triangulated across three orthogonal layers. The layers are orthogonal to Axiom 2's four-layer cognition model (which describes *who acts*); these three describe *what the operator interacts with*.

| Layer | What it is | Where it's authored / surfaced |
|-------|-----------|--------------------------------|
| **Intent** | Declared rules, risk limits, principles, success criteria. The operator's edge hypothesis. | Authored at `/workspace/context/_shared/*` + domain `_operator_profile.md` + `_risk.md` + `/workspace/review/principles.md`. Rendered on `/context`. |
| **Deliverables** | Externalized outputs of the operation. Proposals awaiting approval, briefs, weekly reviews, `_performance.md` snapshots. | Surfaced on `/work` list-mode (primary) and `/review`. |
| **Operation** | Execution substrate: tasks, agents, reconcilers, scheduler. | Drill-down on `/work` detail mode and `/team` — second-class to the operator. |

The loop the operator runs: **Intent → Operation → Deliverables → Intent (refined).** Reports and briefs are side-effects of the loop running, not the point of the loop. Axiom 3 Purpose is first-class in the Intent layer; Axiom 2 Identity fills the Operation layer; Axiom 6 Channel renders the Deliverables layer.

Axiom 3's "Purpose can also be carried by Identity" rule maps directly here: substrate-declared Purpose lives in Intent; interaction-inferred Purpose (operator clicks Approve on a proposal) lives in the Deliverables layer's action affordance.

---

## Axiom 4: Trigger — Three Sub-Shapes of Invocation

**Every invocation has a When. Invocation is periodic, reactive, or addressed.**

Trigger is what invokes Mechanism. One dimension; three sub-shapes:

1. **Periodic** — invoked by schedule (cron). Examples: daily-update (9am UTC), back-office-agent-hygiene (daily), back-office-outcome-reconciliation (daily), workspace cleanup (daily).
2. **Reactive** — invoked by event. Examples: OAuth webhook fires → platform sync; proposal created → `review-proposal` task fires; upload POST → working memory refresh; user feedback submitted → feedback actuation.
3. **Addressed** — invoked by user (or foreign LLM via MCP). Examples: user sends chat message → YARNNN turn; user clicks Approve → `ExecuteProposal`; MCP `pull_context` call → primitive dispatch.

All three sub-shapes resolve to the same Mechanism layer — they only differ in what begins the invocation.

### No parallel dispatch systems

Per Axiom 0's anti-conflation rule, there should be exactly one dispatcher per Trigger sub-shape, not separate systems per mechanic type:

- **Periodic** → unified scheduler (`api/jobs/unified_scheduler.py`). All cron-invoked work flows through one dispatcher. ADR-141 + ADR-164 ratified this by dissolving `agent_pulse.py`, `proactive_review.py`, `platform_sync_scheduler.py` into unified cron + task pipeline.
- **Reactive** → event handlers in `api/routes/` (webhook endpoints, action-proposal triggers). Fan out to the task pipeline or direct primitives.
- **Addressed** → user-facing routes (`/chat`, `/api/proposals/*`) + MCP server (`api/mcp_server/`). All converge on `execute_primitive()`.

If a new mechanic appears to need a new dispatcher, check first whether an existing sub-shape covers it. Usually yes.

### Corollary: Run-now is the default trigger; schedule is an annotation (ADR-205)

For user-created tasks, immediate execution is the default invocation; scheduling is an optional annotation that converts a one-off task into a recurring one. Users validate work by seeing output; they decide cadence after they have something to judge. A task without a schedule is legitimate — it simply has no Periodic invocation. Modes (`recurring` / `goal` / `reactive`, per ADR-149) describe the management posture over the lifetime of the task; they do not dictate whether the first invocation is immediate or deferred.

This corollary does not introduce a fourth Trigger sub-shape. Run-now is Addressed (invoked by user action at creation time). Schedule, when added, layers Periodic on top. Axiom 4's three sub-shapes remain the complete set.

---

## Axiom 5: Mechanism — Spectrum from Code to Judgment

**Every act has a How. How varies continuously from deterministic code to LLM judgment.**

Mechanism is the means by which work happens. One dimension with a spectrum:

| Position on spectrum | Character | Examples |
|---|---|---|
| **Fully deterministic** | Pure Python, zero LLM. Output is a function of input. | Daily-update empty-state template, `_performance.md` frontmatter folding, workspace cleanup, section-kind renderers, risk-gate rule checks, PostgREST queries |
| **Mixed** | LLM with tight structural contract. Output shape is declared; content is judged. | Inference (IDENTITY.md, BRAND.md, context domains), `review-proposal` task with capital-EV prompt, compose substrate's section generation |
| **Fully judgment** | LLM orchestrating with broad latitude. Output is the model's call. | YARNNN chat-mode turns, Agent task-pipeline runs, YARNNN's autonomous workforce composition |

These map cleanly to ADR-141's three-layer execution model (Mechanical / Generation / Orchestration) — which is revealed by Axiom 0 not as three separate dimensions, but as **three points on the Mechanism spectrum within one dimension.** ADR-141 stands; its framing is clarified.

### Primitives are the vocabulary of Mechanism

LLM reasoning in YARNNN speaks through primitives — typed verbs with substrate and permission scope (see [primitives-matrix.md](primitives-matrix.md)). Primitive design is the engineering of Mechanism's vocabulary:

- **Adding a primitive** = extending Mechanism's vocabulary. Requires ADR + rename protocol sweep (CLAUDE.md rule 7b).
- **Scoping a primitive by mode** (chat / headless / MCP) = restricting which Identity can use which vocabulary word.
- **Prompting strategy** = configuring which vocabulary words the LLM reaches for, in which situations. Prompt profiles (ADR-186) are the configuration surface.

**Tool use and prompting are not separate concerns.** They are the two halves of Mechanism's judgment spectrum — prompts shape the reasoning, primitives are the output grammar. Designing one without the other is a dimensional conflation.

### The loosening rule (Spectrum B from YARNNN-DESIGN-PRINCIPLES)

Mechanism loosens over time. Today's codebase is procedural-heavy (pre-gather → single generation → compose → deliver). The direction of travel is toward more judgment at the Mechanism layer, but this loosening is gated by the Reviewer layer (Axiom 2) — independent judgment over proposed writes is what makes runtime autonomy safe.

Substrate rules tighten over time (Axiom 1). Mechanism rules loosen. These are the two spectrums YARNNN-DESIGN-PRINCIPLES names.

---

## Axiom 6: Channel — Output Is Addressed

**Every act has a Where. Where is either Substrate itself or an addressed destination.**

Channel is where output goes. Two sub-shapes:

1. **Substrate-return** — output is written to the filesystem and becomes part of accumulation. Examples: task pipeline writes `/tasks/{slug}/outputs/`; reconciler writes `_performance.md`; Reviewer writes `decisions.md`; feedback actuation writes `memory/feedback.md`. No external addressing.
2. **Addressed** — output is delivered to a cognitive consumer outside the substrate. Examples: email to operator; Slack/Notion/GitHub write-back to platform; ProposalCard rendered in chat; surface view in `/work` or `/agents` or `/context`; platform write-back via `submit_order`, `create_discount_code`, `send_email`.

### Addressed channels have subcategories by cognitive consumer

Axiom 2 says every Identity has a distinct scope. Addressed channels inherit this — the cognitive consumer determines the channel's affordance:

| Consumer | Channel shape | Examples |
|---|---|---|
| Operator (human user) | Surfaces + email | Chat surface, Work surface, Agents surface, Context surface, daily-update email, ProposalCard |
| External platform | Platform API writes | Slack post, Notion block write, Alpaca order submit, Lemon Squeezy discount creation |
| Another Identity within YARNNN | Substrate (see sub-shape 1) | Agent writes to `/workspace/context/` that Reviewer later reads; YARNNN writes `awareness.md` that next chat turn reads |
| Foreign LLM (via MCP) | MCP response to `pull_context` / `work_on_this` / `remember_this` | QueryKnowledge results, composed subject bundles |

### Channel ≠ Mechanism

Compose substrate (ADR-170 / ADR-177) sits at the joint between Mechanism and Channel:
- **Rendering HTML to a file** = Mechanism (substrate-return Channel)
- **Addressing that HTML to a surface or email** = Channel (different consumer, same file)

The file is the durable artifact (Substrate). The rendering is how it was produced (Mechanism). The delivery routing is where it goes (Channel). Three dimensions, one artifact. Compose substrate is the legitimate cross-cut that deliberately couples Mechanism + Channel — and its legitimacy is justified by the singular output-substrate argument in ADR-148 + ADR-170.

Cross-cuts are not always errors. They are errors when unjustified.

---

## Axiom 7: Recursion — The Six Dimensions Compose Over Time

**When the six compose, accumulation happens. Accumulation is the compounding mechanism.**

Recursion is not a seventh dimension. It is what the first six *do* over time. One cycle of the architecture:

```
Trigger (when)
  → Identity + Purpose decide what matters (who + why)
    → Mechanism reads Substrate, reasons, produces output (how, reading what)
      → Channel addresses output to destination (where)
        → Substrate accumulates (what, extended)
          → next Trigger reads richer Substrate ...
```

The cycle is the architecture. Every mechanic participates; some mechanics visit all six cells in one firing (task pipeline), some visit a subset (cleanup cron: Trigger + Substrate + Mechanism).

### Four layers of recursive perception

Perception is Substrate-read (Axiom 1) with zero Mechanism. Four layers of perception feed each Mechanism cycle:

1. **External perception** — Agents call platform APIs (Slack, Notion, GitHub, Alpaca, LS) live during task execution. Raw platform signals processed by agents and written as structured context to `/workspace/context/` domains. Per Axiom 1, no intermediate staging table (ADR-153: `platform_content` sunset).

2. **User-contributed perception** — uploaded documents in `/workspace/uploads/`. Permanent reference material the user explicitly shares. Triggers inference to update workspace context (IDENTITY.md, BRAND.md).

3. **Internal perception** — accumulated workspace context at `/workspace/context/` + task outputs in `/tasks/{slug}/outputs/`. Each run's output feeds the next run's context. Context domains accumulate cross-task intelligence that any Identity can draw from.

4. **Reflexive perception** — user feedback (edits, approvals, dismissals, conversational corrections), YARNNN's observations (`/workspace/notes.md`, `/workspace/style.md`), Reviewer decisions (`/workspace/review/decisions.md`), money-truth reconciliation (`_performance.md`). As time progresses, this accumulated judgment becomes the most valuable signal — more valuable than raw platform data.

### Three substrates for coherence

Perception flows through three distinct **views onto the same filesystem substrate** (Axiom 1) that must stay coherent:

1. **Conversation** — sessions, chat messages, compaction (`/workspace/awareness.md` + session records). What was said.
2. **Filesystem** — workspace files (`AGENT.md`, `memory/`, `TASK.md`, cognitive files, context domains). What the system knows.
3. **Agent cognition** — role prompts, task process declarations, execution strategies. How agents think (this is Mechanism reading Substrate).

Three views are not hierarchical. Intelligence degrades when they fall out of sync: a user directive in conversation that doesn't reach the filesystem evaporates on session rotation; an assessment in the filesystem that agents can't read produces blind spots.

### The recursive property

```
External platforms → live API calls → agent execution → task output →
  /tasks/{slug}/outputs/ + /workspace/context/ → next agent execution → ...
       ↑                                          |
       └── user uploads (/workspace/uploads/) ────┘
       └── user feedback (/workspace/style.md) ──┘
       └── Reviewer decisions (/workspace/review/decisions.md) ─┘
       └── money-truth (_performance.md) ────────┘
       └── YARNNN observations (/workspace/notes.md) ─┘
```

The workspace filesystem acts as an **operating system for agent and human work** — a shared substrate where both contribute and both consume. The filesystem IS the information architecture.

### Implication: Optimize for accumulation, not extraction

External platform integrations are the onramp. The enduring value is in the recursive accumulation: agent memory, learned preferences, domain theses, cross-agent insights. As LLM capabilities improve, the quality of each recursive cycle improves — the system's reasoning gets better at the same substrate. This compounds. Architecture decisions should prioritize the health of this recursive loop over the breadth of external integrations.

---

## Axiom 8: Money-Truth — Substrate Must Carry Reconciled Capital Reality

**Revenue, P&L, and reconciled outcomes belong in the filesystem, per domain, per operator, per cycle.**

YARNNN is not just a knowledge-work platform — it is an **action platform**. Per ADR-192 + ADR-193, agents can write to external platforms (trading orders, commerce product updates, campaign emails). Those writes have capital consequences. The system must close the loop: every action must be reconciled against external reality and the reconciled outcome must live in Substrate where Reviewer, YARNNN, and the operator can read it.

### Canonical home

`/workspace/context/{domain}/_performance.md` per domain. Authored by the daily back-office reconciler (ADR-195 v2). Read by Reviewer (for EV reasoning on proposals), daily-update (for linked pointers, per ADR-198), YARNNN (for workforce judgment), and the operator (via Context surface).

### Three structural properties of money-truth substrate

1. **Reconciled from external reality.** Money-truth is not what YARNNN or the agent *said* happened. It is what the platform API *confirms* happened — order fills, refunds, delivery receipts, subscription events. Reconciliation is the mechanism (`OutcomeProvider` ABC in `api/services/outcomes/`).
2. **Filesystem-native.** Per Axiom 1. No sibling SQL ledger. `action_outcomes` table was dropped by ADR-195 v2 + ADR-196 for this reason.
3. **Idempotent under replay.** Reconciler can run any number of times; output is deterministic modulo platform history. Idempotency via `processed_event_keys` in file frontmatter.

### Three asymmetric bets money-truth substrate enables

1. **The AI Reviewer can reason in capital-EV.** Without `_performance.md`, AI-reviewed decisions collapse to rule-checking. With it, the Reviewer can reason "you're already 40% tech-concentrated, this trade is outside your edge" — capital-EV judgment.
2. **Revenue becomes perception, not infrastructure.** Per ADR-184, product health (revenue, subscribers, churn) flows into the workspace as context domains. The operator's capital trajectory is legible to the same cognitive layers that read every other perception.
3. **Accumulation compounds across action.** A tenured agent + accumulated `_performance.md` is a different product than a tenured agent without. The capital-reconciled substrate is what makes "the team gets better at its job, measured by revenue" a structurally grounded claim rather than a marketing line.

### Revenue as external validation of accumulated attention

Accumulated attention (Axiom 7) is invisible without external validation. For content product businesses, **revenue is the proof that accumulated attention has value.** If quality genuinely improves over time, subscribers notice, retention rises, revenue grows. Switching to any other tool means starting from zero context — quality regresses, revenue declines.

Three-tier metrics hierarchy (ADR-184): product health (revenue, subscribers, churn) is upstream, driven by task quality, driven by agent health. Revenue trajectory *is* the quality metric — not a separate business concern, but the measurable consequence of accumulated attention.

---

## Derived Principles

These follow from the axioms and are stated explicitly for implementation guidance:

1. **Dimensional purity** — No mechanic should span dimensions without explicit justification. When a design decision conflates dimensions (e.g., ADR-195 v2 Phase 4's proposed briefing-absorbs-performance), the conflation is caught by the dimensional test and redesigned. Cross-cuts are legitimate only when argued for (e.g., compose substrate deliberately couples Mechanism + Channel per ADR-148's singular-rendering-path argument).

2. **Substrate is the shared OS** — All persistent state lives in the filesystem roots: `/workspace/` (user context + uploads + accumulated domains + review + awareness), `/agents/{slug}/` (identity + memory), `/tasks/{slug}/` (work + outputs). New capabilities extend paths, not database tables.

3. **Agents are the write path** — All modifications to workspace files flow through Identity-authored primitive calls, not direct user manipulation. The frontend is read-only on workspace (operator feedback is routed through primitive calls). User intent goes through YARNNN → agents. This protects the structural conventions.

4. **Accumulation over extraction** — Prioritize the health of the recursive accumulation loop (Axiom 7) over the breadth of external integrations. Internal and reflexive perception layers are more valuable long-term than the external layer.

5. **Identity develops by its axis; capability is fixed** — Each cognitive layer develops along one axis (YARNNN upward, Specialists outward, Agents inward, Reviewer through calibration). Capabilities are not earned through seniority — they are fixed at creation per the three-registry architecture (ADR-130).

6. **Feedback is perception** — User edits, approvals, and dismissals are first-class Reflexive-perception signals, equivalent in architectural importance to platform data. They drive both Agent development (Axiom 2) and YARNNN's compositional judgment (Mechanism spectrum).

7. **Singular implementation** — One way to do things. If YARNNN composes, there is no separate Composer. If tasks subsume scheduling, there is no parallel trigger system. If the Reviewer seat is a Purpose + Trigger cell, there is no `Reviewer` ABC (resolved by ADR-194 v2).

8. **Work is bounded** — Autonomous work (agent runs, assemblies, renders) consumes tokens (ADR-171) and balance (ADR-172). The `balance_usd` gate is the sole budget — no parallel tier limits.

9. **Mechanism is a spectrum, not a split** — ADR-141's three layers (mechanical / generation / orchestration) are three points on Mechanism's determinism-to-judgment spectrum, within one dimension. Primitives + prompts are the two halves of Mechanism's vocabulary — designing one without the other is a dimensional conflation.

10. **Registries are template libraries, not validation gates** — The task type registry, directory registry, and agent templates are curated libraries of domain-specific patterns (ADR-188). YARNNN can draw from them or compose novel definitions. The execution pipeline reads workspace files (TASK.md, AGENT.md, `_domain.md`) at runtime, not the registries.

11. **Substrate tightens; Mechanism loosens** — Over time, Axiom 1's substrate discipline grows stricter (fewer DB tables holding semantic content, cleaner file conventions). Axiom 5's mechanism grows looser (more agent autonomy, less procedural scaffolding). The Reviewer layer (Axiom 2) is the pivot that makes Mechanism loosening safe. See [YARNNN-DESIGN-PRINCIPLES.md](YARNNN-DESIGN-PRINCIPLES.md) "The Two Spectrums."

12. **Channel legibility gates autonomy** — Autonomous writes must have a legible Channel back to the operator (approval UX, daily-update pointers, dedicated surfaces). An action without a visible channel is a trust leak — the operator cannot supervise what they cannot see. This is why surface archetype design (ADR-198) is load-bearing for the autonomous-operator ICP.

---

## Relationship to Existing ADRs

Ax 0 (dimensional model) was the missing frame — its introduction does not invalidate prior ADRs, only clarifies their placement. The table below maps key ADRs to the dimension(s) they primarily touch.

| ADR | Primary dimension(s) | Status under v6.0 |
|-----|---------------------|------------------|
| ADR-106 (Workspace) | Substrate | Foundational — Axiom 1 implementation |
| ADR-138 (Agents as Work Units) | Identity + Purpose | Aligned |
| ADR-141 (Execution Architecture) | Trigger + Mechanism | Aligned — three layers = Mechanism spectrum (Principle 9) |
| ADR-146 + ADR-168 (Primitive Matrix) | Mechanism | Aligned — primitives are Mechanism vocabulary |
| ADR-151 + ADR-152 + ADR-158 (Context Domains) | Substrate | Aligned |
| ADR-153 (platform_content Sunset) | Substrate | Axiom 1 correction shipped |
| ADR-156 (Composer Sunset) | Identity + Mechanism | Aligned — singular-implementation (Principle 7) |
| ADR-161 (Daily Update Anchor) | Trigger + Channel + Purpose | Aligned |
| ADR-163 (Surface Restructure) | Channel | Aligned — precursor to ADR-198 archetypes |
| ADR-164 (Back Office Tasks) | Identity + Trigger | Aligned — YARNNN is Identity, back-office is Trigger sub-shape |
| ADR-166 (Registry Coherence) | Purpose | Aligned — output_kind is a Purpose property |
| ADR-168 (Primitive Matrix) | Mechanism | Aligned — substrate × mode × capability = Mechanism × Identity scoping |
| ADR-169 (MCP as Context Hub) | Trigger (addressed) + Mechanism + Channel | Aligned — MCP is a third caller of `execute_primitive()` |
| ADR-170 (Compose Substrate) | Mechanism + Channel (legitimate cross-cut) | Aligned — justified by singular-rendering (ADR-148) |
| ADR-171 (Token Metering) | Substrate (audit ledger, permitted kind 2) | Aligned |
| ADR-181 (Feedback Layer) | Substrate (feedback.md) + Mechanism (actuation) | Aligned |
| ADR-183 + ADR-184 (Commerce + Product Health) | Substrate (money-truth) | Aligned — Axiom 8 content |
| ADR-186 (Prompt Profiles) | Mechanism (prompt config) + Identity (profile per surface) | Aligned |
| ADR-188 (Domain-Agnostic Framework) | Purpose + Substrate | Aligned — registries as templates (Principle 10) |
| ADR-189 (Three-Layer Cognition) | Identity | Aligned — expanded to four layers by ADR-194 |
| ADR-193 (ProposeAction + Approval Loop) | Trigger (reactive) + Channel (Queue) | Aligned |
| ADR-194 v2 (Reviewer Layer) | Identity + Purpose + Trigger | Aligned — Reviewer distinctness is Purpose+Trigger (Axiom 2 clarification) |
| ADR-195 v2 (Money-Truth Substrate) | Substrate | Axiom 8 content |
| ADR-196 + ADR-197 (Legacy Table Sunsets) | Substrate | Axiom 1 correction |
| ADR-198 (Surface Archetypes) | Channel | Aligned — five archetypes = five substrate-consumer-purpose cells |

Any ADR that cannot be mapped to one or more dimensions is either incomplete or drifted — the dimensional test flags it for revision.

---

## Open Questions

Carried forward from v5.1, updated for v6.0:

1. **Agent evolution mechanics** — When an agent's domain expands (a Slack digest agent starts also monitoring email threads from the same team), does it become a new agent or does the existing agent's scope expand? Who decides? (Identity dimension — specifically, how Identity's scope mutates over time.)

2. **Surface composition at scale** — ADR-198's five archetypes map to four nav tabs. As operator workflows mature, does a sixth archetype emerge (e.g., Alerts as distinct from Queue)? How does the nav structure absorb this without fragmenting Channel? (Channel dimension, scale question.)

3. **Mechanism loosening rate** — Principle 11 says Mechanism loosens over time. What signal triggers the next loosening step (more agent autonomy within a task run, multi-round reasoning, filesystem browsing)? The Reviewer layer gates safety, but the *pacing* of loosening is open. (Mechanism dimension, direction of travel.)

4. **Multi-workspace for polymath operators** — ADR-191 commits to polymath-operator ICP. When an operator runs multiple businesses on one YARNNN account, is each a separate workspace or sub-scopes of one? How do the six dimensions behave under nesting? (Cross-cutting — Substrate nesting affects Identity, Purpose, Channel.)

5. **Display vs. Substrate-rendering boundary** — Principle 12 says autonomous writes need legible Channel. When a surface renders a filesystem file, where does Substrate-read end and Channel begin? ADR-198's Invariant I2 (no surface embeds foreign substrate) is a first cut; real surface work will surface edge cases. (Channel dimension, boundary question.)

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-15 | v1 — Initial axioms: one intelligence, recursive perception, accumulated attention, taxonomy as configuration, TP subsumes orchestration, autonomy as direction |
| 2026-03-15 | v2 — Two-layer intelligence model (TP meta-cognitive + agent domain-cognitive), agent developmental trajectory (intentions, capabilities, autonomy), recursive perception expanded |
| 2026-03-18 | v3 — Project execution evolution: PM as domain-cognitive agent, project-level intentions, Composer/PM separation, agents-as-write-path, work-is-bounded, project autonomous flow |
| 2026-03-19 | v3.1 — ADR-123 terminology: `intent` → `objective`, intentions consolidated into PM `memory/work_plan.md` |
| 2026-03-20 | v3.2 — PM for all projects; agents produce, projects deliver |
| 2026-03-20 | v3.3 — Agent Pulse (ADR-126); proactive/coordinator modes dissolved; autonomous flow updated |
| 2026-03-21 | v3.4 — Multi-Agent Coherence Protocol (ADR-128); three intelligence substrates |
| 2026-03-22 | v3.5 — Three-registry architecture (ADR-130); seniority-gated progression removed |
| 2026-03-23 | v3.6 — Work-First Onboarding (ADR-132) |
| 2026-03-24 | v3.7 — Project Charter Architecture (ADR-136) |
| 2026-03-24 | v3.8 — Declarative Pipeline Execution (ADR-137) |
| 2026-03-25 | v4.0 — ADR-138 project layer collapse. PM dissolved into TP. Projects replaced by tasks. |
| 2026-03-25 | v4.1 — Mode moves from agents to tasks (ADR-138 revision) |
| 2026-03-25 | v4.2 — Unified filesystem (ADR-142); four perception layers |
| 2026-03-31 | v4.3 — platform_content sunset (ADR-153); agents call platform APIs live |
| 2026-04-15 | v4.4 — Commerce substrate + product health metrics (ADR-183, ADR-184) |
| 2026-04-17 | v4.5 — Domain-agnostic framework (ADR-188); universal roles, contextual application |
| 2026-04-17 | v5.0 — Three-layer cognition (ADR-189); YARNNN / Specialist / Agent |
| 2026-04-19 | v5.1 — Axiom 0 added (filesystem is substrate); Axiom 1 extended to four layers (Reviewer); Axiom 7 money-truth |
| 2026-04-20 | v6.0 — **Complete restructure.** Axiom 0 reframed as the dimensional model: six orthogonal dimensions (Substrate / Identity / Purpose / Trigger / Mechanism / Channel) derived from the interrogative test (What / Who / Why / When / How / Where). Previous axioms recast: v5.1 Axiom 0 → Axiom 1 (Substrate); v5.1 Axiom 1 → Axiom 2 (Identity) with Reviewer-is-Purpose+Trigger clarification; new Axiom 3 (Purpose); new Axiom 4 (Trigger); new Axiom 5 (Mechanism as spectrum, including primitives+prompts); new Axiom 6 (Channel); v5.1 Axiom 2 → Axiom 7 (Recursion, now derivable from six-dimensional composition); v5.1 Axiom 7 → Axiom 8 (Money-Truth). Derived Principles re-numbered; three new principles (9: Mechanism is a spectrum; 11: Substrate tightens / Mechanism loosens; 12: Channel legibility gates autonomy). Relationship-to-ADRs table rewritten as dimension-mapping. The stress test that produced this rewrite resolved six real scenarios; the model survived with two refinements (Purpose can live in Substrate or Identity; Mechanism is a determinism-spectrum not a split). See [YARNNN-DESIGN-PRINCIPLES.md](YARNNN-DESIGN-PRINCIPLES.md) for Spectrum A/B framing that sits beneath Principle 11. |
