# CLAUDE.md - Development Guidelines for YARNNN

This file provides context and guidelines for Claude Code when working on this codebase.

## Project Overview

YARNNN is an **autonomous agent platform for recurring knowledge work**. Persistent AI agents connect to work platforms (Slack, Gmail, Notion, Calendar), run on schedule, learn from feedback, and produce outputs that improve with tenure.

**Architecture**: Next.js frontend → FastAPI backend → Supabase (Postgres) → Claude API

**Key terminology** (ADR-103):
- **Agent** (was: Deliverable) — a persistent, autonomous entity with identity, instructions, memory, tools, schedule, and output history
- **Agent Run** (was: Deliverable Version) — a single execution of an agent, producing draft/final content
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
- **ADR-088**: Trigger Dispatch - `dispatch_trigger()` in `api/services/trigger_dispatch.py`, single decision point for schedule/event/signal triggers (Phase 1 implemented)
- **ADR-092**: Agent Intelligence & Mode Taxonomy - five modes (`recurring`, `goal`, `reactive`, `proactive`, `coordinator`); signal processing dissolved from L3; `RefreshPlatformContent` extended to headless; coordinator agents replace `signal_emergent` origin (Implemented — signal processing removed, modes active, coordinator pipeline in `proactive_review.py`)
- **ADR-101**: Agent Intelligence Model - four-layer knowledge model (Skills / Directives / Memory / Feedback); learned preferences from edit history injected into headless system prompt; `get_past_versions_context()` includes delivered runs
- **ADR-102**: yarnnn Content Platform - agent outputs written as `platform_content` rows with `platform="yarnnn"`, closing the accumulation loop; always retained; searchable by TP and headless agents; no OAuth, no sync
- **ADR-103**: Agentic Framework Reframe - terminology migration from "deliverable" to "agent" throughout codebase. Agents are persistent autonomous entities, not document generators.
- **ADR-104**: Agent Instructions as Unified Targeting - `agent_instructions` is the single targeting layer; dual-injected into system prompt (behavioral constraints) and user message (priority lens); dead infrastructure deleted (DataSource.scope/filters, SECTION_TEMPLATES, unused type_config fields, template_structure)
- **ADR-105**: Instructions to Chat Surface Migration - directives (instructions, audience) flow through chat; configuration (schedule, sources) stays in drawer; design principle in `docs/design/SURFACE-ACTION-MAPPING.md`
- **ADR-106**: Agent Workspace Architecture - virtual filesystem over Postgres (`workspace_files` table); agents interact via path-based operations; archetype-driven strategies (reporter/analyst/researcher/operator); reasoning agents drive own context gathering from workspace instead of receiving platform dumps; replaces `agent_memory` JSONB; storage-agnostic abstraction layer preserves optionality for cloud storage
- **ADR-109**: Agent Framework — Scope × Role × Trigger taxonomy replacing the 7-type system (ADR-093). Scope (what it knows: platform/cross_platform/knowledge/research/autonomous) determines context strategy. Role (what it does: digest/prepare/monitor/research/synthesize/act) determines prompt + primitives. Trigger (when it acts) = preserved ADR-092 modes. `agent_type` column → `scope` + `role` columns (was `skill`, renamed by ADR-118 Resolved Decision #4 to eliminate naming overload with output gateway skills). Templates are user-facing convenience layer. Canonical reference: `docs/architecture/agent-framework.md`. (Implemented — `skill` → `role` column rename completed in ADR-118 D.1, migration 114.)
- **ADR-110**: Onboarding Bootstrap — deterministic, zero-LLM agent creation on platform connection. Post-sync, auto-creates matching digest agent (Slack→Recap, Gmail→Digest, Notion→Summary) with `origin=system_bootstrap`. Executes first run immediately. Becomes Bootstrap bounded context within Composer (ADR-111). (Implemented.)
- **ADR-111**: Agent Composer — TP's compositional capability (not a separate service). Three bounded contexts: **Bootstrap** (deterministic fast-path), **Heartbeat** (periodic TP self-assessment of agent workforce), **Composer** (assessment + creation/adjustment/dissolution). Unifies Write/CreateAgent into single `CreateAgent` primitive. Autonomy-first: bias toward action, feedback as correction. Proactive/coordinator modes reframed as TP supervisory capabilities. Platform content as onramp (dependency decreases over time). Lifecycle progression: per-agent maturity signals (run count, approval rate, edit distance trend), auto-pause underperformers, auto-create synthesis from mature digests, cross-agent pattern detection. (Implemented — all 5 phases.)
- **ADR-112**: Sync Efficiency & Concurrency Control — three layers: (1) atomic sync lock on `platform_connections` replacing `SCHEDULE_WINDOW_MINUTES` timing hack, (2) platform-level heartbeat fast-path (Gmail historyId, Calendar syncToken, Slack latest, Notion search) to skip source iteration when nothing changed, (3) per-source skip hints (deferred). Coordinates all three sync paths (scheduled, manual, TP RefreshPlatformContent). (Implemented.)
- **ADR-113**: Auto Source Selection — eliminates manual source selection as prerequisite for platform connections. OAuth callback auto-discovers landscape, applies `compute_smart_defaults()`, kicks off first sync immediately. Post-OAuth redirect changed from `/orchestrator` to `/dashboard`. Context pages become optional refinement, not first-time entry point. Dashboard platform cards trigger OAuth directly. (Implemented.)
- **ADR-114**: Composer Substrate-Aware Assessment — evolves Composer from platform-metadata-centric to recursive-substrate-aware. Four phases: (1) knowledge corpus signals in heartbeat_data_query, (2) substrate-aware heuristics in should_composer_act, (3) knowledge summary in LLM prompt, (4) Composer prompt v2.0. Establishes Composer prompt versioning policy (same rigor as Orchestrator). (Phase 1-3 Implemented. Phase 4 — Composer Prompt v2.0 — proposed, current is v1.3.)
- **ADR-116**: Agent Identity & Inter-Agent Knowledge Infrastructure — makes agents discoverable and composable. Five phases: (1) knowledge metadata search (QueryKnowledge filters by agent_id/role/scope), (2) agent discovery primitive (DiscoverAgents), (3) cross-agent workspace reading (ReadAgentContext — read-only), (4) agent card auto-generation + MCP exposure (get_agent_card, search_knowledge, discover_agents tools), (5) consumption tracking + Composer agent dependency graph (orphaned producers, missing producers, stale dependencies). Agent-native identity thesis: workspace IS identity, agents are first-class participants not human proxies. (Implemented.)

- **ADR-117**: Agent Feedback Substrate & Developmental Model — unifies three disconnected feedback rails (user edits, Composer lifecycle, agent self-observation) into workspace as single substrate. Three phases: (1) feedback distillation to `memory/preferences.md` + extend workspace context to all agents (not just analyst), (2) agent self-reflection (post-generation observations), (3) intentions architecture (multi-skill within one agent identity, earned through feedback-gated capability progression). Formalizes FOUNDATIONS.md Axiom 3. Key files: `feedback_distillation.py` (distill edits → preferences.md), `feedback_engine.py` (edit metrics), all strategies call `load_context()` for workspace feedback. Dual injection: preferences in system prompt (high salience) + gathered context. Composer coaching via `supervisor-notes.md`. (Phase 1-2 Implemented. Phase 3 proposed.)

- **ADR-118**: Skills as Capability Layer — "Claude Code online" model. Two-filesystem architecture: capability filesystem (skills on output gateway Docker service, `render/skills/{name}/SKILL.md` + scripts, platform-wide) and content filesystem (workspace_files + S3, user-scoped, accumulating). Adopts Claude Code naming conventions directly: skills (not handlers/capabilities), SKILL.md (not capability guides), skill folders (same structure as Claude Code). Two skill types: local (tools in Docker image, fixed cost) and delegated (external API/MCP, per-call cost). Skills are explicit/curated, earned via feedback-gated progression (Axiom 3). Phase A (delivery-by-default), Phase B (output gateway + first skills), Phase C (Composer + frontend awareness) implemented. Phase D.1 (skills alignment/rename), D.2 (render hardening), D.3 (unified output substrate — output folders as delivery source, `deliver_from_output_folder()`, manifest-based email attachments) implemented. Phase D.4 (expand skill library), D.5 (assets layer) proposed. Full analysis: `docs/analysis/skills-as-capability-layer-2026-03-17.md`.

- **ADR-119**: Workspace Filesystem Architecture — evolves `workspace_files` from flat key-value store to proper folder-based filesystem. Folders are boundaries, folders are context. Key conventions: output folders (`/agents/{slug}/outputs/{date}/`) replace bundle tables — co-located files + `manifest.json` = atomic output. Project folders (`/projects/{slug}/`) with scoped contribution subfolders = cross-agent collaboration. `/working/` = ephemeral scratch. Two schema additions: `version` + `lifecycle` columns on `workspace_files`. Manifest files carry metadata (sources, delivery status, file roles) instead of relational tables. Thesis: folders are boundaries and boundaries are all you need for coordination — same principle as Cowork's folder selection applied to persistent agent workspaces. Makes ADR-118 Phase D structurally sound. Extends ADR-106, interacts with ADR-116 (cross-agent reading), ADR-117 (feedback via manifests). (Phase 1 Implemented — ADR-118 D.3 uses output folders as delivery source.)

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
- `agents` — persistent autonomous agents (was `deliverables`, renamed ADR-103). Key columns: `scope` + `role` (ADR-109, replacing `agent_type`; was `skill`, renamed by ADR-118 to eliminate naming overload), `mode` (trigger)
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
| Tool Primitives | `api/services/primitives/*.py` |
| Memory Service | `api/services/memory.py` |
| Working Memory | `api/services/working_memory.py` |
| Chat/Streaming | `api/services/anthropic.py` |
| OAuth Flow | `api/integrations/core/oauth.py` |
| Agent Workspace | `api/services/workspace.py` (ADR-106) |
| Workspace Primitives | `api/services/primitives/workspace.py` (ADR-106) |
| Agent Framework (canonical) | `docs/architecture/agent-framework.md` (ADR-109) |
| Agent Creation (shared) | `api/services/agent_creation.py` (ADR-111 Phase 1) |
| TP Composer / Heartbeat | `api/services/composer.py` (ADR-111 Phase 3) |
| Onboarding Bootstrap | `api/services/onboarding_bootstrap.py` (ADR-110, implemented) |
| Agent Execution | `api/services/agent_execution.py` |
| Delivery Service | `api/services/delivery.py` (ADR-118 D.3: `deliver_from_output_folder()`) |
| Feedback Distillation | `api/services/feedback_distillation.py` (ADR-117: edits → preferences.md) |
| Feedback Engine | `api/services/feedback_engine.py` (edit metrics computation) |
| Agent Pipeline | `api/services/agent_pipeline.py` |
| Agent Routes | `api/routes/agents.py` |
| Dashboard Summary | `api/routes/dashboard.py` (Supervision Dashboard) |
| Platform Sync Worker | `api/workers/platform_worker.py` (ADR-077) |
| Platform Sync Scheduler | `api/jobs/platform_sync_scheduler.py` |
| Platform API Clients | `api/integrations/core/{slack,google,notion}_client.py` |
| Landscape Discovery | `api/services/landscape.py` |
| Tier Limits | `api/services/platform_limits.py` |
| Agent Scheduler | `api/jobs/unified_scheduler.py` |
| MCP Server | `api/mcp_server/` (ADR-075, ADR-116 Phase 4: 9 tools) |
| Output Gateway (yarnnn-render) | `render/` (ADR-118: skill library = capability filesystem) |
| Output Gateway Skills | `render/skills/` (pptx, pdf, xlsx, chart + future; each folder has SKILL.md + scripts/) |
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
