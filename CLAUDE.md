# CLAUDE.md - Development Guidelines for YARNNN

This file provides context and guidelines for Claude Code when working on this codebase.

## Project Overview

YARNNN is an **autonomous agent platform for recurring knowledge work**. Persistent AI agents connect to work platforms (Slack, Gmail, Notion, Calendar), run on schedule, learn from feedback, and produce outputs that improve with tenure.

**Architecture**: Next.js frontend → FastAPI backend → Supabase (Postgres) → Claude API

**Key terminology** (ADR-103, ADR-126):
- **Agent** (was: Deliverable) — a persistent, autonomous entity with identity, instructions, memory, tools, pulse, and output history
- **Agent Pulse** (ADR-126) — autonomous sense→decide cycle; upstream of execution. Every agent has one. Decisions: generate | observe | wait | escalate
- **Agent Run** (was: Deliverable Version) — a single execution of an agent, producing draft/final content. Only happens when pulse decides "generate"
- **Pulse Cadence** (ADR-126) — how often an agent senses its domain. Evolves with seniority (schedule→every cycle)
- **Delivery Cadence** — when the user receives output. Project-level, PM-coordinated. Decoupled from pulse cadence
- **Orchestrator / TP** — the user-facing conversational agent with full capabilities
- **Agent Instructions** (was: deliverable_instructions) — user-authored behavioral directives
- **Agent Memory** (was: deliverable_memory) — system-accumulated state (observations, goals)
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
- **ADR-110**: Onboarding Bootstrap — deterministic, zero-LLM agent creation on platform connection. Post-sync, auto-creates matching digest agent (Slack→Recap, Gmail→Digest, Notion→Summary) with `origin=system_bootstrap`. Executes first run immediately. Becomes Bootstrap bounded context within Composer (ADR-111). (Implemented.)
- **ADR-111**: Agent Composer — TP's compositional capability (not a separate service). Three bounded contexts: **Bootstrap** (deterministic fast-path), **Heartbeat** (periodic TP self-assessment of agent workforce), **Composer** (assessment + creation/adjustment/dissolution). Unifies Write/CreateAgent into single `CreateAgent` primitive. Autonomy-first: bias toward action, feedback as correction. Proactive/coordinator modes reframed as TP supervisory capabilities. Platform content as onramp (dependency decreases over time). Lifecycle progression: per-agent maturity signals (run count, approval rate, edit distance trend), auto-pause underperformers, auto-create synthesis from mature digests, cross-agent pattern detection. (Implemented — all 5 phases.) **Phases 3-5 partially superseded by ADR-126** — Composer heartbeat/assessment thins to portfolio-only; per-agent assessment replaced by bottom-up pulse outcomes
- **ADR-112**: Sync Efficiency & Concurrency Control — three layers: (1) atomic sync lock on `platform_connections` replacing `SCHEDULE_WINDOW_MINUTES` timing hack, (2) platform-level heartbeat fast-path (Gmail historyId, Calendar syncToken, Slack latest, Notion search) to skip source iteration when nothing changed, (3) per-source skip hints (deferred). Coordinates all three sync paths (scheduled, manual, TP RefreshPlatformContent). (Implemented.)
- **ADR-113**: Auto Source Selection — eliminates manual source selection as prerequisite for platform connections. OAuth callback auto-discovers landscape, applies `compute_smart_defaults()`, kicks off first sync immediately. Post-OAuth redirect changed from `/orchestrator` to `/dashboard`. Context pages become optional refinement, not first-time entry point. Dashboard platform cards trigger OAuth directly. (Implemented.)
- **ADR-114**: Composer Substrate-Aware Assessment — evolves Composer from platform-metadata-centric to recursive-substrate-aware. Four phases: (1) knowledge corpus signals in heartbeat_data_query, (2) substrate-aware heuristics in should_composer_act, (3) knowledge summary in LLM prompt, (4) Composer prompt v2.0. Establishes Composer prompt versioning policy (same rigor as Orchestrator). (Phases 1-3 Implemented. Phase 4 absorbed into ADR-120 Phase 5 — Composer Prompt v2.0 shipped.)
- **ADR-116**: Agent Identity & Inter-Agent Knowledge Infrastructure — makes agents discoverable and composable. Five phases: (1) knowledge metadata search (QueryKnowledge filters by agent_id/role/scope), (2) agent discovery primitive (DiscoverAgents), (3) cross-agent workspace reading (ReadAgentContext — read-only), (4) agent card auto-generation + MCP exposure (get_agent_card, search_knowledge, discover_agents tools), (5) consumption tracking + Composer agent dependency graph (orphaned producers, missing producers, stale dependencies). Agent-native identity thesis: workspace IS identity, agents are first-class participants not human proxies. (Implemented.)

