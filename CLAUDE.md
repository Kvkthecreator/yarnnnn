# CLAUDE.md - Development Guidelines for YARNNN

This file provides context and guidelines for Claude Code when working on this codebase.

## Project Overview

YARNNN is an **autonomous agent platform for recurring knowledge work**. Persistent AI agents connect to work platforms (Slack, Notion), run on schedule, learn from feedback, and produce outputs that improve with tenure.

**Architecture**: Next.js frontend → FastAPI backend → Supabase (Postgres) → Claude API. Agents (identity) + Tasks (work units) as core model.

**Key terminology** (ADR-138, ADR-140):
- **Agent** — persistent domain expert (WHO). Three axes: identity (AGENT.md, evolves), capabilities (type registry, fixed), tasks (assigned, come and go). Pre-scaffolded at sign-up.
- **Agent Types** (ADR-140, v4 domain-steward model) — capability bundles: `competitive_intelligence`, `market_research`, `business_development`, `operations`, `marketing_creative` (domain-stewards) + `executive_reporting` (synthesizer) + `slack_bot`, `notion_bot` (platform-bots). Three classes: **domain-steward** (owns one context domain, multi-step reasoning) vs **synthesizer** (cross-domain composition) vs **platform-bot** (mechanical, scoped to one API).
- **Task** — defined work unit (WHAT). Objective, cadence, delivery, success criteria. Lives in `/tasks/{slug}/TASK.md`. Assigned to one agent. Thin `tasks` DB table for scheduling.
- **Agent Run** — a single execution of an agent on behalf of a task, producing draft/final content
- **Orchestrator / TP** — the user-facing conversational agent. Creates tasks, monitors agents, orchestrates multi-agent work. Absorbs PM coordination role.
- **Workfloor** — the shared workspace substrate. `/workspace/` (identity), `/agents/` (team), `/tasks/` (work), `/knowledge/` (corpus).
- **Perception Pipeline** (was: platform sync) — how agents sense the outside world
- **Knowledge Base** (was: platform_content) — the shared content substrate agents reason over

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
- **ADR-072**: Unified Content Layer - platform_content with retention-based accumulation, TP execution pipeline
- **ADR-080**: Unified Agent Modes - one agent (chat + headless), mode-gated primitives, supersedes ADR-061 two-path separation
- **ADR-087**: Agent Scoped Context - per-agent instructions + memory, session routing via agent_id
- **ADR-088**: Trigger Dispatch - `dispatch_trigger()` in `api/services/trigger_dispatch.py`, single decision point for schedule/event/signal triggers (Phase 1 implemented). **Partially superseded by ADR-126** — pulse decision is now upstream of dispatch; `dispatch_trigger()` invoked only when pulse decides "generate"
- **ADR-092**: Agent Intelligence & Mode Taxonomy - five modes (`recurring`, `goal`, `reactive`, `proactive`, `coordinator`); signal processing dissolved from L3; `RefreshPlatformContent` extended to headless; coordinator agents replace `signal_emergent` origin (Implemented — signal processing removed, modes active, coordinator pipeline in `proactive_review.py`). **Partially superseded by ADR-126** — proactive self-assessment generalized to all agents via pulse Tier 2; coordinator mode dissolved into PM pulse Tier 3
- **ADR-101**: Agent Intelligence Model - four-layer knowledge model (Skills / Directives / Memory / Feedback); learned preferences from edit history injected into headless system prompt; `get_past_versions_context()` includes delivered runs
- **ADR-102**: yarnnn Content Platform - agent outputs written as `platform_content` rows with `platform="yarnnn"`, closing the accumulation loop; always retained; searchable by TP and headless agents; no OAuth, no sync
- **ADR-103**: Agentic Framework Reframe - terminology migration from "deliverable" to "agent" throughout codebase. Agents are persistent autonomous entities, not document generators.
- **ADR-104**: Agent Instructions as Unified Targeting - `agent_instructions` is the single targeting layer; dual-injected into system prompt (behavioral constraints) and user message (priority lens); dead infrastructure deleted (DataSource.scope/filters, SECTION_TEMPLATES, unused type_config fields, template_structure)
- **ADR-105**: Instructions to Chat Surface Migration - directives (instructions, audience) flow through chat; configuration (schedule, sources) stays in drawer; design principle in `docs/design/SURFACE-ACTION-MAPPING.md`
- **ADR-106**: Agent Workspace Architecture - virtual filesystem over Postgres (`workspace_files` table); agents interact via path-based operations; archetype-driven strategies (reporter/analyst/researcher/operator); reasoning agents drive own context gathering from workspace instead of receiving platform dumps; replaces `agent_memory` JSONB; storage-agnostic abstraction layer preserves optionality for cloud storage
- **ADR-109**: Agent Framework — Scope × Role × Trigger taxonomy replacing the 7-type system (ADR-093). Scope (what it knows: platform/cross_platform/knowledge/research/autonomous) determines context strategy. Role (what it does: digest/prepare/monitor/research/synthesize/act) determines prompt + primitives. Trigger (when it acts) = preserved ADR-092 modes. `agent_type` column → `scope` + `role` columns (was `skill`, renamed by ADR-118 Resolved Decision #4 to eliminate naming overload with output gateway skills). Templates are user-facing convenience layer. Canonical reference: `docs/architecture/agent-framework.md`. (Implemented — `skill` → `role` column rename completed in ADR-118 D.1, migration 114.)
- **ADR-110**: Onboarding Bootstrap — deterministic, zero-LLM agent creation on platform connection. Post-sync, auto-creates matching digest agent (Slack→Recap, Notion→Summary) with `origin=system_bootstrap`. Executes first run immediately. Becomes Bootstrap bounded context within Composer (ADR-111). (Implemented.)
- **ADR-111**: Agent Composer — **SUPERSEDED by ADR-156**. Composer deleted. TP is the single intelligence layer for all judgment. Deterministic lifecycle rules (underperformer pausing) moved to scheduler. Workforce health signals (work budget, agent approval rates) moved to working_memory.py. CreateAgent → ManageAgent (ADR-146 pattern).
- **ADR-112**: Sync Efficiency & Concurrency Control — three layers: (1) atomic sync lock on `platform_connections` replacing `SCHEDULE_WINDOW_MINUTES` timing hack, (2) platform-level heartbeat fast-path (Slack latest, Notion search) to skip source iteration when nothing changed, (3) per-source skip hints (deferred). Coordinates all three sync paths (scheduled, manual, TP RefreshPlatformContent). (Implemented.)
- **ADR-113**: Auto Source Selection — eliminates manual source selection as prerequisite for platform connections. OAuth callback auto-discovers landscape, applies `compute_smart_defaults()`, kicks off first sync immediately. Post-OAuth redirect goes to `/orchestrator` (home). Context pages become optional refinement, not first-time entry point. Orchestrator empty state shows platform connect cards for cold-start onboarding. (Implemented.)
- **ADR-114**: Composer Substrate-Aware Assessment — **SUPERSEDED by ADR-156**. Composer deleted. Substrate-aware signals (knowledge corpus, workspace density) absorbed into working_memory.py as TP context.
- **ADR-116**: Agent Identity & Inter-Agent Knowledge Infrastructure — makes agents discoverable and composable. Five phases: (1) knowledge metadata search (QueryKnowledge filters by agent_id/role/scope), (2) agent discovery primitive (DiscoverAgents), (3) cross-agent workspace reading (ReadAgentContext — read-only), (4) agent card auto-generation + MCP exposure (get_agent_card, search_knowledge, discover_agents tools), (5) consumption tracking + Composer agent dependency graph (orphaned producers, missing producers, stale dependencies). Agent-native identity thesis: workspace IS identity, agents are first-class participants not human proxies. (Implemented.)

- **ADR-117**: Agent Feedback Substrate & Developmental Model — unifies feedback rails (user edits, agent self-observation) into workspace as single substrate. Feedback distillation (Phase 1) and self-reflection (Phase 2) preserved. Key files: `feedback_distillation.py` (distill edits → style.md), `feedback_engine.py` (edit metrics). Dual injection: preferences in system prompt (high salience) + gathered context. **Phase 3 seniority-gated capabilities superseded by ADR-130** — capabilities are determined by agent type (fixed at creation), not earned through seniority. Composer coaching deleted (ADR-156). Feedback distillation and self-reflection preserved — agent development is knowledge depth, not capability breadth.

- **ADR-118**: Skills as Capability Layer — "Claude Code online" model. Two-filesystem architecture: capability filesystem (skills on output gateway Docker service, `render/skills/{name}/SKILL.md` + scripts, platform-wide) and content filesystem (workspace_files + S3, user-scoped, accumulating). Adopts Claude Code naming conventions directly: skills (not handlers/capabilities), SKILL.md (not capability guides), skill folders (same structure as Claude Code). Two skill types: local (tools in Docker image, fixed cost) and delegated (external API/MCP, per-call cost). Skills are explicit/curated, earned via feedback-gated progression (Axiom 3). Phases A+B+C+D.1-D.4 Implemented. D.1: skills alignment/rename (`skill`→`role` column). D.2: render hardening (auth, rate limits). D.3: unified output substrate (output folders as delivery source, `deliver_from_output_folder()`, manifest-based email attachments). D.4: skill auto-discovery + 8-skill library. Phase D.5 (assets layer) deferred — implement when user demand emerges. Full analysis: `docs/analysis/skills-as-capability-layer-2026-03-17.md`. **Phase D format-builder skills partially superseded by ADR-130** — 8 format-builder skills dissolve into asset producers (chart/mermaid/image) + HTML compose engine + export pipeline. Two-filesystem architecture and skill auto-discovery preserved.

- **ADR-119**: Workspace Filesystem Architecture — evolves `workspace_files` from flat key-value store to proper folder-based filesystem. Folders are boundaries, folders are context. Key conventions: output folders (`/agents/{slug}/outputs/{date}/`) replace bundle tables — co-located files + `manifest.json` = atomic output. Project folders (`/projects/{slug}/`) with scoped contribution subfolders = cross-agent collaboration. `/working/` = ephemeral scratch. Two schema additions: `version` + `lifecycle` columns on `workspace_files`. Manifest files carry metadata (sources, delivery status, file roles) instead of relational tables. Thesis: folders are boundaries and boundaries are all you need for coordination — same principle as Cowork's folder selection applied to persistent agent workspaces. Makes ADR-118 Phase D structurally sound. Extends ADR-106, interacts with ADR-116 (cross-agent reading), ADR-117 (feedback via manifests). (Phases 1-4 Implemented. Phase 1: output folders + lifecycle + manifest.json. Phase 2: project folders — ProjectWorkspace, CreateProject/ReadProject primitives, /api/projects CRUD, context injection for contributing agents. Phase 3: version history — `/history/{filename}/v{N}.md` convention, capped at 5 versions, `_archive_to_history()` + `list_history()` on AgentWorkspace and KnowledgeBase. Phase 4a: frontend — `/projects` list page, `/projects/{slug}` detail page, dashboard projects section. Phase 4b: AgentOutputsPanel — agent output history tab.)

- **ADR-120**: **Superseded by ADR-138.** Project Execution & Work Budget — makes multi-agent projects alive. PM (Project Manager) is a domain-cognitive agent whose domain is project coordination — NOT a third layer of intelligence. Composer creates projects + PM agents; PM handles execution (contribution freshness, assembly triggering, budget enforcement, escalation to TP). Project heartbeat recurses the cheap-first pattern at project scope. Work budget: autonomous work units (agent runs, assemblies, renders) bounded per user per billing period (Free: 60/mo, Pro: 1000/mo). Intent decomposition: PM translates flat user intent into executable, bounded work plans. Project-level intentions (recurring/goal/reactive) with per-intention trigger, format, delivery, budget. Five phases: (1) PM agent + project heartbeat, (2) assembly execution, (3) work budget governor, (4) intent decomposition + project intentions, (5) Composer v2.0. Absorbs ADR-114 P4. Pricing model (credits vs. subscription) deferred. Implements FOUNDATIONS.md v3. (Phases 1-5 Implemented — P1: `pm` role, PM primitives, project heartbeat. P2: PM decision interpreter, assembly composition + delivery. P3: `work_units` table (migration 117), `check_work_budget()`/`record_work_units()` in platform_limits, scheduler budget gate, RuntimeDispatch budget check, Free 60/Pro 1000 units/month. P4: multi-intention support (superseded by ADR-123 — intentions consolidated into PM's `memory/work_plan.md`), PM prompt v2 with budget_status, `update_work_plan` PM action writes `memory/work_plan.md`, `UpdateWorkPlan` primitive (headless-only, renamed from UpdateProjectIntent by ADR-123), graceful degradation (budget-exhausted → escalate override). P5: Composer prompt v2.0 — `create_project` action, 8-skill library in prompt, budget awareness, `_build_composer_prompt()` extended with projects/budget/skills sections, `_execute_create_project()` resolves slugs + calls handle_create_project(), composition opportunity heuristic in `should_composer_act()`.)

- **ADR-121**: **Superseded by ADR-138.** PM as Project Intelligence Director — evolves PM from logistics coordinator (freshness → assemble) to intelligence director (quality assessment + directive steering + investigation). New actions: `steer_contributor` (write contribution briefs to guide contributors), `request_investigation` (request research on gaps), `assess_quality` (intent-contribution alignment scoring before assembly). Contribution briefs (`/contributions/{slug}/brief.md`) are the steering mechanism — PM writes focus areas, contributors read during context gathering. Mechanics (code, deterministic) and Intelligence (prompts, qualitative) versioned independently. PM prompt versioning: v1.0 (logistics) → v1.1 (intentions) → v1.2 (JSON enforcement) → v2.0 (intelligence director). Four phases: (1) structural foundation + prompt v2.0, (2) quality assessment + assembly gating, (3) investigation + cross-cycle learning, (4) PM developmental trajectory (nascent → senior). Extends ADR-120, implements FOUNDATIONS.md Axiom 1 (PM developmental trajectory) + Axiom 3 (agents develop inward). (Phase 1-2 Implemented — P1: PM prompt v3.0, briefs, quality assessment, steering, contribution content in PM context, assembly prompt v2.0. P2: `_write_contribution_to_projects()` closes critical gap — agent output auto-written to project contributions folder, assembly gating log, work plan focus_areas. Phase 3-4 proposed. Steer path validated end-to-end in production: PM assess→steer→brief→contributor re-run→output updated.)

- **ADR-122**: **Superseded by ADR-138.** Project Type Registry — Unified Scaffolding Layer. Single curated registry (`api/services/project_registry.py`) of project type definitions replaces scattered creation paths. All project creation flows (bootstrap, Composer, TP, API) go through `scaffold_project()`. Platform types (slack_digest, notion_digest) are 1:1 with platform (uniqueness enforced). `type_key` stored in PROJECT.md as immutable identity. Bootstrap rewritten: OAuth → `scaffold_project(type_key)` → project with members + PM (not standalone agent). Composer gap-filling and lifecycle expansion consume same registry. **PM for all projects** — no exceptions, including platform digests. PM agents are project infrastructure, excluded from tier agent limits (`get_active_agent_count` filters `role='pm'`). **Agents produce, projects deliver** — delivery configuration on PROJECT.md, no direct agent delivery (`destination=None`). See `docs/design/PROJECT-DELIVERY-MODEL.md`. Supersedes ADR-110 bootstrap path. Deletes: `BOOTSTRAP_TEMPLATES`, `PLATFORM_DIGEST_TITLES`, `_create_digest_for_platform()`, standalone agent as default creation path. Five phases: (1) registry + scaffold function, (2) bootstrap migration, (3) Composer migration, (4) existing agent migration (soft — new agents always project-scoped, legacy tolerated), (5) dashboard redesign. (Phases 1-3 Implemented. Phase 4: soft migration (new creation paths always project-scoped). Phase 5: project-native dashboard shipped (commit 065c0e5).)

- **ADR-123**: **Superseded by ADR-138.** Project Objective & Ownership Model — resolves intent/intentions naming collision and dual operational substrate. Renames `intent` → `objective` (4-field dict: deliverable, audience, format, purpose = project north star). Objective is mutable by User/Composer/TP, NOT by PM. Deletes `## Intentions` from PROJECT.md — operational planning consolidated into PM's `memory/work_plan.md` (singular substrate). `UpdateProjectIntent` primitive → `UpdateWorkPlan` (writes to PM memory, not PROJECT.md). PROJECT.md becomes the charter (objective + contributors + assembly_spec + delivery). PM reads charter as reference, manages its own operational plan. Legacy migration: `## Intent` accepted on read, auto-migrated; `## Intentions` parsed as `legacy_intentions`, auto-seeded to work_plan on first PM run. PM prompt v4.0 removes `{intentions}` field. Assembly prompt v3.0 uses `{objective}`. Extends ADR-120 (project execution), ADR-121 (PM intelligence), ADR-122 (project type registry). (Phases 1-4 Implemented. P1-2: terminology rename + intentions consolidation. P3: frontend — editable objective in project header, PM quality assessment + briefs in Contributors tab, PM quality/steer events in Timeline tab, `projects.update()` API client method, `PMIntelligence` type. P4: documentation updates across FOUNDATIONS.md, ADR-120, ADR-122, CLAUDE.md.)

- **ADR-124**: **Superseded by ADR-138.** Project Meeting Room — Unified Project Surface. Redesigns `projects/[slug]` as a "meeting room" group chat where agents are visible participants, not abstract data. Five-tab architecture: Meeting Room (chat with attributed messages + activity event cards), Members (contributors + PM intelligence), Context (workspace file browser), Outputs (assembly history), Settings (objective, schedule, delivery). Key architectural insight: **conversation as project context** (Axiom 2 extension) — the meeting room transcript becomes a fourth perception layer alongside external (platform_content), internal (workspace_files), and reflexive (user feedback). Key innovation: users can talk to any agent (`@agent-slug` mentions), not just TP. PM is default interlocutor; TP is implicit infrastructure. New `ChatAgent` class enables agents to participate in conversations with domain-scoped primitives (`agent_chat` mode — third mode alongside `chat` and `headless`). Message attribution via `session_messages.metadata` (`author_agent_id`, `author_agent_slug`, `author_role`). Five phases: (1) ChatAgent class + `agent_chat` mode + routing, (2) Meeting Room frontend + @-mentions + participant panel, (3) agent chat prompts (PM + contributor role-specific), (4) Context tab (workspace browser), (5) Settings tab consolidation. Evolves ADR-119 P4b, extends ADR-080 (two modes → three), integrates ADR-120 (PM primitives in agent_chat), absorbs ADR-123 P3 (PM intelligence panels → inline stream cards). (Phases 1-5 Implemented.)

- **ADR-125**: **Superseded by ADR-138.** Project-Native Session Architecture — two session scopes (Global TP + Project), no standalone agent sessions. Agent requests resolve to their project's session via `resolve_agent_project()`. Thread model: `thread_agent_id` on `session_messages` (NULL = group/meeting room, set = 1:1 agent thread). Project sessions rotate on 24h inactivity (vs 4h for global TP). Author-aware compaction summaries for project sessions attribute decisions to specific agent participants. `chat_sessions.agent_id` DEPRECATED — legacy fallback for agents not yet in projects. Supersedes ADR-087 (agent-scoped sessions). Extends ADR-122 (project-first), ADR-124 (meeting room). (Phases 1-5 Implemented. Migration 123.)

- **ADR-126**: Agent Pulse — Autonomous Awareness Engine. Every agent gets a **pulse** — an autonomous sense→decide cycle upstream of execution. Three-tier funnel: **Tier 1** (deterministic: fresh content? budget? recent run? — zero LLM cost), **Tier 2** (Haiku self-assessment for associate+ agents), **Tier 3** (PM coordination pulse). Pulse decision taxonomy: `generate | observe | wait | escalate`. `agents.next_run_at` → `agents.next_pulse_at`. Scheduler becomes **pulse dispatcher**. **Proactive mode dissolved** — self-assessment generalizes to ALL agents via Tier 2. **Coordinator mode dissolved** — PM Tier 3 pulse handles project coordination. Composer thins to portfolio-only. Role-based pulse cadence: monitor=15min, pm=30min, digest/prepare=12h, others=schedule (in `agent_framework.py`). Activity events: `agent_pulsed`, `pm_pulsed`. Partially supersedes ADR-088 (trigger dispatch), ADR-092 (proactive/coordinator modes), ADR-111 Phases 3-5. Key files: `api/services/agent_pulse.py`, `api/jobs/unified_scheduler.py`, `api/services/agent_framework.py` (ROLE_PULSE_CADENCE). Migration 124. `proactive_review.py` DELETED. (Phases 1-6 Implemented. P5: role-based cadence + Composer pulse integration. P6: frontend surfacing across all surfaces.)

- **ADR-127**: User-Shared File Staging — `user_shared/` ephemeral staging area for user-contributed files at both TP-level (`/user_shared/`) and project-level (`/projects/{slug}/user_shared/`). Files tagged `lifecycle='ephemeral'` with 30-day TTL. PM triages: promote to `contributions/`, `memory/`, or `/knowledge/`, or let expire. Two-tier cleanup cron: `/working/` 24h TTL, `/user_shared/` 30d TTL. Preserves workspace sovereignty (FOUNDATIONS Axiom 3). Key files: `api/services/workspace.py` (`_infer_lifecycle()`), `api/jobs/unified_scheduler.py` (cleanup cron), `docs/architecture/workspace-conventions.md` (v2). Extends ADR-106, ADR-119, ADR-121, ADR-124. (Phase 1 Implemented — workspace conventions + cleanup cron. Phase 2+ in progress — PM triage, ShareFile primitive, frontend.)

- **ADR-128**: **PM portions superseded by ADR-138.** Multi-Agent Coherence Protocol — three intelligence substrates (conversation, filesystem, agent cognition) with four coherence flows. Contributor self-assessment (rolling 5 recent in `memory/self_assessment.md`), PM project assessment (overwrite in `memory/project_assessment.md`), chat directive persistence (`memory/directives.md`, `memory/decisions.md`). Cognitive files seeded at scaffold time. Contributor cognitive model: mandate → domain fitness → context currency → output confidence. Assessment extracted from output, stripped before delivery. PM reads contributor assessment trajectories; contributors read PM assessment. Corollary to FOUNDATIONS Axiom 2 (three substrates) and Axiom 3 (cognitive files as developmental mechanism). Phase 6 (Cognitive Dashboard) deferred — situation room for agent cognitive state. Key files: `api/services/agent_pipeline.py` (role prompts with mandate_context + assessment postamble), `api/services/agent_execution.py` (assessment extraction/stripping/writing), `api/services/workspace.py` (load_context reads PM assessment), `api/agents/chat_agent.py` (directive persistence prompts), `api/services/agent_creation.py` (seed self_assessment.md), `api/services/project_registry.py` (seed project_assessment.md). Extends ADR-106, ADR-120, ADR-121, ADR-124, ADR-126. (Proposed — Phase 5 docs complete.)

- **ADR-129**: **Project tier superseded by ADR-138.** Activity Scoping — Two-Tier Model. Refines Layer 2 (Activity) from flat user-scoped log to two-tier scoping: **Workspace Activity** (macro — platform syncs, Composer decisions, memory extraction, system observability) and **Project Activity** (micro — agent lifecycle, PM coordination, pulse events). Project activity surfaces via three substrates: activity_log events (filtered by `metadata.project_slug`), session_messages (meeting room conversation), and workspace_files (implicit file-change trail). No schema change — metadata enrichment only. Agent lifecycle events (`agent_scheduled`, `agent_generated`, `agent_pulsed`, `agent_approved`, `agent_rejected`, `agent_run`) gain `project_slug` in metadata. Global `/activity` page becomes supervision dashboard; project detail lives in Meeting Room timeline via `mergeTimeline()`. Extends ADR-063, ADR-124, ADR-125, ADR-126. Version-controlled domain doc: `docs/features/activity.md`. Key files: `api/services/activity_log.py` (`resolve_agent_project_slug()`, `resolve_agent_project_slug_full()`), `api/routes/projects.py` (`PROJECT_EVENT_TYPES`). (Phase 1 Implemented — agent event enrichment. Phase 2-4 proposed.)

- **ADR-130**: HTML-Native Output Substrate — Three-Registry Architecture. Three registries: **Agent Type Registry** (v2: 8 user-facing product types — briefer, monitor, researcher, drafter, analyst, writer, planner, scout — plus PM infrastructure; each with display_name, tagline, capabilities), **Capability Registry** (each capability → runtime + tool + skill docs + output type), **Runtime Registry** (where compute happens — internal, python_render, node_remotion, external APIs). Types are product offerings users "hire." Legacy roles (digest, synthesize, research, prepare, custom) mapped via `resolve_role()` + `LEGACY_ROLE_MAP` — no DB migration needed. Multi-agent coordination model: projects are teams (1 PM + 1..N contributors), lean start (1 contributor at scaffold), team grows via Composer/TP/user. HTML-native bet: agents produce markdown + assets, platform composes HTML via compose engine, export (PDF/XLSX) is derivative on-demand. Skills pipeline: SKILL.md convention preserved (Claude Code compatible, marketplace-importable); skills can be built-in (render service), compute-backed (Remotion), or imported (MCP/marketplace). `SKILL_ENABLED_ROLES` → deleted. `classify_seniority()` → deleted. `ROLE_PORTFOLIOS` → deleted. All LLM-facing prompts + code callers migrated to v2 types. Key files: `api/services/agent_framework.py` (three registries + helpers), `web/lib/agent-identity.ts` (display names, colors, taglines), `docs/architecture/output-substrate.md` (canonical), `render/compose.py` (HTML composition engine). Phase 1 implemented (registries, seniority deletion, v2 types, full caller migration). Phase 2 proposed (HTML-native compose integration as post-generation pipeline step). Phase 3 proposed (export pipeline, format-builder skill dissolution, multi-runtime).

- **ADR-131**: Gmail & Calendar Sunset — removes Gmail and Calendar integrations. Google OAuth (`google_client.py`), Gmail sync (`_sync_gmail()`), Calendar sync (`_sync_calendar()`) deleted. `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` env vars removed. Supersedes Gmail/Calendar portions of ADR-077, ADR-100, ADR-112, ADR-113, ADR-122.

- **ADR-147**: GitHub Platform Integration — adds GitHub as third content platform (Slack + Notion + GitHub). Direct API client with rate limiting + token refresh (GitHub tokens expire). Two TP tools: `platform_github_list_repos`, `platform_github_get_issues`. Sync: issues + PRs from selected repos, incremental via cursor. Tier limits: Free 3 repos, Pro unlimited. Key files: `api/integrations/core/github_client.py`, `api/workers/platform_worker.py` (`_sync_github()`), `api/services/landscape.py` (repo scoring). (Phase 1 Implemented — backend core. Phase 2: frontend + delivery.)

- **ADR-132**: **Project scaffolding superseded by ADR-138.** Work-First Onboarding & Project Scaffolding — replaces platform-first onboarding with work-structure-first model. Two-step structured onboarding: (1) "How is your work structured?" — single-focus vs. multi-scope, (2) define work scopes (each becomes a work unit → project). No LLM parsing for extraction — user provides discrete scopes directly. Platform connections enrich existing work-scoped projects rather than creating generic digests. Work types carry implicit lifecycle (persistent vs. bounded). Lightweight onboarding page (`/onboarding`) shown once after signup, completable in <60s. Fallback: users who skip get current platform-first bootstrap. Work-scoped project types added to registry (`workspace`, `bounded_deliverable`). Agent identities derived from work context (e.g., "Acme Reporter" not "Slack Digest Agent"). `/memory/WORK.md` stores structure + work units. Extends ADR-122, ADR-130. Supersedes ADR-110 (bootstrap as primary path), ADR-113 (onboarding flow). Four phases: P1 (onboarding page + data capture), P2 (work unit classification + scaffolding), P3 (platform source mapping to work units), P4 (orchestrator integration). (Proposed.)

- **ADR-133**: **Superseded by ADR-138.** PM-Coordinated Phase Dispatch — fundamental execution model change. Contributors in a project no longer pulse independently — PM owns the heartbeat and dispatches contributor runs in structured phases. Three execution modes: standalone (independent pulse), project contributor (PM-dispatched), PM (coordination pulse). Work plan evolves from free text to structured phases with dependencies. Cross-phase context injection: PM curates prior phase outputs into briefs for next phase contributors. Capability-aware decomposition: PM assigns work based on `AGENT_TYPES` capabilities (ADR-130). `agent_pulse.py` refactored: PM → Tier 3 coordination, contributor → skip (PM dispatches), standalone → Tier 1+2. New workspace conventions: `phase_state.json` (phase tracking), phase-aware contribution briefs. Partially supersedes ADR-126 (independent contributor pulse). Evolves ADR-120 (PM → phase orchestrator), ADR-121 (phase-aware steering), ADR-128 (cross-phase context as fifth coherence flow). Key files: `api/services/agent_pulse.py` (refactored routing), `api/services/agent_execution.py` (PM phase dispatch), `/projects/{slug}/memory/phase_state.json` (phase tracking), `/projects/{slug}/memory/work_plan.md` (structured phases). (Proposed.)

- **ADR-134**: **Superseded by ADR-138.** Output-First Project Surface — replaces ADR-124's 5-tab structure (Meeting Room, Participants, Context, Outputs, Settings) with a continuous 2-panel layout. Output is the hero: latest composed HTML prominently displayed. Left panel toggles between Output view (default) and Chat view (for intervention). Right panel: compact team cards grouped by phase, PM coordination card (latest decision + quality assessment), work plan checklist (phases from phase_state.json). Phase indicator in header (horizontal stepper). Settings via gear icon drawer, not a tab. Context (file browser) accessible via link. Evolves ADR-124 (chat → output-first), extends ADR-133 (phase state surfacing), ADR-130 (composed HTML rendering), ADR-128 (cognitive state in team cards). (Proposed.)

- **ADR-136**: **Superseded by ADR-138.** Project Charter Architecture — Separated Concerns. Splits single PROJECT.md into three charter files: `PROJECT.md` (objective + success criteria), `TEAM.md` (roster + capabilities from type registry), `PROCESS.md` (output spec + cadence + delivery + phases). Strict charter vs. memory separation: charter files are constitution (user/TP writes), memory files are working state (agents accumulate). PM workspace = project workspace (no separate /agents/pm-slug/). Cadence enforcement in Tier 1 prevents runaway loops. Output specification enables composition intelligence — PM reasons about what final deliverable should look like. Append-to-top versioning in charter files preserves change history. Enables deterministic execution → predictable cost (~$0.50/month per project). Supersedes single PROJECT.md model. Evolves ADR-133 (phase dispatch), ADR-134 (project surface), ADR-135 (chat coordination). (Proposed.)

- **ADR-137**: **Superseded by ADR-138.** Declarative Pipeline Execution — replaces PM-coordinated dispatch (ADR-133) with declared execution graphs in PROCESS.md. Pipeline steps have dependencies, executed mechanically by scheduler. PM simplified to pipeline-embedded steps: evaluate (quality gate, Haiku), compose (assembly, Sonnet), reflect (learning, Haiku). No PM coordination pulses. Complexity-adaptive: simple (1 agent, direct deliver), standard (3 agents, sequential), complex (3+ agents with retry loops). Inference produces pipeline spec, not just team. Frontend: pipeline visualization (horizontal step flow with state indicators). Cost: ~$0.17/cycle vs ~$0.25 with PM coordination. Supersedes ADR-133. Evolves ADR-136 (PROCESS.md), ADR-132 (inference). (Proposed.)

- **ADR-138**: Agents as Work Units — Project Layer Collapse. Workspace → Agents → Tasks hierarchy. Projects deleted entirely. PM dissolved — TP absorbs coordination. Agents are WHO (identity, domain expertise, memory). Tasks are WHAT (objective, cadence, delivery, output spec, mode). `mode` (recurring/goal/reactive) is on tasks, not agents — temporal behavior is a property of the work, not the worker. Filesystem-first: TASK.md + memory/run_log.md + outputs/. Thin tasks DB table (scheduling index only). 4 archetypes: monitor, researcher, producer, operator. Cross-agent orchestration via TP (imperative, not pipeline). Clean-slate migration (all test data wiped). **Evolves into ADR-140** for agent type definitions. Supersedes ADR-120–125, ADR-133–137. PM portions of ADR-126, ADR-128 dissolved. Key files: `api/services/task_workspace.py`, `api/routes/tasks.py`, `api/services/primitives/task.py`. (Phases 1-4 Implemented. Phase 5-6 in progress.)

- **ADR-140**: Agent Workforce Model — Pre-Scaffolded Roster (v4 domain-steward model). Three independent axes per agent: (1) Identity = AGENT.md name + domain, evolves with use; (2) Capabilities = type registry, fixed at creation; (3) Tasks = TASK.md work assignments, come and go. Three classes: **domain-steward** (owns one context domain, multi-step reasoning), **synthesizer** (cross-domain composition), and **platform-bot** (mechanical, scoped to one API). Pre-scaffolded roster at sign-up: 5 domain-stewards (Competitive Intelligence, Market Research, Business Development, Operations, Marketing & Creative) + 1 synthesizer (Executive Reporting) + 2 platform-bots (Slack Bot, Notion Bot). Each domain-steward owns one `/workspace/context/{domain}/` folder. Onboarding = context enrichment only (no agent creation); task inference assigns work to existing roster agents. Sign-up creates roster lazily on first onboarding-state check. Bots activated when platform connected. Key files: `api/services/agent_framework.py` (AGENT_TEMPLATES, DEFAULT_ROSTER), `api/routes/memory.py` (_scaffold_default_roster). (Implemented.)

- **ADR-142**: Unified Filesystem Architecture — Four roots, documents as first-class perception. `/knowledge/` dissolved (platform summaries → `/platforms/`, agent outputs stay in `/tasks/`). `/memory/` merged into `/workspace/`. `/user_shared/` dissolved into session-scoped uploads. `filesystem_documents` table dissolves — uploads extract text → `/workspace/uploads/{name}.md` (ADR-152: renamed from `documents/`). Three file-sharing contexts: shared documents (permanent, `/workspace/uploads/`), chat uploads (session TTL, inline), platform syncs (own lifecycle, `/platforms/`). TP always knows uploaded documents exist (working memory injection). Key files: `api/services/workspace.py` (KnowledgeBase → PlatformKnowledge), `api/services/working_memory.py` (document listing), `docs/architecture/workspace-conventions.md` (v4). Supersedes ADR-107 (Knowledge Filesystem), ADR-127 (User-Shared Staging). Evolves ADR-106, ADR-119. (Proposed.)

- **ADR-141**: Unified Execution Architecture — Mechanical Scheduling, LLM Generation. Three-layer separation: Layer 1 (mechanical, zero LLM) = task scheduling via SQL, platform sync, workspace cleanup, health flags; Layer 2 (generation, Sonnet) = task execution pipeline — scheduler triggers → read TASK.md + AGENT.md → gather context → generate → save → deliver; Layer 3 (orchestration, TP) = chat mode + periodic heartbeat. Dissolves `agent_pulse.py` (Tier 1/2). Replaces scheduler stub with live `execute_task()`. Key new file: `api/services/task_pipeline.py` (`execute_task()`, `parse_task_md()`, `gather_task_context()`, `build_task_execution_prompt()`). Supersedes ADR-088 (Trigger Dispatch), ADR-126 (Agent Pulse — remaining Tier 1/2). Preserves ADR-117 (feedback), ADR-118 (output gateway), ADR-130 (compose). (Phase 1-3 Implemented — task pipeline + scheduler + all 5 callers rewired. `agent_pulse.py` + `execution_strategies.py` deleted. `agent_execution.py` retained for helper functions only.)

- **ADR-144**: Inference-First Shared Context — `UpdateSharedContext` as single TP primitive for workspace identity/brand mutations. Inference (from docs, URLs, chat text, platform content) is the single method for context creation and update — no form fields, no separate onboarding page. Workfloor tabs collapse to 3 top-level sections: Tasks | Context (nested: Identity, Brand, Documents) | Platforms. Workspace state signal (`workspace_state` in working memory, ADR-156) always visible to TP — `is_onboarding` flag dissolved (was dead since ADR-140 pre-scaffolds agents). Cold start: suggestion chips in chat empty state + TP context awareness prompt (always injected, graduated judgment). Supersedes ADR-132 (onboarding page), ADR-113 (onboarding flow). Dissolves: `/onboarding` page, `/api/memory/profile` endpoint, `enrich_context()` standalone function, `is_onboarding` gate. Key files: `api/services/primitives/shared_context.py` (UpdateSharedContext), `api/services/context_inference.py` (`infer_shared_context()`), `api/services/working_memory.py` (workspace_state signal), `api/agents/tp_prompts/onboarding.py` (`CONTEXT_AWARENESS` — always-on). (Phases 1-4 Implemented.)

- **ADR-149**: Task Lifecycle Architecture — TP as Context Manager. Four commitments: (1) two registries fixed (AGENT_TYPES + TASK_TYPES), (2) task instances as living knowledge objects with filesystem-first state, (3) mode as TP management posture (recurring=auto-deliver, goal=evaluate→steer→complete, reactive=dispatch-and-done), (4) feedback + evaluation as unified pipeline. New files per task: `DELIVERABLE.md` (quality contract: output spec + expected assets + inferred user preferences, scaffolded from type registry, evolves via feedback inference), `memory/feedback.md` (user corrections + TP evaluations, distinguished by source tag), `memory/steering.md` (TP cycle-specific management notes). Terminology unification: "reflection" = agent self-awareness (renamed from "contributor assessment"), "evaluation" = TP task quality judgment, "feedback" = user corrections routed by TP. Code renames: `_extract_contributor_assessment()` → `_extract_agent_reflection()`, `self_assessment.md` → `reflections.md`. Pipeline extended: reads DELIVERABLE.md + steering.md + feedback.md. ManageTask gains `evaluate`, `steer`, `complete` actions. UpdateContext `feedback_target="deliverable"` routes to task feedback.md. Task deliverable inference (`task_deliverable_inference.py`) distills feedback → DELIVERABLE.md preferences (same pattern as context_inference.py for IDENTITY.md). Extends ADR-138, ADR-141, ADR-144, ADR-145, ADR-146. (Phase 1-5 Implemented — terminology, DELIVERABLE.md scaffold, pipeline reads DELIVERABLE.md + mode-aware output, ManageTask evaluate/steer/complete, UpdateContext feedback_target=deliverable, task deliverable inference. Phase 6 frontend deferred.)

- **ADR-151**: Shared Context Domains — Workspace as Accumulated Intelligence. **Supersedes ADR-150** (task-gated knowledge was wrong). **Absorbed into ADR-152** (unified directory registry). Three registries: Context Domain Registry (NEW — `api/services/domain_registry.py`, `CONTEXT_DOMAINS`), Agent Registry (unchanged), Task Type Registry (extended). Accumulated context lives at `/workspace/context/` (workspace-scoped, shared across all tasks). Six initial domains: `competitors`, `market`, `relationships`, `projects`, `content`, `signals`. Each domain has entity structure (per-entity subfolders with templated files), synthesis files (`_`-prefixed cross-entity summaries), and co-located assets. Tasks declare `context_reads` + `context_writes` (which domains they consume/produce) — replaces `knowledge_schema` from ADR-150. Process steps: `update-context` (agent reads domain + researches + writes back) → `derive-output` (compose deliverable from accumulated context). Tasks are thin work orders — no task-level knowledge, accumulated context lives at workspace scope. **Context outlives tasks.** Agent identity specializes through accumulated domain experience (not type change). Domain scaffolding: TP creates domain folders when tasks first need them. Entity creation: agents create entity folders during execution using domain registry templates. (Phase 1-4 Implemented — domain registry, context_reads/writes on task types, domain scaffold at task creation, pipeline reads /workspace/context/, agent write-back via WriteWorkspace scope=context, diff-aware output derivation. Phase 5 TP domain awareness deferred.)

- **ADR-152**: Unified Directory Registry — consolidates workspace directory governance into single registry. Renames Context Domain Registry → Directory Registry (`api/services/directory_registry.py`, `WORKSPACE_DIRECTORIES`). `documents/` renamed to `uploads/` (clarity: user-contributed vs system-produced). `/workspace/outputs/` added with three output categories: `reports`, `briefs`, `content_output`. Task types declare `output_category` — promoted outputs land in `/workspace/outputs/{category}/`. Absorbs ADR-151 domain registry into unified directory structure. Extends ADR-145, ADR-151. Key files: `api/services/directory_registry.py` (WORKSPACE_DIRECTORIES), `docs/architecture/registry-matrix.md` (output categories in task type catalog), `docs/architecture/workspace-conventions.md` (v8). (Phase 1 Implemented — registry rename, uploads/ rename, output categories.)

- **ADR-153**: Platform Content Sunset — Task-First External Data Flow. **Supersedes ADR-072** (unified content layer), **ADR-077** (platform sync overhaul), **ADR-085** (RefreshPlatformContent). Full deletion of `platform_content` as a context source. Platform connections kept for OAuth/auth only. Platform data flows exclusively through tracking tasks into `/workspace/context/` domains. Deleted: `RefreshPlatformContent` primitive, `Search(scope="platform_content")` scope, `_fallback_platform_content_search()`, `mark_content_retained()` calls, platform sync auto-trigger on OAuth, TP prompt platform_content references. `/platforms/` filesystem directory deprecated. Manual sync endpoint deprecated. `sync_stale_sources()` deprecated. Context domains are THE sole data source. (Phase 1-3 Implemented — primitives, prompts, pipeline cleanup. Phase 4-5 in progress — docs, DB table.)

- **ADR-156**: Composer Sunset — Single Intelligence Layer. **Supersedes ADR-111** (Agent Composer), **ADR-114** (Composer Substrate-Aware Assessment). Composer deleted entirely. TP is the single intelligence layer for all judgment — no background LLM making workforce composition decisions. Three clean layers: Scheduler (mechanical, zero LLM) → Task Pipeline (generation, Sonnet) → TP (orchestration, single intelligence). Deterministic lifecycle rules (underperformer pausing) moved to scheduler. Work budget + agent health signals moved to `working_memory.py` (pure SQL, surfaced to TP in conversation). Key files deleted: `api/services/composer.py`, `api/test_adr111_composer.py`. Key files modified: `api/jobs/unified_scheduler.py` (lifecycle hygiene), `api/services/working_memory.py` (health signals), `api/services/agent_execution.py` (event trigger removed). (Phase 1 Implemented.)

- **ADR-158**: External Context Access — Platform Bot Ownership Model. One bot, one platform, one directory. Platform bots (Slack Bot, Notion Bot, GitHub Bot) own temporal context directories (`/workspace/context/slack/`, `/workspace/context/notion/`, `/workspace/context/github/`). Per-source subfolders (channel/page/repo) with `_tracker.md` for freshness. `temporal: true` flag in directory registry distinguishes from canonical domains. Task type renames: `monitor-slack` → `slack-digest`, `monitor-notion` → `notion-digest`. Platform-specific step instructions. TP working memory separates canonical domains from "Platform awareness (temporal, not canonical)" section. Cross-pollination into canonical domains explicitly out of scope. GitHub implementation deferred (directory exists, no task type yet). Key files: `api/services/directory_registry.py` (v3.0: 3 platform directories), `api/services/agent_framework.py` (bot domain assignment), `api/services/task_types.py` (v5.0: renamed task types + platform-specific instructions), `api/services/working_memory.py` (temporal flag + split formatting). (Phase 1-3 Implemented — P1: registry + ownership + task types + TP awareness. P2: per-task source selection — `**Sources:**` in TASK.md, auto-populated from platform_connections at task creation, ManageTask update, injected into execution context. P3: write-back task types — `slack-respond` (reactive), `notion-update` (reactive), distinct from digest tasks. Phase 4: GitHub implementation.)

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

---

## Prompt Change Protocol

When modifying any prompt, tool definition, or orchestration heuristic in these files:
- `api/agents/thinking_partner.py` (TP system prompt)
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
- Expected behavior: How this affects TP/tool behavior
```

---

## Key Architecture References

### ADR-064: Unified Memory Service (updated by ADR-156)

**Memory is in-session** — TP writes facts proactively via `UpdateContext(target="memory")` during conversation. Follows the Claude Code model: memory happens in the moment of learning, not as a batch job.

- ADR-156: Nightly cron extraction REMOVED. TP writes facts in-session.
- Session summaries: generated inline at session close (chat.py), not by nightly cron.
- Session continuity: TP writes shift notes to AWARENESS.md.
- User can still edit memories directly via Context page.
- Working memory injected into TP prompt is unchanged.

**Key files**:
- `api/services/memory.py` — retained for bulk import only (nightly cron removed)
- `api/services/working_memory.py` — formats memory for prompt injection
- `api/agents/tp_prompts/onboarding.py` — memory-write guidance for TP
- `docs/features/memory.md` — user-facing docs

### ADR-059: Simplified Context Model (Current Schema)

**Tables** (use these names, not legacy):
- `platform_connections` (not `user_integrations`)
- `platform_content` — **DROPPED (ADR-153)**. Was unified content layer with retention (ADR-072). Platform data now flows through tasks into workspace context domains.
- `filesystem_documents` / `filesystem_chunks` — uploaded documents only
- `user_memory` — single Memory store (replaces knowledge_profile, knowledge_styles, knowledge_domains, knowledge_entries)
- `agents` — persistent workforce roster (ADR-140, v4 domain-steward model). Identity-only: `role` (type key: competitive_intelligence, market_research, business_development, operations, marketing_creative, executive_reporting, slack_bot, notion_bot), `title`, `scope`, `status`, `type_config`, `agent_instructions`, `agent_memory`. No schedule, no destination, no mode — those live on tasks. Pre-scaffolded at sign-up (8 agents per workspace: 5 domain-stewards + 1 synthesizer + 2 platform-bots).
- `tasks` — work units (ADR-138). Thin scheduling index: `slug`, `mode` (recurring/goal/reactive), `schedule`, `next_run_at`, `status`. Mode is temporal behavior of the work, not identity of the worker. Charter in workspace `/tasks/{slug}/TASK.md`. Agent assignment via TASK.md `## Process` section (filesystem, not FK).
- `agent_runs` — execution audit trail per agent (was `deliverable_versions`, renamed ADR-103). ADR-118 D.3: dual-write (content still written for frontend compat), but delivery reads from workspace_files output folders. Will become pure audit trail when frontend migrates.
- `agent_type` — column on `agents` table, **DEPRECATED** by ADR-109 — being replaced by `scope` + `role`
- `agent_instructions` — column on `agents` table, **DEPRECATED** by ADR-106 Phase 2 — migrated to workspace `AGENT.md`. No longer written for new agents. DB column kept only for lazy migration of pre-workspace agents via `ensure_seeded()`. Workspace AGENT.md is sole authority.
- `agent_memory` — column on `agents` table, **DEPRECATED** by ADR-106 Phase 2 — migrated to workspace `memory/*.md`. No longer written for new agents. Workspace memory files are sole authority.
- `workspace_files` — virtual filesystem for agent workspaces (ADR-106); path-based access, full-text + vector search; `content_url` column for rendered binary files (ADR-118). ADR-118 Phase D: becomes the single output substrate for all agent outputs (text + binary), replacing agent_runs as the delivery source. ADR-119: adds `version` + `lifecycle` columns; folder conventions (output folders with `manifest.json`, project folders, ephemeral `/working/`) replace relational grouping tables
- `workspace_file_versions` — NOT a table; version history uses `/history/` subfolder convention (ADR-119 Resolved Decision #3). On overwrite of high-value files (thesis.md, memory/*.md, AGENT.md), previous version copied to `/agents/{slug}/history/{filename}-v{N}.md`. Implemented in Phase 3.
- `mcp_oauth_clients` / `mcp_oauth_codes` / `mcp_oauth_access_tokens` / `mcp_oauth_refresh_tokens` — MCP OAuth 2.1 storage (ADR-075, service key only)
- `render_usage` — per-user render call tracking (ADR-118 D.2); `get_monthly_render_count()` RPC for tier limit enforcement

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
| TP Agent (Orchestrator) | `api/agents/thinking_partner.py` |
| Chat Agent (Meeting Room) | `api/agents/chat_agent.py` (ADR-124: agent_chat mode) |
| Tool Primitives | `api/services/primitives/*.py` |
| Memory Service | `api/services/memory.py` |
| Working Memory | `api/services/working_memory.py` |
| Chat/Streaming | `api/services/anthropic.py` |
| OAuth Flow | `api/integrations/core/oauth.py` |
| Agent Workspace | `api/services/workspace.py` (ADR-106) |
| Workspace Primitives | `api/services/primitives/workspace.py` (ADR-106) |
| Agent Framework (canonical) | `docs/architecture/agent-framework.md` (ADR-109) |
| Directory Registry | `api/services/directory_registry.py` (ADR-152: WORKSPACE_DIRECTORIES — context domains, uploads, output categories) |
| Agent Framework (code) | `api/services/agent_framework.py` (ADR-140: workforce roster, AGENT_TEMPLATES, DEFAULT_ROSTER, capabilities, runtimes) |
| Agent Creation (shared) | `api/services/agent_creation.py` (ADR-111 Phase 1) |
| TP Composer / Heartbeat | DELETED (ADR-156 — Composer sunset, single intelligence layer) |
| Agent Pulse Engine | DELETED (ADR-141: dissolved into scheduler SQL + task pipeline) |
| Task Execution Pipeline | `api/services/task_pipeline.py` (ADR-141: `execute_task()` — mechanical pipeline) |
| Agent Execution (legacy) | `api/services/agent_execution.py` (retained for manual/MCP/event callers) |
| Delivery Service | `api/services/delivery.py` (ADR-118 D.3: `deliver_from_output_folder()`) |
| Feedback Distillation | `api/services/feedback_distillation.py` (ADR-117: edits → style.md) |
| Feedback Engine | `api/services/feedback_engine.py` (edit metrics computation) |
| Agent Pipeline | `api/services/agent_pipeline.py` |
| Agent Routes | `api/routes/agents.py` |
| Task Workspace | `api/services/task_workspace.py` (ADR-138: task filesystem operations) |
| Task Primitives | `api/services/primitives/task.py` (ADR-138: CreateTask) |
| Task Management | `api/services/primitives/manage_task.py` (ADR-146: ManageTask — trigger/update/pause/resume + ADR-149: evaluate/steer/complete) |
| Task Deliverable Inference | `api/services/task_deliverable_inference.py` (ADR-149: feedback → DELIVERABLE.md, planned) |
| Task Routes | `api/routes/tasks.py` (ADR-138: task CRUD) |
| Dashboard Summary | DELETED (2026-03-22) — collapsed into Orchestrator |
| Platform Sync Worker | DELETED (ADR-153 — platform_content sunset) |
| Platform Sync Scheduler | DELETED (ADR-153 — platform_content sunset) |
| Platform API Clients | `api/integrations/core/{slack,notion,github}_client.py` |
| Landscape Discovery | `api/services/landscape.py` |
| Tier Limits | `api/services/platform_limits.py` |
| Agent Scheduler | `api/jobs/unified_scheduler.py` (queries `tasks` table for scheduling) |
| MCP Server | `api/mcp_server/` (ADR-075, ADR-116 Phase 4: 9 tools) |
| Output Gateway (yarnnn-render) | `render/` (ADR-118: skill library = capability filesystem) |
| Output Gateway Skills | `render/skills/` (8 skills: pdf, pptx, xlsx, chart, mermaid, html, data, image; each folder has SKILL.md + scripts/). ADR-130 Phase 3: chart/mermaid/image survive as asset producers; pptx/html/data dissolve into compose engine; pdf/xlsx retained as export steps only. |
| RuntimeDispatch Primitive | `api/services/primitives/runtime_dispatch.py` (ADR-118). Retained — type-scoping via `has_asset_capabilities()`. |
| Capability Substrate | `docs/architecture/output-substrate.md` (ADR-130: three-registry architecture + output pipeline) |
| Capability Migration Plan | `docs/design/SKILLS-REFRAME.md` (ADR-130: three-registry migration from current system) |
| Frontend API Client | `web/lib/api/client.ts` |
| Sync Error Categorization | `web/lib/sync-errors.ts` (ADR-086) |
| Onboarding UI | `web/components/onboarding/` |
| Orchestrator (Home) | `web/app/(authenticated)/orchestrator/page.tsx` |
| Route Constants | `web/lib/routes.ts` (HOME_ROUTE = "/orchestrator", PROJECTS_ROUTE) |

---

## Common Pitfalls

1. **Schema mismatch**: Code referencing old table/column names — use `agents` not `deliverables`, `agent_runs` not `deliverable_versions`, `agent_id` not `deliverable_id`
2. **Tool loop exhaustion**: TP hits `max_tool_rounds=5` without text response if tools return empty
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
