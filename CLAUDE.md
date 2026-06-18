# CLAUDE.md - Development Guidelines for YARNNN

This file provides context and guidelines for Claude Code when working on this codebase.

## Project Overview

YARNNN is an **autonomous agent platform for recurring knowledge work**. Persistent AI agents connect to work platforms (Slack, Notion), run on schedule, learn from feedback, and produce outputs that improve with tenure.

**Architecture**: Next.js frontend → FastAPI backend → Supabase (Postgres) → Claude API. Agents (identity) + Tasks (work units) as core model.

> **OS framing note (as of 2026-04-27, ADR-222 + FOUNDATIONS Principle 16)**: YARNNN is canonized as an **agent-native operating system**. The substrate (filesystem + primitives + axioms + privileged daemons) is the **kernel**; the primitive matrix is the **syscall ABI**; the chat agent is the **shell**; workspaces are **userspaces**; programs (alpha-trader, etc.) are **applications** running in userspace; their bundle (`docs/programs/{program}/`) is an `.app`-equivalent (manifest + reference workspace + composition manifest); a **compositor** layer (forthcoming) reads program-shipped composition manifests against substrate to render the cockpit. The kernel boundary is sacred — programs do not modify the kernel; the shell is application code; the compositor reads but never authors. Workspaces don't have "types" — they run programs; the program declaration is the implicit type; specialization happens at the compositor, not the kernel. See [ADR-222](docs/adr/ADR-222-agent-native-operating-system-framing.md) + [FOUNDATIONS Principle 16](docs/architecture/FOUNDATIONS.md) + [GLOSSARY "Operating System Framing"](docs/architecture/GLOSSARY.md) + [docs/programs/](docs/programs/README.md) + [implementation roadmap](docs/architecture/os-framing-implementation-roadmap.md).

> **Surface model addendum (as of 2026-06-02, ADR-308 + ADR-309 + ADR-312)**: the authenticated workspace is an OS Desktop with **three windowed registers, one window manager** (`useSurfacePreferences`). ADR-312 D5 cleaved ADR-309's single `settings` register into **`intent`** (the operation's authored intent — the *constitution*: Mandate, Principles, Identity; surfaced first-class as the Home's Constitution band, NOT a config drawer) + **`os-config`** (the OS configuring itself: Autonomy, Pace, Connectors, Program, Settings); content parsers in `web/lib/content-shapes/`. **Applications** (`register: application`) = open files + live state (Files, **Home**, Feed, Queue, Activity, Agents, Cadence). **The Cockpit dissolves into Home** (ADR-312 D1): `slug: home`, route `/home`, `HomeRenderer`/`HomeHeader` — a *composition over the workspace's present constituents* (six kernel slots: constitution band · ground-truth hero · decision queue · live entities · recent artifacts · judgment trail; the program weights/labels/shapes them via SURFACES.yaml `home.program_sections`, never invents slots, the kernel never hardcodes a program noun). Substrate-forward when empty (the constitution-band CTA is onboarding/activation), operation-forward when a program runs. Slot #2's ground-truth hero is GENERIC (`CANONICAL_L3='GroundTruthHero'`); `TraderMoneyTruth` is the alpha-trader binding (D3). Trader-data routes are program-scoped (`/api/programs/alpha-trader/*`); pace is a kernel governance dial (`/api/pace`) — D9. **Artifacts are files, not surfaces** — a Reviewer-generated report/PDF is substrate opened by a viewer Application via the **type→application association** (`web/lib/file-types::resolveViewerApplication`, the OS "which app opens this type" layer); the report Application is `DeliverableMiddle`. **Redirect stubs are pure server transport** (`redirect()`, ADR-308) — never `'use client'` + `useEffect` redirects, which paint an orphaned frame inside the OS shell. `brand` is NOT a surface (Identity co-renders Brand; `/brand` → `/identity`). **Agent-composed Applications** (the agent writing an app-manifest file in pursuit of the mandate) is the ratified-but-deferred horizon. See [ADR-312](docs/adr/ADR-312-home-as-composition.md) + [ADR-309](docs/adr/ADR-309-two-registers-settings-and-applications.md) + [ADR-308](docs/adr/ADR-308-redirect-stubs-as-pure-transport.md) + [compositor.md](docs/architecture/compositor.md).

> **Vocabulary note (as of 2026-04-24, ADR-216 reframe)**: "Agent" in YARNNN canon means a **persona-bearing judgment entity** — Reviewer and user-authored domain Agents. YARNNN is the **orchestration chat surface**, not an Agent (reclassified by ADR-216 from ADR-212 D1). Production machinery (task pipeline, production roles like Researcher/Writer/etc., platform integrations, YARNNN chat surface) is **Orchestration**, not persona-bearing. See [docs/architecture/LAYER-MAPPING.md](docs/architecture/LAYER-MAPPING.md) + [ADR-216](docs/adr/ADR-216-orchestration-surface-vs-judgment-persona.md) for the authoritative taxonomy. Historical ADR summaries below may use pre-flip vocabulary ("Specialist" / "Platform Bot" as entity terms, or YARNNN-as-Agent); those are historical artifacts preserved verbatim — for current framing read the Key terminology section below.

**Key terminology** (current canon, 2026-04-24 — ADR-216 Orchestration-vs-Judgment reframe):

> **Authoritative taxonomy**: [docs/architecture/LAYER-MAPPING.md](docs/architecture/LAYER-MAPPING.md) + [ADR-216](docs/adr/ADR-216-orchestration-surface-vs-judgment-persona.md). The definitions below are the quick-reference; LAYER-MAPPING + ADR-216 are the deep ones. Historical ADR summaries below may use pre-flip vocabulary (Specialist, Platform Bot as entity terms, YARNNN-as-Agent); those are preserved as historical artifact — for current framing, read this section and LAYER-MAPPING + ADR-216 first.

- **Agent** (= **persona-bearing judgment entity**) — holds standing intent on behalf of the operator (the principal). Reasons from operator-authored persona (`IDENTITY.md`) + principles (the framework the persona applies) + substrate (data the persona reasons against). **Persona-read at reasoning time is load-bearing** (ADR-216 Commit 2). Two classes:
  - **Reviewer** — the *sole* systemic persona-bearing Agent, one per workspace. Independent judgment on proposed actions. Substrate at `/workspace/review/`. IDENTITY.md declares the persona (generic default at signup; operator overwrites to embody a specific judgment character — Simons, Buffett, Deming, or operator-authored original). principles.md declares the evaluation framework. Future systemic Agents (Auditor, Advocate, etc.) will be additional persona-bearing members, registered in `api/services/orchestration.py`.
  - **User-authored domain Agents** — instance Agents, zero-to-many per workspace, user-authored through YARNNN chat. On `/agents`. Each has its own IDENTITY.md + persona content.
- **YARNNN** (= **orchestration chat surface**, NOT a persona-bearing Agent per ADR-216). The conversational façade of the orchestrator — how the operator drives the system. Platform-authored fixed-voice interlocutor (in `api/agents/prompts/base.py`), no workspace-authored IDENTITY file. Retains an `agents` table row with `role='thinking_partner'` as pragmatic implementation substrate (chat session state + continuity); the row is implementation, the classification is architectural. Still surfaces as a card on `/agents` for discoverability, labeled as orchestration surface. Scaffolded at signup.
- **Persona** — operator-authored judgment character for a persona-bearing Agent. Embodied in `IDENTITY.md` at the Agent's canonical path. Read at reasoning time. Distinct from *principles* (the framework the persona applies) and *role* (the seat's structural function). Swappable per workspace: one workspace's Reviewer can embody Simons, another's Buffett, with identical seat structure and distinct output distributions. **The persona is the axis on which Agents self-improve.**
- **Orchestration** — production machinery (task pipeline, dispatch routing, capability bundles, back-office scheduling, YARNNN chat surface). Stateless infrastructure, no standing intent, never personified. Never persona-bearing. Performance-fungible (swap one orchestrator for another and work executes the same way).
  - **Orchestrator** — the system-level dispatch machinery that Agents use to get production work done.
  - **Production roles** — orchestration capability bundles: `researcher`, `analyst`, `writer`, `tracker`, `designer`, `reporting` (synthesizer). NOT Agents. Packaged production configurations. Registered in `PRODUCTION_ROLES`. (Previously called "Specialists" — retired as entity term.)
  - **Platform integrations** — orchestration capability bundles for platform APIs (Slack, Notion, GitHub, Commerce, Trading). NOT Agents. Capability-gated by active `platform_connections` per ADR-207 P4a. (Previously called "Platform Bots" — retired as entity term.)
- **Enum-slug exceptions** (GLOSSARY): internal enum strings `"specialist"` (Python `class` field + API `agent_class` + frontend TS type + `authored_by="specialist:<role>"` revision data) and `"platform-bot"` (same cross-cutting pattern) are retained as data-compatibility slugs. The **human-readable concept** is "production role" / "platform integration"; the **enum string** is stable for code dispatch + data format.
- **Task** — a **nameplate + pulse + contract** attached to a category of recurring, goal-bounded, or reactive invocations (FOUNDATIONS Axiom 9 Clause C, 2026-04-25). Nameplate = slug + `/tasks/{slug}/TASK.md`. Pulse = the future trigger shape (schedule, reactive event, or none). Contract = `DELIVERABLE.md` (for `produces_deliverable`) or context-domain mapping (for `accumulates_context`). Team (Agents + production roles) assigned via `## Team` section. `/work` is the narrative filtered by task slug, not a parallel log. Thin `tasks` DB table for scheduling.
- **Invocation** — one cycle through the six dimensions; the atom of action (FOUNDATIONS Axiom 9 Clause A, 2026-04-25). Actor-class-agnostic: Agents, YARNNN orchestration surface, production roles, platform integrations, and external MCP callers all emit invocations of the same shape. Logged three places: `agent_runs` row (audit), substrate writes (the work), narrative entry (operator-legible surface).
- **Pulse** — the actor-scoped vocabulary wrapper around Axiom 4 Trigger. Four sub-shapes: **periodic** (cron), **reactive** (event), **addressed** (user or MCP call), **heartbeat** (liveness ping — design-intent flavor of periodic). Not a new dimension; Trigger through the Identity lens. Reviewer is reactive-pulsed; YARNNN is addressed-pulsed; a recurring task carries a periodic pulse on its assigned Agent.
- **Narrative** — the single chat-shaped operator-facing log of every invocation (FOUNDATIONS Axiom 9 Clause B). `/chat` is the narrative surface; the operator's own messages are one thread among many. Every invocation emits a narrative entry; rendering weight (material / routine / housekeeping) is UI policy, logging is complete. See [docs/architecture/invocation-and-narrative.md](docs/architecture/invocation-and-narrative.md).
- **Inline action** — an invocation without a task nameplate. "Pull today's revenue" is an inline action; "do that every morning" graduates it into a task by attaching a nameplate + pulse. Transition is gradient and reversible.
- **Agent Run** — a single execution of an Agent / production-role on behalf of a task, producing draft/final content. One invocation = one agent run row (audit ledger).
- **Workfloor** — the shared workspace substrate. `/workspace/` (context + memory + Reviewer seat), `/agents/` (instance Agents), `/tasks/` (work). Reviewer (systemic) is path-named by role (`/workspace/review/`); instance Agents slug-named (`/agents/{slug}/`). YARNNN as orchestration surface has no workspace persona path.
- **Context Domains** — accumulated intelligence at `/workspace/context/{domain}/`. Created by work demand, not pre-scaffolded. Shared across all tasks.
- **Mandate** — the operator's authored Primary-Action declaration at `/workspace/context/_shared/MANDATE.md` (ADR-207). Hard gate on task creation.

## The Two Hats: System Editor vs External Developer of the System

YARNNN is an Agent OS. Real operators of YARNNN interact via the cockpit + chat surface; the system runs Reviewer + System Agent + Orchestration + substrate + governance on their behalf. **All of that — every file under `api/`, `web/`, every ADR, every architecture doc, every bundle reference-workspace — is INSIDE the system.** That's the world FOUNDATIONS describes.

There is a separate surface — the **external developer surface** — that exists only because we are still iterating on YARNNN. It comprises the operator-proxy capability (ADR-294), scripted scenarios + evaluations (`docs/evaluations/`, renamed from `docs/observations/` 2026-05-26 per criterion-declaration discipline — see `docs/evaluations/README.md` §"Why 'evaluations' and not 'observations'"), ADR drafts before they ratify, the human developer (KVK), and Claude as a collaborator. **None of this ships to real operators.** It is the toolchain through which YARNNN's canon evolves.

**Two hats. Don't conflate them.**

### Hat A — System Editor

When working in any of these locations, you are editing the system real operators will inherit:
- `api/services/`, `api/agents/`, `api/routes/`, `api/services/primitives/`, `api/scripts/alpha_ops/` (yes — alpha-ops orchestrates real persona workspaces)
- `web/` (frontend cockpit)
- `docs/adr/`, `docs/architecture/`, `docs/programs/{program}/` (canon + bundles)
- `api/prompts/CHANGELOG.md` (LLM-facing behavior)
- Any bundle reference-workspace file (`docs/programs/{program}/reference-workspace/**`)

System-hat discipline:
- Speak in system vocabulary (Reviewer, operator, substrate, gating). Do NOT introduce "developer," "Claude," "observation" as system actors.
- Singular implementation, doc-first ADR amendments, full Render parity check.
- The change ships through git → Render deploy → real operator workspaces.

### Hat B — External Developer of the System