- **ADR-117**: Agent Feedback Substrate & Developmental Model — unifies three disconnected feedback rails (user edits, Composer lifecycle, agent self-observation) into workspace as single substrate. Three phases: (1) feedback distillation to `memory/preferences.md` + extend workspace context to all agents (not just analyst), (2) agent self-reflection (post-generation observations), (3) duties & role portfolios (multi-duty within one agent identity, earned through feedback-gated seniority progression). Formalizes FOUNDATIONS.md Axiom 3. Key files: `feedback_distillation.py` (distill edits → preferences.md), `feedback_engine.py` (edit metrics), `agent_framework.py` (ROLE_PORTFOLIOS, SKILL_ENABLED_ROLES, classify_seniority), all strategies call `load_context()` for workspace feedback. Dual injection: preferences in system prompt (high salience) + gathered context. Composer coaching via `supervisor-notes.md`. Seniority levels: new/associate/senior (renamed from nascent/developing/mature). Terminology: "duties" = agent responsibilities (expand with seniority), "objective" = project north star (ADR-123, was "intent"). Composer prompt v2.1: `promote_duty` action validates against ROLE_PORTFOLIOS. 5 project activity events for frontend surfacing. (Phases 1-3 Implemented.)

- **ADR-118**: Skills as Capability Layer — "Claude Code online" model. Two-filesystem architecture: capability filesystem (skills on output gateway Docker service, `render/skills/{name}/SKILL.md` + scripts, platform-wide) and content filesystem (workspace_files + S3, user-scoped, accumulating). Adopts Claude Code naming conventions directly: skills (not handlers/capabilities), SKILL.md (not capability guides), skill folders (same structure as Claude Code). Two skill types: local (tools in Docker image, fixed cost) and delegated (external API/MCP, per-call cost). Skills are explicit/curated, earned via feedback-gated progression (Axiom 3). Phases A+B+C+D.1-D.4 Implemented. D.1: skills alignment/rename (`skill`→`role` column). D.2: render hardening (auth, rate limits). D.3: unified output substrate (output folders as delivery source, `deliver_from_output_folder()`, manifest-based email attachments). D.4: skill auto-discovery + 8-skill library. Phase D.5 (assets layer) deferred — implement when user demand emerges. Full analysis: `docs/analysis/skills-as-capability-layer-2026-03-17.md`.

- **ADR-119**: Workspace Filesystem Architecture — evolves `workspace_files` from flat key-value store to proper folder-based filesystem. Folders are boundaries, folders are context. Key conventions: output folders (`/agents/{slug}/outputs/{date}/`) replace bundle tables — co-located files + `manifest.json` = atomic output. Project folders (`/projects/{slug}/`) with scoped contribution subfolders = cross-agent collaboration. `/working/` = ephemeral scratch. Two schema additions: `version` + `lifecycle` columns on `workspace_files`. Manifest files carry metadata (sources, delivery status, file roles) instead of relational tables. Thesis: folders are boundaries and boundaries are all you need for coordination — same principle as Cowork's folder selection applied to persistent agent workspaces. Makes ADR-118 Phase D structurally sound. Extends ADR-106, interacts with ADR-116 (cross-agent reading), ADR-117 (feedback via manifests). (Phases 1-4 Implemented. Phase 1: output folders + lifecycle + manifest.json. Phase 2: project folders — ProjectWorkspace, CreateProject/ReadProject primitives, /api/projects CRUD, context injection for contributing agents. Phase 3: version history — `/history/{filename}/v{N}.md` convention, capped at 5 versions, `_archive_to_history()` + `list_history()` on AgentWorkspace and KnowledgeBase. Phase 4a: frontend — `/projects` list page, `/projects/{slug}` detail page, dashboard projects section. Phase 4b: AgentOutputsPanel — agent output history tab.)