When working in these locations, you are operating the developer toolchain that probes + iterates on the system:
- `api/services/operator_proxy/`, `api/scripts/operator/` (the harness)
- `docs/evaluations/` (scenarios + captures + findings)
- Pre-ratification ADR drafts (after ratification they're system canon)

Developer-hat discipline:
- Speak in evaluation vocabulary (scenarios, expected vs observed, hypotheses, findings).
- A finding here recommends system-side changes; it does not make them. The *fix* lands in Hat A territory.
- Don't introduce concepts that only make sense to developers into the system's vocabulary. If a recommendation requires a new primitive / axiom / ADR, that primitive/axiom/ADR lives in Hat A docs after ratification.

### Crossing hats inside one session

The hat distinction is directional, not ceremonial. The discipline that matters is **substrate-receipts under every load-bearing claim** — revision_ids, execution_event ids, wake_queue ids, reproducible queries. A claim without a receipt is narrative, not evidence; that's the drift the discipline exists to prevent.

When the same session both surfaces a finding and lands the fix: use whichever commit shape produces honest commits. Small + obvious + named in-canon precedent → cross-over in a single commit is fine. Anything that benefits from operator sign-off, multi-module changes, or design discussion → separate commits. The goal is not single-author optimism (same author finds the bug and validates the fix as one indivisible motion); the goal is not commit-counting ceremony either.

### Why the hats matter for autonomy

The Agent-OS aspiration is full autonomy: the Reviewer can take capital actions AND meta-aware-edit every operator-canon file (principles, mandate, risk envelope, ground-truth) on its own initiative, under in-system discipline + audit trail + revertibility. The current ADR-293 lock-set on three governance files (`AUTONOMY.md` + `_autonomy.yaml` + `_token_budget.yaml`) is **current dev-trust state**, not permanent architecture. As we harden the Reviewer's self-amendment discipline through Hat-A edits (validated *via* Hat-B evaluation runs), the lock-set should shrink toward zero.

**Wake architecture (ADR-296 v2, fully Implemented 2026-05-20).** The Reviewer is event-fired, not continuously-running. Five wake sources (`cron_tick | addressed | proposal_arrival | substrate_event | manual_fire`) contribute proposals to one evaluation funnel (`services/wake_evaluation.py`); the Reviewer fires only on escalation. The Reviewer's authority is over **cadence preference** (Schedule) + **standing intent** (WriteFile to `/workspace/review/standing_intent.md`) + **substrate-event hooks** (ManageHook) — NOT over invoking itself. **FireInvocation removed from `REVIEWER_PRIMITIVES` per D3**; FireInvocation remains in `CHAT_PRIMITIVES` for operator-initiated manual fire. Singular invocation gateway: `services/wake.py::submit_wake_proposal(source, payload)` (and `stream_addressed_wake(...)` for the SSE-streaming addressed path). Source-side modules at `services/wake_sources/{cron_tick, addressed, proposal_arrival, substrate_event, manual_fire}.py` are the only sites that wake the Reviewer. Substrate-event hooks at `/workspace/_hooks.yaml` (sibling of `_recurrences.yaml`) — operator/Reviewer declare interest in substrate transitions; scheduler walks recent `workspace_file_versions` against declared hooks at every tick. Telemetry: `execution_events.wake_source` + `funnel_decision` (migration 177) populate at every Reviewer-wake call site. Bundle migrations: alpha-trader `trade-proposal` recurrence dissolved into `signal-evaluation` inline ProposeAction; alpha-author `pre-ship-audit` migrated from `schedule: null` recurrence to `_hooks.yaml` substrate-event hook. **Canon rewrite Implemented (2026-05-20)**: FOUNDATIONS Axiom 2 + Axiom 4 amendments + new Derived Principle 20 (wake-as-irreducible-unit) + GLOSSARY new entries (Wake / Wake source / Wake proposal / Wake evaluation funnel / Hook / ManageHook) + amendments to Recurrence + Pulse + Reviewer + Loop entries + `invocation-and-narrative.md` §2 rewrite (Pulse aligned to wake sources) + `primitives-matrix.md` (ManageHook row + REVIEWER_PRIMITIVES update + mode totals) + SERVICE-MODEL Execution Flow rewrite + 8 ADR status banners (ADR-253/256/260/261/263/274/275/276). See [ADR-296](docs/adr/ADR-296-continuous-judgment-cycle.md) + [implementation scope](docs/architecture/adr296-implementation-scope.md).

**Hat-B is the feedback loop. Hat-A is where the system actually changes.**

If a session is unclear which hat applies, the test is: *would a real operator on a stable YARNNN release see this change?* If yes, Hat A. If no, Hat B. The system's own runtime never references Hat-B artifacts; FOUNDATIONS doesn't mention them; ADRs treat them as out-of-canon. They exist purely as our scaffolding while we build.

## Core Execution Disciplines

### 0. Before Proposing Architectural Changes

**ALWAYS check existing ADRs first** before suggesting new patterns or comparing against external systems:

```bash
# Search for existing decisions on a topic
ls docs/adr/ | grep -i "<topic>"
# Or search ADR content
grep -r "<keyword>" docs/adr/
```

Key ADRs that define YARNNN's philosophy (not just implementation):
- **ADR-049**: Context freshness model - SUPERSEDED by ADR-072 (accumulation moat thesis)
- **ADR-059**: Simplified context model - current Memory schema (user_memory), inference removal
- **ADR-062**: Platform context architecture - SUPERSEDED by ADR-072 (unified content layer)
- **ADR-063**: Four-layer model (Memory / Activity / Context / Work) - activity_log, working memory injection
- **ADR-067**: Session compaction and continuity - follows Claude Code's model
- **ADR-072**: Unified Content Layer - platform_content with retention-based accumulation, YARNNN execution pipeline
- **ADR-080**: Unified Agent Modes - one agent (chat + headless), mode-gated primitives, supersedes ADR-061 two-path separation
- **ADR-087**: Agent Scoped Context - per-agent instructions + memory, session routing via agent_id
- **ADR-088**: Trigger Dispatch - `dispatch_trigger()` in `api/services/trigger_dispatch.py`, single decision point for schedule/event/signal triggers (Phase 1 implemented). **Partially superseded by ADR-126** — pulse decision is now upstream of dispatch; `dispatch_trigger()` invoked only when pulse decides "generate"
- **ADR-092**: Agent Intelligence & Mode Taxonomy - five modes (`recurring`, `goal`, `reactive`, `proactive`, `coordinator`); signal processing dissolved from L3; `RefreshPlatformContent` extended to headless; coordinator agents replace `signal_emergent` origin (Implemented — signal processing removed, modes active, coordinator pipeline in `proactive_review.py`). **Partially superseded by ADR-126** — proactive self-assessment generalized to all agents via pulse Tier 2; coordinator mode dissolved into PM pulse Tier 3
- **ADR-101**: Agent Intelligence Model - four-layer knowledge model (Skills / Directives / Memory / Feedback); learned preferences from edit history injected into headless system prompt; `get_past_versions_context()` includes delivered runs
- **ADR-102**: yarnnn Content Platform - agent outputs written as `platform_content` rows with `platform="yarnnn"`, closing the accumulation loop; always retained; searchable by YARNNN and headless agents; no OAuth, no sync
- **ADR-103**: Agentic Framework Reframe - terminology migration from "deliverable" to "agent" throughout codebase. Agents are persistent autonomous entities, not document generators.
- **ADR-104**: Agent Instructions as Unified Targeting - `agent_instructions` is the single targeting layer; dual-injected into system prompt (behavioral constraints) and user message (priority lens); dead infrastructure deleted (DataSource.scope/filters, SECTION_TEMPLATES, unused type_config fields, template_structure)
- **ADR-105**: Instructions to Chat Surface Migration - directives (instructions, audience) flow through chat; configuration (schedule, sources) stays in drawer. Superseded by ADR-215's four-shape CRUD matrix — see `docs/design/SURFACE-CONTRACTS.md`.
- **ADR-106**: Agent Workspace Architecture - virtual filesystem over Postgres (`workspace_files` table); agents interact via path-based operations; archetype-driven strategies (reporter/analyst/researcher/operator); reasoning agents drive own context gathering from workspace instead of receiving platform dumps; replaces `agent_memory` JSONB; storage-agnostic abstraction layer preserves optionality for cloud storage
- **ADR-109**: Agent Framework — Scope × Role × Trigger taxonomy replacing the 7-type system (ADR-093). Scope (what it knows: platform/cross_platform/knowledge/research/autonomous) determines context strategy. Role (what it does: digest/prepare/monitor/research/synthesize/act) determines prompt + primitives. Trigger (when it acts) = preserved ADR-092 modes. `agent_type` column → `scope` + `role` columns (was `skill`, renamed by ADR-118 Resolved Decision #4 to eliminate naming overload with output gateway skills). Templates are user-facing convenience layer. Canonical reference: `docs/architecture/agent-orchestration.md`. (Implemented — `skill` → `role` column rename completed in ADR-118 D.1, migration 114.)
- **ADR-110**: Onboarding Bootstrap — deterministic, zero-LLM agent creation on platform connection. Post-sync, auto-creates matching digest agent (Slack→Recap, Notion→Summary) with `origin=system_bootstrap`. Executes first run immediately. Becomes Bootstrap bounded context within Composer (ADR-111). (Implemented.)
- **ADR-111**: Agent Composer — **SUPERSEDED by ADR-156 + ADR-164**. Composer deleted. YARNNN is the single intelligence layer for all judgment. Deterministic lifecycle rules (underperformer pausing) moved to scheduler by ADR-156, then moved again to the `back-office-agent-hygiene` task (owned by YARNNN) by ADR-164. Workforce health signals (work budget, agent approval rates) moved to working_memory.py. CreateAgent → ManageAgent (ADR-146 pattern).
- **ADR-112**: Sync Efficiency & Concurrency Control — three layers: (1) atomic sync lock on `platform_connections` replacing `SCHEDULE_WINDOW_MINUTES` timing hack, (2) platform-level heartbeat fast-path (Slack latest, Notion search) to skip source iteration when nothing changed, (3) per-source skip hints (deferred). Coordinates all three sync paths (scheduled, manual, YARNNN RefreshPlatformContent). (Implemented.)
- **ADR-113**: Auto Source Selection — eliminates manual source selection as prerequisite for platform connections. OAuth callback auto-discovers landscape, applies `compute_smart_defaults()`, kicks off first sync immediately. Post-OAuth redirect goes to `/orchestrator` (home). Context pages become optional refinement, not first-time entry point. Orchestrator empty state shows platform connect cards for cold-start onboarding. (Implemented.)
- **ADR-114**: Composer Substrate-Aware Assessment — **SUPERSEDED by ADR-156**. Composer deleted. Substrate-aware signals (knowledge corpus, workspace density) absorbed into working_memory.py as YARNNN context.
- **ADR-116**: Agent Identity & Inter-Agent Knowledge Infrastructure — makes agents discoverable and composable. Five phases: (1) knowledge metadata search (QueryKnowledge filters by agent_id/role/scope), (2) agent discovery primitive (DiscoverAgents), (3) cross-agent workspace reading (ReadAgentContext — read-only), (4) agent card auto-generation + MCP exposure (get_agent_card, search_knowledge, discover_agents tools), (5) consumption tracking + Composer agent dependency graph (orphaned producers, missing producers, stale dependencies). Agent-native identity thesis: workspace IS identity, agents are first-class participants not human proxies. (Implemented.)

- **ADR-117**: Agent Feedback Substrate & Developmental Model — unifies feedback rails (user edits, agent self-observation) into workspace as single substrate. Feedback distillation (Phase 1) and self-reflection (Phase 2) preserved. Key files: `feedback_distillation.py` (distill edits → style.md), `feedback_engine.py` (edit metrics). Dual injection: preferences in system prompt (high salience) + gathered context. **Phase 3 seniority-gated capabilities superseded by ADR-130** — capabilities are determined by agent type (fixed at creation), not earned through seniority. Composer coaching deleted (ADR-156). Feedback distillation and self-reflection preserved — agent development is knowledge depth, not capability breadth.

- **ADR-118**: Skills as Capability Layer — "Claude Code online" model. Two-filesystem architecture: capability filesystem (skills on output gateway Docker service, `render/skills/{name}/SKILL.md` + scripts, platform-wide) and content filesystem (workspace_files + S3, user-scoped, accumulating). Adopts Claude Code naming conventions directly: skills (not handlers/capabilities), SKILL.md (not capability guides), skill folders (same structure as Claude Code). Two skill types: local (tools in Docker image, fixed cost) and delegated (external API/MCP, per-call cost). Skills are explicit/curated, earned via feedback-gated progression (Axiom 3). Phases A+B+C+D.1-D.4 Implemented. D.1: skills alignment/rename (`skill`→`role` column). D.2: render hardening (auth, rate limits). D.3: unified output substrate (output folders as delivery source, `deliver_from_output_folder()`, manifest-based email attachments). D.4: skill auto-discovery + 8-skill library. Phase D.5 (assets layer) deferred — implement when user demand emerges. Full analysis: `docs/analysis/skills-as-capability-layer-2026-03-17.md`. **Phase D format-builder skills partially superseded by ADR-130** — 8 format-builder skills dissolve into asset producers (chart/mermaid/image) + HTML compose engine + export pipeline. Two-filesystem architecture and skill auto-discovery preserved.

- **ADR-119**: Workspace Filesystem Architecture — evolves `workspace_files` from flat key-value store to proper folder-based filesystem. Folders are boundaries, folders are context. Key conventions: output folders (`/agents/{slug}/outputs/{date}/`) replace bundle tables — co-located files + `manifest.json` = atomic output. Project folders (`/projects/{slug}/`) with scoped contribution subfolders = cross-agent collaboration. `/working/` = ephemeral scratch. Two schema additions: `version` + `lifecycle` columns on `workspace_files`. Manifest files carry metadata (sources, delivery status, file roles) instead of relational tables. Thesis: folders are boundaries and boundaries are all you need for coordination — same principle as Cowork's folder selection applied to persistent agent workspaces. Makes ADR-118 Phase D structurally sound. Extends ADR-106, interacts with ADR-116 (cross-agent reading), ADR-117 (feedback via manifests). (Phases 1-4 Implemented. Phase 1: output folders + lifecycle + manifest.json. Phase 2: project folders — ProjectWorkspace, CreateProject/ReadProject primitives, /api/projects CRUD, context injection for contributing agents. Phase 3: version history — `/history/{filename}/v{N}.md` convention, capped at 5 versions, `_archive_to_history()` + `list_history()` on AgentWorkspace and KnowledgeBase. Phase 4a: frontend — `/projects` list page, `/projects/{slug}` detail page, dashboard projects section. Phase 4b: AgentOutputsPanel — agent output history tab.)

- **ADR-120–137** (the Project / PM layer): **ALL SUPERSEDED by ADR-138.** This was the project-manager era — projects as a hierarchy layer (PROJECT.md/TEAM.md/PROCESS.md charters), PM agents coordinating contributors, meeting-room surfaces, phase dispatch, pulse engine, declarative pipelines. ADR-138 collapsed the entire project layer (Workspace → Agents → Tasks; PM dissolved into YARNNN). Don't build on any of these; they're history. (ADR-131 Gmail/Calendar sunset + ADR-147 GitHub integration + ADR-130 three-registry/agent-type-registry are the survivors of this band, but registries themselves later became template libraries per ADR-188 then dissolved per ADR-207/231.)

- **ADR-138**: Agents as Work Units — Project Layer Collapse. Workspace → Agents → Tasks hierarchy. Projects deleted entirely. PM dissolved — YARNNN absorbs coordination. Agents are WHO (identity, domain expertise, memory). Tasks are WHAT (objective, cadence, delivery, output spec, mode). `mode` (recurring/goal/reactive) is on tasks, not agents — temporal behavior is a property of the work, not the worker. Filesystem-first: TASK.md + memory/run_log.md + outputs/. Thin tasks DB table (scheduling index only). 4 archetypes: monitor, researcher, producer, operator. Cross-agent orchestration via YARNNN (imperative, not pipeline). Clean-slate migration (all test data wiped). **Evolves into ADR-140** for agent type definitions. Supersedes ADR-120–125, ADR-133–137. PM portions of ADR-126, ADR-128 dissolved. Key files: `api/services/task_workspace.py`, `api/routes/tasks.py`, `api/services/primitives/task.py`. (Phases 1-4 Implemented. Phase 5-6 in progress.)

- **ADR-140/176**: Agent Workforce Model. ADR-140 (ICP roster) superseded by **ADR-176** (Work-First Agent Model — "work exists first; agents serve work"). Six universal specialist roles (`researcher`/`analyst`/`writer`/`tracker`/`designer` + `reporting`) + platform-bots + `thinking_partner`. Capability split: accumulation specialists (no RuntimeDispatch) vs production (designer — chart/mermaid/image/video). `## Team` in TASK.md; domains created by work demand. The fixed-roster "hospital principle" was later softened by ADR-188 (universal roles, contextual application) and the roster scaffold dissolved entirely by ADR-205.

- **ADR-141**: Unified Execution Architecture — Mechanical Scheduling, LLM Generation. Three layers: Layer 1 (mechanical, zero LLM) = scheduling/sync/cleanup; Layer 2 (generation, Sonnet) = task pipeline; Layer 3 (orchestration) = YARNNN chat. Supersedes ADR-088 + ADR-126 (pulse). **The Layer-2 headless task pipeline itself was later dissolved by ADR-260/261** (real-time Reviewer loop) — Layer 1/3 separation survives.

- **ADR-142/144/149/151/152/161/162/163/166**: The **task-era substrate band** (largely superseded by ADR-231 Task Abstraction Sunset). Worth knowing the survivors: **ADR-153** Platform Content Sunset (`platform_content` deleted; data flows through tasks into `/workspace/context/` — supersedes 072/077/085); **ADR-156** Composer Sunset (YARNNN is the single intelligence layer — no background LLM; supersedes 111/114); **ADR-159** Filesystem-as-Memory (compact index ~200-500 tok + on-demand reads replaces the working-memory dump — the live context model, evolved by ADR-221); **ADR-164** Back-Office Tasks (YARNNN as an agent; back-office work as ordinary tasks — back-office tasks later dissolved into recurrences by ADR-260/261). The rest (142 four-roots, 144 inference-first shared context, 149 task lifecycle, 151/152 context-domain + directory registries, 161 daily-update anchor, 162 inference hardening, 163 surface nav, 166 output_kind enum, 178 task creation routes, 177 section-kind rendering) are task-abstraction history dissolved by ADR-231 + ADR-207.

- **ADR-167**: List/Detail Surfaces with Kind-Aware Detail. `/work` and `/agents` become single surfaces with URL-driven list-mode vs detail-mode (`?task=`/`?agent=`); auto-select-first deleted. `WorkDetail` dispatches a kind-specific middle band on `output_kind`. Largely reshaped by the later compositor/surface work (ADR-245/297/312); the list-vs-detail + kind-middle pattern is the durable idea.

- **ADR-168**: Primitive Matrix — canonical primitive reference at `docs/architecture/primitives-matrix.md`. Two axes (substrate family × permission mode) + capability tags. **Naming reform**: entity layer `Read→LookupEntity`/`List→ListEntities`/`Search→SearchEntities`/`Edit→EditEntity`; file layer `ReadWorkspace→ReadFile`/`WriteWorkspace→WriteFile`/`SearchWorkspace→SearchFiles`/`ListWorkspace→ListFiles`. `Execute` deleted, `CreateTask` folded into ManageTask. **NOTE**: the entity-layer primitives were heavily pruned by ADR-322, file verbs completed by ADR-337, scopes retired for topology by ADR-321 — primitives-matrix.md is the live source, not this entry.

- **ADR-173**: Accumulation-First Execution — read the workspace before producing; the gap between current state and the convergence target is the only work. Context domains accumulate additively; task outputs converge replacively. Durable principle, survives into the recurrence era.

- **ADR-181**: Source-Agnostic Feedback Layer — user / system-verification / YARNNN-evaluation feedback all write one `feedback.md` per work unit (source-tagged entries, optional `Action:` directives). Two tiers: injection (last-3 into prompt) + actuation (threshold-gated workspace mutations). Zero new primitives/tables/LLM calls.

- **ADR-182**: Pre-Gather Pipeline Optimization — splits Layer-2 execution into mechanical context assembly (zero LLM) + reduced-tool LLM synthesis for `produces_deliverable` tasks (~50% per-task cost cut). Task-pipeline-era; the pipeline it optimized was later dissolved by ADR-260/261.

- **ADR-183/184/187**: Platform substrate additions — **ADR-183** Commerce (Lemon Squeezy, provider-agnostic, `customers/`+`revenue/` domains); **ADR-187** Trading (Alpaca, the alpha-trader program seed — "internalized E2E test of the framework", graduated paper→live execution, guardrails); **ADR-184** Product Health Metrics (revenue as first-class perception). Commerce + Trading are the two flagship programs; trading is the live dogfooding bet.

- **ADR-186/188**: **ADR-186** YARNNN Prompt Profiles (surface-aware `workspace`/`entity` profiles replace the monolith — evolved heavily by ADR-302/306/323 persona-frame collapse). **ADR-188** Domain-Agnostic Framework — registries reframed from product definitions to curated *template libraries* YARNNN composes beyond; "universal roles, contextual application" (softens ADR-176 hospital principle). The agnosticism boundary (fixed framework vs contextual config) is the durable idea; registries later dissolved further (ADR-207/224/231).

- **ADR-169**: MCP as Context Hub — three intent-shaped tools (`work_on_this`/`pull_context`/`remember_this`) replace the 9-tool CRUD surface. Cross-LLM continuity narrative; zero internal-LLM on the serving path; MCP is the fifth caller of `execute_primitive()`. **Reframed by ADR-310/311** as the interop *face* of the one moat (raw file + revision primitives, not intent tools) — see interop arc below.

- **FOUNDATIONS v6.0** (2026-04-20) — **Six-dimensional axiomatic model** (the current spine, now at v9.5). Every mechanic occupies a cell in six orthogonal dimensions: **Substrate** (What persists) · **Identity** (Who acts) · **Purpose** (Why) · **Trigger** (When) · **Mechanism** (How, a code→judgment spectrum) · **Channel** (Where). Axiom 0 names the model; Axioms 1–9 are the dimension + recursion + ground-truth + invocation axioms. Design drift = a mechanic spanning a dimension without necessity. **Read FOUNDATIONS.md directly** — it's the live canon (axioms + 29 derived principles), not this entry.

- **ADR-194 v2**: **The Reviewer / judgment seat** (load-bearing, still live). One Reviewer per workspace, scaffolded at signup, filesystem home `/workspace/review/`. Distinctness lives in Purpose + Trigger, not Identity — which is why the seat is **interchangeable** (human / AI / impersonation fill the same structural seat). AI Reviewer reasons capital-EV over ground-truth, not rule-checking. The seat is the durable trust surface. Heavily evolved since (occupant carve ADR-315, denaming ADR-326, stewardship ADR-319) but the seat-vs-occupant model is ADR-194's. **Canonical home: `docs/architecture/reviewer-seat-substrate.md`** (per CLAUDE.md Reviewer-canon section).

- **ADR-195 v2**: **Money-Truth / Ground-Truth Substrate** — performance lives in a per-domain `_performance.md` file (not a SQL table — `action_outcomes` dropped as an Axiom 1 violation). Regenerated idempotently by outcome-reconciliation from platform events. Renamed "Ground-Truth Substrate" by ADR-282 (kernel concept, money-truth is the trading instance); intake generalized beyond platform APIs by ADR-330.

- **ADR-196/197**: Substrate-cleanup ADRs — **ADR-196** dropped the vestigial `user_memory` table (filesystem replacement live since ADR-156). **ADR-197** `filesystem_documents` → `/workspace/uploads/` migration (Axiom 1 compliance).

- **ADR-198/202**: Channel discipline — **ADR-198** Surface Archetypes (Document / Dashboard / Queue / Briefing / Stream — five Channel cells, each with invariants). **ADR-202** External Channel Discipline (every email/notification is a *pointer* not a content-replacement; `deep_links.py` is the single URL source of truth). Both heavily superseded at the surface layer by the ADR-297/312/338/340 compositor + experience work.

- **ADR-208** (**WITHDRAWN**): Workspace Git Backend — proposed a per-workspace git repo; withdrawn before code shipped (Postgres-vs-git bifurcation, imported coordination infra alpha operators don't need). Superseded by ADR-209.

- **ADR-209**: **Authored Substrate** (FULLY IMPLEMENTED, load-bearing — Axiom 1's second clause). Every mutation to `workspace_files` is attributed (`authored_by` + `message`, required), parent-pointered (`workspace_file_versions`), and retained (content-addressed `workspace_blobs`). Adopts three of git's five capabilities (content-addressing, parent-pointer history, attribution) without branching/distributed-replication. `services/authored_substrate.py::write_revision()` is the single write path. **This is the moat's substrate floor.** Canonical: `docs/architecture/authored-substrate.md`.

- **ADR-205/206/207**: **The operation-first / mandate pivot** (the move from "AI report generator" to "supervised autonomous operation"). **ADR-205** Workspace Primitive Collapse (YARNNN as sole persistent identity; specialists + platform-bots become dispatch-time capability bundles, not agent rows; chat-first triggering — schedule optional). **ADR-206** Operation-First Scaffolding (signup scaffolds skeletons only — zero operational tasks; `_shared/*` relocation; back-office materializes on trigger). **ADR-207** Primary-Action-Centric Workflow — every operator workspace has one **Primary Action** (the value-moving external write); `MANDATE.md` is the hard gate for task creation; Platform Bots deleted, capability-gating replaces them; `TASK_TYPES` no longer dispatch-authoritative (tasks self-declare in TASK.md). This band is the conceptual root of the program/mandate model that ADR-222 (OS framing) + ADR-231 (task sunset) built on.

- **ADR-205** (2026-04-22, v1.1 Backend Implemented — Frontend Phase 4–5 Proposed): Workspace Primitive Collapse — YARNNN as Sole Persistent Identity, Emergent Scaffolding, Chat-First Triggering. Shipped via **Architecture Y** (lazy scaffolding within the existing `agents` table, not a separate `workspace_identity` table — see ADR-205 Implementation Notes for the pivot rationale and its equivalence to the ADR thesis). Migration 154 applied: 31 non-YARNNN `system_bootstrap` rows dropped, 9 YARNNN rows backfilled, 11 workspaces end with exactly one YARNNN row each. Helpers `classify_role` / `resolve_infra_role_from_ref` / `ensure_infrastructure_agent` / `ensure_infrastructure_agents_for_type` / `delete_platform_bot` live in `services/agent_creation.py`. Task pipeline dispatch, ManageTask create/update, repurpose fallback, integration connect/disconnect, and account clear-integrations all route through the new helpers. Chat-first triggering: `ManageTask._handle_create` treats `schedule` as optional and runs the task inline when absent (`should_run_now = has_bootstrap or mode == 'goal' or (not schedule and mode != 'reactive')`). **Supersedes ADR-189 Phase 2** (pragmatic preservation of infrastructure `agents` rows now reversed). **Amends** ADR-152 (directory registry is naming-convention reference, no signup-time pre-creation), ADR-161 (daily-update owner is workspace identity, not agent row), ADR-176 (Decision 4 capability split survives as code-level dispatch, not as roster composition), ADR-188 (completes Phase 3+ agent/directory collapse), ADR-204 (cockpit object graph re-scoped — no infrastructure rows to surface). **Preserves** FOUNDATIONS v6.0, ADR-141, ADR-168, ADR-189 three-layer cognition model + authored-team moat + GLOSSARY discipline, ADR-194 Reviewer seat, ADR-181 feedback layer, ADR-195 money-truth substrate. **Decisions**: (1) Signup scaffolds one persistent entity — YARNNN (as `workspace_identity` row, not `agents` row) — plus `/workspace/IDENTITY.md` + `/workspace/BRAND.md` + `/workspace/review/` + daily-update task + two back-office tasks. Zero Specialist rows, zero Platform Bot rows, zero context domain directories at signup. (2) Specialists collapse into `AGENT_TEMPLATES` as dispatch-time palette — `task_pipeline.py` resolves by reading templates, not by `agents` table lookup. ADR-117 role-keyed style distillation moves to `/workspace/specialists/{role}/style.md`. (3) Platform Bots become connection-bound capability bundles keyed on `platform_connections`, not `agents` rows. Tool surface + task type eligibility + domain ownership all key on active connection. (4) Workspace directories are emergent — `WORKSPACE_DIRECTORIES` is naming-convention reference; domains materialize at first-write. (5) Tasks default to immediate execution — `tasks.schedule` becomes nullable (migration 154); `ManageTask._handle_create()` immediately triggers when no schedule provided. Scheduling is an annotation, not a precondition. (6) Explicit modal CRUD affordances — `CreateTaskModal` + `ManageContextModal` coexist with chat for users who arrive with clear intent. (7) Onboarding re-scoped to context injection only — seeds IDENTITY + BRAND + optional uploads + optional first-task intent; no scaffolding calls. **Key files** (Phases 1–8): migration 154 (drop `agents` rows where `origin='system_bootstrap'`, nullable `tasks.schedule`, create `workspace_identity`), `api/services/workspace_init.py` (Phase 5 collapse), `api/services/orchestration.py` (delete `DEFAULT_ROSTER`), `api/services/task_pipeline.py` (dispatch refactor — no `agents` table lookup for Specialists or YARNNN), `api/services/platform_tools.py` + `api/services/task_types.py` (Platform Bot capability bundles), `api/services/directory_registry.py` (no pre-creation callers), `api/services/primitives/manage_task.py` (`_handle_create` optional schedule + immediate trigger), `api/routes/tasks.py` + `api/routes/onboarding.py` + `api/routes/integrations.py` (contract updates), `web/components/work/CreateTaskModal.tsx` + `web/components/context/ManageContextModal.tsx` (new), `web/components/onboarding/*` (re-scoped), `api/agents/yarnnn_prompts/{workspace,onboarding}.py` (authored-team + chat-first framing), `api/prompts/CHANGELOG.md`. Dimensional classification: **Substrate** (primary) + **Identity** (Specialists + Platform Bots) + **Trigger** (run-now default) + **Purpose** (user-driven) + **Channel** (modals + chat).

- **ADR-214** (2026-04-23, Implemented): Agents Page Consolidation — Four-Tab Nav, Systemic Agents Inside. Cockpit nav collapses from 5 tabs (`Chat | Work | Files | Team | Review`) to 4 (`Chat | Work | Agents | Files`). `/review` deleted — Reviewer becomes a systemic pseudo-agent detail view inside `/agents?agent=reviewer`, absorbing `ReviewSurface`'s three panes (IDENTITY.md + principles.md + decisions.md). Route reverses ADR-201 — `/agents` is canonical again; `/team` becomes a redirect stub mirroring the pre-existing `/agents`→`/team` bookmark-safety pattern. **Agents roster = Agents only** per ADR-212 — two groups: **Systemic** (YARNNN + Reviewer, always two cards) and **Domain** (user-authored instance Agents). Production Roles + Integrations groups deleted from the roster (they're Orchestration, not Agents). Production-role composition visible on `/work` task-detail `## Team` sections; integration setup stays at `/settings?tab=connectors`. **Backend Reviewer synthesis** (`api/routes/agents.py::list_agents()`) inserts a Reviewer pseudo-agent envelope (id="reviewer", role="reviewer", agent_class="reviewer", origin="system_bootstrap") — substrate stays filesystem-first per ADR-194 v2, synthesis is a read-side adapter only. Filter loosened to include `role='thinking_partner'` rows regardless of origin (YARNNN visible again); other `system_bootstrap` rows still hidden per ADR-189. **Frontend dispatch**: `AgentContentView` routes `agent_class='reviewer'` to `ReviewerDetailView.tsx`. New `reviewer` added to `CanonicalAgentRole` + `AgentClass` type unions and `ROLE_META` registry (rose palette, `ShieldCheck` icon). **Cleanup pass** absorbed (ADR-212 post-flip): `AgentContentView.tsx:327` "Specialist domain outputs" → "Production Role domain outputs"; `WorkspaceStateView.tsx:408` "specialist(s)" → "Production Role(s)" + `bots` stat label → "Platform Integration(s)" with href redirected to `/settings?tab=connectors`. **Cross-link migration**: `TEAM_ROUTE` + `REVIEW_ROUTE` constants deleted, replaced by `AGENTS_ROUTE = "/agents"`; all 6 call sites migrated (`WorkDetail.tsx` 3x, `AuthenticatedLayout.tsx`, `SinceLastLookPane.tsx`, `SnapshotPane.tsx` 2x, `work/page.tsx` breadcrumb, `middleware.ts` protected-prefix set). `components/review/` directory deleted (4 files); ReviewerCardPane / PrinciplesPane / DecisionsStreamPane relocated under `components/agents/reviewer/`. **Supersedes** ADR-200 (Review as standalone surface). **Amends** ADR-167 v2 (list/detail gains systemic-agent slot convention), ADR-189 (Systemic section is unconditionally present; Domain section carries the authored-team moat), ADR-201 (URL reversed). **Preserves** ADR-212 taxonomy, ADR-194 v2 Reviewer substrate, ADR-205 F1 chat-first landing, ADR-180 Files label, ADR-167 v2 list/detail pattern. Dimensional classification: **Channel** (primary, Axiom 6) + **Identity** (Axiom 2). Key files: `web/lib/routes.ts`, `web/components/shell/ToggleBar.tsx`, `web/app/(authenticated)/agents/page.tsx` (moved from /team), `web/app/(authenticated)/team/page.tsx` (new redirect stub), `web/components/agents/reviewer/` (new dir: ReviewerDetailView + 3 relocated panes), `web/components/agents/AgentRosterSurface.tsx` (regrouped), `web/components/agents/AgentContentView.tsx` (dispatch), `web/lib/agent-identity.ts` (reviewer role meta), `web/components/agents/AgentIcon.tsx` (ShieldCheck added), `web/types/index.ts` (agent_class union + reviewer), `api/routes/agents.py` (synthesis + filter loosened), `docs/adr/ADR-214-agents-page-consolidation.md`. **Follow-on**: ADR-215 "Files Platforms Pane" (Integrations visibility on `/files`) deferred — requires weighing duplication with `/settings?tab=connectors` as source-of-truth.

- **ADR-251** (2026-05-06, **Proposed**): System Agent + Reviewer as First-Class Surfaces — Roster Reinstated. **Supersedes** ADR-241 D1 (roster deletion reversed). **Decisions**: (D1) Entity rename — "System Agent" is the cockpit entity label for the orchestration surface. In chat speaks as "YARNNN" (brand); on `/agents` labeled "System Agent". `display_name` in `SYSTEMIC_AGENTS`: `"YARNNN"` → `"System Agent"`. URL param: `?agent=yarnnn` → `?agent=system` (with `?agent=yarnnn`/`?agent=thinking-partner` as bookmark-safety redirects). `THINKING_PARTNER_ROUTE` → `SYSTEM_AGENT_ROUTE`. Internal DB slug `thinking_partner`, class enum `meta-cognitive`, `YarnnnAgent` class, `TPContext` — all unchanged (GLOSSARY exceptions). (D2) Roster reinstated — two systemic cards (System Agent + Reviewer) + Your Agents section. (D3) System Agent detail (`?agent=system`) tabs: Identity · Mandate · Back Office. Autonomy + Principles removed (migrate to Reviewer). (D4) Reviewer detail (`?agent=reviewer`) tabs: Identity · Principles · Autonomy · Track Record · Decisions. Autonomy + Principles correctly housed under Reviewer. `?agent=reviewer` redirect (ADR-241 D3) deleted — now renders `ReviewerDetail` directly. (D5) Autonomy tab gains heartbeat cadence section (reads `back-office.yaml` schedules + last-run from `execution_events` via `GET /api/reviewer/cadence`). (D6) Deep-links: `CockpitHeader` autonomy → `?agent=reviewer&tab=autonomy`. (D7) Bookmark-safety: `?agent=yarnnn` + `?agent=thinking-partner` → `?agent=system`; `?agent=yarnnn&tab=principles|autonomy` → `?agent=reviewer&tab=...`. **GLOSSARY/FOUNDATIONS/LAYER-MAPPING amended** — System Agent entry added, meta-cognitive/TP retired as user-facing labels. CHANGELOG `[2026.05.06.3]`. Key files: `docs/adr/ADR-251-system-agent-reviewer-first-class-surfaces.md`, `docs/architecture/GLOSSARY.md` (System Agent entry + Exceptions), `docs/architecture/LAYER-MAPPING.md` (amended), `docs/architecture/FOUNDATIONS.md` (Axiom 2 amended), `api/services/orchestration.py` (display_name), `web/lib/agent-identity.ts` (displayName/tagline), `web/lib/routes.ts` (SYSTEM_AGENT_ROUTE + REVIEWER_ROUTE), `web/lib/constants/agents.ts`, `web/components/agents/{AgentContentView,AutonomyTab,PrinciplesTab}.tsx` (routing + taglines), `web/app/(authenticated)/agents/page.tsx` (roster + redirects), `web/components/library/CockpitHeader.tsx` (autonomy link).

- **ADR-276** (2026-05-14, **Implemented**): Reactive-Trigger Envelope Governance Pre-Load — closes the FOUNDATIONS v8.5 dev-sequence arc. **Companion ancestors**: FOUNDATIONS v8.5 Axiom 4 + Derived Principle 18 (via ADR-274), introspection-cadence-as-Reviewer-authored (via ADR-275), addressed-trigger envelope pre-load (via ADR-275 refinement). ADR-276 finishes the structural arc by closing the symmetric gap on the reactive-trigger envelope. **The architectural problem**: Run-2 e2e of ADR-275 refinement validated addressed-trigger envelope pre-load works empirically (Reviewer authored 3× `Schedule` with correct attribution). But the run-2 observation surfaced that `services/invocation_dispatcher.py` (reactive trigger — recurrence fires + proposal arrivals) was still operating with the pre-ADR-275 envelope: only `recurrence_prompt + recurrence_slug + capabilities + options + operating_context_block` reached the Reviewer; MANDATE/IDENTITY/principles/AUTONOMY/`_preferences.yaml`/domain substrate were NOT pre-loaded. Same prose-vs-pre-load asymmetry that addressed turns suffered. **Decisions**: (D1) New canonical helper `services/reviewer_envelope.py::load_reviewer_governance_envelope(client, user_id)` — reads 9 governance + domain paths in parallel via `asyncio.gather` + signal-files compact summary, returns dict keyed by `ReviewerContext` field names. (D2) `routes/feed.py` (addressed) migrates from inline 9-path gather to call the helper — Singular Implementation discipline (one helper, two callers, identical envelope shape). (D3) `services/invocation_dispatcher.py` (reactive) adds the helper call before `invoke_reviewer()`. Context bag dict-spreads `**governance_envelope` alongside recurrence-specific keys (`recurrence_prompt`, `recurrence_slug`, `capabilities`, `options`, `operating_context_block`). (D4) No persona-frame changes — contract was already correct post-ADR-275 refinement; only structural delivery for reactive triggers gets corrected. (D5) decisions.md dual-writer race (run-2 observation §Side a) explicitly out of scope — separate Singular Implementation question deserves its own discourse. (D6) `signal-evaluation` empty-signals gap (run-2 observation §Side b) NOT preemptively patched — re-tested by the post-deploy reactive wake; if governance pre-load was the cause, `signals/` populates naturally; if not, the gap is in prompt/logic. **Amends** ADR-260 (reactive wake envelope shape made structural), ADR-261 (recurrence shape preserved), ADR-263 (mechanical vs judgment mode dispatch preserved). **Preserves** FOUNDATIONS Axioms 1–8, ADR-209 Authored Substrate, schema (no new tables/columns), primitive surface (no new primitives), mechanical-mode recurrences (don't wake the Reviewer). Net implementation: ~150 LOC across 8 files (new helper module + feed.py migration + dispatcher wiring + regression gate + doc cascade). Regression gate `api/test_adr276_reactive_envelope.py` 16/16 PASS. Sibling gates (ADR-275 / ADR-274 / ADR-272 / ADR-269 / ADR-261 Phase B) all green post-update. The Reviewer perceives full governance substrate at every wake regardless of trigger shape (addressed | reactive | future trigger types). Derived Principle 18 lands operationally across the entire trigger surface. CHANGELOG `[2026.05.14.10]`. Key files: `docs/adr/ADR-276-reactive-trigger-envelope-governance-preload.md`, `api/services/reviewer_envelope.py` (new), `api/routes/feed.py` (inline gather DELETED, helper call added), `api/services/invocation_dispatcher.py` (helper call added), `api/test_adr276_reactive_envelope.py`, `docs/adr/ADR-275-introspection-cadence-reviewer-authored.md` (§5b status update — ADR-276 implemented).

---

### The 2026-04 / 2026-05 arcs (collapsed — read the ADR files for detail)

These bands are mostly *intermediate steps* superseded by later endpoints. Summarized as arcs; the live endpoints are flagged. **For any of these, read `docs/adr/ADR-NNN-*.md` directly — these one-liners exist only so you know the ADR exists and roughly what it did.**

- **OS-framing arc (ADR-222 → 226, 230)**: **ADR-222** Agent-Native OS Framing (LIVE canon — kernel = substrate+primitives+axioms; shell = YARNNN chat; userspace = workspace; **programs** = applications; bundles at `docs/programs/{slug}/`; compositor reads-never-authors; kernel boundary is sacred; "workspaces run programs, they don't have types"). **ADR-223** Program Bundle Specification (`MANIFEST.yaml` + `README.md` + `SURFACES.yaml` + `reference-workspace/`). **ADR-224** Kernel/Program Boundary (program-specific templates deleted from kernel registries; bundles are sole source; `bundle_reader.py`). **ADR-225** Compositor Layer (`GET /api/programs/surfaces`, `composition_resolver.py`, `web/components/library/`). **ADR-226** Reference-Workspace Activation (`fork_reference_workspace` with tier frontmatter `canon`/`authored`/`placeholder`). **ADR-230** Persona-Program Registry Unification (one activation path; `scaffold_trader.py` deleted → `activate_persona.py`; `personas.yaml` gains `program:`).

- **Cockpit arc (ADR-228 → 273 → 312)**: the cockpit-rendering question, resolved three times. **ADR-228** Cockpit as Operation (four faces) → **ADR-273** Kernel/Program Section Split (substrate-backed trader sections) → **ADR-312** Home as Composition (the LIVE endpoint — cockpit dissolves into Home; six kernel constituent slots; generic `GroundTruthHero`; `intent`/`os-config`/`application` register split; `/api/cockpit/*` folded to `/api/programs/alpha-trader/*` + `/api/pace`). 228 + 273 are superseded at the framing level by 312.

- **Reviewer-loop arc (ADR-247 → 276)**: the Reviewer chat/loop evolution, heavily self-superseding. The LIVE endpoint is **ADR-260/261/262** (Real-Time Reviewer Loop + Recurrences-as-Prompts + Output-Topology — the biggest collapse since ADR-138; −8,342 LOC; one recurrence shape `{slug, schedule, prompt}` in `_recurrences.yaml`; headless task pipeline dissolved; specialists become `DispatchSpecialist` sub-LLM-calls; back-office package deleted). Steps along the way, mostly superseded: 247 three-party narrative · 248 periodic reviewer pulse · 252 reviewer-as-primary-intelligence · 253 reviewer execution authority · 254 file-format discipline (`.md` prose / `.yaml` machine — still the live rule, see §9) · 256 unified `invoke_reviewer` (superseded 218/252) · 258→258-revised reviewer-as-personified-chat-mode (`REVIEWER_PRIMITIVES` curated subset, `DEFAULT_REVIEWER_WRITE_LOCKS`) · 259 Feed Surface (renamed "chat surface" → "feed surface"; `/chat`→`/feed`, `routes/chat.py`→`routes/feed.py`) · 274/275/276 trigger-authoring + introspection-cadence-reviewer-authored + reactive-envelope-governance-preload (Reviewer authors its own cadence via `Schedule`; bundles ship no judgment cadence; `reviewer_envelope.py` governance pre-load). The Reviewer canon now lives in `docs/architecture/reviewer-seat-substrate.md` + siblings (per CLAUDE.md Reviewer-canon section), not these ADRs.

- **Task-sunset (ADR-231)**: **FULLY IMPLEMENTED** — Task Abstraction Sunset. Tasks-as-units dissolved into mandate-driven recurrences; `task_pipeline.py`/`task_types.py`/`manage_task.py` (~7,800 LOC) deleted; `tasks` table → thin scheduling index; `/api/tasks` → `/api/recurrences`. Supersedes 138/149/161/166. The recurrence model (`recurrence.py` + `scheduling.py` + `invocation_dispatcher.py`) is live; further reshaped by ADR-260/261.

- **FE-kernel arc (ADR-236 → 245)**: **ADR-236** Frontend Cockpit Coherence Pass (umbrella) → sub-ADRs 237 (chat role dispatch — `MessageDispatch.tsx`) · 238 (autonomy FE) · 239 (decisions parser) · 240→244 (onboarding→Workspace Settings surface) · 241 (single cockpit persona). Endpoint: **ADR-245** Three-Layer Content Rendering (LIVE FE kernel model — L1 raw view escape hatch / L2 content-shape parsers in `web/lib/content-shapes/` / L3 structured affordances in `web/components/library/`; "L1 dispatches on file format, L2/L3 on content shape"). Heavily extended by ADR-297/312/338/340.

- **ADR-213/221/243**: **ADR-213** Surface-Pull Composition (tasks write substrate, surfaces compose HTML on-demand with content-addressed cache — the compose-on-read model, evolved by ADR-333). **ADR-221** Layered Context Strategy (compact-index + windowed history + in-session-compaction sunset — evolves ADR-159). **ADR-243** Schedule Surface (cadence-framed sibling of `/work`).

---

### Recent ADRs (277–340) — the current era

The live frontier. These are concise pointers — **read `docs/adr/ADR-NNN-*.md` for any one you're touching.** Grouped by arc; the LIVE-canon ones are flagged.

**Substrate / kernel-boundary hardening:**
- **ADR-280/281**: substrate organization is operator-readable canon. **ADR-281** (LIVE) — bundles ship a `_workspace_guide.md` teaching the six-role substrate taxonomy (`operator-canon`/`reviewer-workbench`/`system-ledger`/`world-mirror`/`running-narrative`/`kernel-index`); the kernel doesn't author its own pedagogy. (280 was Phase-1, superseded by 281.) FOUNDATIONS Axiom 1 §5.
- **ADR-286**: Single-Writer Per Path (LIVE) — every substrate path has exactly one authoritative writer (kernel-universal / bundle-owned / runtime). Eliminates the dual-write race + skeleton-detection heuristics. FOUNDATIONS Axiom 1 §6.
- **ADR-288**: caller identity as a first-class auth field. **ADR-292** Continuous Substrate Reapply (operator-initiated versioned substrate updates, not daily cron — kernel/bundle seed constants reach live workspaces on demand). **ADR-296** v2 Wake Architecture (LIVE — see CLAUDE.md top; five wake sources → one funnel → Reviewer fires on escalation; `services/wake.py`). **ADR-298** Reviewer Wake Queue + Pace (LIVE — `wake_queue` transient compute, single-lane drain, operator-declared pace; see schema section).
- **ADR-320**: Constitution-Region Topological Cut (LIVE — FOUNDATIONS Axiom 1 §7 + DP25). Five semantic-class roots (`governance/`/`constitution/`/`persona/`/`operation/`/`system/`); `_is_path_locked(caller, path)` is the agent OS's `access(2)` — write permission derived from the path's top-level root alone. Collapses the two divergent lock functions into one prefix table. **ADR-321** path-native file primitives (retire the `scope` enum for topology). **ADR-322** entity-layer pruning (entity primitives shrink to a `/proc`-style surface; document/task reads move to the file family). **ADR-328** Substrate Portability Invariant (Layer 1 authored FS authoritative+portable; Layer 2 embeddings reconstructable cache; Layer 3 sidecars operational).

**Reviewer / persona-frame:**
- **ADR-295** reviewer self-amendment discipline (four evidence patterns). **ADR-301/303/314** reviewer envelope + posture taxonomy + substrate-conditional posture (frame indexes intent, doesn't assert it exists — standby reasons from absence). **ADR-318** Agentic Wake Posture (a wake is a situation not a task — serve the named prompt then reason forward when judgment warrants).
- **ADR-302/305/306/323**: **persona-frame collapse** (LIVE endpoint = **ADR-306** + **ADR-323**). System prompt collapses ~36K (13 sections) → ~3.5K (1 section) carrying only principal-shift + action-grammar; rules-of-judgment move to `principles.md`, pedagogy to envelope headers. DP22 (the persona-frame carries only the model↔runtime interface contract). 323 deleted `cockpit_awareness` DP22-violating content.
- **ADR-315**: Occupant Carve (LIVE — seat≠occupant split; `reviewer-seat-substrate.md` + `reviewer-occupant.md` + `reviewer-occupant-contract.md`; the published ABI is `api/agents/occupant_contract.py`). See CLAUDE.md Reviewer-canon section.
- **ADR-319**: Stewardship of Intent Against Ground-Truth (LIVE — DP24). The Reviewer owns the mandate as the same principal one wake later and revises it against reconciled reality; **ground truth moves intent, operator pressure never does.**
- **ADR-342**: Dormancy as Ground-Truth Evidence (LIVE — DP24 amendment v9.6, extends ADR-318/319). The ground truth that moves intent includes *persistent dormancy* (a strategy producing nothing across cadence), not only *decay* (outcomes gone negative). The persona-frame's situation-scoped posture gains an **offensive limb**: under a production mandate, persistent silence is a condition to act on — research, widen the **aperture** (universe / entry bands / watch set), revise the rules that stopped producing. The guard is the **aperture/floor split**: dormancy moves the aperture, never lowers the **floor** (per-action risk envelope — sizing/stops/var/caps); a dormancy-rationalized floor edit is the pressure-capitulation in a costume. Frame limb = stance (kernel `reviewer_agent.py`); rules = trader `principles.md` §Dormancy-driven + §aperture/floor split. The organ (strategy-vitality cadence) is **Reviewer-authored, NOT bundle-scaffolded** (ADR-275 D1 preserved); research path promoted bootstrap-only → standing capability. Empirical trigger: 16 organic RTH `signal-evaluation` fires (kvk, Jun 8–17) → 0 proposals; the only executed trade ever is an off-hours fixture — a mandate-holder constituted as a rule-executor.
- **ADR-343**: Aperture/Floor as a Kernel-Derivable Principle (LIVE — DP24 amendment v9.7). ADR-342 shipped the split as a trader-bundle rule (file-lists); this lifts the **definition** to the kernel so every production-mandate program inherits the *capacity to derive its own split*. Kernel names the categories program-neutrally (**aperture** = selection surface of what the operation engages; **floor** = per-act integrity + outcomes-in attestation honesty — can't fake an outcome); the Reviewer **derives instances** from MANDATE + ground-truth (ADR-222: kernel names category, never instance). Over-determined by DP23 (floor=consequential-gate class) + DP25 (topology lock) + DP27 (aperture=watch portfolio). Frame made program-neutral. VALIDATED on alpha-author (derived floor=anti-slop/voice / aperture=topic+source+format with no hand-authored rules).
- **ADR-344**: The Standing Obligation (LIVE — DP30 v9.8, the altitude ABOVE DP24). A Reviewer is accountable for its mandate's **reachability**, not only its rules. It **derives an owed-output** (budget→pace × mandate→output kind+volume × quality bar — "the long-standing to-do"), checks actual-vs-owed at wake-time, and **classifies a shortfall**: **(A) quiet-world** → dormancy/aperture; **(B) structurally-can't** (the loop has no organ to originate what it owes) → author the missing organ within the floor (Reviewer-authored, ADR-275 D1) OR surface + Clarify. Floor never moves to close the gap. The **wake-time self-application of DP26** (which was design-time bundle conformance — orthogonal: a bundle can be flow-complete on paper yet structurally inert at runtime). Empirical trigger: a left-alone alpha-author converges to *articulate inaction* (recurrences all audit, none originates) — autonomy-in-costume. Stance→frame (ceiling 11k→11.5k, ADR-344 §10); derivation+thresholds→both bundles' principles.md §Standing-Obligation; optional explicit owed-output→MANDATE. VALIDATED on author (classified (B), offered compose-organ within floor, 0 floor writes); author loop closes fully on the operator's compose-authority decision.
- **ADR-345**: Expected Output — the workspace's declared output contract + autonomy-as-witness reframe (LIVE — GLOSSARY v2.8). Gives ADR-344's derived owed-output a **declared** referent. **Rhythm** (`_budget.yaml` = rate of attention, ADR-327) and **Expected Output** (the output contract — kind + delivery-cadence + bar) are **orthogonal, captured separately** (a trader wakes every minute / produces zero trades for weeks = on-contract; an author wakes weekly / owes 2 essays/month — neither derives the other). Home: `MANDATE ## Expected Output` (prose, the promise) + `governance/_expected_output.yaml` (machine sidecar, Reviewer-reads-not-authors). A **delivery-cadence the floor gates, NEVER a quota** (a quota = the Goodhart pressure the floor resists). **Autonomy-as-witness reframe** (prose only — gate code already behaves this way per `permission.py`): autonomy is the **witness dial** (which beats the operator witnesses before they bind), not a ceiling — the agent always works the full job; QUEUE = decided-and-waiting-for-witness, never blocked. Resolves "does full autonomy = zero operator approval?" → yes. Reclassifies the author Path-A/B Clarify as a missing-contract symptom. Wired: `expected_output_yaml` in the wake envelope + ReviewerContext; standing-obligation reads declared-then-derive. Both bundles ship worked instances.
- **ADR-326** (DRAFT): de-name "Reviewer" → operator-facing entity is "your Agent" that HAS a Persona (not IS one); internal `reviewer` slug preserved.

**Permission / cost / autonomy:**
- **ADR-307**: Unified Permission Taxonomy (LIVE — DP23). One gate at `execute_primitive()`, not scattered per-tool; consequential actions gate, reads/narration don't; one durable queue (`action_proposals`). Adopts the Claude Code architecture.
- **ADR-291** unified cost ledger (`execution_events` is the sole cost ledger; collapses the token_usage parallel). **ADR-300→327**: pace retires. **ADR-327** Budget and the Self-Improving Loop (LIVE — cost governance collapses to one `_budget.yaml`; calibration drives cadence; supersedes 300/313). **ADR-334** Per-Operation Pricing (RATIFIED direction — delegation-tiered seats Supervised/Delegated/Autonomous $149/$299/$499 over the cost ledger; AUTONOMY dial IS the pricing axis).
- **ADR-325** Embed as a gated primitive (make-AI-ready is explicit + autonomy-governed, flows through the 307 gate). **ADR-324** InferContext dissolution (it's a workflow not a primitive — merge/gap-detect/author relocate to server helpers + WriteFile).

**Interop / moat:**
- **ADR-310/311**: the interop face (LIVE framing — Proposed). **ADR-310** Judged Substrate Served Everywhere (MCP is the *distribution face* of authored-substrate-under-judgment, not a separate moat; foreign writes judged async via `substrate_event` wake). **ADR-311** Primitive Interop Surface (exposes raw kernel file + revision primitives over MCP — ReadFile/WriteFile/SearchFiles/QueryKnowledge/ListRevisions/DiffRevisions; supersedes ADR-169's intent-shaped tools). This is the "one moat, two faces" canon.

**Output / programs / ground-truth:**
- **ADR-282** Axiom 8 rename (Money-Truth → Ground-Truth Substrate, kernel concept). **ADR-283** alpha-author bundle (second program — substrate-continuity archetype). **ADR-287** bundle conformance CI discipline. **ADR-330** Ground-Truth Intake (LIVE — generalized beyond platform APIs: CSV/operator/retrospective intake; attestation field `platform|operator|agent` on every outcome). **ADR-332** Four-Flow Completeness Model (RATIFIED framing — DP26: context-in → work-out → outcomes-in → loop; a program IS a flow-declaration set).
- **ADR-333** Compose as Lazy Projection (LIVE — retire eager auto-compose; render pulled at consumption). **ADR-317** Daily P&L post-judgment dispatcher (out-of-band email via system Resend wire). **ADR-299/304** operator-addressing writes (email/Slack/Notion) are *system infrastructure*, not workspace capabilities.

**Perception field (the latest arc):**
- **ADR-335**: Perception Field (LIVE — FOUNDATIONS Axiom 1 §8 + DP27). Reality enters only as attributed observation; watches are *declared* (kernel slot `substrate_abi.watches`), never crawled; transports are peripherals (driver-class, transport-blind judgment); attention is calibrated like acts. **ADR-336** TrackWebSources (web/RSS standing watch, mechanical zero-LLM).

**Surfaces / management plane / experience (the FE frontier):**
- **ADR-289** feed vs conversation render grammars. **ADR-297** Surfaces as Substrate Mirror (LIVE — 16 atomic kernel surfaces mirror substrate files; compositor owns the surface registry; supersedes 244/266/243). **ADR-316** chat as a dockable rail (flex-row sibling, not overlay). **ADR-329** Files as First-Class Work-Legibility Surface (five file verbs carry the whole permission story). **ADR-337/339** file-layer verb completion (EditFile/DeleteFile/MoveFile + exact SearchFiles; killed the 0-byte WriteFile class; recursive ListFiles with git-status-shape metadata).
- **ADR-331** Setup as Rendering (LIVE — `/setup` is a Sequence surface walking flow declarations, not a system; harvest is a bounded invocation). **ADR-338** Management Plane (LIVE framing + FE — DP28: operating the operation is first-class product; consent line separates legible surface from invisible mechanics; App Store / installer / drivers / System Settings vocabulary).
- **ADR-340**: Operator Experience Model (LIVE — DP29, the current capstone). **"Mirror once, compose few"** — two surface classes (mirror = one surface↔one substrate concern, the escape hatch; composition = one surface↔one operator *act*). Standing loop (Decide/Read/Dwell/Tune/Amend/Setup) derived from four flows × consent line. Attention routing is OS-owned, derived-never-stored. **Open follow-ons** (ADR-340 §9, deferred): launcher IA re-sort (~17→~7); Home re-derivation as "front page of compositions."

---

If an external system (Claude Code, ChatGPT, etc.) does something differently, check if YARNNN has an ADR explaining why we chose a different approach.

### 1. Documentation Alongside Code

When refactoring or implementing features:
- Update relevant ADRs with implementation status
- Update `docs/database/ACCESS.md` if schema changes
- Keep inline docstrings current with behavior

### 2. Singular Implementation (No Dual Approaches)

- **Delete legacy code** when replacing with new implementation
- **No backwards-compatibility shims** unless explicitly required for migration
- **One way to do things** - avoid parallel implementations that cause confusion
- If old code is superseded, remove it entirely

### 3. Database Operations

- **SQL execution**: Refer to `docs/database/ACCESS.md` for connection strings
- **Migrations**: Run via psql with the connection string in ACCESS.md
- **Schema verification**: Always verify table/column names match current schema
- **PostgREST cache**: After schema changes, may need Supabase dashboard refresh

### 4. Code Quality Checks

Before completing work:
- **Double-check endpoints**: Verify API routes match frontend calls
- **Column name mismatches**: Ensure code uses current schema (e.g., `platform` not `provider`)
- **Import paths**: Verify all imports resolve correctly

### 5. Render Service Parity

YARNNN runs on **4 Render services** (ADR-083: worker + Redis removed; ADR-118: output gateway added; ADR-153: platform sync removed). When changing environment variables, secrets, or architectural patterns, check ALL services:

| Service | Type | Render ID |
|---------|------|-----------|
| yarnnn-api | Web Service | `srv-d5sqotcr85hc73dpkqdg` |
| yarnnn-unified-scheduler | Cron Job | `crn-d604uqili9vc73ankvag` |
| yarnnn-mcp-server | Web Service | `srv-d6f4vg1drdic739nli4g` |
| yarnnn-render | Web Service (Docker) | `srv-d6sirjffte5s73f90pfg` |

All execution is inline — no background worker, no Redis. Output gateway (yarnnn-render) is independent (Docker, pandoc + python-pptx + openpyxl + matplotlib + pillow). See ADR-118 for the "Claude Code online" model: two-filesystem architecture — capability filesystem (skills in `render/skills/`, platform-wide) + content filesystem (workspace_files + S3, user-scoped). Skills follow Claude Code SKILL.md conventions.

**Critical shared env vars** (must be on API + Unified Scheduler):
- `INTEGRATION_ENCRYPTION_KEY` — Fernet key for OAuth token decryption. Scheduler needs it for task execution with platform APIs.
- `NOTION_CLIENT_ID` / `NOTION_CLIENT_SECRET` — needed by Scheduler for task execution with Notion API

**API-only env vars** (not needed on schedulers):
- `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` — ADR-147: only needed for OAuth initiation on API. Schedulers use encrypted tokens from DB for sync.

**MCP Server env vars** (separate from above — MCP server uses service key, not user JWTs):
- `SUPABASE_SERVICE_KEY` — Service key for RLS bypass (same as Schedulers)
- `MCP_USER_ID` — User UUID for data scoping (auto-approve OAuth + static bearer fallback)
- `MCP_BEARER_TOKEN` — Static bearer token for Claude Desktop/Code
- `MCP_SERVER_URL` — OAuth issuer URL (defaults to `https://yarnnn-mcp-server.onrender.com`)

**MCP Auth model** (ADR-075): OAuth 2.1 for Claude.ai/ChatGPT (auto-approve, tokens stored in `mcp_oauth_*` tables). Static bearer token fallback for Claude Desktop/Code. See `api/mcp_server/oauth_provider.py`.

**Output gateway env vars** (yarnnn-render — independent Docker service, ADR-118):
- `SUPABASE_URL` — For storage uploads
- `SUPABASE_SERVICE_KEY` — For storage uploads (service key, same as Schedulers)
- `RENDER_SERVICE_SECRET` — Shared secret for service-to-service auth (ADR-118 D.2, must match API + Scheduler)

**RuntimeDispatch env vars** (must be on API + Unified Scheduler):
- `RENDER_SERVICE_URL` — URL of yarnnn-render service (defaults to `https://yarnnn-render.onrender.com`)
- `RENDER_SERVICE_SECRET` — Shared secret for authenticating to POST /render (ADR-118 D.2, must match Render service)

**Common mistake**: Adding an env var to the API service but forgetting the Scheduler. The API handles OAuth and stores tokens; Scheduler decrypts and uses them for task execution with platform APIs.

**Impact triggers** — if you change any of these, check the affected services:
| If you change... | Also check... |
|-----------------|--------------|
| Env vars (any) | All 4 services — use Render MCP `update_environment_variables` |
| OAuth flow / token handling | Unified Scheduler (decrypts & uses tokens for task execution) |
| Supabase schema (RPC, tables, RLS) | Unified Scheduler + MCP Server (both use service key) |
| Agent execution / pipeline logic | Unified Scheduler (triggers agent runs via cron) |
| MCP tool definitions / auth | MCP Server (separate service, separate deploy) |
| Output gateway / artifact rendering | yarnnn-render (independent Docker service, ADR-118) |

**Note**: Both platforms (Slack, Notion) use Direct API clients — no gateway service needed (ADR-076).

### 6. Git Workflow

- **Commit when appropriate**: Can commit and push when changes are complete and tested
- **Meaningful commits**: Use conventional commit style with ADR references where applicable
- **No force pushes** to main unless explicitly requested

### 7. Progress Tracking

- **Use TodoWrite tool** for multi-step tasks to track progress
- **Share progress** to keep context visible across conversation turns
- **Mark todos complete immediately** after finishing each step

### 8. Hooks (Automated Reminders)

Two hooks auto-inject context so the user doesn't need to manually paste reminders.

- **Config**: `.claude/settings.json` (committed, shared)
- **Hook files**: `.claude/hooks/` directory

| Hook | Event | Matcher | Purpose |
|------|-------|---------|---------|
| `execution-reminders.txt` | `UserPromptSubmit` | all | Execution disciplines (singular impl, docs, quality checks, etc.) — every message |
| `session-reorient.sh` | `SessionStart` | `startup\|compact` | Recent git log + orientation checklist — new sessions and post-compaction |

- **To edit reminders**: Update the `.txt` or `.sh` file — no need to touch hook config

### 9. File Format Discipline (ADR-254)

Every workspace file has exactly one primary consumer. Format follows the consumer:

| Format | Primary consumer | Rule |
|--------|-----------------|------|
| `.md` (UPPERCASE) | Operator / LLM | Prose docs — `MANDATE.md`, `IDENTITY.md`, `AUTONOMY.md`. Never machine-parsed. |
| `.md` (lowercase) | LLM / append-only | Accumulated narrative — `principles.md`, `decisions.md`, `_performance.md`. Never machine-parsed. |
| `_.yaml` (underscore prefix) | Python code | Machine config/state — `_autonomy.yaml`, `_universe.yaml`, `_principles.yaml`. Always `yaml.safe_load()`. |
| `_.yaml` (recurrence declarations) | Scheduler | `_spec.yaml`, `_action.yaml`, `_recurring.yaml`, `back-office.yaml`. |
| `.json` | Machine only | Manifests — `sys_manifest.json`. No comments needed. |
| `.html` | Render surface | Composed output artifacts. System-produced. |

**Rules:**
- **No new YAML-frontmatter `.md` files.** `_performance.md` and `OCCUPANT.md` are grandfathered exceptions (machine-written body + LLM reads full content). No new mixed-format files.
- **No hand-rolled frontmatter parsers.** Use `load_workspace_yaml()` from `services.review_policy` for `.yaml` bodies, or `re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)` + `yaml.safe_load()` for frontmatter extraction. No regex line-splitting.
- **Underscore prefix = machine-parsed.** All `_*.yaml` files are machine-parsed config or state. Human edits these to configure; Python reads them at runtime.
- **Integer fields in `.yaml` are ints, not strings.** `ceiling_cents: 20000` not `ceiling_cents: "20000"`. `load_autonomy()` and `load_principles()` now coerce and log on mismatch.

### 10. MCP Servers (Local Setup)

Project-scoped MCP servers wired in `.mcp.json` at the repo root. The file itself contains no secrets — tokens flow in via `${VAR}` shell-env interpolation, so the file is safe to commit.

| Server | Transport | Required env var (parent shell) | Scopes |
|--------|-----------|---------------------------------|--------|
| `sentry` | stdio (`npx @sentry/mcp-server`) | `SENTRY_AUTH_TOKEN` | `org:read`, `project:read`, `event:read`, `team:read` |

- **Token setup**: mint at https://sentry.io/settings/account/api/auth-tokens/, `export SENTRY_AUTH_TOKEN=...` in `~/.zshrc`, `source` it, restart Claude Code.
- **Never paste the token into chat, JSON, or git.** If it leaks, revoke immediately and mint a fresh one — Sentry tokens are shown once at creation.
- **Restart required**: `.mcp.json` changes are read at Claude Code startup, not hot-reloaded.

---

## Prompt Change Protocol

When modifying any prompt, tool definition, or orchestration heuristic in these files:
- `api/agents/thinking_partner.py` (YARNNN system prompt)
- `api/services/primitives/*.py` (tool definitions)
- ~~`api/services/composer.py`~~ DELETED (ADR-156 — Composer sunset)

You MUST:
1. Update `api/prompts/CHANGELOG.md` with the change
2. Note the expected behavior change
3. If significant, increment the version comment at the top of the prompt section
4. ~~For Composer changes~~ — DELETED (ADR-156: Composer sunset). No separate orchestration prompts exist.

### Changelog Format

```markdown
## [YYYY.MM.DD.N] - Description

### Changed
- file.py: What changed and why
- Expected behavior: How this affects YARNNN/tool behavior
```

---

## Key Architecture References

### Reviewer seat — substrate canon + partition-discipline canon

**Canonical homes; do not re-derive, look them up first.** If a session would benefit from understanding what `principles.md` is for, what `IDENTITY.md` carries, what the persona-frame owns, what the seat's six files are, or where the content boundaries live — these are the singular references. Per ADR-315 (2026-06-04) the Reviewer technical canon is split along the seat≠occupant line:

- **[`docs/architecture/reviewer-substrate.md`](docs/architecture/reviewer-substrate.md)** — one-screen index routing to the three docs below. Start here if unsure which to read.
- **[`docs/architecture/reviewer-seat-substrate.md`](docs/architecture/reviewer-seat-substrate.md)** — the **kernel/seat** canon. Six seat files, occupant rotation protocol, calibration trail semantics, delegation vocabulary, prospective-attribution contract with chat surfaces. The seat is substrate. Referenced from ADR-194, 195, 211, 212, 253, 280, 282, 284, 285 + FOUNDATIONS Derived Principle 14.
- **[`docs/architecture/reviewer-occupant.md`](docs/architecture/reviewer-occupant.md)** — the **occupant** canon. The AI agent (`reviewer_agent.py`) that fills the seat: occupant classes, `invoke_reviewer`, model-by-trigger, persona-frame discipline, how the occupant consumes the contract.
- **[`docs/architecture/reviewer-occupant-contract.md`](docs/architecture/reviewer-occupant-contract.md)** — the **published ABI** (ADR-315). `ReviewerContext` / `ReviewerOutput` / `REVIEWER_MODEL_IDENTITY` / `invoke_reviewer` / the kernel-side envelope assembler. Defined in `api/agents/occupant_contract.py` (pure data — no LLM runtime; the kernel depends on the contract, never on the occupant impl).
- **[`docs/architecture/agent-composition.md`](docs/architecture/agent-composition.md) §3.2.1** — **the singular enforcement home for the partition between `principles.md` (the rule-set the persona applies) and the persona-frame `_compute_*` sections in `api/agents/reviewer_agent.py` (the reasoning posture).** Names the four-field rule shape, the bright-line list of content that does NOT belong in `principles.md` (self-amendment discipline, anti-patterns, fiduciary principle, posture taxonomy, standing-intent contract, cadence-trifecta, wake-context discipline, write authority, voice/narration — all in persona-frame), the conflict-resolution rule (PRECEDENT > principles; persona-frame > principles for reasoning-posture; AUTONOMY ceiling > principles for delegation widening), and a diagnostic test for uncertain content.

**When to consult §3.2.1**: before editing any `docs/programs/{slug}/reference-workspace/review/principles.md` (bundle template); before drafting an ADR that prescribes principles.md content; before adding a `_compute_*` section to `api/agents/reviewer_agent.py`; when auditing whether a workspace's `principles.md` has drifted to multi-purpose. Future ADRs that reshape principles.md content **must update §3.2.1 in the same commit** — the partition discipline is enforced at the canon layer, not by re-derivation.

The one-line statement (canonized at `agent-composition.md` §4.2 + §3.2.1): **persona is *how to reason*; mandate is *why we exist*; autonomy is *how far decisions bind*; principles is *what the rules of judgment are*.**

### ADR-064: Unified Memory Service (updated by ADR-156, post-ADR-235)

**Memory is in-session** — YARNNN writes facts proactively via `WriteFile(scope="workspace", path="memory/notes.md", content="...", mode="append")` during conversation. Follows the Claude Code model: memory happens in the moment of learning, not as a batch job. (Pre-ADR-235 used `UpdateContext(target="memory")`.)

- ADR-156: Nightly cron extraction REMOVED. YARNNN writes facts in-session.
- Session summaries: generated inline at session close (chat.py), not by nightly cron.
- Session continuity: YARNNN writes shift notes to AWARENESS.md.
- User can still edit memories directly via Context page.
- Working memory injected into YARNNN prompt is unchanged.

**Key files**:
- `api/services/memory.py` — retained for bulk import only (nightly cron removed)
- `api/services/working_memory.py` — formats memory for prompt injection
- `api/agents/prompts/chat/onboarding.py` — memory-write guidance for YARNNN (dir renamed from `tp_prompts/` per ADR-189; reorganized into `prompts/{chat,headless}/` per ADR-233 Phase 1)
- `docs/features/memory.md` — user-facing docs

### ADR-059: Simplified Context Model (Current Schema)

**Tables** (use these names, not legacy):
- `platform_connections` (not `user_integrations`)
- `platform_content` — **DROPPED (ADR-153)**. Was unified content layer with retention (ADR-072). Platform data now flows through tasks into workspace context domains.
- `filesystem_documents` / `filesystem_chunks` — uploaded documents only
- `user_memory` — single Memory store (replaces knowledge_profile, knowledge_styles, knowledge_domains, knowledge_entries)
- `agents` — persistent workforce roster. Identity-only: `role`, `title`, `scope`, `status`, `type_config`, `agent_instructions`, `agent_memory`, `origin`. No schedule, no destination, no mode — those live on tasks. **ADR-205 (2026-04-22):** signup scaffolds exactly ONE row — YARNNN (role=`thinking_partner`, origin=`system_bootstrap`). Specialists (researcher/analyst/writer/tracker/designer/executive) lazy-create on first dispatch via `services.agent_creation.ensure_infrastructure_agent()`. Platform Bots (slack_bot/notion_bot/github_bot/commerce_bot/trading_bot) materialize on OAuth connect and delete on disconnect (connection-bound lifecycle). User-authored Agents use `origin='user_configured'` and are unchanged. The user-facing `/agents` list filters by `origin != 'system_bootstrap'` per ADR-189.
- `tasks` — **thin scheduling index** post-ADR-231 D4 Path B (migration 164). Columns: `id, user_id, slug, status, schedule, next_run_at, last_run_at, created_at, updated_at, declaration_path, paused`. The `mode` and `essential` columns dropped. Authoritative recurrence-declaration substrate is workspace_files YAML at `declaration_path` (e.g., `/workspace/reports/{slug}/_spec.yaml` for DELIVERABLE shape). The table is fully reconstructable from filesystem state via `services.scheduling.materialize_scheduling_index()`. The table name "tasks" identifies the SCHEDULING INDEX, not work substrate. **`/tasks/{slug}/` filesystem tree DELETED per ADR-231 D2.** Per-shape natural-home paths per D2/D3: DELIVERABLE → `/workspace/reports/{slug}/_spec.yaml` + `/workspace/reports/{slug}/{date}/output.md`; ACCUMULATION → entry in `/workspace/context/{domain}/_recurring.yaml`; ACTION → `/workspace/operations/{slug}/_action.yaml`; MAINTENANCE → entry in `/workspace/_shared/back-office.yaml` + audit log at `/workspace/_shared/back-office-audit.md`.
- `agent_runs` — execution audit trail per agent (was `deliverable_versions`, renamed ADR-103). ADR-118 D.3: dual-write (content still written for frontend compat), but delivery reads from workspace_files output folders. Will become pure audit trail when frontend migrates.
- `agent_type` — column on `agents` table, **DEPRECATED** by ADR-109 — being replaced by `scope` + `role`
- `agent_instructions` — column on `agents` table, **DEPRECATED** by ADR-106 Phase 2 — migrated to workspace `AGENT.md`. No longer written for new agents. DB column kept only for lazy migration of pre-workspace agents via `ensure_seeded()`. Workspace AGENT.md is sole authority.
- `agent_memory` — column on `agents` table, **DEPRECATED** by ADR-106 Phase 2 — migrated to workspace `memory/*.md`. No longer written for new agents. Workspace memory files are sole authority.
- `workspace_files` — virtual filesystem for agent workspaces (ADR-106); path-based access, full-text + vector search; `content_url` column for rendered binary files (ADR-118). ADR-118 Phase D: becomes the single output substrate for all agent outputs (text + binary), replacing agent_runs as the delivery source. ADR-119: adds `version` + `lifecycle` columns; folder conventions (output folders with `manifest.json`, project folders, ephemeral `/working/`) replace relational grouping tables. **ADR-209 (2026-04-23)**: adds `head_version_id` pointer column + two sibling tables for the Authored Substrate: `workspace_blobs` (content-addressed CAS keyed by sha256) and `workspace_file_versions` (parent-pointered revision chain with required `authored_by` + `message` attribution). `ADR-119 Phase 3 /history/` subfolder convention superseded — versioning moves from filesystem namespace to substrate-native revision chain. `version` integer column scheduled for drop in ADR-209 Phase 5.
- `workspace_blobs` — ADR-209 Authored Substrate: content-addressed immutable store keyed by sha256. Shared across workspaces (identical content reuses one blob). No user-level scoping — scoping lives at the revision layer.
- `workspace_file_versions` — ADR-209 Authored Substrate: parent-pointered revision chain per `(user_id, path)`. Every mutation to `workspace_files` produces exactly one row here. `authored_by` taxonomy: `operator` | `yarnnn:<model>` | `agent:<slug>` | `specialist:<role>` | `reviewer:<identity>` | `system:<actor>`. `parent_version_id` is NULL on the first revision for a path; forms a walkable DAG.
- `workspace_file_versions` — NOT a table; version history uses `/history/` subfolder convention (ADR-119 Resolved Decision #3). On overwrite of high-value files (thesis.md, memory/*.md, AGENT.md), previous version copied to `/agents/{slug}/history/{filename}-v{N}.md`. Implemented in Phase 3.
- `mcp_oauth_clients` / `mcp_oauth_codes` / `mcp_oauth_access_tokens` / `mcp_oauth_refresh_tokens` — MCP OAuth 2.1 storage (ADR-075, service key only)
- `render_usage` — per-user render call tracking (ADR-118 D.2); `get_monthly_render_count()` RPC for tier limit enforcement
- `wake_queue` — **ADR-298 transient compute, not authoritative state** (migration 179, ADR fully Implemented 2026-05-22). Per-workspace queue for single-lane Reviewer execution with two-lane drain (paced/live). Mechanically reconstructable from filesystem + DB substrate at every moment per Axiom 1; modeled on `tasks` scheduling-index precedent (ADR-231 D4). UNIQUE `(user_id, wake_source, dedup_key)` enforces cross-source dedup at insert time — the **singular dedup surface** post-Phase 5 (legacy `execution_events.wake_dedup_key` column dropped via migration 180 + walker pre-check + telemetry kwarg removed in commit `dc36cdf`). Status taxonomy: `pending → locked → completed | failed | dropped`. RLS service-role-only; operators do NOT read queue directly — they read configuration (yaml), outcomes (feed + `execution_events`), and watch-state (`standing_intent.md`). Service helpers in `api/services/wake_queue.py`.

**Removed files** (ADR-064 + ADR-090 + ADR-092):
- `api/services/extraction.py` — replaced by `memory.py`
- `api/services/work_execution.py` — replaced by `agent_execution.py`
- `api/agents/factory.py` — replaced by `generate_draft_inline()`
- `api/routes/work.py`, `api/routes/agents.py` (old) — work_tickets endpoints removed
- `api/services/signal_extraction.py`, `api/services/signal_processing.py` — dissolved in ADR-092
- `api/routes/signal_processing.py` — dissolved in ADR-092
- `api/integrations/readers/` — deprecated module, zero imports

**Removed tables** (ADR-059 — do not reference in new code):
- `knowledge_profile`, `knowledge_styles`, `knowledge_domains`, `knowledge_entries`
- `deliverables`, `deliverable_versions`, `deliverable_*` — renamed to `agents`, `agent_runs`, `agent_*` (ADR-103)
- `work_tickets`, `work_outputs` — dropped

### ADR-077: Platform Sync Overhaul — **SUPERSEDED by ADR-153**

**ADR-153 sunset**: `platform_content` table, `platform_worker.py`, `platform_sync_scheduler.py` all deleted. Platform data now flows through tasks into workspace context domains. Agents call platform APIs live during task execution.

**Preserved infrastructure**: `platform_connections` (OAuth tokens), API clients (`slack_client.py`, `notion_client.py`, `github_client.py`), `sync_registry` (observability), `landscape.py` (source discovery).

### ADR-106: Agent Workspace Architecture

**Virtual filesystem over Postgres** — agents interact with workspace via path-based operations (`read`, `write`, `list`, `search`). Storage-agnostic abstraction layer.

- **Schema**: `workspace_files` table with `path`, `content`, `embedding`, `tags`
- **Path conventions**: `/agents/{slug}/AGENT.md` (like CLAUDE.md), `/agents/{slug}/thesis.md`, `/agents/{slug}/memory/*.md` (topic-scoped), `/knowledge/slack/{channel}/{date}.md`
- **Agent archetypes**: Reporter (platform dump, unchanged), Analyst (workspace-driven search), Researcher (workspace + WebSearch), Operator (future)
- **Key change**: Reasoning agents drive own context gathering from workspace. No pre-gathered platform dump.
- **Replaces**: `agent_memory` JSONB blob, `user_memory` KV pairs (phased migration)
- **Abstraction**: `AgentWorkspace` class — swap backing store without changing agent code

**Key files** (to be created in Phase 1):
- `api/services/workspace.py` — AgentWorkspace + KnowledgeBase abstraction
- `api/services/primitives/workspace.py` — ReadWorkspace, WriteWorkspace, SearchWorkspace, QueryKnowledge
- `api/services/execution_strategies.py` — AnalystStrategy, ResearcherStrategy additions

### ADR-057: Streamlined Onboarding (updated by ADR-113)

- OAuth callback auto-discovers landscape + auto-selects sources + kicks off sync (ADR-113)
- Redirects to `/orchestrator?provider=X&status=connected`
- Source curation on context pages is optional refinement, not prerequisite
- Tier-gated source limits enforced by `compute_smart_defaults()` max_sources

### ADR-056: Per-Source Sync

- Sync operates per-source (channel, label, page) not per-platform
- `integration_import_jobs` — DEPRECATED (ADR-153 + ADR-156: import jobs sunset, platform data flows through task execution)

---

## File Locations

| Concern | Location |
|---------|----------|
| YARNNN Chat Surface (Orchestration) | `api/agents/yarnnn.py` — YarnnnAgent class. Renamed from `thinking_partner.py` per ADR-189. Classified as orchestration chat surface, not persona-bearing Agent, per ADR-216. |
| YARNNN Prompt Profiles (ADR-186 + ADR-233 Phase 1) | `api/agents/prompts/` — five-profile registry under one home. **Shared (root)**: `__init__.py` (resolver — `build_prompt(profile_key)` + `build_system_prompt(profile=...)` + `PROFILE_KEYS` + `HEADLESS_POSTURES`), `base.py` (chat identity/tone — platform-fixed voice, NO workspace-authored IDENTITY per ADR-216 D2), `tools_core.py` (shared primitive docs), `platforms.py` (shared platform tools). **Chat profiles** (`prompts/chat/`): `workspace.py` (workspace profile), `entity.py` (entity profile), `activation.py` (ADR-226 activation overlay), `onboarding.py` (CONTEXT_AWARENESS for workspace profile), `task_scope.py` (entity preamble template), `behaviors.py` (legacy BEHAVIORS_SECTION, no longer wired). **Headless profiles** (`prompts/headless/`): `base.py` (HEADLESS_BASE_BLOCK — universal output rules, conventions, accumulation-first, tool usage, visual assets, empty-context handling), `deliverable.py` (DELIVERABLE_POSTURE — replacive gap-filling), `accumulation.py` (ACCUMULATION_POSTURE — additive folder-as-mind), `action.py` (ACTION_POSTURE — propose-not-execute Reviewer-gated). Five profile keys: `chat/workspace`, `chat/entity`, `headless/deliverable`, `headless/accumulation`, `headless/action`. Dir renamed from `tp_prompts/` (ADR-189) → `yarnnn_prompts/` → `prompts/{chat,headless}/` (ADR-233 Phase 1, commit `cdbf5de`). |
| YARNNN Profile Resolver | `api/routes/chat.py` — `resolve_profile()`, `SURFACE_PROFILES` dict |
| Chat Agent (Meeting Room) | `api/agents/chat_agent.py` (ADR-124: agent_chat mode) |
| Tool Primitives (code) | `api/services/primitives/*.py` — canonical registry in `registry.py` |
| Tool Primitives (canonical doc) | `docs/architecture/primitives-matrix.md` (ADR-168) — substrate × mode × capability matrix, rename protocol, deleted primitives ledger |
| Memory Service | `api/services/memory.py` |
| Working Memory | `api/services/working_memory.py` |
| Chat/Streaming | `api/services/anthropic.py` |
| OAuth Flow | `api/integrations/core/oauth.py` |
| **Workspace (canonical doc)** | `docs/architecture/WORKSPACE.md` — layers, filesystem inventory, 5-phase bootstrap, autonomy threshold. Paired with `docs/design/WORKSPACE.md` (per-tab surface contracts). **Start here for anything substrate/init/onboarding/bootstrap/autonomy-threshold.** |
| Workspace Initialization | `api/services/workspace_init.py` — `initialize_workspace()` (5 phases: YARNNN row → skeletons → narrative session → balance audit → optional fork). Called by `GET /api/workspace/state` (lazy scaffold), `DELETE /account/workspace` (L2), `DELETE /account/reset` (L4). |
| Workspace Path Constants | `api/services/workspace_paths.py` — `SHARED_CONTEXT_FILES` (kernel-seeded set: MANDATE, IDENTITY, BRAND, AUTONOMY, PRECEDENT). `SHARED_CONVENTIONS_PATH` kept as a constant but **not in `SHARED_CONTEXT_FILES`** — CONVENTIONS is program-scoped. |
| Workspace Utilities | `api/services/workspace_utils.py` — `is_skeleton_content()` + `classify_file_state()`. Single source of truth for skeleton detection (used by init, workspace state surface, and activation state classifier). |
| Program Lifecycle (fork) | `api/services/programs.py` — `fork_reference_workspace()`, `_strip_tier_frontmatter()`, `parse_active_program_slug()`, `strip_program_marker_from_mandate()`. Bundle fork logic is here, not in workspace_init. |
| Back-Office Lifecycle | `api/services/back_office/__init__.py` — `materialize_back_office_task()`. Trigger-based (first proposal, platform connect). NOT called at signup. |
| Agent Workspace | `api/services/workspace.py` (ADR-106) |
| Workspace Primitives | `api/services/primitives/workspace.py` (ADR-106) |
| Authored Substrate (ADR-209) | `api/services/authored_substrate.py` — `write_revision()` is the single write path for every `workspace_files` content-layer mutation. Also `list_revisions()`, `read_revision()`, `count_revisions()`, `is_valid_author()`. **Phase 5 (2026-04-23) — ADR CLOSED**: Migration 159 dropped `workspace_files.version`, tightened lifecycle constraint (`archived` enum value removed), deleted residual `/history/` artifact row. `workspace_files.content` denormalization retained after measurement (FTS + embedding indexes require it). Permanent CI regression guard `api/test_adr209_no_filename_versioning.py` (12 banned-pattern checks with allowlist). Branches + distributed replication explicitly out of scope per D10 + authored-substrate.md §7. **Phase 4 (2026-04-23)** adds HTTP revision endpoints, optional `message` field on `PATCH /api/workspace/file`, new `web/components/workspace/RevisionHistoryPanel.tsx` wired into BrandSection / TaskContentView / AgentContentView. `_append_inference_meta` schema simplified (dropped `inferred_at`). `save_identity` / `save_brand` routes now pass explicit `authored_by="operator"`. **Phase 3 (2026-04-23)** adds read-side primitives at `api/services/primitives/revisions.py`: `ListRevisions` / `ReadRevision` / `DiffRevisions` (chat + headless; NOT MCP — ADR-169 intent-shape). `ListFiles` extended with `authored_by`/`since`/`until` filters. `working_memory._get_recent_authorship_sync()` + one-line activity summary in compact index. "Revision-Aware Reading" posture in `yarnnn_prompts/tools_core.py`. **Phases 1–2 (2026-04-23)**: every caller in `services/workspace.py`, `services/task_workspace.py`, `services/reviewer_audit.py`, `services/primitives/workspace.py`, `services/primitives/runtime_dispatch.py`, `services/outcomes/ledger.py`, and `routes/{documents,chat,workspace,integrations}.py` routes through `write_revision`. `/history/` subfolder convention, `_archive_to_history`, `_cap_history`, `_is_evolving_file`, `list_history`, ADR-176 Phase 4 entity-profile `v{N}.md` archive all DELETED. Permitted direct-mutation exceptions (2): `authored_substrate._upsert_workspace_file` (the write target) and `primitives/workspace._embed_workspace_file` (metadata-only embedding update). Test gates: Phase 1 (11/11) + Phase 2 (14/14) + Phase 3 (15/15) + Phase 4 (13/13) + Phase 5 (12/12) = **65/65**. |
| Agent Framework (canonical) | `docs/architecture/agent-orchestration.md` (ADR-109) |
| Directory Registry | `api/services/directory_registry.py` (ADR-152: WORKSPACE_DIRECTORIES — context domains, uploads, output categories) |
| Agent Framework (code) | `api/services/orchestration.py` (ADR-140 + ADR-166: workforce roster, AGENT_TEMPLATES, DEFAULT_ROSTER, capabilities, runtimes, PLAYBOOK_METADATA, TASK_OUTPUT_PLAYBOOK_ROUTING) |
| Agent Playbook Framework | `docs/features/agent-playbook-framework.md` (playbook loading, selective injection, governing axioms) |
| Agent Creation (shared) | `api/services/agent_creation.py` (ADR-111 Phase 1) |
| YARNNN Composer / Heartbeat | DELETED (ADR-156 — Composer sunset, single intelligence layer) |
| Agent Pulse Engine | DELETED (ADR-141: dissolved into scheduler SQL + task pipeline) |
| Invocation Dispatcher | `api/services/invocation_dispatcher.py` (ADR-231: YAML-native dispatch — `dispatch(decl)` routes by RecurrenceShape; replaces deleted `task_pipeline.execute_task`) |
| Dispatch Helpers | `api/services/dispatch_helpers.py` (ADR-231 Phase 3.7: survivor helpers — `_generate`, `gather_task_context`, `build_task_execution_prompt`, `_load_user_context`, empty-state writers; all natural-home substrate via UserMemory + recurrence_paths) |
| Recurrence Module | `api/services/recurrence.py` + `recurrence_paths.py` (ADR-231: YAML schema + walker + path resolution per D2/D9/D10) |
| Scheduling | `api/services/scheduling.py` (ADR-231 Phase 3.3: `compute_next_run_at`, `materialize_scheduling_index`, `get_due_declarations`, CAS claim) |
| Recurrence Lifecycle Primitive | `api/services/primitives/manage_recurrence.py::handle_manage_recurrence` + `services/primitives/fire_invocation.py` (ADR-235 D1.c: `Schedule(action=...)` for create/update/pause/resume/archive + `FireInvocation` for manual fire. **Replaces** deleted `UpdateContext(target='recurrence')` and `ManageTask` primitives.) |
| Inference Primitives (ADR-235 D1.a) | `api/services/primitives/infer_context.py::handle_infer_context` (identity/brand merge) + `api/services/primitives/infer_workspace.py::handle_infer_workspace` (first-act scaffold). **Replaces** deleted `UpdateContext(target='workspace'\|'identity'\|'brand')`. |
| Substrate Write Primitive (ADR-235 D1.b + Option A) | `api/services/primitives/workspace.py::handle_write_file` with `scope='workspace'`. Reaches operator-shared substrate (`context/_shared/*`, `memory/*`, `reports/*/feedback.md`, etc.) via workspace-relative path. Recognized canonical paths emit activity-log events automatically. |
| Feedback Formatters (ADR-235 D1.b) | `api/services/feedback_formatters.py` — pure-Python helpers for memory/agent/task feedback formatting; called server-side from chat dispatch when feedback is being routed. |
| Agent Execution (deleted) | DELETED (ADR-271 dead-headless-path sweep, 2026-05-14). Pre-ADR-261 task pipeline `execute_agent_generation` + `generate_draft_inline` + `_build_headless_system_prompt` had no live caller after ADR-141 + ADR-261. Live execution paths today: scheduler → `invocation_dispatcher.dispatch` (Path 1) and chat → `invoke_reviewer(trigger='addressed')` (Path 2). Sub-LLM calls go through `dispatch_specialist.py` (headless tool surface). |
| Delivery Service | `api/services/delivery.py` (ADR-118 D.3: `deliver_from_output_folder()`) |
| Feedback Distillation | `api/services/feedback_distillation.py` (ADR-117: edits → style.md; ADR-231: writes to natural-home `_feedback.md`) |
| Feedback Engine | `api/services/feedback_engine.py` (edit metrics computation) |
| Agent Pipeline | `api/services/agent_pipeline.py` |
| Agent Routes | `api/routes/agents.py` |
| Task Deliverable Inference | `api/services/task_deliverable_inference.py` (ADR-149: feedback → recurrence YAML's `deliverable:` block via UpdateContext per ADR-231) |
| Recurrences Routes | `api/routes/recurrences.py` (ADR-231 Phase 3.8: renamed from `routes/tasks.py`; URL `/api/recurrences/*`) |
| **DELETED (ADR-231 Phase 3.7)** | `api/services/task_pipeline.py` (4,204 LOC), `api/services/task_workspace.py` (319), `api/services/task_types.py` (1,836), `api/services/task_derivation.py` (334), `api/services/primitives/manage_task.py` (1,498) — all replaced by `invocation_dispatcher` + `dispatch_helpers` + recurrence-walker substrate. |
| Dashboard Summary | DELETED (2026-03-22) — collapsed into Agents page |
| Platform Sync Worker | DELETED (ADR-153 — platform_content sunset) |
| Platform Sync Scheduler | DELETED (ADR-153 — platform_content sunset) |
| Platform API Clients | `api/integrations/core/{slack,notion,github}_client.py` |
| Landscape Discovery | `api/services/landscape.py` |
| Tier Limits | `api/services/platform_limits.py` |
| Agent Scheduler | `api/jobs/unified_scheduler.py` (ADR-231 Phase 3.3: walks recurrence YAML declarations via `services.scheduling.get_due_declarations`; thin `tasks` index gates due-row queries). **ADR-298 Phase 3 cutover (2026-05-22):** walkers enqueue to `wake_queue` via `submit_wake_proposal`; the scheduler tick calls `wake_drainer.drain_all_users_with_pending(client)` after the walker block (preceded by `wake_queue.reclaim_stale_locks` for crash recovery per Scenario J). Reviewer is NOT invoked inline by `submit_wake_proposal` post-cutover; execution happens in the drainer with single-in-flight + pace-aware drain. |
| Wake Queue (ADR-298) | `api/services/wake_queue.py` — single-lane Reviewer execution per workspace, two-lane drain (paced/live), cross-source dedup at insert time. Transient compute per Axiom 1 (migration 179, Phase 1 Implemented 2026-05-22). Service helpers: `enqueue`, `get_next_pending`, `try_lock`, `has_in_flight`, `mark_completed`/`mark_failed`/`mark_dropped`, `reclaim_stale_locks`, `gc_completed`, `queue_depth`. |
| Wake Drainer (ADR-298 Phase 3) | `api/services/wake_drainer.py` — drainer pulls pending wakes, respects paced-lane pace cap + single-in-flight constraint, dispatches to source-specific Reviewer-invocation body. `drain_next_for_user`, `drain_user_until_empty`, `drain_all_users_with_pending`, `drain_can_acquire_for_user`, `paced_lane_eligible_to_drain`. Called from scheduler tick after walker block. Phase 3 Implemented 2026-05-22. |
| Pace (ADR-298) | `api/services/pace.py` — operator-declared pace substrate (Trigger-dimension dial of Pace + Autonomy + Persona trifecta, ADR-298 D11). Substrate file `/workspace/context/_shared/_pace.yaml` (machine-parsed yaml, operator-authored only — `SHARED_PACE_PATH` in `DEFAULT_REVIEWER_WRITE_LOCKS`). `parse_pace_yaml()`, `read_pace()`, `cron_fires_per_day()`, `check_population_constraint()`, `pace_at_least_as_frequent()` (Phase 4 ordering helper). Schedule primitive gates `create` + `update(schedule)` against drain rate at declaration time per D5 — returns `pace_exceeded` error when total declared frequency would breach cap. Pace included in reviewer wake envelope (ADR-276 helper) so Reviewer's mid-loop Schedule() calls land within budget. (Phase 2 Implemented 2026-05-22; Phase 4 ordering helper added 2026-05-22.) |
| Bundle minimum_pace gate (ADR-298 Phase 4) | `docs/programs/{slug}/MANIFEST.yaml::minimum_pace` declared by program author (alpha-trader + alpha-author both ship `daily`); read by `services.bundle_reader.get_minimum_pace(slug)`. Enforced at activation in `services.programs.fork_reference_workspace`: if operator's existing `_pace.yaml` is below the bundle minimum (per `services.pace.pace_at_least_as_frequent`), activation refuses with a `ValueError` carrying Scenario A guidance (raise pace, choose different program, or skip). When operator has no `_pace.yaml` yet (first activation), D8 default-seed writes `pace: {kind: <bundle minimum>}` to the canonical path with `authored_by="system:bundle-fork"`. Operator can later override upward (faster pace allowed) but not downward without deactivating the program first. Reference / deferred / nonexistent bundles return `minimum_pace=None` and bypass the gate entirely. Test gate: `api/test_adr298_phase4_bundle_pace.py` (36/36 PASS). |
| MCP Server | `api/mcp_server/` (ADR-075 infra + ADR-169 tool surface: 3 intent-shaped tools — `work_on_this`, `pull_context`, `remember_this`; fifth caller of `execute_primitive()` per ADR-164) |
| MCP Composition | `api/services/mcp_composition.py` (ADR-169: `compose_subject_context`, `compose_active_candidates`, `classify_memory_target` two-branch, `stamp_provenance`, `derive_client_name`, `extract_domain_from_path`) |
| MCP Feature Docs | `docs/features/mcp/` — `README.md` (entry), `tool-contracts.md`, `workflows.md`, `architecture.md` (ADR-169 canonical product framing) |
| Output Gateway (yarnnn-render) | `render/` (ADR-118: skill library = capability filesystem) |
| Output Gateway Skills | `render/skills/` (8 skills: pdf, pptx, xlsx, chart, mermaid, html, data, image; each folder has SKILL.md + scripts/). ADR-130 Phase 3: chart/mermaid/image survive as asset producers; pptx/html/data dissolve into compose engine; pdf/xlsx retained as export steps only. |
| RuntimeDispatch Primitive | `api/services/primitives/runtime_dispatch.py` (ADR-118). Retained — type-scoping via `has_asset_capabilities()`. |
| Capability Substrate | `docs/architecture/output-substrate.md` (ADR-130: three-registry architecture + output pipeline) |
| Capability Migration Plan | `docs/design/SKILLS-REFRAME.md` (ADR-130: three-registry migration from current system) |
| Frontend API Client | `web/lib/api/client.ts` |
| Sync Error Categorization | `web/lib/sync-errors.ts` (ADR-086) |
| Onboarding / First-run UI | `web/app/auth/callback/page.tsx` (redirect gate) + `web/components/settings/WorkspaceSection.tsx` (Settings → Workspace surface, ADR-244). `web/components/onboarding/` DELETED (ADR-244 D6). |
| Agents Page (Home) | `web/app/(authenticated)/agents/page.tsx` |
| Chat Page | `web/app/(authenticated)/chat/page.tsx` |
| Route Constants | `web/lib/routes.ts` (HOME_ROUTE = "/chat" per ADR-205 F1) |
| Workspace Surface Contracts | `docs/design/WORKSPACE.md` (renamed from SURFACE-CONTRACTS.md 2026-05-12; ADR-215: per-tab contracts + 4-shape CRUD matrix for Chat · Work · Agents · Files; paired with `docs/architecture/WORKSPACE.md`) |
| Invocation & Narrative (canonical) | `docs/architecture/invocation-and-narrative.md` (FOUNDATIONS Axiom 9: atom = one cycle of the six dimensions; narrative = single chat-shaped log of every invocation; task = nameplate + pulse + contract legibility wrapper; `/work` is narrative filtered by task slug) |

---

## Common Pitfalls

1. **Schema mismatch**: Code referencing old table/column names — use `agents` not `deliverables`, `agent_runs` not `deliverable_versions`, `agent_id` not `deliverable_id`
2. **Tool loop exhaustion**: YARNNN hits `max_tool_rounds=5` without text response if tools return empty
3. **PGRST205 errors**: PostgREST schema cache needs refresh after table changes
4. **Render env var drift**: Worker/Scheduler missing env vars that API has — Worker silently fails to decrypt tokens, reports `success=True` with 0 items. Always check all services.
5. **Backend/frontend field name mismatch**: Backend returns one shape (e.g., `selected_sources`), frontend expects another (e.g., `sources`). Verify API response matches frontend consumer.

---

## Quick Commands

```bash
# Run API locally
cd api && uvicorn main:app --reload --port 8000

# Run frontend locally
cd web && pnpm dev

# Run SQL migration
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/XXX_name.sql

# Check recent commits
git log --oneline -20
```