- **ADR-120**: Project Execution & Work Budget — makes multi-agent projects alive. PM (Project Manager) is a domain-cognitive agent whose domain is project coordination — NOT a third layer of intelligence. Composer creates projects + PM agents; PM handles execution (contribution freshness, assembly triggering, budget enforcement, escalation to TP). Project heartbeat recurses the cheap-first pattern at project scope. Work budget: autonomous work units (agent runs, assemblies, renders) bounded per user per billing period (Free: 60/mo, Pro: 1000/mo). Intent decomposition: PM translates flat user intent into executable, bounded work plans. Project-level intentions (recurring/goal/reactive) with per-intention trigger, format, delivery, budget. Five phases: (1) PM agent + project heartbeat, (2) assembly execution, (3) work budget governor, (4) intent decomposition + project intentions, (5) Composer v2.0. Absorbs ADR-114 P4. Pricing model (credits vs. subscription) deferred. Implements FOUNDATIONS.md v3. (Phases 1-5 Implemented — P1: `pm` role, PM primitives, project heartbeat. P2: PM decision interpreter, assembly composition + delivery. P3: `work_units` table (migration 117), `check_work_budget()`/`record_work_units()` in platform_limits, scheduler budget gate, RuntimeDispatch budget check, Free 60/Pro 1000 units/month. P4: multi-intention support (superseded by ADR-123 — intentions consolidated into PM's `memory/work_plan.md`), PM prompt v2 with budget_status, `update_work_plan` PM action writes `memory/work_plan.md`, `UpdateWorkPlan` primitive (headless-only, renamed from UpdateProjectIntent by ADR-123), graceful degradation (budget-exhausted → escalate override). P5: Composer prompt v2.0 — `create_project` action, 8-skill library in prompt, budget awareness, `_build_composer_prompt()` extended with projects/budget/skills sections, `_execute_create_project()` resolves slugs + calls handle_create_project(), composition opportunity heuristic in `should_composer_act()`.)

- **ADR-121**: PM as Project Intelligence Director — evolves PM from logistics coordinator (freshness → assemble) to intelligence director (quality assessment + directive steering + investigation). New actions: `steer_contributor` (write contribution briefs to guide contributors), `request_investigation` (request research on gaps), `assess_quality` (intent-contribution alignment scoring before assembly). Contribution briefs (`/contributions/{slug}/brief.md`) are the steering mechanism — PM writes focus areas, contributors read during context gathering. Mechanics (code, deterministic) and Intelligence (prompts, qualitative) versioned independently. PM prompt versioning: v1.0 (logistics) → v1.1 (intentions) → v1.2 (JSON enforcement) → v2.0 (intelligence director). Four phases: (1) structural foundation + prompt v2.0, (2) quality assessment + assembly gating, (3) investigation + cross-cycle learning, (4) PM developmental trajectory (nascent → senior). Extends ADR-120, implements FOUNDATIONS.md Axiom 1 (PM developmental trajectory) + Axiom 3 (agents develop inward). (Phase 1-2 Implemented — P1: PM prompt v3.0, briefs, quality assessment, steering, contribution content in PM context, assembly prompt v2.0. P2: `_write_contribution_to_projects()` closes critical gap — agent output auto-written to project contributions folder, assembly gating log, work plan focus_areas. Phase 3-4 proposed. Steer path validated end-to-end in production: PM assess→steer→brief→contributor re-run→output updated.)

- **ADR-122**: Project Type Registry — Unified Scaffolding Layer. Single curated registry (`api/services/project_registry.py`) of project type definitions replaces scattered creation paths. All project creation flows (bootstrap, Composer, TP, API) go through `scaffold_project()`. Platform types (slack_digest, gmail_digest, notion_digest) are 1:1 with platform (uniqueness enforced). `type_key` stored in PROJECT.md as immutable identity. Bootstrap rewritten: OAuth → `scaffold_project(type_key)` → project with members + PM (not standalone agent). Composer gap-filling and lifecycle expansion consume same registry. **PM for all projects** — no exceptions, including platform digests. PM agents are project infrastructure, excluded from tier agent limits (`get_active_agent_count` filters `role='pm'`). **Agents produce, projects deliver** — delivery configuration on PROJECT.md, no direct agent delivery (`destination=None`). See `docs/design/PROJECT-DELIVERY-MODEL.md`. Supersedes ADR-110 bootstrap path. Deletes: `BOOTSTRAP_TEMPLATES`, `PLATFORM_DIGEST_TITLES`, `_create_digest_for_platform()`, standalone agent as default creation path. Five phases: (1) registry + scaffold function, (2) bootstrap migration, (3) Composer migration, (4) existing agent migration (soft — new agents always project-scoped, legacy tolerated), (5) dashboard redesign. (Phases 1-3 Implemented. Phase 4: soft migration (new creation paths always project-scoped). Phase 5: project-native dashboard shipped (commit 065c0e5).)

- **ADR-123**: Project Objective & Ownership Model — resolves intent/intentions naming collision and dual operational substrate. Renames `intent` → `objective` (4-field dict: deliverable, audience, format, purpose = project north star). Objective is mutable by User/Composer/TP, NOT by PM. Deletes `## Intentions` from PROJECT.md — operational planning consolidated into PM's `memory/work_plan.md` (singular substrate). `UpdateProjectIntent` primitive → `UpdateWorkPlan` (writes to PM memory, not PROJECT.md). PROJECT.md becomes the charter (objective + contributors + assembly_spec + delivery). PM reads charter as reference, manages its own operational plan. Legacy migration: `## Intent` accepted on read, auto-migrated; `## Intentions` parsed as `legacy_intentions`, auto-seeded to work_plan on first PM run. PM prompt v4.0 removes `{intentions}` field. Assembly prompt v3.0 uses `{objective}`. Extends ADR-120 (project execution), ADR-121 (PM intelligence), ADR-122 (project type registry). (Phases 1-4 Implemented. P1-2: terminology rename + intentions consolidation. P3: frontend — editable objective in project header, PM quality assessment + briefs in Contributors tab, PM quality/steer events in Timeline tab, `projects.update()` API client method, `PMIntelligence` type. P4: documentation updates across FOUNDATIONS.md, ADR-120, ADR-122, CLAUDE.md.)

- **ADR-124**: Project Meeting Room — Unified Project Surface. Redesigns `projects/[slug]` as a "meeting room" group chat where agents are visible participants, not abstract data. Five-tab architecture: Meeting Room (chat with attributed messages + activity event cards), Members (contributors + PM intelligence), Context (workspace file browser), Outputs (assembly history), Settings (objective, schedule, delivery). Key architectural insight: **conversation as project context** (Axiom 2 extension) — the meeting room transcript becomes a fourth perception layer alongside external (platform_content), internal (workspace_files), and reflexive (user feedback). Key innovation: users can talk to any agent (`@agent-slug` mentions), not just TP. PM is default interlocutor; TP is implicit infrastructure. New `ChatAgent` class enables agents to participate in conversations with domain-scoped primitives (`agent_chat` mode — third mode alongside `chat` and `headless`). Message attribution via `session_messages.metadata` (`author_agent_id`, `author_agent_slug`, `author_role`). Five phases: (1) ChatAgent class + `agent_chat` mode + routing, (2) Meeting Room frontend + @-mentions + participant panel, (3) agent chat prompts (PM + contributor role-specific), (4) Context tab (workspace browser), (5) Settings tab consolidation. Evolves ADR-119 P4b, extends ADR-080 (two modes → three), integrates ADR-120 (PM primitives in agent_chat), absorbs ADR-123 P3 (PM intelligence panels → inline stream cards). (Phases 1-5 Implemented.)

- **ADR-125**: Project-Native Session Architecture — two session scopes (Global TP + Project), no standalone agent sessions. Agent requests resolve to their project's session via `resolve_agent_project()`. Thread model: `thread_agent_id` on `session_messages` (NULL = group/meeting room, set = 1:1 agent thread). Project sessions rotate on 24h inactivity (vs 4h for global TP). Author-aware compaction summaries for project sessions attribute decisions to specific agent participants. `chat_sessions.agent_id` DEPRECATED — legacy fallback for agents not yet in projects. Supersedes ADR-087 (agent-scoped sessions). Extends ADR-122 (project-first), ADR-124 (meeting room). (Phases 1-5 Implemented. Migration 123.)

- **ADR-126**: Agent Pulse — Autonomous Awareness Engine. Every agent gets a **pulse** — an autonomous sense→decide cycle upstream of execution. Three-tier funnel: **Tier 1** (deterministic: fresh content? budget? recent run? — zero LLM cost), **Tier 2** (Haiku self-assessment for associate+ agents), **Tier 3** (PM coordination pulse). Pulse decision taxonomy: `generate | observe | wait | escalate`. `agents.next_run_at` → `agents.next_pulse_at`. Scheduler becomes **pulse dispatcher**. **Proactive mode dissolved** — self-assessment generalizes to ALL agents via Tier 2. **Coordinator mode dissolved** — PM Tier 3 pulse handles project coordination. Composer thins to portfolio-only. Role-based pulse cadence: monitor=15min, pm=30min, digest/prepare=12h, others=schedule (in `agent_framework.py`). Activity events: `agent_pulsed`, `pm_pulsed`. Partially supersedes ADR-088 (trigger dispatch), ADR-092 (proactive/coordinator modes), ADR-111 Phases 3-5. Key files: `api/services/agent_pulse.py`, `api/jobs/unified_scheduler.py`, `api/services/agent_framework.py` (ROLE_PULSE_CADENCE). Migration 124. `proactive_review.py` DELETED. (Phases 1-6 Implemented. P5: role-based cadence + Composer pulse integration. P6: frontend surfacing across all surfaces.)

- **ADR-127**: User-Shared File Staging — `user_shared/` ephemeral staging area for user-contributed files at both TP-level (`/user_shared/`) and project-level (`/projects/{slug}/user_shared/`). Files tagged `lifecycle='ephemeral'` with 30-day TTL. PM triages: promote to `contributions/`, `memory/`, or `/knowledge/`, or let expire. Two-tier cleanup cron: `/working/` 24h TTL, `/user_shared/` 30d TTL. Preserves workspace sovereignty (FOUNDATIONS Axiom 3). Key files: `api/services/workspace.py` (`_infer_lifecycle()`), `api/jobs/unified_scheduler.py` (cleanup cron), `docs/architecture/workspace-conventions.md` (v2). Extends ADR-106, ADR-119, ADR-121, ADR-124. (Phase 1 Implemented — workspace conventions + cleanup cron. Phase 2+ in progress — PM triage, ShareFile primitive, frontend.)

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

YARNNN runs on **5 Render services** (ADR-083: worker + Redis removed; ADR-118: output gateway added). When changing environment variables, secrets, or architectural patterns, check ALL services:

| Service | Type | Render ID |
|---------|------|-----------|
| yarnnn-api | Web Service | `srv-d5sqotcr85hc73dpkqdg` |
| yarnnn-unified-scheduler | Cron Job | `crn-d604uqili9vc73ankvag` |
| yarnnn-platform-sync | Cron Job | `crn-d6gdvi94tr6s73b6btm0` |
| yarnnn-mcp-server | Web Service | `srv-d6f4vg1drdic739nli4g` |
| yarnnn-render | Web Service (Docker) | `srv-d6sirjffte5s73f90pfg` |

All execution is inline — no background worker, no Redis. Platform sync runs in crons; on-demand sync uses FastAPI BackgroundTasks. Output gateway (yarnnn-render) is independent (Docker, pandoc + python-pptx + openpyxl + matplotlib + pillow). See ADR-118 for the "Claude Code online" model: two-filesystem architecture — capability filesystem (skills in `render/skills/`, platform-wide) + content filesystem (workspace_files + S3, user-scoped). Skills follow Claude Code SKILL.md conventions.

**Critical shared env vars** (must be on API + Unified Scheduler + Platform Sync):
- `INTEGRATION_ENCRYPTION_KEY` — Fernet key for OAuth token decryption. Schedulers **cannot sync** without it.
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — needed by Schedulers for token refresh
- `NOTION_CLIENT_ID` / `NOTION_CLIENT_SECRET` — needed by Schedulers for Notion API

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

**Common mistake**: Adding an env var to the API service but forgetting Schedulers. The API handles OAuth and stores tokens; Schedulers decrypt and use them for sync.

**Impact triggers** — if you change any of these, check the affected services:
| If you change... | Also check... |
|-----------------|--------------|
| Env vars (any) | All 5 services — use Render MCP `update_environment_variables` |
| OAuth flow / token handling | Unified Scheduler + Platform Sync (they decrypt & use tokens) |
| Supabase schema (RPC, tables, RLS) | Unified Scheduler + Platform Sync + MCP Server (all use service key) |
| Agent execution / pipeline logic | Unified Scheduler (triggers agent runs via cron) |
| Platform sync logic | Platform Sync cron (runs `platform_worker.py`) |
| MCP tool definitions / auth | MCP Server (separate service, separate deploy) |
| Output gateway / artifact rendering | yarnnn-render (independent Docker service, ADR-118) |

**Note**: All platforms (Slack, Notion, Gmail, Calendar) use Direct API clients — no gateway service needed (ADR-076).

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
- `api/services/composer.py` (Composer system prompt, heuristics, assessment data model — ADR-114)

You MUST:
1. Update `api/prompts/CHANGELOG.md` with the change
2. Note the expected behavior change
3. If significant, increment the version comment at the top of the prompt section
4. For Composer changes: every heuristic/prompt change dictates autonomous orchestration — document behavioral delta carefully

### Changelog Format

```markdown
## [YYYY.MM.DD.N] - Description

### Changed
- file.py: What changed and why
- Expected behavior: How this affects TP/tool behavior
```

---

## Key Architecture References

### ADR-064: Unified Memory Service

**Memory is implicit** — TP no longer has explicit memory tools (`create_memory`, `update_memory`, etc.)

- Memory extraction happens via nightly cron (midnight UTC) via `api/services/memory.py` — NOT at real-time session end
- User can still edit memories directly via Context page
- Working memory injected into TP prompt is unchanged

**Key files**:
- `api/services/memory.py` — extraction service
- `api/services/working_memory.py` — formats memory for prompt injection
- `docs/features/memory.md` — user-facing docs

### ADR-059: Simplified Context Model (Current Schema)

**Tables** (use these names, not legacy):
- `platform_connections` (not `user_integrations`)
- `platform_content` — unified content layer with retention (ADR-072); includes `platform="yarnnn"` for agent outputs (ADR-102)
- `filesystem_documents` / `filesystem_chunks` — uploaded documents only
- `user_memory` — single Memory store (replaces knowledge_profile, knowledge_styles, knowledge_domains, knowledge_entries)
- `agents` — persistent autonomous agents (was `deliverables`, renamed ADR-103). Key columns: `scope` + `role` (ADR-109, replacing `agent_type`; was `skill`, renamed by ADR-118 to eliminate naming overload), `mode` (trigger), `duties` JSONB (ADR-117 Phase 3: multi-duty portfolio, null = single-duty)
- `agent_runs` — execution audit trail per agent (was `deliverable_versions`, renamed ADR-103). ADR-118 D.3: dual-write (content still written for frontend compat), but delivery reads from workspace_files output folders. Will become pure audit trail when frontend migrates.
- `agent_type` — column on `agents` table, **DEPRECATED** by ADR-109 — being replaced by `scope` + `role`
- `agent_instructions` — column on `agents` table, **DEPRECATED** by ADR-106 Phase 2 — migrated to workspace `AGENT.md`
- `agent_memory` — column on `agents` table, **DEPRECATED** by ADR-106 Phase 2 — migrated to workspace `memory/*.md`
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

### ADR-077: Platform Sync Overhaul

**Three-phase sync model** per platform: landscape discovery → delta detection → content extraction.

- **Scheduler**: `platform_sync_scheduler.py` (separate from `unified_scheduler.py`) — checks tier-based frequency, dispatches to `platform_worker.py`
- **Worker**: `platform_worker.py` — `_sync_slack()`, `_sync_gmail()`, `_sync_notion()`, `_sync_calendar()` — all fully paginated with platform-specific hardening
- **Clients**: Direct API via `api/integrations/core/{slack,google,notion}_client.py` — no MCP, no gateway (ADR-076)
- **Content**: Stored in `platform_content` with TTL-based retention (Slack 14d, Gmail 30d, Notion 90d, Calendar 2d)
- **Tier limits**: Free=5/5/10, Pro=unlimited (slack/gmail/notion sources) — ADR-100 2-tier model
- **Google split**: Single `platform="google"` connection provides both Gmail and Calendar. Worker splits `selected_sources` by `metadata.platform` from landscape resources.

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
- Redirects to `/dashboard?provider=X&status=connected`
- Source curation on context pages is optional refinement, not prerequisite
- Tier-gated source limits enforced by `compute_smart_defaults()` max_sources

### ADR-056: Per-Source Sync

- Sync operates per-source (channel, label, page) not per-platform
- `integration_import_jobs` tracks sync state per resource

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
| Agent Framework (code) | `api/services/agent_framework.py` (ADR-117 Phase 3: portfolios, seniority, skills; ADR-126 Phase 5: ROLE_PULSE_CADENCE) |
| Agent Creation (shared) | `api/services/agent_creation.py` (ADR-111 Phase 1) |
| Project Type Registry | `api/services/project_registry.py` (ADR-122: project types, `scaffold_project()`) |
| TP Composer / Heartbeat | `api/services/composer.py` (ADR-111 Phase 3) |
| Onboarding Bootstrap | `api/services/onboarding_bootstrap.py` (ADR-110 → ADR-122: `maybe_bootstrap_project()`) |
| Agent Pulse Engine | `api/services/agent_pulse.py` (ADR-126: 3-tier sense→decide cycle) |
| Agent Execution | `api/services/agent_execution.py` |
| Delivery Service | `api/services/delivery.py` (ADR-118 D.3: `deliver_from_output_folder()`) |
| Feedback Distillation | `api/services/feedback_distillation.py` (ADR-117: edits → preferences.md) |
| Feedback Engine | `api/services/feedback_engine.py` (edit metrics computation) |
| Agent Pipeline | `api/services/agent_pipeline.py` |
| Agent Routes | `api/routes/agents.py` |
| Project Workspace | `api/services/workspace.py` — `ProjectWorkspace` class (ADR-119 Phase 2) |
| Project Primitives | `api/services/primitives/project.py` (ADR-119 Phase 2: CreateProject, ReadProject) |
| Project Routes | `api/routes/projects.py` (ADR-119 Phase 2: CRUD) |
| Dashboard Summary | `api/routes/dashboard.py` (Supervision Dashboard) |
| Platform Sync Worker | `api/workers/platform_worker.py` (ADR-077) |
| Platform Sync Scheduler | `api/jobs/platform_sync_scheduler.py` |
| Platform API Clients | `api/integrations/core/{slack,google,notion}_client.py` |
| Landscape Discovery | `api/services/landscape.py` |
| Tier Limits | `api/services/platform_limits.py` |
| Agent Scheduler | `api/jobs/unified_scheduler.py` |
| MCP Server | `api/mcp_server/` (ADR-075, ADR-116 Phase 4: 9 tools) |
| Output Gateway (yarnnn-render) | `render/` (ADR-118: skill library = capability filesystem) |
| Output Gateway Skills | `render/skills/` (8 skills: pdf, pptx, xlsx, chart, mermaid, html, data, image; each folder has SKILL.md + scripts/) |
| RuntimeDispatch Primitive | `api/services/primitives/runtime_dispatch.py` (ADR-118) |
| Frontend API Client | `web/lib/api/client.ts` |
| Sync Error Categorization | `web/lib/sync-errors.ts` (ADR-086) |
| Onboarding UI | `web/components/onboarding/` |
| Supervision Dashboard | `web/app/(authenticated)/dashboard/page.tsx` |
| Orchestrator (TP Chat) | `web/app/(authenticated)/orchestrator/page.tsx` |
| Route Constants | `web/lib/routes.ts` (HOME_ROUTE, ORCHESTRATOR_ROUTE) |

---

## Common Pitfalls

1. **Schema mismatch**: Code referencing old table/column names — use `agents` not `deliverables`, `agent_runs` not `deliverable_versions`, `agent_id` not `deliverable_id`
2. **Tool loop exhaustion**: TP hits `max_tool_rounds=5` without text response if tools return empty
3. **PGRST205 errors**: PostgREST schema cache needs refresh after table changes
4. **OAuth provider vs platform**: Google OAuth provides both `gmail` and `calendar` capabilities
5. **Render env var drift**: Worker/Scheduler missing env vars that API has — Worker silently fails to decrypt tokens, reports `success=True` with 0 items. Always check all services.
6. **Backend/frontend field name mismatch**: Backend returns one shape (e.g., `selected_sources`), frontend expects another (e.g., `sources`). Verify API response matches frontend consumer.

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
