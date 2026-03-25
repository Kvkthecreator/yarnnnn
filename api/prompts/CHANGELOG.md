# Prompt Changelog

Track changes to system prompts, tool definitions, and LLM-facing content.

Format: `[YYYY.MM.DD.N]` where N is the revision number for that day.

---

## [2026.03.25.2] - ADR-140: TP Workforce Awareness + Task-Centric Commands

### Changed
- `agents/tp_prompts/tools.py`: Replaced archetype list (monitor/researcher/producer/operator) with ADR-140 workforce model (6 types: research, content, marketing, crm, slack_bot, notion_bot). Added "Workforce Model" section describing the pre-scaffolded 6-agent roster. Task creation is now the primary flow; agent creation is secondary. TP knows agents exist at sign-up.
- `agents/tp_prompts/base.py`: Updated terminology section — added pre-scaffolded roster awareness, bot/agent distinction, task-first guidance.
- `services/commands.py`: Added `/task` command (primary). Rewrote `/recap`, `/summary`, `/research` to create tasks on existing roster agents instead of creating new agents. `/create` demoted to secondary (roster usually covers needs). All commands now use CreateTask instead of CreateAgent.
- `services/working_memory.py`: Agent section in prompt renamed from "Active agents" to "Your team (N agents)" with role display.
- Expected behavior: TP guides users to assign tasks to their pre-existing 6-agent roster. Only creates new agents when roster doesn't cover the need. Slash commands create tasks, not agents.

---

## [2026.03.25.1] - ADR-138: Agents as Work Units — Project Layer Collapse

### Added
- `services/primitives/task.py`: CreateTask + TriggerTask primitives. CreateTask writes TASK.md, creates DB row, assigns agent. TriggerTask sets next_run_at to now for immediate execution.
- `services/task_workspace.py`: TaskWorkspace class for /tasks/{slug}/ filesystem operations.
- `routes/tasks.py`: CRUD API routes (list, get, create, update, archive) at /api/tasks.

### Changed
- `agents/tp_prompts/tools.py`: Complete rewrite of Domain Terms, Creating Agents, and Creating Tasks sections. Agents are WHO (identity, expertise). Tasks are WHAT (objective, cadence, delivery). Removed all project/PM language. Removed CreateProject documentation. Added CreateTask and TriggerTask documentation.
- `services/primitives/coordinator.py`: Simplified CreateAgent to identity-only (title, role, agent_instructions). Removed schedule, sources, destination, recipient_context, trigger_context, dedup_key parameters. Deleted AdvanceAgentSchedule primitive entirely.
- `services/primitives/registry.py`: Removed 7 stale project primitives (CreateProject, ReadProject, CheckContributorFreshness, ReadProjectStatus, RequestContributorAdvance, UpdateWorkPlan, AdvanceAgentSchedule). Added CreateTask, TriggerTask. Removed `agent_chat` from all PRIMITIVE_MODES. 23 primitives total.
- `services/agent_creation.py`: Simplified create_agent_record() — removed schedule, sources, destination, recipient_context, next_pulse_at params. Agents are identity-only (title, role, scope, mode, instructions, type_config).
- Expected behavior: TP uses CreateAgent for domain experts (WHO) and CreateTask for work definitions (WHAT). No project creation. No PM agents. Scheduling lives on tasks, not agents.

### Removed
- `services/primitives/project.py`: CreateProject, ReadProject primitives (deleted in Phase 2)
- `services/primitives/project_execution.py`: PM execution primitives (deleted in Phase 2)
- `services/pm_coordination.py`: PM chat coordination (deleted in Phase 2)
- `services/pipeline_executor.py`: Declarative pipeline execution (deleted in Phase 2)
- `services/project_registry.py`: Project type registry + scaffold_project() (deleted in Phase 2)
- PM prompt v6.0 from agent_pipeline.py (~200 lines)
- PM Tier 3 coordination from agent_pulse.py (~330 lines)
- PM decision interpreter from agent_execution.py (~500 lines)
- ProjectWorkspace class from workspace.py (~400 lines)
- Total: ~11,544 lines of project/PM code removed

## [2026.03.24.6] - ADR-137 Phase 1: Declarative pipeline executor

### Added
- `services/pipeline_executor.py`: Reads PROCESS.md pipeline, advances steps mechanically. `advance_pipeline()` called by scheduler per project. `parse_pipeline()` reads step definitions. `pipeline_state.json` tracks cycle + step states. Steps advance when dependencies complete. Cadence enforcement built-in.

### Changed
- `jobs/unified_scheduler.py`: Pipeline execution runs BEFORE individual pulse dispatch. Project agents (with pipeline in PROCESS.md) execute via pipeline. Standalone agents (no project) keep pulse system. Pulse loop filters out project contributors.
- Expected behavior: project agent runs are deterministic (pipeline step order), not LLM-decided. Standalone agents unaffected. ~95% reduction in PM coordination overhead.

## [2026.03.24.5] - ADR-132: Onboarding redesign — document-first + multi-scope inference

### Changed
- `onboarding/page.tsx`: Complete rewrite. Removed 3-step flow (single/multi → scopes → brand). Now 2-step: (1) share context (files + text), (2) brand + name. File upload zone with drag-drop. Text description as textarea. Submit sends everything for inference.
- `project_inference.py`: Complete rewrite. `infer_work_scopes()` — single Sonnet call reads ALL uploaded docs + text → extracts MULTIPLE scopes with rich specs (objective, success_criteria, output_spec, team, cadence). `read_uploaded_documents()` reads doc content from filesystem_chunks.
- `routes/memory.py`: Onboarding endpoint redesigned. Phase 1: LLM inference extracts scopes. Phase 2: scaffold per scope with inferred overrides. Fallback: lightweight type inference if Sonnet fails.
- Expected behavior: user drops pitch deck → system infers "Competitive Intel (weekly, scout)" + "Product Development (daily, briefer)" → scaffolds 2 projects with rich charter content.

### Removed
- Single/multi step from onboarding (conceptually wrong question)
- Per-scope text inputs (replaced by single text description)
- `enrich_scaffold_params()` (replaced by multi-scope `infer_work_scopes()`)

## [2026.03.24.4] - Cost optimization: Tier 2 pre-screen + PM prompt modes

### Changed
- `agent_pulse.py`: Tier 2 tool rounds reduced from 5 to 2 (quick domain check, not deep investigation). Prompt updated: "Be efficient — one quick search is usually enough." Saves ~60% on Haiku pre-screen calls.
- `agent_framework.py`: Added `PM_MODES` registry — 4 prompt modes (coordinate/evaluate/reflect/compose) with model + cost + when metadata. Enables cost-aware PM intelligence: Haiku for coordination, Sonnet for composition.
- Expected behavior: contributors pre-screen faster (2 tool rounds vs 5). PM mode selection enables ~$0.12-0.15/week per project instead of unbounded.

## [2026.03.24.3] - ADR-136: Project inference — LLM-enriched charter content

### Added
- `services/project_inference.py`: Single Haiku call that enriches generic project templates with specific content. `infer_project_spec()` takes scope name + description + document context → returns specific objective, success criteria, output spec, team recommendation, cadence. `enrich_scaffold_params()` reads uploaded docs and produces scaffold_project() overrides.
- Charter files now contain specific, actionable content instead of template interpolation.

### Changed
- `routes/memory.py`: Onboarding endpoint calls `enrich_scaffold_params()` before `scaffold_project()`. Accepts `document_ids` parameter. Falls back to lightweight `infer_topic_type()` if LLM inference fails.
- `project_registry.py`: `scaffold_project()` accepts `success_criteria` and `output_spec` params, passes to `write_project()`.
- `workspace.py`: `write_project()` accepts `success_criteria` and `output_spec` params. PROJECT.md success criteria and PROCESS.md output spec populated from inference results.
- Expected behavior: "AI Competitive Intel" → PROJECT.md with "Cover top 5 AI competitors, include pricing comparison" instead of "Relevant to stated audience."

## [2026.03.24.2] - TP→PM handoff + onboarding file upload

### Changed
- `project_registry.py`: `scaffold_project()` now writes a PM handoff message to the project chat session via `pm_announce()`. Message includes: title, objective summary, team names, cadence. PM reads this on first pulse for context.
- `onboarding/page.tsx`: Step 2 now has file upload drop zone alongside text inputs. Users can share docs (pitch decks, briefs) for context inference. Document IDs passed to scaffold API.
- `api/client.ts`: `onboardingScaffold.save()` accepts optional `documentIds` parameter.
- Expected behavior: PM's first chat message is the handoff — "Project created: X. Team: Y. Cadence: Z." User sees this when they open the project. Onboarding accepts files OR text OR both.

## [2026.03.24.1] - ADR-136: Charter file split + cadence enforcement + PM process awareness

### Changed
- `workspace.py`: `write_project()` now writes 3 charter files (PROJECT.md + TEAM.md + PROCESS.md). `read_project()` reads all three and merges. TEAM.md maps contributors to AGENT_TYPES capabilities. PROCESS.md defines cadence, output spec, delivery, phases.
- `project_registry.py`: `scaffold_project()` passes frequency + role to `write_project()`. Contributor records include role for TEAM.md.
- `agent_pulse.py`: Tier 1 Gate 3 (cadence enforcement) reads PROCESS.md cadence, blocks if already ran in cadence window. PM Tier 3 prompt includes cadence + process context for coordination decisions.
- Expected behavior: weekly projects run once/week. Cadence gate prevents duplicate runs. PM knows the delivery rhythm and output spec.

## [2026.03.23.14] - ADR-133: Perception/Production/Coordination agent model

### Changed
- `agent_framework.py`: **AGENT_TYPES v3** — three categories: perception (briefer, monitor, scout), production (researcher, drafter, analyst, writer, planner), coordination (pm). `category` field added to each type.
- `agent_framework.py`: `read_platforms` REMOVED from production types. Production agents get `search_knowledge` instead — they read processed knowledge from perception agents, not raw platform data.
- `agent_framework.py`: `search_knowledge` capability added to capabilities registry (maps to QueryKnowledge tool).
- `project_registry.py`: Platform-specific project types DELETED (slack_digest, notion_digest, cross_platform_synthesis, custom). Two types only: workspace + bounded_deliverable.
- `onboarding_bootstrap.py`: Bootstrap creates workspace project with briefer (not platform-specific type). Uses infer_topic_type for scope_name.
- Expected behavior: perception agents bridge external→internal (one-way). Production agents work recursively within PM-orchestrated loop. No spray-and-pray platform data injection.

### Removed
- Platform project types: slack_digest, notion_digest, cross_platform_synthesis, custom
- `read_platforms` from: researcher, drafter, analyst, writer, planner, scout
- Platforms tab from Orchestrator panel (moved to Settings — infrastructure)
- Platform connect action cards from Orchestrator empty state

## [2026.03.23.13] - ADR-135: Chat as coordination substrate

### Changed
- `agent_pulse.py`: PM Tier 3 decisions now write to project chat session via `pm_announce()`. Dispatch, advance_phase, escalate, generate — all announced as attributed PM messages. PM log (`memory/pm_log.md`) read before decisions for cross-context continuity. JSON prompt strengthened with "IMPORTANT: ONLY raw JSON."
- `agent_execution.py`: Contributor run completions write to project chat via `contributor_report()`. Summary includes word count + confidence assessment.
- Expected behavior: Project chat timeline shows agent coordination (PM dispatches, contributor completions, phase advances) as natural language messages attributed to agents. No more "PM pulsed — unknown."

### Added
- `services/pm_coordination.py`: Unified helper for agent→chat communication. `pm_announce()` writes to chat session + pm_log.md + activity event. `contributor_report()` writes to chat session. `read_pm_log()` reads rolling decision history.

## [2026.03.23.12] - ADR-132: CreateProject primitive — title-based type inference + multi-step guidance

### Changed
- `primitives/project.py`: **CreateProject tool description v2** — three modes: work project (title-only, inferred), platform project (type_key), custom project (explicit agents). Multi-step workflow guidance: when user uploads a file and wants a project, TP should Search → extract details → CreateProject with informed objective. Examples updated for new types.
- `primitives/project.py`: **handle_create_project** — when no type_key and no contributors, auto-infers agent type + lifecycle from title via `infer_topic_type()`. "Fundraising" → drafter (bounded). "Competitive Watch" → scout (persistent). Falls through to manual creation only when explicit contributors provided.
- Expected behavior: TP can create work-scoped projects with just a title — no need to ask user for type_key, agent type, or lifecycle. Type inference handles it. Multi-step "upload → create project" flow documented in tool description.

## [2026.03.23.11] - ADR-133 Phases 2+3: Cross-phase context + capability-aware coordination

### Changed
- `agent_pulse.py`: `_write_phase_briefs()` — PM writes phase-aware contribution briefs before dispatching contributors. Briefs include prior phase output previews (cross-phase context injection). Contributors read these via existing `read_brief()` in workspace load_context().
- `agent_pulse.py`: `_advance_phase_state()` — updates `phase_state.json` when PM advances a phase. Logs `phase_advanced` activity event.
- `agent_pulse.py`: `_build_tier3_prompt()` — PM coordination prompt now includes contributor capabilities (asset types per role) and available agent types reference. PM can reason about capability gaps and escalate for missing types.
- Expected behavior: when PM dispatches contributors, they receive briefs with prior phase context. PM advances phases deterministically. PM knows what each contributor can produce (charts, video, etc.) for capability-aware coordination.

## [2026.03.23.10] - ADR-133 Phase 1: PM-coordinated phase dispatch

### Changed
- `agent_pulse.py`: Refactored `run_agent_pulse()` with three-mode routing:
  - PM agents → Tier 1 + Tier 3 (new PM coordination pulse)
  - Project contributors → PM-dispatched (Tier 1 safety gates, then generate)
  - Standalone agents → Tier 1 + Tier 2 (independent pulse, unchanged)
- New: `_tier3_pm_coordination()` — PM reads work plan, phase_state.json, contributor assessments. Decides: dispatch, advance_phase, generate, escalate, or wait. Dispatches contributors by setting `next_pulse_at`.
- New: `_dispatch_contributors()` — sets `next_pulse_at` on target contributors, logs `contributor_dispatched` events.
- New: `_build_tier3_prompt()` — PM coordination prompt with project objective, work plan, phase state, contributor status.
- Expected behavior: PM is the sole heartbeat for project-scoped work. Contributors run when PM dispatches. Standalone agents unaffected.

## [2026.03.23.9] - ADR-130 v2: Type-specific prompt templates

### Added
- `agent_pipeline.py`: **4 new ROLE_PROMPTS** — `drafter` (deliverable production: reports, decks, memos), `writer` (external content: newsletters, investor updates, social), `planner` (plans, agendas, action tracking), `scout` (competitive intelligence: competitor monitoring + web search + positioning implications).
- Each prompt has distinct structure, instructions, and output format tailored to the agent's purpose.
- `scout` field handler: injects `today_date` for time-sensitive competitive intel.
- Expected behavior: agents now get role-appropriate prompts instead of falling back to generic custom template. Drafter produces polished deliverables. Writer matches user's voice. Planner tracks action items. Scout cites sources and recommends positioning responses.

### Unchanged
- `briefer` = `digest` prompt (platform summarization — well-tested, no change)
- `analyst` = `synthesize` prompt (cross-reference patterns — well-tested)
- `researcher` = `research` prompt (investigation + web search — well-tested)
- `monitor` prompt (change detection + alerts — well-tested)

## [2026.03.23.8] - ADR-130: Capability redistribution + video skill + platform write-backs

### Changed
- `agent_framework.py`: Capability redistribution across types:
  - Added `image` to: researcher, drafter, writer, scout (visual content producers)
  - Added `video_render` to: drafter, writer (media content producers)
  - Added `write_slack`, `write_notion` to: pm (delivery agent, user-authorized)
  - `video_render` capability runs on `python_render` runtime (same service, Remotion added to Docker)
  - `node_remotion` runtime deleted — collapsed into `python_render`
  - `write_slack`/`write_notion` capabilities added with `requires_auth: True` (user-authorized per agent)
- `primitives/runtime_dispatch.py`: Tool definition updated — added video skill (type="video", max 30s, MP4). Extended timeout to 180s for video renders. Chart/mermaid/image unchanged at 60s.
- `render/Dockerfile`: Added `@remotion/cli` and `remotion` npm packages for video rendering.
- Expected behavior: drafter/writer agents get video SKILL.md injected, can produce short-form MP4 clips. PM agents declare platform write-back capability (tools not yet implemented — capability declared for future wiring).

### Added
- `render/skills/video/SKILL.md`: Short-form video skill specification — scene-based JSON input, 30s max, silent MP4 output. Scene types: title, metric, comparison, text, chart.
- `render/skills/video/scripts/render.py`: Python wrapper for Remotion CLI (`npx remotion render`). Validates constraints (duration, scene count), writes props JSON, calls subprocess.

## [2026.03.23.7] - ADR-130 Phase 3 (partial): Format-builder skill dissolution

### Changed
- `primitives/runtime_dispatch.py`: Tool description updated — removed document/presentation/spreadsheet skills. Now lists only asset renderers: chart, mermaid, image. Output format narrowed to png/svg.
- Expected behavior: agents no longer see pptx/xlsx/pdf as available RuntimeDispatch types. They produce markdown + charts/diagrams. Compose engine handles presentation; export pipeline (future) handles file conversion.

### Removed
- `render/skills/pptx/` — format-builder dissolved (presentation layout mode replaces)
- `render/skills/html/` — absorbed into compose engine
- `render/skills/data/` — absorbed into compose engine
- `render/skills/pdf/` and `render/skills/xlsx/` retained for future export pipeline (not agent-facing)

## [2026.03.23.6] - ADR-130 Phase 2: HTML-native compose integration

### Changed
- `agent_execution.py`: Post-generation compose step — after save_output(), calls `/compose` on yarnnn-render for agents with `compose_html` capability. Stores `output.html` in output folder alongside `output.md`. Non-fatal — agent run succeeds even if compose fails.
- `delivery.py`: Email delivery prefers composed HTML (`output.html`) when available. Falls back to `generate_email_html()` from markdown if no composed HTML exists. No behavioral change for agents without compose capability.
- Expected behavior: agents that produce output get styled, branded HTML email bodies instead of basic markdown-to-HTML conversion. Charts/diagrams are inline (via asset URL resolution). Layout mode defaults to `document`.

## [2026.03.23.5] - ADR-130 v2: Full codebase migration to v2 agent types

### Changed
- `composer.py`: Composer prompt v3.0 — valid roles updated to v2 types (briefer, monitor, researcher, drafter, analyst, writer, planner, scout). Templates, heuristics, source inference all migrated. `senior_agents` → `proven_agents` in maturity signals.
- `tp_prompts/tools.py`: CreateAgent role list updated to v2 types
- `tp_prompts/behaviors.py`: Agent creation guidance table updated to v2 types with new schedule defaults
- `primitives/coordinator.py`: CreateAgent tool doc + examples updated to v2 types
- `agent_pipeline.py`: Role prompt selection uses `resolve_role()` + `LEGACY_ROLE_MAP` for backward compat. Output validation handles both old and new type names.
- `agent_execution.py`: Strategy selection handles planner/prepare, validation handles briefer/digest and analyst/synthesize
- `agent_pulse.py`: Default fallback changed from "custom" to "briefer". Autonomous scope check includes new research types.
- `agent_creation.py`: VALID_ROLES derived from AGENT_TYPES registry. ROLE_TO_SCOPE includes all v2 types. Capability reference uses `has_asset_capabilities()`.
- `routes/agents.py`: Role Literal type updated with v2 types + legacy compat
- `commands.py`: All command templates migrated (digest→briefer, synthesize→analyst)
- `mcp_server/server.py`: Role filter documentation updated to v2 types
- Expected behavior: all new agent creation uses v2 types. Existing agents with old role values handled via `resolve_role()` / `LEGACY_ROLE_MAP`.

## [2026.03.23.5] - ADR-132: Topic → agent type inference + DB migration 127

### Changed
- `project_registry.py`: `infer_topic_type()` heuristic — topic name keywords → agent type + lifecycle + objective purpose. No LLM call.
- `memory.py` (routes): `save_topics()` uses `infer_topic_type()` to select agent type per topic. Passes `contributors_override` + `objective_override`.
- `project_registry.py`: `scaffold_project()` interpolates `{scope_name}` in contributor overrides.
- Expected behavior: "Fundraising" → drafter (bounded), "Competitive tracking" → scout (persistent), "Client: Acme" → briefer (persistent).

### Database
- Migration 127: `agents_role_check` expanded with v2 types. Existing agents migrated: digest→briefer, research→researcher.

## [2026.03.23.4] - ADR-130 v2: Agent type registry — 8 product types + multi-agent coordination

### Changed
- `agent_framework.py`: **AGENT_TYPES v2** — 8 user-facing types (briefer, monitor, researcher, drafter, analyst, writer, planner, scout) + PM infrastructure. Each type has `display_name`, `tagline`, capabilities, description. Types are product offerings, not internal taxonomy. `resolve_role()` maps legacy names (digest→briefer, synthesize→analyst, research→researcher, prepare→planner, custom→briefer). `list_agent_types()` for TP prompt injection.
- `agent-identity.ts`: **v2** — `resolveRole()` frontend mapping. New display names, avatar colors, badge colors, taglines for all 8 types. Legacy roles transparently mapped.
- `agent_pipeline.py`: `DEFAULT_INSTRUCTIONS` extended with v2 type entries. `ROLE_PROMPTS` aliases: briefer→digest template, analyst→synthesize, researcher→research, scout→research, drafter/writer/planner→custom (TODO: type-specific prompts).
- `project_registry.py`: Contributor templates updated — `"Slack Agent"→"Slack Briefer"`, `"Notion Agent"→"Notion Briefer"`, `"Cross-Platform Synthesizer"→"Cross-Platform Analyst"`, `"{scope_name} Digest"→"{scope_name} Briefer"`. Role values: `digest→briefer`, `synthesize→analyst`.
- `output-substrate.md`: Agent type registry section rewritten for v2 types + multi-agent coordination model.
- Expected behavior: all new agents created with v2 type names. Existing DB agents with legacy role values work via `resolve_role()` / `resolveRole()` mappings. No DB migration needed — soft migration at read time.

### Dissolved
- `synthesize` type → `analyst` (cross-referencing is what analysts do)
- `prepare` type → `planner` (broader: plans, agendas, follow-ups, not just meeting prep)
- `custom` type → `briefer` (safe default; every agent should have a real type)
- `digest` type → `briefer` (product name: "keeps you briefed", not "recaps")

## [2026.03.23.3] - ADR-132: Work-first onboarding — working memory + Composer integration

### Changed
- `working_memory.py`: TP system prompt now includes "Your work" section — reads `/memory/WORK.md` via `_get_work_index_sync()`, renders active work scopes with project links. TP sees user's declared work landscape in every conversation.
- `composer.py`: Heartbeat data query reads `/memory/WORK.md` via `_get_work_index()`. `should_composer_act()` gains `work_scope_gap` check — triggers when declared scopes lack corresponding projects.
- `memory.py` (routes): `OnboardingStateResponse` simplified to `has_work_index` only. Legacy `state`/`memory_count`/`document_count`/`has_recent_chat` fields removed. Endpoint streamlined to single WORK.md existence check.
- Expected behavior: TP can reference user's work structure in conversation. Composer detects and acts on unscaffolded work scopes. New users without work index are gated to `/onboarding` on login.

### Added
- `memory.py` (routes): `POST /api/memory/user/work` — saves work index + scaffolds projects per scope. `GET /api/memory/user/work` — reads and parses work index.
- `onboarding_bootstrap.py`: `_has_work_index()` check — skips generic platform digest when user has work-scoped projects from onboarding.
- `project_registry.py`: `workspace` + `bounded_deliverable` work-scoped types with `{scope_name}` template interpolation.

### Removed
- `useOnboardingState` hook (frontend) — dead code, zero consumers
- `OnboardingState` type (`cold_start | minimal_context | active`) — replaced by `has_work_index`
- Legacy onboarding state computation (memory counts, document counts, chat history checks)

## [2026.03.23.2] - ADR-130 Phase 1a: Three-registry architecture + seniority deletion

### Changed
- `agent_framework.py`: **Complete rewrite** — three registries (AGENT_TYPES, CAPABILITIES, RUNTIMES) replace seniority system. Agent capabilities are deterministic per type, fixed at creation. No seniority-gated progression. Helper functions: `get_type_capabilities()`, `has_asset_capabilities()`, `get_type_skill_docs()`. Type definitions are v1 (expect revision after ADR-132).
- `composer.py`: **Composer Prompt v3.0** — removed `promote_duty` action, seniority references. Deleted `_execute_promote_duty()` (~140 lines). Maturity signals renamed: `senior_agents` → `proven_agents` (5+ runs, 60%+ approval). Lifecycle heuristics preserved but rebased on run count/approval instead of seniority classification.
- `agent_pulse.py`: Tier 2 self-assessment now available to ALL agents (was associate+ only). Removed `classify_seniority` import and eligibility gate. Simplified: Tier 1 passes → Tier 2 always runs.
- `working_memory.py`: TP system reference now built from `AGENT_TYPES` registry instead of `ROLE_PORTFOLIOS`/`SKILL_ENABLED_ROLES`. Agent roles show capabilities list and asset capability flag.
- `agent_execution.py`: Skill docs fetch gate changed from `role in SKILL_ENABLED_ROLES` to `has_asset_capabilities(role)` — type-scoped capability check.
- Expected behavior: agents no longer earn capabilities through feedback. All agents get Tier 2 pulse self-assessment. Composer cannot promote duties. Agent development = knowledge depth (memory, preferences), not capability breadth.

### Removed
- `agent_framework.py`: `classify_seniority()`, `ROLE_PORTFOLIOS`, `get_eligible_duties()`, `get_promotion_duty()`, `SKILL_ENABLED_ROLES`
- `composer.py`: `_execute_promote_duty()`, `promote_duty` prompt examples, duty promotion heuristic in `should_composer_act()`, duty promotion handler in `run_lifecycle_assessment()`
- `test_adr117_p3_duties.py`: Entire seniority test file deleted

## [2026.03.23.1] - API cost optimization: relaxed pulse cadence + Haiku for extraction

### Changed
- `agent_framework.py`: Relaxed `ROLE_PULSE_CADENCE` — monitor 15min→1h, pm 30min→2h. Reduces Tier 2 Haiku calls by ~4x for monitors and ~4x for PMs.
- `memory.py`: Default `EXTRACTION_MODEL` changed from Sonnet to Haiku (`claude-haiku-4-5-20251001`). Memory extraction runs once daily — Haiku is sufficient for fact extraction from conversations.
- `session_continuity.py`: Default `SUMMARY_MODEL` changed from Sonnet to Haiku. Session summaries are structured extraction, not creative work.
- Expected behavior: ~75% reduction in nightly extraction cost, ~4x reduction in pulse LLM frequency. Both still overridable via `MEMORY_EXTRACTION_MODEL` env var.

## [2026.03.22.6] - ADR-131 Phase 4: Dead code cleanup — Gmail/Calendar remnants

### Removed
- `context_import.py`: Deleted `import_gmail_messages()` and `_format_gmail_messages()` (zero callers)
- `platform_semantics.py`: Deleted `GmailSemanticSignals` class and `extract_gmail_message_signals()` (zero callers)
- `test_adr056_sync.py`: Removed Gmail and Calendar test cases (functions already deleted from worker)
- `slack_client.py`, `notion_client.py`: Cleaned stale GoogleAPIClient references in docstrings
- `platform_sync_scheduler.py`: Removed stale Google split-sync comment

## [2026.03.22.5] - ADR-131 Phase 3: Deep sweep — Gmail/Calendar removal from all code paths

### Changed
- `exporters/__init__.py`: **CRASH FIX** — removed `from .gmail import GmailExporter` (file was already deleted)
- `exporters/resend.py`: Updated docstrings (sole email channel), renamed `generate_gmail_html` → `generate_email_html`
- `platform_output.py`: Renamed `generate_gmail_html` → `generate_email_html`, updated Literal type, section header
- `delivery.py`: Removed Gmail lookup fallbacks, renamed `generate_gmail_html` calls
- `integrations.py`: Deleted CalendarEventResponse/CalendarEventsListResponse models, removed Gmail/Calendar from provider validation, summary endpoint, landscape sync, limit maps, resource type maps
- `agent_pipeline.py`: Deleted gmail/calendar from `_PLATFORM_DIGEST_SIGNALS`, deleted `prepare` role default instruction and prompt template, cleaned synthesize/digest prompts
- `composer.py`: Removed calendar exclusion from gap-filling, cleaned example description
- `notifications.py`: Removed "gmail" from delivery_platform check
- `agent_execution.py`: Updated comment (email via Resend, not gmail exporter)
- `primitives/refresh.py`: Platform enum → slack/notion only, removed Google alias resolution
- `primitives/search.py`: Platform enum → slack/notion only, cleaned memory error message
- `primitives/system_state.py`: Removed gmail/calendar landscape branches, cleaned description
- `primitives/registry.py`: Removed Google metadata extraction, cleaned tool description
- `event_triggers.py`: Cleaned Literal types to slack/notion only
- `execution_strategies.py`: Removed Google platform set and alias matching
- `commands.py`: Deleted entire "prep" command, cleaned platform references in recap/search/sync/research
- `command_embeddings.py`: Deleted prep command embedding, cleaned platform references
- `routes/agents.py`: Cleaned EventTrigger/SourceConfig Literal types, updated PrepareConfig docstring
- `routes/admin.py`: Cleaned platform content loop and limit field mapping
- `routes/system.py`: Cleaned content_platforms and all_platforms lists, removed Google alias resolution
- `routes/memory.py`: Cleaned STYLE_PLATFORM_ALIASES and ALLOWED_STYLE_PLATFORMS
- `workers/platform_worker.py`: Removed Google alias resolution from sync lock/release/main sync, cleaned TTL map

### Expected behavior
- **Crash fix**: Agent generation no longer fails with `No module named 'integrations.exporters.gmail'`
- All tool definitions (Search, RefreshPlatformContent, list_integrations, SystemState) now only expose slack/notion as valid platforms
- Email delivery uses `generate_email_html` (renamed from gmail-specific name)
- No Google/Gmail/Calendar alias resolution anywhere in codebase

---

## [2026.03.22.4] - ADR-130 three-registry architecture — docs sweep

### Changed
- `docs/architecture/agent-framework.md`: Removed seniority system (classify_seniority, ROLE_PORTFOLIOS, SKILL_ENABLED_ROLES), duty mechanics, promotion flow. Replaced with ADR-130 agent type registry — deterministic capabilities per type. Development = knowledge depth, not capability expansion. Gmail/Calendar templates removed (ADR-131).
- `docs/architecture/primitives.md`: RuntimeDispatch → RenderAsset. Gmail/Calendar removed from platform filters, RefreshPlatformContent, list_integrations.
- `docs/architecture/workspace-conventions.md`: RuntimeDispatch → RenderAsset. Duties folder removed. Gmail/Calendar removed from knowledge section.
- `docs/design/COGNITIVE-DASHBOARD-DESIGN.md`: Removed seniority references from InlineProfileCard design.
- `docs/design/SCHEDULER-EVOLUTION.md`: Removed seniority gating from Tier 2. Phase 5 rewritten as type-based cadence (ADR-130), not seniority graduation.
- `docs/design/AGENT-PRESENTATION-PRINCIPLES.md`: Gmail/Calendar removed from source affinity groups, creation flow, icon derivation.
- `docs/design/USER_FLOW_ONBOARDING_V4.md`: Gmail removed from dashboard cards, orchestrator cards, scaffold table.
- `docs/features/context.md`: Gmail/Calendar removed from platform_content schema, TTL table, sync table.
- `docs/features/meeting-prep.md`: Archived — Calendar sunset (ADR-131).
- `docs/features/memory.md`: Gmail removed from preferences example.
- `docs/testing/PRODUCTION_TESTING_PLAYBOOK.md`: RuntimeDispatch → RenderAsset. Gmail removed from type_key table.

### Expected behavior
- All secondary docs now consistent with ADR-130 (three-registry, no seniority) and ADR-131 (Gmail/Calendar sunset).
- No behavioral change — documentation-only updates.

---

## [2026.03.22.3] - ADR-131 Phase 2: Full Gmail/Calendar code removal

### Changed
- `api/agents/tp_prompts/tools.py`: Removed `gmail_digest` from CreateProject examples, updated platform list.
- `api/services/primitives/project.py`: Removed `gmail_digest` from CreateProject type_key descriptions.
- `api/services/platform_tools.py`: Deleted GMAIL_TOOLS, CALENDAR_TOOLS, `_handle_google_tool()`, `_execute_gmail_tool()`, `_execute_calendar_tool()`. Only Slack and Notion tool handlers remain.
- `api/routes/webhooks.py`: Deleted Gmail push notification endpoint and helpers.
- `api/integrations/validation.py`: Deleted `_test_gmail_read()` and Gmail branch.
- `api/jobs/import_jobs.py`: Deleted `process_gmail_import()` and Gmail branch in `process_import_job()`.
- `api/services/working_memory.py`: Removed Calendar synthesis from Gmail platform connection row.
- `api/services/event_triggers.py`: Deleted `GmailEventType` and `handle_gmail_event()`.
- `api/services/platform_content.py`: Deleted `store_gmail_items_batch()`, removed Gmail/Calendar from TTL config, cleaned Google provider normalization.

### Expected behavior
- Zero Gmail/Calendar code paths remain in the runtime. No tool definitions, no event handlers, no sync, no import.
- Platform tools dynamically loaded only for Slack and Notion.

---

## [2026.03.22.2] - ADR-131: Gmail & Calendar sunset — prompt cleanup

### Changed
- `api/agents/tp_prompts/platforms.py`: Removed Gmail/Calendar sections — landing zones, Calendar CRUD workflow, Gmail tool references. Only Slack and Notion remain.
- `api/agents/tp_prompts/tools.py`: Removed Gmail/Calendar from RefreshPlatformContent examples.
- `api/agents/tp_prompts/behaviors.py`: Updated examples (Gmail → Notion), removed Calendar create example, updated platform lists from "Slack/Notion/Gmail" to "Slack/Notion".
- `api/agents/tp_prompts/base.py`: Updated tool usage guidance — removed "creating drafts, managing calendar".
- `api/services/project_registry.py` v1.5: Removed `gmail_digest` project type.

### Expected behavior
- TP no longer references Gmail or Calendar tools or content. Platform guidance scoped to Slack and Notion.
- Bootstrap no longer creates Gmail digest projects.
- Existing Gmail/Calendar platform_content remains in DB but is no longer refreshed or referenced.

---

## [2026.03.22.1] - Fix PM-as-contributor bug + platform project naming — ADR-122

### Changed
- `api/services/project_registry.py` v1.5: PM no longer added to `contributor_records` in `scaffold_project()`. PM is project infrastructure (ADR-122), not a functional contributor — only actual contributor agents appear in PROJECT.md § Contributors. Platform project `display_name` simplified: "Slack Recap" → "Slack", "Gmail Recap" → "Gmail", "Notion Recap" → "Notion". Platform name is the stable identity anchor; agent duties may evolve beyond digest.
- `api/services/agent_execution.py`: `_load_pm_project_context()` Layer 2 structural assessment filters out PM entries (by `expected_contribution == "project coordination"`) from actual contributor count. Safety net for existing projects scaffolded before the registry fix.

### Expected behavior
- New projects: PM created but excluded from PROJECT.md contributors list. Structural assessment sees correct contributor count.
- Existing projects: PM entry in PROJECT.md tolerated — runtime filter prevents false escalation about wrong structure.
- Platform projects named by platform ("Slack"), not by initial duty ("Slack Recap"). Agents may earn duties beyond digest over time.

---

## [2026.03.21.4] - ADR-128: Multi-Agent Coherence Protocol — Phases 0-4 implementation

### Changed
- `api/services/agent_creation.py`: Phase 0 — seed `memory/self_assessment.md` with "awaiting first run" template at agent creation. Add coherence protocol reference to AGENT.md for non-PM contributors.
- `api/services/project_registry.py`: Phase 0 — seed `memory/project_assessment.md` with "PM has not pulsed" template in `scaffold_project()` after PM creation.
- `api/services/agent_pipeline.py`: Phase 1 — added `{mandate_context}` field to all 6 contributor role templates (digest v3, prepare v4, synthesize v5, monitor v2, research v3, custom v2). Added `_ASSESSMENT_POSTAMBLE` requesting `## Contributor Assessment` block with 4 dimensions (mandate, domain fitness, context currency, output confidence). `build_role_prompt()` passes `mandate_context` from config as common field. PM prompt unchanged.
- `api/services/agent_execution.py`: Phase 1 — `_build_mandate_context()` reads project membership + PM brief + last self-assessment from workspace. `_extract_contributor_assessment()` parses `## Contributor Assessment` block from draft output. `_append_self_assessment()` writes rolling history (5 most recent, newest first) to `memory/self_assessment.md`. Assessment extracted and stripped before delivery. Phase 2 — `_load_pm_project_context()` contributor loop now reads `memory/self_assessment.md` (latest entry, 300 chars) and latest `agent_pulsed` activity log event per contributor.
- `api/agents/chat_agent.py`: Phase 3 — PM Chat Prompt v3.0 → v4.0: added "Directive Persistence (ADR-128)" section instructing PM to persist project-level decisions to `memory/decisions.md` via WriteWorkspace. Contributor Chat Prompt v2.0 → v3.0: added analogous section for persisting user directives to `memory/directives.md`.
- `api/services/workspace.py`: Phase 4 — `AgentWorkspace.load_context()` project loop reads PM's `memory/project_assessment.md` (500 chars) and injects as "Project Assessment (from PM)" in contributor context.

### Expected behavior
- New projects: cognitive files seeded at scaffold time with explicit "not yet assessed" state
- Contributor runs: mandate_context injected into prompt, self-assessment block produced and stripped before delivery, rolling history (5 entries) written to workspace
- PM pulses: reads contributor self-assessments + pulse metadata alongside freshness and content — trajectory reasoning enabled
- Meeting room: agents persist durable directives/decisions to workspace files surviving session rotation
- Contributors: read PM's project_assessment.md during execution — know which prerequisite layer constrains the project
- Graceful degradation: non-project agents get empty mandate_context; missing assessment block is non-fatal

---

## [2026.03.21.3] - ADR-128: Multi-Agent Coherence Protocol — documentation phase

### Changed
- `docs/architecture/FOUNDATIONS.md`: v3.4 — Axiom 2 corollary: three intelligence substrates (conversation, filesystem, agent cognition) + four coherence flows. Axiom 3 extension: agent cognitive state (self_assessment.md, directives.md) as developmental mechanism. ADR-128 in relationship table.
- `docs/architecture/agent-execution-model.md`: Pulse→Generation pipeline updated with mandate_context injection (step 3), assessment output (step 5), assessment extraction + stripping (new step 6). PM coordination pulse enriched with self-assessment reading and 5-layer prerequisite walk.
- `docs/architecture/agent-framework.md`: New "Agent Cognitive Architecture (ADR-128)" section — contributor cognitive model (4 dimensions), cognitive files table, initialization at scaffold time, coherence loop diagram, Phase 6 placeholder.
- `docs/architecture/workspace-conventions.md`: Added `self_assessment.md` and `directives.md` to agent workspace tree. Added `decisions.md` to project workspace tree. Updated memory file table with 4 new entries. Updated access patterns with cognitive file writers. Added ADR-128 reference.
- `docs/design/PROJECT-DELIVERY-MODEL.md`: v1.1 — PM heartbeat reads contributor self-assessments alongside freshness. Assembly gating includes cognitive state.
- `docs/design/PROJECTS-PRODUCT-DIRECTION.md`: New settled decision #8: PM as coherence monitor. Memory tab expanded with project_assessment.md and decisions.md.
- `docs/design/USER_FLOW_ONBOARDING_V4.md`: Bootstrap scaffold note — cognitive files seeded at creation with "awaiting first run/pulse" state.
- `docs/features/memory.md`: New "Agent Cognitive Files (ADR-128)" section distinguishing user memory from agent cognitive state.
- `docs/features/sessions.md`: New "Directive and Decision Persistence (ADR-128)" section — how meeting room directives survive session rotation via WriteWorkspace.
- `docs/features/context.md`: New "Agent Cognitive Files — Cross-Agent Context (ADR-128)" section — mandate_context as third context substrate alongside platform and knowledge.
- `docs/adr/ADR-128-multi-agent-coherence-protocol.md`: New ADR — three substrates, four flows, contributor cognitive model, design decisions D1-D4, workspace file conventions, 6 implementation phases.
- `CLAUDE.md`: ADR-128 entry added to ADR reference list.

### Expected behavior
- No runtime behavior changes — this is documentation only
- Establishes canonical reference for multi-agent coherence protocol
- Code implementation follows in subsequent changelog entries (Phases 0-4)

---

## [2026.03.21.2] - PM cognitive model v1.0 — layered prerequisite reasoning + project_assessment.md

### Changed
- `api/agents/chat_agent.py`: PM Chat Prompt v2.0 → v3.0. Replaces flat status dump with 5-layer prerequisite cognitive model: (1) Commitment — is the objective complete?, (2) Structure — right team for the commitment?, (3) Context — right inputs for the objective? (platform connections are supply, not demand), (4) Output Quality — contribution depth/coverage, (5) Delivery Readiness — assembly/budget/work plan. PM stops at the first broken layer. New template fields: `{commitment_assessment}`, `{structural_assessment}`, `{context_assessment}`, `{prior_assessment}`. Communication guidelines: opinionated stance, act-don't-narrate, context-objective fitness over platform enumeration.
- `api/services/agent_pipeline.py`: PM headless prompt v5.0 → v6.0. Same 5-layer model. Every PM JSON response now requires `"project_assessment"` field — structured layered evaluation (constraint_layer, per-layer status). Persisted to `memory/project_assessment.md` as PM's evolving cognitive state. Decision rules rewritten in prerequisite order: commitment → structure → context → quality → readiness. Layer 1-3 gaps → escalate. `build_role_prompt()` PM branch: passes new context fields (`commitment_assessment`, `structural_assessment`, `context_assessment`, `prior_assessment`).
- `api/services/agent_execution.py`: `_load_pm_project_context()` enriched with three new data layers: (1) Commitment assessment — checks objective field completeness (deliverable/audience/format/purpose). (2) Structural assessment — queries project type registry for expected vs actual contributor roles/scopes, detects missing scopes (e.g., cross_platform project with single-platform agents). (3) Context assessment — queries `platform_connections` + `sync_registry` for connected platforms and freshness, evaluates against project scope requirements (cross-platform needs 2+ platforms). Also loads `memory/project_assessment.md` as prior assessment. `_handle_pm_decision()`: extracts `project_assessment` from PM JSON output and writes to `memory/project_assessment.md` as formatted markdown.
- `docs/architecture/workspace-conventions.md`: Added `memory/project_assessment.md` to project folder tree, notes, memory file table, and writer table.

### Expected behavior
- PM reasons through prerequisite layers on every pulse and chat turn — stops at the first broken layer instead of reporting everything at equal weight
- A cross-platform synthesis project with only Slack connected will get Layer 2/3 escalation ("cannot fulfill objective") instead of "Slack data is stale"
- PM's layered assessment persists in `memory/project_assessment.md` — creates evolving cognitive state across pulses
- PM chat responses lead with the constraint layer, not a flat status dump
- Platform connections are evaluated for objective-relevance, not assumed to be context

---

## [2026.03.21.1] - Data surfacing streamline — PM in PROJECT.md, dead DB writes removed, naming unified

### Changed
- `api/services/project_registry.py`: **PM sequencing fix** — PM agent created BEFORE `write_project()` so PM appears in PROJECT.md contributor list. Previously PM was created after, leaving it invisible in Members tab. Registry key `"members"` → `"contributors"` for consistency with PROJECT.md and API. Response key `members_created` → `contributors_created`. Parameter `members_override` → `contributors_override`. Version: v1.4.
- `api/services/agent_creation.py`: **Removed dead DB writes** — `agent_instructions` and `agent_memory` columns no longer written for new agents. Workspace AGENT.md and memory/*.md are sole authority (ADR-106). DB columns kept in schema for lazy migration of pre-workspace agents via `ensure_seeded()`. `AGENT_COLUMNS` set updated to exclude deprecated columns.
- `api/services/composer.py`: `members_created` → `contributors_created` throughout (naming alignment).
- `api/jobs/unified_scheduler.py`: `members_created` → `contributors_created` in Composer result handling.
- `api/services/onboarding_bootstrap.py`: `members_created` → `contributors_created`.
- `api/routes/projects.py`: POST response key `"members"` → `"contributors"`.

### Expected behavior
- PM agents now appear in project Members tab (visible in PROJECT.md contributors section)
- New agents no longer write to deprecated `agent_instructions`/`agent_memory` DB columns — workspace files are sole authority
- Consistent `contributors` terminology across registry, scaffolding, API responses, and workspace

---

## [2026.03.20.12] - ADR-127: TP-level global user_shared/ — working memory awareness + share endpoint

### Changed
- `api/services/working_memory.py`: Added `_get_user_shared_files_sync()` — queries `workspace_files` for global `/user_shared/%` paths (up to 10 files, ordered by updated_at desc). Integrated into `build_working_memory()` as parallel thread query. Added "Your shared files" section to `format_for_prompt()` with filename, summary, and date.
- `api/routes/documents.py`: New `POST /share` endpoint — writes to global `/user_shared/{filename}` with `lifecycle='ephemeral'`, sanitized filename, version increment on overwrite. Uses `ShareFileRequest` (filename + content).
- `web/lib/api/client.ts`: Added `api.documents.shareFile(filename, content)` method calling `POST /api/share`.
- `web/components/desk/ChatFirstDesk.tsx`: Orchestrator PlusMenu "Share a file" action — inline form (filename + content textarea), calls `api.documents.shareFile()`, sends confirmation chat message on success.

### Expected behavior
- TP sees global user_shared/ files in working memory context (up to 10 files)
- Users can share files from Orchestrator chat — files land in global `/user_shared/` with 30-day TTL
- Shared files visible to TP for reference in conversation

---

## [2026.03.20.11] - ADR-127: User-shared file staging — PM prompt v5.0 + triage_file action

### Changed
- `api/services/agent_pipeline.py`: PM prompt v4.0 → v5.0. Added `{user_shared_files}` context field. Added `triage_file` action (8th action) with promote/ignore semantics. Decision rule: "If user_shared/ files are present, triage them before other actions — user contributions deserve prompt attention."
- `api/services/agent_pipeline.py`: `build_role_prompt()` PM branch: formats `user_shared_files` context with "USER-SHARED FILES (triage needed)" header, empty string when no files.
- `api/services/agent_execution.py`: `_load_pm_project_context()` now lists `user_shared/` files with 300-char content excerpts. Returns `user_shared_files` field.
- `api/services/agent_execution.py`: `_handle_pm_decision()` routes `triage_file` action — reads source from `user_shared/`, writes to destination (contributions/memory/knowledge), logs `project_file_triaged` activity event.
- `api/services/activity_log.py`: Added `project_file_triaged`, `project_contributor_steered`, `project_quality_assessed` to `VALID_EVENT_TYPES` (latter two were used but missing from registry).
- `api/routes/projects.py`: New `POST /projects/{slug}/share` endpoint — writes sanitized filename to `user_shared/` with ephemeral lifecycle.

### Expected behavior
- PM sees user-shared files in context and triages them before other actions
- Files shared by users land in `user_shared/` with 30-day TTL
- PM can promote files to contributions/memory/knowledge or ignore them
- `project_file_triaged` events appear in Meeting Room timeline

---

## [2026.03.20.10] - ADR-126 Phase 5: Role-based pulse cadence + Composer pulse integration

### Changed
- `api/services/agent_framework.py`: Added `ROLE_PULSE_CADENCE` registry — role-based sensing frequency (monitor=15min, pm=30min, digest=12h, synthesize/research/custom=schedule-derived). Added `get_pulse_cadence()` accessor.
- `api/services/agent_pulse.py`: `calculate_next_pulse_at()` now uses role cadence from `ROLE_PULSE_CADENCE` instead of always using schedule. Fixed-interval roles (monitor, pm, digest, prepare) pulse independently of delivery schedule.
- `api/services/composer.py`: `heartbeat_data_query()` replaced N+1 per-agent `agent_runs` queries with (a) single batch query for maturity signals and (b) pulse event read from `activity_log` for agent health. Added `pulse_health` to assessment dict. `should_composer_act()` gained `pulse_escalation` heuristic (reads `agent_pulsed` escalation events), replaced `stale_agents` heuristic (agents now self-report via pulse).
- `api/services/agent_creation.py`, `api/services/project_registry.py`: Migrated from `calculate_next_run_from_schedule` to `calculate_next_pulse_from_schedule`.
- `api/jobs/unified_scheduler.py`: Deleted backwards-compat alias `calculate_next_run_from_schedule`.
- Architecture docs: 6 docs updated to replace `next_run_at` → `next_pulse_at`, pre-pulse scheduler descriptions → pulse dispatcher model.
- `docs/architecture/agent-framework.md`: Added full Pulse section (three-tier funnel, role cadence table, decision taxonomy, visibility model). Updated Trigger axis with ADR-126 generalization note.

### Expected behavior
- Monitor agents pulse every 15 min, PM agents every 30 min — regardless of delivery schedule
- Digest/prepare agents pulse every 12h (twice per daily delivery cycle)
- Synthesize/research/custom agents pulse on their configured schedule
- Composer reads agent pulse events for escalation detection instead of computing staleness top-down
- Maturity computation is batch (1 query per user) instead of N+1 per agent

---

## [2026.03.20.9] - ADR-126: Agent Pulse implementation — Phases 1-4

### Changed
- `api/services/agent_pulse.py` (NEW): Core pulse engine. `run_agent_pulse()` → `PulseDecision`. Three-tier funnel: Tier 1 (deterministic gates, zero LLM), Tier 2 (Haiku self-assessment, associate+ seniority), Tier 3 (PM coordination, reframes existing `_handle_pm_decision`). Absorbs all logic from deleted `proactive_review.py`.
- `api/services/proactive_review.py` (DELETED): All logic absorbed into `agent_pulse.py` Tier 2.
- `api/jobs/unified_scheduler.py`: Rewritten as pulse dispatcher. `get_due_agents()` → `get_due_pulse_agents()`. Main loop calls `run_agent_pulse()`, acts on decision (generate → `process_agent()`, observe/wait/escalate → log only). Deleted: `get_due_proactive_agents()`, `process_proactive_agent()`, `should_skip_agent()`. Summary stats now pulse-aware (gen/obs/wait/esc).
- `api/services/composer.py`: Deleted `_run_supervisory_review()` and `_get_due_supervisory_agents()` (Phase 4 thinning). Removed Step 4 supervisory loop from `run_heartbeat()`. Composer heartbeat now focuses purely on workforce composition.
- `api/services/agent_execution.py`: Added `pm_pulsed` event logging in `_handle_pm_decision()` (Tier 3). Updated trigger context handling: `proactive_review` → `pulse_generate`.
- `api/services/activity_log.py`: Added `agent_pulsed` and `pm_pulsed` to `VALID_EVENT_TYPES`.
- `api/test_adr092_modes.py`: Phase 3 rewritten to test `_apply_pulse_decision()` with `PulseDecision` objects + workspace verification (not `agent_memory` JSONB). Phase 5 updated for `_parse_pulse_response`.
- `supabase/migrations/124_agent_pulse.sql` (NEW): `next_run_at` → `next_pulse_at`, drops `proactive_next_review_at`, replaces `get_due_agents` RPC with `get_due_pulse_agents` (queries ALL active agents, no mode filter).
- ~19 files: `next_run_at` → `next_pulse_at` rename across API, frontend, and tests.

### Expected behavior
- Every agent gets a pulse on schedule — autonomous sense→decide cycle upstream of execution
- ~80% of pulses resolve at Tier 1 (zero LLM cost): budget check, content freshness, first-run detection
- Associate+ agents get Tier 2 (Haiku self-assessment): domain-scoped, reads workspace context
- PM agents log `pm_pulsed` events (Tier 3) for Composer/dashboard visibility
- Scheduler dispatches ALL active agents (not mode-filtered) — pulse engine handles mode-specific logic
- Composer heartbeat is thinner: no per-agent supervisory review, just workforce composition

---

## [2026.03.20.8] - Project-native Orchestrator: 3+1 cards, bootstrap→projects

### Changed
- `web/components/desk/ChatFirstDesk.tsx`: PROJECT_TEMPLATES slimmed from 6 cards (3 aspirational) to 4 registry-backed cards: Slack Recap, Gmail Recap, Notion Recap, New Project. Meeting Prep / Work Summary / Proactive Insights removed — no registry backing. CAPABILITY_TEMPLATES slimmed from 3 to 2 (removed "Ask anything"). Bootstrap banner now polls projects (not agents) and links to `/projects/{slug}` Meeting Room (not `/agents/{id}`). Bootstrap filter IDs fixed (`gmail-digest` → `gmail-recap`, `notion-summary` → `notion-recap`, `gmail` → `google`). Removed unused imports (Brain, Agent type).
- `docs/design/USER_FLOW_ONBOARDING_V4.md`: Full rewrite to v6 — project-native onboarding. Documents 3+1 card model, bootstrap→project flow, Meeting Room as post-creation surface, project-level onboarding philosophy (context + objective in one PM conversation).

### Expected behavior
- Orchestrator empty state shows only what the system can deliver deterministically: 3 platform project cards + 1 custom project card
- Bootstrap banner says "View project →" and links to Meeting Room, not agent page
- "New Project" card routes to TP chat for custom project creation, which then points user to Meeting Room
- Plus menu "Create project" shows the same 4 cards
- No aspirational cards that send freeform prompts without registry backing

---

## [2026.03.20.7] - ADR-126: Agent Pulse — Composer prompt evolution path

### Planned (implementation phases)
- **Phase 1 — `agent_pulse.py`**: New pulse decision engine. Tier 1 (deterministic: fresh content? budget? recent run?) → Tier 2 (Haiku self-assessment for associate+ agents) → decision: generate | observe | wait | escalate. Agent prompt: domain-scoped self-assessment (Haiku, ~200 tokens context). PM prompt: Tier 3 coordination pulse (assemble | steer | advance_contributor | assess_quality | wait | escalate).
- **Phase 2 — Scheduler becomes pulse dispatcher**: `unified_scheduler.py` dispatches pulses (not executions). `agents.next_run_at` → `agents.next_pulse_at`. On "generate" decision → existing `dispatch_trigger()` pipeline. On other decisions → log activity, update workspace observations.
- **Phase 3 — Composer thins to portfolio-only**: Composer reads pulse outcomes from `activity_log` instead of reimplementing per-agent assessment. Heartbeat assessment shrinks from ~1000 lines to ~300. Portfolio decisions only: create/dissolve projects, rebalance workforce.
- **Phase 4 — Proactive/coordinator dissolution**: Proactive self-assessment generalized to all agents via Tier 2 pulse. Coordinator mode dissolved — PM Tier 3 pulse handles project coordination. Existing coordinator agents pulse as proactive.
- **Phase 5 — Pulse cadence evolution**: New agents pulse on schedule (training wheels). Senior agents pulse every cycle (always sensing). Seniority-based cadence graduation.

### Expected behavior (end state)
- Every agent has a pulse — autonomous sense→decide cycle upstream of execution
- Pulse events (`agent_pulsed`, `pm_pulsed`) visible in activity log, project meeting rooms, timelines
- Composer complexity dramatically reduced — reads bottom-up agent intelligence instead of reimplementing it
- Schedule becomes delivery cadence (project-level, PM-coordinated), not execution trigger
- Three distinct concerns: pulse cadence (agent), generation decision (agent pulse), delivery timing (PM + project)

### Prompt versions affected (planned)
- Agent self-assessment prompt: NEW (Haiku, Tier 2 — ~200 token context, domain-scoped)
- PM coordination prompt: v5.0 (Tier 3 pulse — senses project state, coordination decisions)
- Composer prompt: v3.0 (portfolio-only — reads pulse outcomes, thins assessment logic)
- TP heartbeat assessment: DEPRECATED (replaced by Composer reading pulse outcomes)

---

## [2026.03.20.6] - PM for all projects + delivery model update

### Changed
- `api/services/primitives/project.py`: CreateProject tool description updated — all projects now create PM agent, removed "no PM needed" for platform types.
- `api/services/agent_pipeline.py`: PM prompt unchanged but now applies to all project types including single-agent platform digests.

### Expected behavior
- CreateProject always scaffolds PM agent alongside member agents
- PM passthrough: single-contributor projects skip LLM composition, deliver content directly
- No change to PM prompt — PM will see single contributor and handle accordingly
- TP/Composer should stop saying "no PM needed" for platform projects

---

## [2026.03.20.5] - Agent chat: PM role gate for coordination primitives

### Changed
- `api/agents/chat_agent.py`: `tool_executor` now enforces PM-only write primitives at runtime. `RequestContributorAdvance` and `UpdateWorkPlan` return `not_authorized` for non-PM agents. Read primitives (`ReadProjectStatus`, `CheckContributorFreshness`) remain open to all agent_chat agents.

### Expected behavior
- Contributors can check project status and contributor freshness in meeting rooms (read is open)
- Only PM agents can advance contributor schedules or update work plans (coordination is PM-only)
- Matches the principle: anyone can check the board, only PM moves the tickets

---

## [2026.03.20.4] - Primitive cleanup: remove dead weight, fix bugs

### Removed
- `api/services/primitives/todo.py`: Todo primitive removed entirely. Conversation stream is the progress indicator (Claude Code pattern).
- `api/services/primitives/execute.py`: `agent.approve` action + handler removed (ADR-066 removed approval gates; handler had undefined `run_id` bug). `memory.extract` action removed (ADR-064 moved to nightly cron; no handler existed).
- `api/services/primitives/registry.py`: Respond tool definition + handler deleted (was already excluded from PRIMITIVES).
- `api/services/primitives/search.py`: Dead `_search_user_memories()` function removed (unreachable). Dead `memory` entry removed from `SEARCH_FIELDS`.

### Changed
- `api/services/primitives/execute.py`: Tool description updated — removed references to deleted actions, fixed outdated `platform.sync` example.

### Expected behavior
- TP tool surface reduced from 27 to 25 primitives. Execute actions reduced from 6 to 4. No functional impact — all removed items were dead code.

---

## [2026.03.20.3] - ADR-125: Project-Native Session Architecture

### Changed
- `api/routes/chat.py`: Two-path session routing (project or global TP). Agent requests resolve to project sessions via `resolve_agent_project()`. `thread_agent_id` on messages for 1:1 agent threads within project sessions. Project session 24h inactivity rotation (was lifetime). Author-aware summarization for project sessions.
- `api/services/session_continuity.py`: Added `generate_project_session_summary()` — author-aware summaries that attribute decisions to specific agent participants.
- `api/services/working_memory.py`: `_get_recent_sessions_sync()` now includes `project_slug` on session summaries. Rendering tags project summaries with project name. Fixed `_build_system_reference()` to use `"members"` key (registry rename).

### Expected behavior
- Agent page chats now resolve to the project session with thread filtering — agent identity enriched by project context.
- Project sessions rotate after 24h inactivity instead of persisting forever.
- Global TP sees cross-project session summaries ("2026-03-20: PM steered Slack Agent... (slack-recap)")
- `chat_sessions.agent_id` deprecated — new code uses project sessions with thread_agent_id.

---

## [2026.03.20.2] - CreateProject tool: type_key delegates to scaffold_project()

### Changed
- `api/services/primitives/project.py`: CreateProject tool definition now includes `type_key` parameter with available types listed. Description updated to explain two modes: platform project (type_key → scaffold_project, creates agents automatically) vs custom project (manual contributors). When type_key matches registry, `handle_create_project()` delegates to `scaffold_project()` instead of manual PROJECT.md creation.

### Expected behavior
- TP can now create platform projects (slack_digest, notion_digest, gmail_digest) with a single tool call that creates both the project AND its member agent(s). No more orphaned projects without agents.
- Tool description tells TP not to ask follow-up questions for platform digest projects — just use the type_key.

---

## [2026.03.20.1] - TP System Reference — meta-awareness of YARNNN capabilities

### Changed
- `api/services/working_memory.py`: Added `_build_system_reference()` — programmatically generates a "System reference" section from `PROJECT_TYPE_REGISTRY`, `ROLE_PORTFOLIOS`, `SKILL_ENABLED_ROLES`, and connected platforms. Injected into working memory and rendered in `format_for_prompt()`.
- `api/agents/tp_prompts/behaviors.py`: Replaced static type table with reference to System Reference in working memory. Added explicit guidance: platform projects are 1:1 (don't offer multiple options), check platform→project type mapping.
- `api/agents/tp_prompts/tools.py`: Rewrote CreateProject section to reference Project Type Registry. Clarified when to use CreateProject vs CreateAgent. Added `type_key` as primary parameter.

### Expected behavior
- TP now knows exactly which project types exist and which platform maps to which type — stops improvising redundant options (e.g., offering 3 Notion choices when only `notion_digest` exists).
- As new project types are added to the registry, TP automatically sees them without prompt editing.
- Connected platform→project type mapping is dynamic — TP adapts to each user's connected platforms.
- Agent roles and duty portfolios visible to TP for accurate creation guidance.

---

## [2026.03.19.14] - ADR-124 Phase 3: Live project context injection in ChatAgent prompts

### Changed
- `api/agents/chat_agent.py`: PM Chat Prompt v1.0 → v2.0 — now receives live project context (project overview, contributor freshness, work plan, budget status) via `_load_pm_project_context()` reuse. Contributor Chat Prompt v1.0 → v2.0 — receives project objective + own expected contribution from PROJECT.md.
- `api/agents/chat_agent.py`: `execute_stream_with_tools` loads role-appropriate project context before building system prompt. PM path calls `_load_pm_project_context()` (singular implementation — same loader as headless). Contributor path reads PROJECT.md via `ProjectWorkspace.read_project()` and extracts objective + contribution brief.

### Expected behavior
- PM agents in meeting room now answer with awareness of project status, contributor freshness, work plan, and budget — previously had no project context beyond workspace files.
- Contributor agents now see the project objective and their expected contribution — previously only had generic scope description.
- Graceful degradation: if context loading fails, prompts fall back to defaults ("Not available", "Not specified").

---

## [2026.03.19.13] - ADR-124 Phase 2: Meeting Room frontend — attributed messages + @-mention

### Changed
- `web/types/desk.ts`: TPMessage gains `authorAgentId`, `authorAgentSlug`, `authorRole`, `authorName` fields. UPDATE_STREAMING_MESSAGE action extended with author fields.
- `web/contexts/TPContext.tsx`: `sendMessage` accepts `targetAgentId` in context param, sent as `target_agent_id` in API body. Handles `stream_start` SSE event for author attribution. History reconstruction reads author metadata from stored messages.
- `web/app/(authenticated)/projects/[slug]/page.tsx`: TimelineTab replaced with MeetingRoomTab — attributed message bubbles (color-coded by role: PM purple, contributor blue, user primary), @-mention picker (type @ to target specific agent), target agent indicator above input. Tab renamed "Timeline" → "Meeting Room".
- `web/types/index.ts`: ProjectContributor gains `title?` and `role?` fields.
- `api/routes/projects.py`: GET /projects/{slug} enriches contributors with agent title/role from agents table for meeting room participant panel.

### Expected behavior
- Project page default tab is now "Meeting Room" instead of "Timeline".
- Message bubbles show author name (PM, contributor agent names) with role-appropriate color accents.
- Typing @ in chat input opens a mention picker showing project contributors.
- Selecting a contributor sets `target_agent_id` on the message — backend routes to that agent's ChatAgent.
- Without @-mention, messages still default to PM (Phase 1 backend behavior).
- Historical messages loaded from session show correct author attribution from stored metadata.

---

## [2026.03.19.12] - ADR-124 Phase 1: ChatAgent class + agent_chat mode + routing

### Changed
- `api/agents/chat_agent.py` (NEW): ChatAgent class — enables agents to participate in project meeting room conversations. Two prompt templates: PM Chat Prompt v1.0 (coordinator persona, PM primitives) and Contributor Chat Prompt v1.0 (domain specialist persona, read-heavy). Inherits from BaseAgent, uses `agent_chat` mode tools.
- `api/services/primitives/registry.py`: Added `"agent_chat"` as third primitive mode. 13 primitives enabled: workspace read/write/search/list, QueryKnowledge, DiscoverAgents, ReadAgentContext, Clarify, ReadProject, and 4 PM execution primitives.
- `api/routes/chat.py`: ChatRequest gains `target_agent_id` field. Project-scoped sessions route to ChatAgent when target_agent_id is set or defaults to PM. SSE stream emits `stream_start` event with author attribution. Assistant messages stored with `metadata.author_agent_id`, `metadata.author_agent_slug`, `metadata.author_role`. Done event includes author fields.

### Expected behavior
- In project meeting rooms, plain messages route to PM agent (default interlocutor).
- `@agent-slug` mentions (frontend sends `target_agent_id`) route to the specific agent.
- Agent responses stream with author attribution — frontend can render attributed bubbles.
- Slash commands (`/` prefix) continue routing to TP as before.
- Outside project sessions, all behavior is unchanged.

---

## [2026.03.19.11] - ADR-123 Phase 3: Frontend objective editing + PM intelligence surfacing

### Changed
- `api/routes/projects.py`: GET /projects/{slug} returns `pm_intelligence` (quality_assessment markdown + per-contributor briefs). `PROJECT_EVENT_TYPES` extended with `project_quality_assessed`, `project_contributor_steered`.
- `web/lib/api/client.ts`: Added `projects.update()` method (PATCH /api/projects/{slug}).
- `web/types/index.ts`: Added `PMIntelligence` interface. `ProjectDetail` extended with `pm_intelligence` field.
- `web/app/(authenticated)/projects/[slug]/page.tsx`: Objective section is now editable (inline form, saves via PATCH). PM quality assessment shown at top of Contributors tab. Per-contributor PM briefs shown when contributor expanded. Timeline renders `project_quality_assessed` and `project_contributor_steered` events.

### Expected behavior
- User can edit project objective directly from project detail page header (hover → pencil icon → inline form → save).
- Contributors tab shows PM quality assessment summary at top, per-contributor briefs inside expanded sections.
- Timeline shows PM quality assessment and steer events with structured metadata display.

---

## [2026.03.19.10] - ADR-123: Project Objective & Ownership Model — Phase 1-2

### Changed
- `api/services/workspace.py`: `read_project()` returns `objective` (was `intent`), accepts both `## Objective` and `## Intent` headers for migration. `write_project()` param renamed `intent` → `objective`, writes `## Objective` section. `## Intentions` section parsed as `legacy_intentions` for migration, no longer written. Backward-compat derivation deleted.
- `api/services/agent_pipeline.py`: PM prompt v4.0 — `{intentions}` field removed (operational planning in work_plan only), all `intent` refs → `objective`. Assembly composition prompt v3.0 — `{intent}` → `{objective}`.
- `api/services/agent_execution.py`: `_load_pm_project_context()` returns `objective` field (was `intent`), no longer returns `intentions` field. Legacy intentions auto-migrated to `memory/work_plan.md` on first PM run. Assembly composition uses `objective` field.
- `api/services/primitives/project_execution.py`: `UpdateProjectIntent` → `UpdateWorkPlan`. Writes assembly_spec/delivery to PROJECT.md, work_plan to PM's `memory/work_plan.md`. Singular operational substrate.
- `api/services/primitives/project.py`: CreateProject tool schema `intent` → `objective`. Handler accepts both for transition.
- `api/services/primitives/registry.py`: `UpdateProjectIntent` → `UpdateWorkPlan` in PRIMITIVES, HANDLERS, PRIMITIVE_MODES.
- `api/services/project_registry.py`: All 5 registry entries `intent` → `objective`. `scaffold_project()` param `intent_override` → `objective_override`.
- `api/services/composer.py`: Composer prompt example uses `objective`. `_execute_create_project()` reads `objective` (accepts `intent` fallback).
- `api/services/working_memory.py`: Project scope uses `objective` (was `intent`).
- `api/routes/projects.py`: `ProjectIntent` → `ProjectObjective`. Create/update handlers use `objective`.
- `api/routes/chat.py`: Project surface context uses `objective`.
- `web/types/index.ts`: `ProjectDetail.project.intent` → `.objective`.
- `web/app/(authenticated)/projects/[slug]/page.tsx`: Renders `objective` fields.

### Expected behavior
- PROJECT.md is the charter (objective, contributors, assembly_spec, delivery) — owned by User/Composer/TP.
- PM memory/ is the operational plan (work_plan, quality_assessment) — owned by PM.
- PM no longer receives `{intentions}` template field — reads work_plan from memory.
- Legacy PROJECT.md files with `## Intent` and `## Intentions` auto-migrate on read/PM run.
- `UpdateWorkPlan` primitive writes operational planning to PM's `memory/work_plan.md`, not PROJECT.md.

---

## [2026.03.19.9] - ADR-121: Steer path validated end-to-end

### Validated
- PM Intelligence Director steer path confirmed in production (PM v6→v9)
- `assess_quality` → `steer_contributor` → brief.md written → contributor advanced → contributor re-ran with brief injected → output updated via contribution bridge
- Two bugs found and fixed during validation: brace-balanced JSON parser (2026.03.19.7), quality assessment injection (2026.03.19.8b)
- ADR-121 updated with production validation section

### Expected behavior
- PM correctly chooses `steer_contributor` when prior assessment shows `needs_steering` verdict
- Brief appears in contributing agent's context as "PM Directive (brief)"
- Contribution bridge writes agent output back to project workspace after delivery

---

## [2026.03.19.8] - ADR-122: Project Type Registry — unified scaffolding layer

### Changed
- NEW `api/services/project_registry.py`: Project Type Registry v1.0 — curated dict of project type definitions (slack_digest, gmail_digest, notion_digest, cross_platform_synthesis, custom). Access functions: `get_project_type()`, `get_platform_project_type()`, `list_project_types()`. Unified `scaffold_project()` replaces all scattered creation paths.
- `api/services/onboarding_bootstrap.py`: REWRITTEN — `maybe_bootstrap_agent()` → `maybe_bootstrap_project()`. Deleted `BOOTSTRAP_TEMPLATES` dict. Now a thin caller of `scaffold_project()`.
- `api/services/composer.py`: Deleted `PLATFORM_DIGEST_TITLES` dict and `_create_digest_for_platform()` function. Gap-filling now uses `scaffold_project()`. Lifecycle expansion (senior digest → synthesis) now uses `scaffold_project("cross_platform_synthesis")`. Coverage detection rewritten: checks `type_key` in PROJECT.md instead of agent title heuristics. Assessment keys renamed: `platforms_with_digest` → `platforms_with_coverage`, `platforms_without_digest` → `platforms_without_coverage`.
- `api/services/workspace.py`: `write_project()` accepts `type_key` param, writes `**Type**: {type_key}` to PROJECT.md. `read_project()` parses `type_key` field.
- `api/services/primitives/project.py`: `handle_create_project()` accepts and passes `type_key` to `write_project()`.
- `api/workers/platform_worker.py`: Calls `maybe_bootstrap_project()` instead of `maybe_bootstrap_agent()`.

### Expected behavior
- All project creation (bootstrap, Composer gap-fill, Composer lifecycle expansion, TP CreateProject, API routes) flows through one path: `scaffold_project()`.
- Platform types (slack_digest, gmail_digest, notion_digest) enforce 1:1 uniqueness per platform per user via `type_key` in PROJECT.md.
- Single-agent platform projects have `pm: False` — no PM overhead, agent output IS the deliverable.
- Multi-agent projects (cross_platform_synthesis, custom) have `pm: True` — PM auto-created.
- Bootstrap now creates projects (not standalone agents): OAuth → sync → `scaffold_project(type_key)` → project with agent inside.

---

## [2026.03.19.7] - Fix P0: PM JSON parser brace-balanced extraction (ADR-121)

### Changed
- `api/services/agent_execution.py`: Replaced simple regex `[^{}]*` JSON extraction with brace-balanced parser. The old regex couldn't match nested objects (e.g., `assess_quality` with `assessments` array containing inner `{}`), causing PM's intelligent decisions to fall through to the keyword inference fallback. Production PM v5 correctly chose `assess_quality` with detailed assessments, but the parser failed to extract it and defaulted to `assemble`.

### Expected behavior
- PM decisions with nested JSON structures (assess_quality assessments, update_work_plan with contributors array) are now correctly parsed even when PM writes narrative preamble before the JSON.
- Keyword fallback is truly last-resort, not the default path for complex decisions.

---

## [2026.03.19.6] - ADR-121 Phase 2: Contribution bridge + assembly gating + work plan focus areas

### Changed
- `api/services/agent_execution.py`: New `_write_contribution_to_projects()` — after agent delivery, writes output to `/projects/{slug}/contributions/{agent_slug}/output.md` for every project the agent belongs to. **This closes the critical gap**: PM can now read actual contribution content because it exists in the project workspace.
- `api/services/agent_execution.py`: Assembly gating log — PM assembly now logs whether a quality assessment exists before proceeding. Informational, not blocking (PM prompt v3.0 already guides assess-before-assemble behavior).
- `api/services/agent_execution.py`: `update_work_plan` handler now includes `focus_areas` per contributor in work plan markdown. PM v3.0 prompt outputs focus areas in its work plan JSON.

### Expected behavior
- After any non-PM agent delivers, its output is automatically written to all projects it belongs to. PM's next run will see actual content (not empty contributions).
- PM can now meaningfully assess quality because `/projects/{slug}/contributions/{agent_slug}/output.md` contains real content.
- Work plans show per-contributor focus areas, enabling directed follow-up.
- No behavior changes for agents that aren't in projects.

---

## [2026.03.19.5] - ADR-121 Phase 1: PM prompt v3.0 (Intelligence Director) + Assembly prompt v2.0

### Changed
- `api/services/agent_pipeline.py` ROLE_PROMPTS["pm"]: **v2 → v3.0** — PM reframed as "Intelligence Director" (not logistics coordinator). Two new actions: `assess_quality` (evaluate contributions for coverage/depth/differentiation against intent) and `steer_contributor` (write specific brief + advance agent). Prompt now instructs PM to assess quality before assembling, steer overlapping/thin contributions, and reason about what the project needs. Title in prompt changed from "Project Manager" to "Intelligence Director". Decision rules updated: prefer assess_quality before assemble, steer rather than blindly advance.
- `api/services/agent_pipeline.py` ASSEMBLY_COMPOSITION_PROMPT: **v1 → v2.0** — Now intent-first (organize by audience questions, not by contributor). Includes `{quality_notes}` field from PM assessment. Gap acknowledgment: thin topics noted as "areas for deeper investigation" rather than padded. Attribution to source data rather than contributor agent names.
- `api/services/agent_execution.py` `_handle_pm_decision()`: Routes two new actions — `steer_contributor` (writes brief.md via ProjectWorkspace, then advances contributor) and `assess_quality` (writes quality_assessment.md, logs verdicts). Both emit activity events.
- `api/services/agent_execution.py` `_load_pm_project_context()`: PM now receives contribution content excerpts (first 500 chars per file) alongside freshness status, plus any active PM briefs. Enables quality reasoning.
- `api/services/agent_execution.py` `_execute_pm_assemble()`: Reads `memory/quality_assessment.md` and injects into composition. Filters out `brief.md` from contributions (directives, not content).
- `api/services/workspace.py` `ProjectWorkspace`: Added `write_brief()` and `read_brief()` methods for PM steering directives at `/contributions/{slug}/brief.md`.
- `api/services/workspace.py` `AgentWorkspace.load_context()`: Contributing agents now read PM briefs during context gathering (injected as "PM Directive" alongside project context).

### Expected behavior
- PM will now assess contribution quality before deciding to assemble, instead of using freshness as the sole gate.
- PM can steer contributors with specific directives (what to focus on, what's missing, how they fit the assembly).
- Contributing agents see PM briefs as part of their execution context, shaping their next output.
- Assembly composition is intent-driven: organized by audience needs, acknowledges gaps, avoids repetition.
- All existing PM actions (assemble, advance_contributor, wait, escalate, update_work_plan) continue to work unchanged.

### PM Prompt Version History
| Version | Date | Description |
|---------|------|-------------|
| v1.0 | ADR-120 P1 | Logistics: freshness + assemble/wait/escalate |
| v1.1 | ADR-120 P4 | + intentions, budget awareness, work plan |
| v1.2 | 2026-03-19 | + CRITICAL JSON enforcement, resilient parsing |
| **v3.0** | 2026-03-19 | Intelligence Director: quality assessment, steering, contribution content (ADR-121 P1) |

---

## [2026.03.19.4] - ADR-121: PM prompt versioning policy + intelligence director proposal

### Changed
- `docs/adr/ADR-121-pm-intelligence-director.md`: New ADR proposing PM evolution from logistics coordinator to intelligence director. Establishes PM prompt versioning as independent artifact (v1.0 → v2.0), mechanics vs. intelligence separation, new actions (`steer_contributor`, `request_investigation`, `assess_quality`), contribution briefs mechanism.
- `docs/architecture/FOUNDATIONS.md`: Added ADR-121 to alignment table. ADR-120 status updated to Implemented. Added open question #11 (PM qualitative intelligence) as addressed by ADR-121.
- `CLAUDE.md`: Added ADR-121 reference to ADR catalog.

### Expected behavior
- No runtime changes — this is a documentation/architecture proposal. PM prompt v2.0 implementation will follow in ADR-121 Phase 1.
- Establishes the principle that PM prompt changes are versioned independently from code changes, tracked in this CHANGELOG with their own version numbers.

---

## [2026.03.19.3] - TP prompt: CreateProject documentation + PM type_config fix

### Changed
- `api/agents/tp_prompts/tools.py`: Added "Creating Projects (ADR-120)" section documenting CreateProject tool — title, intent (with format field), contributors (UUID/title/slug), assembly_spec, delivery. Explains when to use projects vs. individual agents.
- `api/services/agent_execution.py`: Fixed NameError in PM decision path — `type_config` was referenced in `execute_agent_generation()` scope but only defined in `generate_draft_inline()`. Changed to `agent.get("type_config", {})` at point of use.
- `api/services/primitives/project.py`: CreateProject contributor resolution now supports three-tier lookup: UUID → title ilike → slug derivation match. Previously only UUID worked, but Orchestrator passes titles/slugs.

### Expected behavior
- Orchestrator can now directly call CreateProject when user asks for multi-agent projects, instead of spending tool rounds searching without acting.
- PM agent runs no longer crash with NameError on all executions.
- Contributors are resolved regardless of how the LLM references them (UUID, title, or slug).

---

## [2026.03.19.2] - Project-scoped working memory injection (ADR-119 P4b)

### Changed
- `api/services/working_memory.py`: `build_working_memory()` accepts optional `project_slug` parameter. When provided, calls `_extract_project_scope()` which reads PROJECT.md (title, intent, contributors, status), recent assemblies, and work plan snippet from workspace.
- `api/services/working_memory.py`: `format_for_prompt()` renders "### Current project: {title}" section with purpose, deliverable, contributors, recent assemblies, and work plan.
- `api/agents/thinking_partner.py`: Passes `scoped_project_slug` from chat parameters to `build_working_memory()`.
- `api/routes/chat.py`: Extracts `projectSlug` from `SurfaceContext`, creates project-scoped sessions via `get_or_create_project_session()` (persists for project lifetime, no 4h rotation), adds `project-detail` handler in `load_surface_content()`.
- Expected behavior: When user chats from a project page, TP receives project context (title, intent, contributors, assemblies, work plan) in its system prompt. Separate sessions per project, persisting for project lifetime.

---

## [2026.03.19.1] - Composer v2.1: promote_duty action + seniority rename (ADR-117 Phase 3)

### Changed
- `api/services/composer.py`: `COMPOSER_SYSTEM_PROMPT` v2.0 → v2.1 — added `promote_duty` action (agent_id, new_duty), portfolio validation rules. Seniority rename: nascent→new, developing→associate, mature→senior throughout all prompt text and heuristics.
- `api/services/composer.py`: `should_composer_act()` — added `duty_promotion` heuristic: senior agents eligible for expanded duties per `ROLE_PORTFOLIOS`. Lifecycle handler routes `duty_promotion` trigger to deterministic `_execute_promote_duty()`.
- `api/services/composer.py`: Maturity classification now delegates to `classify_seniority()` from `agent_framework.py` instead of inline if/elif.
- `api/services/composer.py`: Assessment dict key rename: `mature_agents` → `senior_agents`. All references updated.
- Expected behavior: Composer now autonomously promotes senior agents along pre-configured career tracks. A digest agent with 10+ runs and 80%+ approval gains monitor duty.

---

## [2026.03.18.13] - Composer v2.0: project awareness + skill library + PM delegation (ADR-120 Phase 5)

### Changed
- `api/services/composer.py`: `COMPOSER_SYSTEM_PROMPT` v1.3 → v2.0 — added `create_project` action (title, intent, contributors, assembly_spec, delivery), replaced generic "Output Capabilities" with concrete 8-skill library (pdf, pptx, xlsx, chart, mermaid, image, data, html), added Projects section explaining cross-agent collaboration, added budget awareness principle.
- `api/services/composer.py`: `_build_composer_prompt()` extended with Active Projects, Work Budget, and Skill Library sections via `_format_projects_section()` and `_format_budget_section()` helpers.
- `api/services/composer.py`: `_execute_composer_decisions()` routes `create_project` to new `_execute_create_project()` — resolves contributor slugs from assessment, calls `handle_create_project()` primitive (auto-creates PM agent).
- `api/services/composer.py`: `should_composer_act()` — composition opportunity heuristic: 2+ mature agents with different roles and no project triggers LLM path.

### Expected behavior
- Composer can now autonomously propose project creation when it detects agents producing complementary outputs.
- Composer sees full skill library and can reference specific skills in agent instructions and project assembly specs.
- Budget-exhausted state suppresses new agent/project proposals (observe, don't create).
- `create_project` flows through existing `handle_create_project()` primitive — PM agent auto-created, contributor workspaces seeded.

---

## [2026.03.18.12] - Intent decomposition & project intentions (ADR-120 Phase 4)

### Changed
- `api/services/agent_pipeline.py`: PM role prompt v2 — added `{intentions}`, `{budget_status}` template fields, `update_work_plan` as 5th PM action, budget-aware decision rules.
- `api/services/agent_pipeline.py`: PM validation now accepts `update_work_plan` action; requires `work_plan` object.
- `api/services/workspace.py`: `read_project()` parses `## Intentions` section (type/description/format/delivery/budget/deadline per intention). Backward-compat: derives single intention from `## Intent` + `## Delivery` when no intentions section exists.
- `api/services/workspace.py`: `write_project()` accepts optional `intentions` list, writes `## Intentions` section.
- `api/services/agent_execution.py`: `_load_pm_project_context()` injects intentions + budget_status into PM prompt context.
- `api/services/agent_execution.py`: `_handle_pm_decision()` handles `update_work_plan` action (writes `memory/work_plan.md`); graceful degradation overrides assemble/advance → escalate when budget exhausted.
- `api/services/primitives/project_execution.py`: New `UpdateProjectIntent` primitive (headless-only) — PM can refine assembly_spec, delivery, intentions without touching title/contributors.
- `api/services/primitives/registry.py`: Registered `UpdateProjectIntent` (headless-only mode gate).

### Expected behavior
- PM's first run on a new project produces `update_work_plan` action, writing operational decomposition to `memory/work_plan.md`.
- Multi-intention projects specify per-intention format, delivery, and budget in `## Intentions` section.
- PM sees budget status; reduces assembly when budget >80%, escalates when exhausted.
- Existing projects without intentions section work unchanged (backward-compat fallback).

---

## [2026.03.18.11] - Work budget governor (ADR-120 Phase 3)

### Added
- `supabase/migrations/117_work_budget.sql`: `work_units` table + `get_monthly_work_units()` RPC. Tracks per-action cost: agent_run (1), assembly (2), render (1), pm_heartbeat (1).
- `api/services/platform_limits.py`: `monthly_work_units` field on `PlatformLimits` (Free: 60, Pro: 1000). `check_work_budget()`, `record_work_units()`, `get_monthly_work_units()` functions. Added to `get_usage_summary()`.
- `api/jobs/unified_scheduler.py`: Budget check before agent dispatch — skips agents when user's budget is exhausted.
- `api/services/agent_execution.py`: Records work units after delivered agent runs, PM runs, and assemblies.
- `api/services/primitives/runtime_dispatch.py`: Budget check before render + records render work units.
- `api/services/composer.py`: `work_budget` status in heartbeat data for Composer awareness.

### Expected behavior
- Agents are skipped by scheduler when monthly work units exhausted. Renders are rejected. PM assembly is bounded.
- Free tier: 60 units/month (~2 agents daily). Pro tier: 1000 units/month (~10 agents daily + projects).
- Work budget is additive to render limits — a render costs both 1 render limit AND 1 work unit.

---

## [2026.03.18.10] - Assembly execution — PM decision interpreter + composition (ADR-120 Phase 2)

### Added
- `api/services/agent_execution.py`: PM decision interpreter (`_handle_pm_decision`) parses PM's JSON output and routes by action: `assemble` → `_execute_pm_assemble()`, `advance_contributor` → reuses P1's `handle_request_contributor_advance`, `wait` → no-op, `escalate` → writes note to project workspace. Assembly composition (`_compose_assembly`) performs separate LLM call with RuntimeDispatch access to produce cohesive deliverable from contributions. Assembly orchestration (`_execute_pm_assemble`) gathers contributions, composes, writes via `ProjectWorkspace.assemble()`, delivers via `deliver_from_assembly_folder()`.
- `api/services/agent_pipeline.py`: `ASSEMBLY_COMPOSITION_PROMPT` (v1) — composition-specific template for combining contributor outputs into unified deliverable. Separate from PM's decision prompt.
- `api/services/delivery.py`: `deliver_from_assembly_folder()` — delivers project assembly output, mirrors `deliver_from_output_folder()` pattern. Routes through existing `_deliver_email_from_manifest()` or exporter registry.
- `api/services/workspace.py`: `ProjectWorkspace.update_manifest_delivery()` — updates assembly manifest with delivery status, mirrors AgentWorkspace's version.
- `api/services/agent_execution.py`: PM branch in `execute_agent_generation()` — after `generate_draft_inline()`, PM's JSON decision is intercepted before normal delivery. PM still creates agent_runs (audit trail) but skips external delivery.

### Expected behavior
- PM's "assemble" action now triggers full assembly pipeline: gather contributions → LLM composition → RuntimeDispatch (if format requires it) → write to assembly folder → deliver.
- PM's "advance_contributor" action now actually advances the target agent's schedule.
- PM's "escalate" action writes an escalation note to the project workspace.
- PM agent_runs records include `pm_decision` in metadata for audit trail.
- Assembly delivery uses project's delivery config from PROJECT.md, not the PM agent's destination.

---

## [2026.03.18.9] - PM agent role + project execution primitives (ADR-120 Phase 1)

### Added
- `api/services/agent_creation.py`: Added `pm` role to `VALID_ROLES`, mapped to `knowledge` scope in `ROLE_TO_SCOPE`. PM agents get project-specific AGENT.md seeding.
- `api/services/agent_pipeline.py`: PM role prompt (v1) — structured JSON action output (assemble/advance_contributor/wait/escalate). PM validation checks JSON structure and required fields. `build_role_prompt()` handles PM `project_context`/`contributor_status`/`work_plan` template fields.
- `api/services/primitives/project_execution.py`: Three new headless-only primitives — `CheckContributorFreshness` (per-contributor freshness vs last assembly), `ReadProjectStatus` (full project state), `RequestContributorAdvance` (advance contributor schedule to now).
- `api/services/primitives/project.py`: `handle_create_project()` auto-creates PM agent (role=pm, origin=composer, daily schedule) and stores reference in `memory/pm_agent.json`.
- `api/services/agent_execution.py`: PM context injection (`_load_pm_project_context`) loads project identity + freshness into type_config before `build_role_prompt`. Project heartbeat (`_maybe_trigger_project_heartbeat`) advances PM schedule when contributor produces output (1h debounce). PM gets 4 tool rounds.
- `api/services/composer.py`: Project health signals in `heartbeat_data_query()` (active projects, PM count, stale PMs). Two new heuristics in `should_composer_act()`: `project_pm_stale` (PM idle 7+ days) and `project_no_pm` (project without PM agent).

### Expected behavior
- Creating a project via `CreateProject` now auto-provisions a PM agent. PM runs daily by default, but schedule is advanced when any contributor produces new output (project heartbeat).
- PM agents output structured JSON decisions, not prose. Validation enforces JSON with valid action field.
- Composer heartbeat detects projects without PMs and stale PMs.

---

## [2026.03.18.8] - Expand skill library — 4 new skills (ADR-118 D.4)

### Added
- `render/skills/mermaid/` — **diagram** skill. Mermaid syntax → PNG/SVG via mermaid-cli (mmdc). Supports flowcharts, sequence diagrams, class/state/ER diagrams, Gantt, pie, mindmap, timeline. Docker: Chromium + Node.js + @mermaid-js/mermaid-cli.
- `render/skills/html/` — **report** skill. Markdown → styled self-contained HTML via pandoc. Embedded CSS for clean, print-friendly reports. No new Docker deps (pandoc already installed).
- `render/skills/data/` — **data_export** skill. Structured data → CSV (with UTF-8 BOM for Excel) or JSON (pretty-printed). Pure Python stdlib, no Docker deps.
- `render/skills/image/` — **image** skill. Layout spec → PNG/JPG via Pillow. Text + rect elements on configurable canvas. Layout presets (card 1200x630, banner 1200x300, square 1080x1080). No new Docker deps (Pillow already installed).
- `render/Dockerfile`: Added `nodejs`, `npm`, `chromium` apt packages + `@mermaid-js/mermaid-cli` npm global install for diagram rendering.

### Expected behavior
- **Auto-discovered.** All 4 skills picked up by `_discover_skills()` on startup — no registry or API changes needed. RuntimeDispatch types: `diagram`, `report`, `data_export`, `image`.
- **Total skill count: 8.** document, presentation, spreadsheet, chart, diagram, report, data_export, image.

---

## [2026.03.18.7] - Skill auto-discovery (ADR-118 D.4)

### Changed
- `render/main.py`: Replaced hard-coded `SKILLS` dict and `SKILL_TYPE_TO_FOLDER` with auto-discovery from `skills/` directory. Skills are now dynamically imported via `importlib`. SKILL.md frontmatter `name` field maps logical type (e.g., "document") to folder name (e.g., "pdf"). GET /skills endpoint returns `{skills, type_to_folder}` mapping.
- `render/skills/{pdf,pptx,xlsx}/SKILL.md`: Updated `name` frontmatter to match RuntimeDispatch types (document, presentation, spreadsheet) instead of folder names.
- `api/services/primitives/runtime_dispatch.py`: Removed static `enum` on `type` field. Now accepts any string — agents learn valid types from SKILL.md docs in their context.
- `api/services/agent_execution.py`: Replaced hard-coded `SKILL_TYPE_TO_FOLDER` with dynamic fetch from render service's `/skills` endpoint. Falls back to known folders on failure.

### Expected behavior
- **Install a skill = copy folder + deploy.** New skills auto-discovered on render service startup. No API-side code changes needed. SKILL.md frontmatter determines the RuntimeDispatch type name.
- **Backwards compatible.** Existing agents using `type="document"` etc. work unchanged. The logical type→folder mapping is preserved via SKILL.md `name` field.

---

## [2026.03.18.6] - Version history for evolving files (ADR-119 Phase 3)

### Changed
- `api/services/workspace.py` (AgentWorkspace): Added `_archive_to_history()` — copies evolving file content to `/history/{filename}/v{N}.md` before overwrite. `_is_evolving_file()` gates which files get versioned (AGENT.md, thesis.md, memory/*). `_cap_history()` enforces max 5 versions. `list_history()` returns version list. `write()` now increments `version` column for evolving files and archives previous content.
- `api/services/workspace.py` (KnowledgeBase): Replaced legacy `_archive_if_exists()` + `_next_version_number()` + `_is_version_file()` + `_version_prefix()` + `list_versions()` with new `_archive_to_history()` + `list_history()` following same /history/ subfolder convention. Singular implementation — one versioning pattern for both agent and knowledge files.

### Expected behavior
- **Evolving files get version history.** AGENT.md, thesis.md, memory/*.md are archived to `/history/{filename}/v{N}.md` before each overwrite. Max 5 versions retained (oldest deleted). Non-evolving files (outputs, working scratch, manifests) skip versioning.
- **Version column incremented.** The `version` column on `workspace_files` now tracks how many times an evolving file has been overwritten.
- **Legacy code deleted.** KnowledgeBase's v{N}.md-in-same-directory pattern replaced with /history/ subfolder. No dual approaches.

---

## [2026.03.18.5] - Project folders (ADR-119 Phase 2)

### Changed
- `api/services/workspace.py`: Added `ProjectWorkspace` class scoped to `/projects/{slug}/` — core I/O (read/write/list/search/exists/delete), `read_project()` parses PROJECT.md into structured dict, `write_project()` serializes from structured data, `contribute()` writes to `/contributions/{agent_slug}/`, `assemble()` creates dated assembly folders with manifest.json, `list_contributors()`, `list_assemblies()`, `load_context()` concatenates PROJECT.md + memory/*. Added `get_project_slug()` helper. Extended `AgentWorkspace.load_context()` to inject project context from `memory/projects.json`.
- `api/services/primitives/project.py`: New file. `CreateProject` primitive — slugifies title, resolves contributor agents, writes PROJECT.md, seeds contributor workspaces with `memory/projects.json` pointer. `ReadProject` primitive — reads parsed PROJECT.md + contributions + assemblies.
- `api/services/primitives/registry.py`: Registered CreateProject + ReadProject in PRIMITIVES, HANDLERS, PRIMITIVE_MODES (both chat + headless).
- `api/routes/projects.py`: New file. REST CRUD: GET /api/projects (list), GET /api/projects/{slug} (detail), POST /api/projects (create), PATCH /api/projects/{slug} (update), DELETE /api/projects/{slug} (archive).
- `api/main.py`: Included projects router at `/api/projects`.

### Expected behavior
- **Projects are collaboration spaces.** Creating a project writes PROJECT.md (coordination contract) + seeds contributing agent workspaces with project membership pointers. Contributing agents receive project intent in their generation context.
- **Recursive pattern.** Project folders mirror agent folder structure: PROJECT.md (identity), /memory/ (state), /contributions/ (per-agent), /assembly/ (composed outputs), /working/ (scratch).
- **Context injection.** When an agent's `load_context()` runs, it checks `memory/projects.json` and injects each project's intent + preferences into the agent's generation context.

---

## [2026.03.18.4] - Unified output substrate (ADR-118 Phase D.3)

### Changed
- `api/services/agent_execution.py`: Restructured execution pipeline — `save_output()` now runs BEFORE delivery with `pending_renders` from RuntimeDispatch. New delivery path via `deliver_from_output_folder()` for all destinations. Fallback to legacy `deliver_version()` if output folder write fails. Added `_log_export_standalone()`, `_notify_delivery()`, `_notify_delivery_failed()` helpers. `generate_draft_inline()` now returns `(draft, usage, pending_renders)` tuple.
- `api/services/delivery.py`: Added `deliver_from_output_folder()` — reads `output.md` + `manifest.json` from workspace output folder instead of agent_runs. Email delivery builds attachment links from manifest `files[]` array. Non-email platforms use existing exporters with text from output folder. Added `_deliver_email_from_manifest()` and `_get_exporter_context_standalone()` helpers.
- `api/services/workspace.py`: Added `AgentWorkspace.update_manifest_delivery()` — updates manifest.json with delivery channel, status, external_id after successful send.
- `api/services/primitives/registry.py`: `HeadlessAuth` gains `pending_renders: list[dict]` accumulator and `agent_slug` property. Executor function exposes `.auth` attribute for callers to read pending_renders after generation.
- `api/services/primitives/runtime_dispatch.py`: After successful render + workspace write, appends rendered file metadata to `auth.pending_renders` for inclusion in output folder manifest.

### Expected behavior
- **Output folder is delivery source.** All agent deliveries now read content from the output folder (text from `output.md`, binary attachments from `manifest.files[]`) instead of from `agent_runs.final_content`.
- **Rendered files in manifest.** When agents use RuntimeDispatch during generation, produced files accumulate in `pending_renders` and appear in the output folder's `manifest.json` with `content_url` links. Email delivery includes these as download links.
- **Dual-write maintained.** `agent_runs` still receives `draft_content`/`final_content` for backward compatibility (frontend reads). Output folder is the authoritative delivery source.
- **Fallback safety.** If `save_output()` fails, the pipeline falls back to the legacy `deliver_version()` path that reads from `agent_runs`. No delivery is silently dropped.
- **Manifest delivery tracking.** After successful delivery, `manifest.json` is updated with `delivery.channel`, `delivery.status`, `delivery.sent_at`, `delivery.external_id`.

---

## [2026.03.18.3] - Output folders + lifecycle (ADR-119 Phase 1)

### Changed
- `api/services/workspace.py`: `AgentWorkspace.write()` now accepts `lifecycle`, `content_type`, `content_url`, `metadata` parameters. Auto-infers `lifecycle='ephemeral'` for `/working/` paths. `list()` excludes ephemeral/archived by default. New `save_output()` method creates dated output folders (`/outputs/{date}/`) with `output.md` + `manifest.json`. Dead `save_run()` replaced.
- `api/services/agent_execution.py`: After successful generation, calls `save_output()` to write the run's text output + manifest to the agent's output folder (alongside existing knowledge write).
- `api/services/primitives/workspace.py`: Updated tool descriptions for ReadWorkspace, WriteWorkspace, ListWorkspace, SearchWorkspace — references output folders, ephemeral working notes, lifecycle filtering.
- `api/jobs/unified_scheduler.py`: Added hourly ephemeral file cleanup (deletes `lifecycle='ephemeral'` files older than 24h).

### Expected behavior
- **Output folders.** Each agent run now writes to `/agents/{slug}/outputs/{date}/` with `output.md` (text) and `manifest.json` (metadata, file listing, sources, delivery status). This establishes the folder-as-bundle pattern for ADR-118 D.3.
- **Ephemeral scratch.** Files written to `/working/` are automatically marked `lifecycle='ephemeral'` and cleaned up after 24h. Agents can still read/write them during a run.
- **Lifecycle filtering.** `ListWorkspace` and default queries now exclude ephemeral and archived files, reducing noise for agents exploring their workspace.
- **Backwards-compatible.** Existing workspace files default to `lifecycle='active'`, `version=1`. No migration of existing data needed.

---

## [2026.03.18.2] - Render service hardening (ADR-118 Phase D.2)

### Changed
- `render/main.py`: v2.0.0 → v2.1.0. Added `X-Render-Secret` shared secret validation on POST /render, 5MB request size limit, in-memory rate limiter (60 req/min per caller), `user_id` field in RenderRequest for user-scoped storage paths (`{user_id}/{date}/{filename}.{ext}`).
- `api/services/primitives/runtime_dispatch.py`: Sends `X-Render-Secret` header + `user_id` on every render call. Checks `check_render_limit()` before dispatch — hard reject if monthly limit exceeded. Records usage via `record_render_usage()` after successful render.
- `api/services/platform_limits.py`: Added `monthly_renders` to PlatformLimits (free=10, pro=100). Added `check_render_limit()`, `get_monthly_render_count()`, `record_render_usage()`. Usage summary includes render counts.
- `supabase/migrations/115_render_usage_tracking.sql`: `render_usage` table + `get_monthly_render_count()` RPC.

### Expected behavior
- **Auth enforced.** POST /render rejects requests without valid `X-Render-Secret` header (401). GET /skills/* and /health remain unauthenticated (read-only).
- **Rate limiting.** 60 requests/minute per caller (user_id or IP). Returns 429 when exceeded.
- **Size limits.** Requests >5MB rejected with 413.
- **User-scoped storage.** Files uploaded to `{user_id}/{date}/{filename}.{ext}` — no cross-user file collision, enables per-user cleanup.
- **Render limits.** Free tier: 10 renders/month. Pro: 100/month. Hard rejection in RuntimeDispatch before calling the gateway. Agent receives clear error message.
- **Usage tracking.** Every successful render recorded in `render_usage` table for audit and limit enforcement.

---

## [2026.03.18.1] - Skills alignment + SKILL.md injection (ADR-118 Phase D.1)

### Changed
- `render/`: Restructured `handlers/` → `skills/{name}/scripts/render.py` + `SKILL.md` per skill. Deleted `handlers/` directory entirely.
- `render/main.py`: `HANDLERS` → `SKILLS` dict. Added `GET /skills/{name}/SKILL.md` and `GET /skills` endpoints for serving skill documentation. Updated all terminology (handler → skill).
- `api/services/primitives/runtime_dispatch.py`: Updated tool definition — "handler" → "skill" throughout. Tool description references SKILL.md injection. Workspace write made FATAL (Resolved Decision #3) — failed workspace row creation now fails the entire RuntimeDispatch call instead of silently swallowing.
- `api/services/agent_execution.py`: Added `_fetch_skill_docs()` — fetches SKILL.md content from output gateway via HTTP. Added `skill_docs` parameter to `_build_headless_system_prompt()`. Injected "Output Skill Documentation" section into system prompt for agents with RuntimeDispatch-authorized roles (synthesize, research, monitor, custom, orchestrate).

### Expected behavior
- **Agents read SKILL.md to learn spec construction.** When a synthesize/research/monitor/custom/orchestrate agent runs headlessly, the system prompt now includes the full SKILL.md documentation for all 4 output skills (pdf, pptx, xlsx, chart). This teaches agents how to construct high-quality RuntimeDispatch input specs.
- **Fatal workspace writes.** If the workspace_files row fails after a render, the agent gets an error (with the storage URL for reference) instead of silent success. No more orphaned binaries.
- **Graceful degradation.** If the render gateway is unreachable, skill docs are skipped — agent execution continues without them. Digest/prepare agents (not in RUNTIME_DISPATCH_ROLES) never fetch skill docs.

---

## [2026.03.17.15] - Composer capability awareness + AGENT.md hints (ADR-118 Phase C)

### Changed
- `api/services/composer.py`: COMPOSER_SYSTEM_PROMPT gains "Output Capabilities (ADR-118)" section — teaches Composer that agents can produce PDF, PPTX, XLSX, and chart outputs via RuntimeDispatch. Composer may now suggest rich outputs when scaffolding agents.
- `api/services/agent_creation.py`: AGENT.md seed appends "Available Capabilities" section for synthesize, research, monitor, and custom skill agents. Agents see RuntimeDispatch availability in their identity file.

### Expected behavior
- **Composer considers rich outputs when scaffolding agents.** When proposing a weekly synthesis for a manager, Composer may include "Produce a PDF summary" in the agent's instructions.
- **Agents know they can render.** AGENT.md for applicable skills includes a capability reference, so the headless prompt includes RuntimeDispatch awareness.
- **No change for digest/prepare agents.** These skills produce email-native content — no capability hints added.

---

## [2026.03.17.14] - RuntimeDispatch primitive + render infrastructure (ADR-118 Phase B)

### Added
- `api/services/primitives/runtime_dispatch.py`: New `RuntimeDispatch` primitive — headless-only. Allows agents to dispatch rendering (PDF, PPTX, XLSX, charts) during generation. Calls `yarnnn-render` service, uploads to Supabase Storage, writes `workspace_files` row with `content_url`.
- `api/services/primitives/registry.py`: Registered `RuntimeDispatch` in PRIMITIVES, HANDLERS, and PRIMITIVE_MODES (headless only).
- `render/`: New render service directory — FastAPI app with 4 handlers: document (pandoc → PDF/DOCX), presentation (python-pptx → PPTX), spreadsheet (openpyxl → XLSX), chart (matplotlib → PNG/SVG).

### Changed
- `api/services/workspace.py`: `WorkspaceFile` dataclass gains `content_url` field. `read_file()` select includes `content_url`.
- `api/integrations/exporters/resend.py`: Email delivery now queries `workspace_files` for rendered artifacts with `content_url IS NOT NULL` and includes download links in an "Attachments" section at the bottom of the email.
- `api/jobs/email.py`: `send_email()` gains optional `attachments` parameter (Resend API attachment support).

### Expected behavior
- **Headless agents can produce rich artifacts.** RuntimeDispatch is available alongside WriteWorkspace, QueryKnowledge, WebSearch in headless mode. Agents call it to render structured data into downloadable files.
- **Rendered files appear as email download links.** When a run produces rendered outputs, the Resend exporter includes them as clickable links in the email body.
- **Workspace tracks rendered outputs.** Every rendered file gets a `workspace_files` row with `content_url` pointing to Supabase Storage. The `content` column stores the spec/description that generated it.

---

## [2026.03.17.13] - Delivery-aware skill prompts (ADR-118 Phase A)

### Changed
- `api/services/agent_pipeline.py`: Added DELIVERY directive to `digest`, `prepare`, `synthesize`, `monitor`, and `research` skill prompts. Each now instructs the model that output will be emailed directly, and to write for mobile scanning — short paragraphs, bold key names/decisions, lead with action items.
- `api/services/onboarding_bootstrap.py`: Bootstrap agents now set `destination={"platform": "email", "target": <user_email>, "format": "send"}` via `get_user_email()`. Previously bootstrap agents had no destination — outputs were invisible.
- `api/services/composer.py`: All 4 agent creation paths (deterministic digest, LLM-driven, lifecycle expansion, cross-agent pattern) now set email destination by default.
- `api/services/primitives/coordinator.py`: `CreateAgent` tool schema now accepts `destination` field. Both coordinator and chat mode auto-default to email delivery when no destination specified.

### Expected behavior
- **Every auto-created agent delivers to user's inbox.** Bootstrap, Composer, and coordinator-created agents all default to email via Resend exporter. No user configuration needed.
- **Skill prompts produce email-optimized output.** Digests, preps, syntheses, monitors, and research reports are written for mobile scanning — shorter paragraphs, bolder key info, action-item-first structure.
- **No regression for existing agents.** Agents with explicit destinations are unchanged. Agents without destinations continue to work (delivery is best-effort, non-fatal).

---

## [2026.03.17.12] - Preferences system prompt injection + observation windowing (ADR-117)

### Changed
- `api/services/agent_execution.py`: `_build_headless_system_prompt()` now accepts `workspace_preferences` param and injects `memory/preferences.md` content into the system prompt under "## Learned Preferences". Previously preferences were only in the user-message context blob where they could be drowned out by platform data.
- `api/services/agent_execution.py`: `generate_draft_inline()` reads `memory/preferences.md` from workspace and passes it to the system prompt builder.
- `api/services/workspace.py`: `load_context()` now windows `observations.md` to last 10 entries. Prevents token bloat as observations accumulate over many runs.

### Expected behavior
- **Preferences have high salience.** Injected into system prompt alongside Agent Instructions and Agent Memory — same position as behavioral directives. The model sees "Always include Action Items (added in 4/5 runs)" at the same priority level as user instructions, not buried after 3000 tokens of Slack messages.
- **Dual injection preserved.** Preferences still appear in gathered context via `load_context()` (user message) AND in system prompt. Matches ADR-104 pattern for agent_instructions.
- **Observation window.** After 50 runs, only the last 10 observations are loaded. Full history preserved in workspace file for manual review. No information loss — just context window efficiency.

---

## [2026.03.17.11] - Remove dead past_versions from skill prompts (ADR-117 cleanup)

### Removed
- `api/services/agent_pipeline.py`: Deleted `past_versions` parameter from `build_skill_prompt()` and all 7 skill prompt templates. Was always passed as empty string since ADR-117 moved feedback to workspace.
- `api/services/agent_execution.py`: Removed `past_versions=""` argument from `build_skill_prompt()` call.

### Expected behavior
- **No behavioral change.** `past_versions` was already empty string in all calls since ADR-117 Phase 1. This removes dead code per singular implementation discipline.
- **Prompt templates are ~1 blank line shorter** each — the `{past_versions}` placeholder injected an empty line between recipient context and instructions.

---

## [2026.03.17.10] - Agent Self-Reflection for All Skills (ADR-117 Phase 2)

### Added
- `api/services/agent_execution.py`: `_extract_run_observation()` — rule-based observation extraction from generated content. Captures topics (from markdown headers), source coverage, data volume signals, and skill-specific notes. No LLM call.
- `api/services/agent_execution.py`: Post-delivery hook calls `ws.record_observation(observation, source="self")` after every successful agent run. Appends timestamped observation to `memory/observations.md`.

### Expected behavior
- **All agents accumulate longitudinal awareness.** Previously only analyst/research agents wrote observations (via `_build_analyst_directive`). Now every skill — digest, synthesize, monitor, prepare, research — records a self-observation after each run.
- **Observations are lightweight.** Topics from headers, source coverage stats, data volume. Example: `"Topics: Team Updates, Action Items; Sources: slack (12 items); Dense output (1500 words)"`.
- **Observations visible on next run.** `memory/observations.md` is loaded via `load_context()` (Phase 1). Over 10 runs, patterns emerge: "Slack #engineering quiet for 3 runs", "Gmail action items recurring around quarterly planning".
- **Non-fatal.** Observation failure never blocks delivery or downstream processing.

---

## [2026.03.17.9] - Singular Implementation Cleanup (ADR-117)

### Removed
- `api/services/agent_execution.py`: Removed `get_past_versions_context` import, `learned_preferences` parameter from `_build_headless_system_prompt()`, and `## Learned Preferences` system prompt injection block. Feedback preferences are now loaded from workspace `memory/preferences.md` via strategy-level `load_context()`.
- `api/services/agent_pipeline.py`: Deleted `get_past_versions_context()` function entirely (was ~40 lines). This was the last remaining dual feedback path — raw edit pattern injection alongside workspace preferences.
- `api/services/feedback_engine.py`: Updated docstring to reference `feedback_distillation.py` instead of removed function.

### Expected behavior
- **One feedback path, not two.** Before this change, agents received feedback via both workspace preferences (new) AND raw `learned_preferences` injection in the system prompt (old). Now only workspace preferences exist — singular implementation per ADR-117.
- **No behavioral change for agents.** The same feedback signals reach agents, just through the workspace substrate instead of direct prompt injection.

---

## [2026.03.17.8] - Unified Feedback Substrate (ADR-117 Phase 1)

### Changed
- `api/services/execution_strategies.py`: All four strategies (PlatformBound, CrossPlatform, Research, Analyst) now load agent workspace context via `load_context()`. Raw `_get_past_versions_context()` injection removed — workspace `memory/preferences.md` is the single feedback substrate. Dead helper `_get_past_versions_context()` deleted (singular implementation).
- `api/services/composer.py`: Lifecycle underperformer path writes coaching feedback to `memory/supervisor-notes.md` via `write_supervisor_notes()`. Composer can now coach agents, not just pause them.

### Added
- `api/services/feedback_distillation.py`: New module — `distill_feedback_to_workspace()` converts cumulative edit patterns from `agent_runs` into structured behavioral directives in `memory/preferences.md`. `write_supervisor_notes()` bridges Composer lifecycle to agent workspace.
- `api/routes/agents.py`: PATCH version endpoint triggers async feedback distillation after edit metrics are computed. Every user feedback event updates the agent's workspace preferences.

### Expected behavior
- **Digest agents gain longitudinal memory.** Previously, digest agents received only a platform dump and raw edit patterns. Now they load their full workspace context (AGENT.md + thesis + memory/preferences.md + observations). Quality compounds across runs.
- **Feedback distillation converts raw patterns to directives.** "User added: action items" across 4 runs becomes "Always include an Action Items section" in preferences.md. Overwritten each distillation — represents current best understanding.
- **Composer coaching is visible to agents.** When an underperformer is monitored (not yet paused), Composer writes specific coaching to supervisor-notes.md. The agent sees this on its next run.
- **No new LLM calls.** Distillation is pure logic; workspace writes use existing AgentWorkspace abstraction.

---

## [2026.03.17.7] - Consumption Tracking & Composer Dependency Graph (ADR-116 Phase 5)

### Added
- `api/services/primitives/workspace.py`: `_log_cross_agent_reference()` — writes `memory/references.json` to consuming agent's workspace. Called from QueryKnowledge (when results reference other agents) and ReadAgentContext (always).
- `api/services/composer.py`: `heartbeat_data_query()` step 10 — reads reference logs from all active agents, builds `agent_graph` with edges, orphaned producers, consumed IDs.
- `api/services/composer.py`: `should_composer_act()` — `orphaned_producers` heuristic: 2+ agents producing unconsumed knowledge triggers Composer.

### Expected behavior
- Cross-agent consumption tracked implicitly via workspace reference files. Composer heartbeat aggregates into dependency graph.
- Orphaned producer detection: agents producing knowledge no other agent consumes → Composer fires to suggest synthesis or pause.

---

## [2026.03.17.6] - Agent Card Auto-Generation & MCP Tools (ADR-116 Phase 4)

### Added
- `api/services/agent_execution.py`: `_generate_agent_card()` — auto-generates `agent-card.json` after each successful run. Schema v1 with description, thesis, maturity, interop.
- `api/mcp_server/server.py`: 3 new MCP tools — `get_agent_card`, `search_knowledge`, `discover_agents`. Total: 9 tools.

### Expected behavior
- External agents (Claude Desktop, ChatGPT) can discover YARNNN's fleet, query knowledge by agent/skill, and read agent cards.
- Cards auto-regenerate per run. Fresh maturity signals always available.

---

## [2026.03.17.5] - Agent Identity Quality: Composer Dedup + Rich Creation

### Changed
- `api/services/composer.py`: COMPOSER_SYSTEM_PROMPT v1.3 — response format now requires `description` and `instructions` fields on create actions. LLM provides workspace-contextualized identity for each agent it creates, not just title+skill.
- `api/services/composer.py`: `_execute_composer_decisions()` — passes `description` and `agent_instructions` through to `create_agent_record()`. Agents created by Composer now have differentiated identity from birth.
- `api/services/composer.py`: Dedup logic upgraded from title-only to title + skill. Non-per-platform skills (synthesize, research, etc.) are one-per-workspace. Prevents creative title variants from creating duplicate coverage.
- `api/services/agent_creation.py`: `create_agent_record()` — resolved instructions (explicit or DEFAULT_INSTRUCTIONS fallback) now written to `agent_instructions` DB column, not just AGENT.md. Agents are no longer hollow shells.
- `api/services/onboarding_bootstrap.py`: Bootstrap templates now include `description` field. Bootstrap agents get dashboard-visible descriptions from day one.

### Expected behavior
- Composer-created agents now have: (1) LLM-authored description visible on dashboard, (2) workspace-specific instructions guiding execution, (3) differentiated AGENT.md. No more empty instructions/description.
- Skill dedup prevents: "Weekly Cross-Platform Synthesis" AND "Weekly Analysis: Patterns & Gaps" both being created as `skill=synthesize`. Second creation blocked with log: "Skill 'synthesize' already covered by '...'".
- Digest and monitor skills are exempt from skill dedup (multiple per-platform digests are valid).
- All agents (bootstrap, composer, user-created) now persist `agent_instructions` in DB column. Previously only AGENT.md received the instructions text.

---

## [2026.03.17.4] - Cross-Agent Workspace Reading (ADR-116 Phase 3)

### Added
- `api/services/primitives/workspace.py`: `ReadAgentContext` tool — new headless primitive. Agents can read another agent's identity files (AGENT.md, thesis.md) and memory files. Read-only, same-user scoped.
- `api/services/primitives/registry.py`: `ReadAgentContext` registered as headless-only primitive.

### Expected behavior
- Synthesis agents call `DiscoverAgents()` → pick an agent → `ReadAgentContext(agent_id="<uuid>")` to deeply understand that agent's perspective before synthesizing. The full inter-agent reading chain is now operational.
- Only identity and memory files exposed. Working notes (`working/`) and past runs (`runs/`) are excluded — process artifacts, not identity.
- Memory files truncated to 1000 chars each for token budget control.
- Agent lookup validates same-user ownership. Returns agent_not_found for non-existent or other-user agents.

---

## [2026.03.17.3] - Inter-Agent Knowledge Infrastructure (ADR-116 Phases 1-2)

### Added
- `api/services/primitives/workspace.py`: `QueryKnowledge` tool — extended with `agent_id`, `skill` filter parameters. Agents can now query knowledge by producer agent, skill type, and content class. Results include provenance metadata (produced_by, skill, scope, version).
- `api/services/primitives/workspace.py`: `DiscoverAgents` tool — new headless primitive. Agents can discover sibling agents by skill/scope/status, receiving agent cards with thesis summaries and maturity signals.
- `api/services/workspace.py`: `KnowledgeBase.search_by_metadata()` — metadata-aware search using new `search_knowledge_by_metadata` RPC.
- `supabase/migrations/111_search_knowledge_by_metadata.sql` — Postgres RPC for filtering `/knowledge/` by agent_id, skill, scope, content_class.

### Changed
- `api/services/primitives/registry.py`: `DiscoverAgents` registered as headless-only primitive. Available to synthesize and orchestrate skills per ADR-109 framework.
- `QueryKnowledge` tool description updated to reference DiscoverAgents for agent ID lookup.
- `QueryKnowledge` `query` parameter changed from required to optional (metadata-only queries are valid).

### Expected behavior
- Synthesis agents can now call `DiscoverAgents(skill="digest")` to find digest agents, then `QueryKnowledge(agent_id="<uuid>")` to get exactly that agent's outputs. This is the inter-agent compounding loop.
- Existing QueryKnowledge calls (text-only, no metadata filters) are unchanged — same code path, same fallback to platform_content.
- DiscoverAgents excludes the calling agent from results. Returns thesis summary (first 300 chars) and run count for each discovered agent.

---

## [2026.03.17.2] - State-Change Gate for Density-Triggered LLM (ADR-115)

### Added
- `api/services/composer.py`: `_get_last_assessed_state()` — fetches state tuple (knowledge_files, total_agent_runs, active_agents) from the most recent `composer_heartbeat` where `should_act=true`. One query on activity_log (limit 20).
- `api/services/composer.py`: `should_composer_act()` — state-change comparison before density-triggered LLM fire. If workspace state unchanged since last assessment, returns `HEARTBEAT_OK: awaiting new signal` instead of calling LLM.

### Expected behavior
- First heartbeat for any user always fires LLM (no prior assessment exists).
- Subsequent heartbeats only fire LLM when knowledge_files, total_agent_runs, or active_agents has changed.
- If an agent delivers (kf increments) → next heartbeat fires LLM. If LLM returns "observe" → subsequent heartbeats skip until next state change.
- **Cost reduction**: ~288 Haiku/day → ~2-5/day per Pro user for developing workspaces.
- Mechanical heuristics (coverage_gap, underperformer, stale_agents) are unaffected — they fire regardless of state-change gate.
- Fail-open: if activity_log query fails, LLM fires (safe default).

---

## [2026.03.17.1] - Workspace Density Model in Composer (ADR-115)

### Added
- `api/services/composer.py`: `_classify_workspace_density()` — pure function classifying workspace as sparse/developing/dense from knowledge file count, total agent runs, and maturity signals. Zero additional DB queries.
- `api/services/composer.py`: `should_composer_act()` — `sparse_workspace` and `developing_workspace` heuristics fire before `HEARTBEAT_OK`. Both route to LLM assessment. Only `dense` workspaces reach HEARTBEAT_OK through the density gate.
- `api/services/composer.py`: `heartbeat_data_query()` return dict includes `workspace_density` and `total_agent_runs`.
- `api/services/composer.py`: `_build_composer_prompt()` includes "Workspace Density" section telling LLM whether to be eager, proactive, or conservative.

### Changed
- `COMPOSER_SYSTEM_PROMPT` v1.1 → v1.2: Reframed from "assess platforms and agents" to "assess knowledge substrate." Three density-aware principles: sparse (eager), developing (proactive — fill skill gaps), dense (conservative). Value chain ordering (digests → synthesis → analysis → research).
- `run_heartbeat()` assessment_summary includes `workspace_density` and `total_agent_runs`.

### Expected behavior
- **Sparse** (<5 knowledge files, <10 runs): LLM assessment with "be eager" framing.
- **Developing** (between sparse and dense): LLM assessment with "fill skill gaps" framing. Proposes research/analysis if workspace only has digests.
- **Dense** (>50 knowledge files, 3+ non-nascent agents): HEARTBEAT_OK unless other heuristics fire.
- **Behavioral delta from v1.1**: A workspace like kvkthecreator's (13 kf, 12 runs, all digests) now triggers `developing_workspace` → LLM assessment, instead of HEARTBEAT_OK. The LLM sees "propose agents for skill types the workspace lacks."
- Self-correcting: eager-mode agents that underperform are still caught by `lifecycle_underperformer` (8+ runs, <30% approval).

---

## [2026.03.16.10] - Knowledge Corpus Signals in Composer (ADR-114 Phases 1-3)

### Added
- `api/services/composer.py`: `heartbeat_data_query()` step 9 — queries `workspace_files` for `/knowledge/` corpus: per-class counts (digests/analyses/briefs/research/insights), latest timestamp, producing agents. Single DB query, zero LLM cost.
- `api/services/composer.py`: `should_composer_act()` — three new knowledge-substrate heuristics: `knowledge_gap_analysis` (10+ digests, 0 analyses, no synthesize agent), `stale_knowledge` (latest file >7d old, agents active), `knowledge_asymmetry` (80%+ digests, ≤1 non-digest). All route to LLM assessment.

### Changed
- `api/services/composer.py`: `_build_composer_prompt()` v1.1 — added "Knowledge Corpus" section with per-class file counts, recency, and producing agents. LLM now sees accumulated outputs, not just platform metadata.
- `api/services/composer.py`: `run_heartbeat()` assessment_summary includes `knowledge_files` count.
- `COMPOSER_SYSTEM_PROMPT` version: v1.0 → v1.1.

### Not included (deferred)
- `knowledge_gap_research` trigger: needs keyword extraction from digest content (ADR-114 Open Question 2).
- `agents_consuming`: needs provenance tracking for workspace reads (ADR-114 Open Question 3).

### Expected behavior
- Composer now detects when agents are perceiving (producing digests) but not reasoning (no analyses/research).
- After 10 digests accumulate with 0 analyses and no synthesize agent, triggers LLM assessment.
- Stale knowledge (>7d old, agents active) triggers LLM assessment.
- Knowledge asymmetry (>80% digests) triggers LLM assessment.
- LLM assessment prompt now includes substrate context: "8 digest files, 0 analyses" vs just "2 digest agents, 3 runs each."

---

## [2026.03.16.9] - Event-Driven Composer Heartbeat (ADR-114)

### Added
- `api/services/composer.py`: `maybe_trigger_heartbeat()` — DB-debounced event trigger for substrate changes. Pro: 3min debounce. Free: midnight-window only (same as cron). Writes `composer_heartbeat` activity_log with `"origin": "event"` and `trigger_event`/`trigger_metadata`.
- `api/services/agent_execution.py`: Trigger heartbeat after delivered agent runs (`trigger_event: "agent_run_delivered"`).
- `api/workers/platform_worker.py`: Trigger heartbeat after platform sync with new content (`trigger_event: "platform_synced"`).

### Changed
- `api/jobs/unified_scheduler.py`: Added `"origin": "cron"` to heartbeat metadata to distinguish from event-driven heartbeats.

### Not included (intentionally)
- OAuth `platform_connected` trigger omitted: fires before content exists, risks premature composition since coverage-gap logic keys off connected platforms. Post-sync trigger covers this path safely.
- This is a *responsiveness* upgrade (changes *when* Composer looks), not a *substrate awareness* upgrade (changes *what* it sees). ADR-114 Phase 1 (knowledge corpus signals in `heartbeat_data_query()`) is the real substrate tightening.

### Known limitations
- DB-backed debounce is not atomic. Cron and event can race and both pass the check, producing two heartbeats. Blast radius: two Haiku calls worst case. Advisory locks deferred.

### Expected behavior
- Pro: Composer reassesses within ~3min of substrate changes (delivered runs, syncs) instead of waiting for next cron cycle.
- Free: event-driven heartbeats only fire in midnight UTC window, keeping Free truly daily.
- Cron heartbeat remains backstop. Event-driven is supplementary.
- Dashboard System Pulse updates sooner after agent activity (Pro users).

---

## [2026.03.16.8] - Composer Prompt Versioning Baseline (ADR-114)

### Established
- `api/services/composer.py`: **Composer v1.0 baseline** — documenting current state for versioned evolution.
- `COMPOSER_SYSTEM_PROMPT` (v1.0): Instructs Haiku to assess platforms, agents, work patterns. Principles: bias toward action, highest-value first (digest→synthesis→research), respect existing, one agent per decision. Output: JSON `create` or `observe`.
- `_build_composer_prompt()` (v1.0): Passes trigger reason, connected platforms, active agents, coverage gaps, health (stale/feedback), maturity signals, tier constraints.
- `should_composer_act()` heuristics (v1.0): coverage_gap, lifecycle_underperformer, lifecycle_expansion, cross_agent_consolidation, cross_platform_opportunity, engaged_user, stale_agents.
- Coverage detection: source-based + title-based matching (bootstrap agents with empty sources).
- `docs/adr/ADR-114-composer-substrate-aware-assessment.md`: New ADR proposing evolution from platform-metadata-centric to substrate-aware assessment. Four phases: knowledge corpus signals → substrate-aware heuristics → LLM prompt injection → prompt v2.0.

### Policy
- All future Composer prompt or heuristic changes MUST include a CHANGELOG entry with version bump, behavioral delta, and expected outcome. Composer orchestration decisions are product-defining — same rigor as Orchestrator prompt versioning.

---

## [2026.03.16.7] - ADR-113: Auto Source Selection — eliminate manual prerequisite + smarter heuristics

### Changed
- `api/routes/integrations.py`: OAuth callback now auto-discovers landscape, applies `compute_smart_defaults()`, and kicks off first sync as BackgroundTask. Users no longer need to manually select sources before sync begins.
- `api/integrations/core/oauth.py`: Default post-OAuth redirect changed from `/orchestrator` to `/dashboard`. Users see their platform connected and syncing progress.
- `web/app/(authenticated)/dashboard/page.tsx`: Empty state platform cards trigger OAuth directly (no redirect to context page). Transitional state reframed from "Select sources to sync" to "Customize synced sources" (optional). Added "Connect more platforms" section. Loading state on connect buttons.
- `api/services/landscape.py`: `compute_smart_defaults()` upgraded from single-signal sorting to multi-signal scoring. Slack: name pattern matching (boost work channels like `team-`, `eng-`, `incident`; penalize noise like `random`, `social`, `fun`) + purpose/topic keyword analysis + member count as tiebreaker. Notion: boost databases (+3), workspace-level pages (+2), penalize Untitled (-3), recency tiebreaker. Gmail/Calendar unchanged.
- `docs/design/USER_FLOW_ONBOARDING_V4.md`: Updated to V5 reflecting auto-selection flow.
- `docs/adr/ADR-113-auto-source-selection.md`: New ADR documenting the change and heuristics.
- Expected behavior: Platform connection is now a single click → auto-discover → auto-select → auto-sync → auto-bootstrap flow. Manual source curation moves from prerequisite to optional refinement. Auto-selected sources are now work-biased, not just popularity-biased.

---

## [2026.03.16.6] - Orchestrator surface alignment: commands, starter cards, plus menu

### Changed
- `api/services/commands.py`: Renamed `/status` → `/summary`, `/digest` → `/recap`, `/brief` → `/prep`, `/deep-research` → `/research`. Updated `/create` to remove "or memory" ambiguity. Added 4 capability commands: `/search` (platform content), `/sync` (refresh), `/memory` (save preference), `/web` (web search). All command prompts updated to use `CreateAgent(...)` instead of stale `Write(ref="agent:new", ...)`.
- `web/components/desk/ChatFirstDesk.tsx`: Starter cards split into "Create an agent" (6 templates) and "Or ask directly" (3 capability cards: search platforms, web research, ask anything). Replaced generic "Just chat" catch-all. Plus menu expanded: added web search, refresh platforms, save to memory. Panel tab renamed "Sources" → "Platforms".
- Expected behavior: Users now discover TP's full capabilities (search, sync, memory, web research) from the welcome screen, slash commands, and plus menu — not just agent creation. Command names align with ADR-109 skill taxonomy.

---

## [2026.03.16.5] - Fix: Headless agent tool-narration leak + output validation

### Changed
- `api/services/agent_execution.py`: Added empty-context handling guidance to headless system prompt — agents must produce properly formatted "no activity" output instead of narrating tool usage. Added `_strip_tool_narration()` to detect and reject drafts that are purely tool-use narration (e.g., "Let me check what platform content is available"). Added blocking retry for critically short drafts (<20 words) — forces a synthesis call with explicit instructions to produce content.
- Expected behavior: Agents that receive empty context or get no results from tools will now produce a structured "no recent activity" output in the correct format, instead of leaking internal reasoning as the final output. Critically short outputs trigger an automatic retry before delivery.

---

## [2026.03.16.4] - ADR-111 Phase 5: Lifecycle Progression

### Changed
- `api/services/composer.py`: `heartbeat_data_query()` enriched with per-agent maturity signals (run count, approval rate, edit distance trend, tenure, maturity stage, underperformer flag). `should_composer_act()` extended with lifecycle triggers (underperformer, expansion, cross-agent pattern). New `run_lifecycle_assessment()` handles deterministic lifecycle actions (pause underperformers, create synthesis from mature digests). `run_composer_assessment()` routes lifecycle triggers without LLM. `_build_composer_prompt()` includes maturity data for LLM path.
- `api/jobs/unified_scheduler.py`: `composer_lifecycle` counter tracks lifecycle actions in summary + heartbeat metadata.
- Expected behavior: Heartbeat now detects agent maturity patterns. Agents with 8+ runs and <30% approval are auto-paused. Mature digest agents (10+ runs, 80%+ approval) across 2+ platforms trigger automatic cross-platform synthesis agent creation. 3+ active digest agents trigger consolidation. All lifecycle actions are deterministic (zero LLM cost).

---

## [2026.03.16.3] - ADR-111 Phase 4: Supervisory Reframe

### Changed
- `api/services/composer.py`: Added `_run_supervisory_review()` and `_get_due_supervisory_agents()`. Heartbeat now invokes per-agent review for proactive/coordinator agents — TP owns the supervisory cadence. `run_heartbeat()` extended with Step 4 (supervisory reviews) after Composer assessment.
- `api/services/proactive_review.py`: Docstring reframed — TP's per-agent supervisory check, invoked by Heartbeat. Mechanical flow preserved.
- `api/jobs/unified_scheduler.py`: Proactive section absorbed into Heartbeat. `get_due_proactive_agents()` and `process_proactive_agent()` deprecated (kept for test compat). `proactive_reviewed` counter populated from Heartbeat supervisory results.
- Expected behavior: Proactive/coordinator agents are now reviewed within TP's Heartbeat cycle, not as a separate scheduler section. Same review mechanics (Haiku → generate/observe/sleep), but owned by TP.

---

## [2026.03.16.2] - ADR-111 Phase 3: TP Composer Heartbeat + Assessment

### Added
- `api/services/composer.py` (new): Composer system prompt for LLM assessment — instructs Haiku to evaluate agent workforce gaps and recommend one agent creation per assessment. Bias toward action. Valid skills/frequencies enumerated.
- Expected behavior: Composer fires via scheduler heartbeat (Free: daily, Pro: every 5min). Cheap data query first; LLM only when `should_composer_act()` identifies a gap (coverage, staleness, cross-platform opportunity). Auto-creates agents with `origin="composer"`.

---

## [2026.03.16.1] - ADR-111 Phase 1: Complete singular agent creation path

### Changed
- `api/routes/agents.py`: POST `/agents` now delegates to shared `create_agent_record()` instead of inline insert. Local `infer_scope()` replaced with import from `services.agent_creation`. Tier check and response formatting remain as route concerns.
- `api/services/agent_creation.py`: Added `infer_scope()` (moved from routes, handles sources + skill + mode). Added `description` and `platform_variant` optional params. Scope inference upgraded from simple `SKILL_TO_SCOPE` dict to full `infer_scope()` logic.
- `api/agents/tp_prompts/behaviors.py`: Fixed 3 stale `Write(ref="agent:new", ...)` examples → `CreateAgent(...)` to match tools.py.
- Expected behavior: All agent creation paths (UI form, TP chat, coordinator, bootstrap) now funnel through single `create_agent_record()`. No behavioral change for users — same validation, same workspace seeding, same response shape.

---

## [2026.03.15.2] - ADR-112: RefreshPlatformContent sync lock awareness

### Changed
- `api/services/primitives/refresh.py`: Added sync lock check before running sync. When `platform_connections.sync_in_progress` is true (non-stale), returns "Sync already in progress" message instead of starting a redundant sync. Preserves conversation flow.
- Expected behavior: TP gets a helpful message when sync is already running, instead of waiting 10-30s for a duplicate sync that wastes API quota. No functional change when no sync is in progress.

---

## [2026.03.15.1] - Remove legacy signal processing + pattern detection from system state

### Changed
- `api/services/primitives/system_state.py`: Removed `SignalPassSummary` dataclass, `_get_last_signal_pass()` fetcher, and "signals" scope option. Signal processing was dissolved in ADR-092; no code writes `signal_processed` events.
- `api/services/primitives/system_state.py`: Removed signal pass from `SystemStateSnapshot.to_dict()` and `_format_state_message()`.
- `api/services/working_memory.py`: Removed `last_signal_pass` from system summary dict and signal pass formatting block. TP system prompt no longer includes stale "Signal processing: unknown" line.
- Expected behavior: GetSystemState no longer returns empty `last_signal_pass: null`. Working memory prompt is cleaner. No functional change — signal processing hasn't run since ADR-092.

---

## [2026.03.13.2] - ADR-111: Unified CreateAgent primitive + ADR-110: Onboarding Bootstrap

### Changed
- `api/agents/tp_prompts/tools.py`: Write tool description no longer mentions agents — redirects to CreateAgent. New "Creating Agents" section documents CreateAgent with full parameter list (skills, frequency, optional fields). Replaces old `Write(ref="agent:new", ...)` examples.
- `api/services/primitives/write.py`: Rejects `ref="agent:new"` with redirect to CreateAgent. `_process_agent()` deleted. Tool description updated: "Create a new memory or document entity."
- `api/services/primitives/coordinator.py`: `handle_create_agent()` rewritten to support both chat and headless modes. Detects mode via `coordinator_agent_id` on auth context. Chat mode: `origin=user_configured`, respects user schedule. Headless mode: `origin=coordinator_created`, `execute_now=True`.
- `api/services/primitives/registry.py`: CreateAgent mode changed from `["headless"]` to `["chat", "headless"]`.
- `api/services/agent_creation.py` (new): Shared `create_agent_record()` — single source of truth for all agent creation paths (chat, headless, bootstrap, API route).
- `api/services/onboarding_bootstrap.py` (new): Deterministic bootstrap service. Auto-creates digest agent on platform sync completion. Template mapping: Slack→Recap, Gmail→Digest, Notion→Summary. Checks: existing digest, tier limit, synced content.
- `api/workers/platform_worker.py`: Calls `maybe_bootstrap_agent()` after successful sync.
- Expected behavior: TP uses CreateAgent (not Write) for agent creation in chat. First platform sync auto-creates a matching digest agent. All creation paths funnel through `create_agent_record()`.

---

## [2026.03.13.1] - Fix ADR-109 scope/skill gaps across all agent primitives

### Changed
- `api/services/primitives/write.py`: Write tool description now documents agent fields (scope, skill with valid values). `_process_agent()` defaults `skill` to `custom` and auto-infers `scope` from skill via `SKILL_TO_SCOPE` mapping when not provided or invalid. Added `AGENT_COLUMNS` allowlist to strip unknown fields before INSERT (prevents Supabase 400). Exported `VALID_SCOPES`, `VALID_SKILLS`, `SKILL_TO_SCOPE` for reuse.
- `api/services/primitives/coordinator.py`: `CreateAgent` now validates `skill` against `VALID_SKILLS` and infers `scope` from `SKILL_TO_SCOPE`. Previously missing `scope` entirely — would 400 on every coordinator-created agent.
- `api/services/primitives/edit.py`: Added scope/skill validation when updating agents. Returns clear error for invalid values instead of passing through to Supabase constraint violation.
- Expected behavior: All three agent mutation paths (Write, CreateAgent, Edit) now enforce valid scope+skill per ADR-109 schema constraints. TP and coordinator agents no longer hit silent 400 loops.

---

## [2026.03.12.2] - ADR-109: Scope × Skill × Trigger framework migration

### Changed
- `api/routes/agents.py`: `AgentType` literal → `Scope` + `Skill` literals. Deleted `TYPE_TIERS`, `get_type_classification()`. Added `infer_scope()` for auto-inferring scope from sources+skill+mode. Config classes renamed (BriefConfig→PrepareConfig, etc.). `AgentCreate/Update/Response` use `scope`+`skill` instead of `agent_type`+`type_classification`.
- `api/services/agent_pipeline.py`: `TYPE_PROMPTS` → `SKILL_PROMPTS`, `build_type_prompt()` → `build_skill_prompt()`, `validate_output()` uses `skill` parameter.
- `api/services/execution_strategies.py`: `HybridStrategy` deleted. `get_execution_strategy()` rewritten to direct scope→strategy mapping. `PlatformBoundStrategy` renamed to `platform` strategy_name.
- `api/services/agent_execution.py`: `_build_headless_system_prompt()` uses `skill`. `HEADLESS_TOOL_ROUNDS` rekeyed by scope. `generate_draft_inline()` uses `skill`+`scope`.
- `api/services/proactive_review.py`: All `agent_type` → `skill`, deep research condition uses scope.
- `api/services/workspace.py`: `CONTENT_CLASS_MAP` rekeyed by skill.
- `api/services/skills.py`: All skill definitions use `"skill"` key with new values.
- `api/services/working_memory.py`, `api/routes/admin.py`, `api/routes/chat.py`, `api/services/delivery.py`, `api/services/primitives/write.py`, `api/services/primitives/coordinator.py`, `api/mcp_server/server.py`, `api/jobs/unified_scheduler.py`: All `agent_type` → `skill`/`scope`.
- Expected behavior: Agents are now classified by orthogonal Scope (auto-inferred) × Skill (user-selected) × Trigger (mode). No more 7-type taxonomy. Strategy selection is direct scope→strategy, no heuristic.

---

## [2026.03.12.1] - ADR-108: SaveMemory primitive

### Added
- `api/services/primitives/save_memory.py`: New `SaveMemory` chat-mode-only primitive. Persists user-stated facts, preferences, and instructions to `/memory/notes.md` in real time. Add-only (no update/delete from chat). Deduplicates on content. Logs to activity_log.
- `api/services/primitives/registry.py`: Registered SaveMemory in PRIMITIVES, HANDLERS, and PRIMITIVE_MODES (chat-only).
- Expected behavior: When user explicitly asks TP to remember something, TP calls SaveMemory to persist it immediately. Nightly cron continues for implicit extraction. Memory page remains the UI for edit/delete. Primitive count: 10 → 11.

---

## [2026.03.11.6] - ADR-108: User memory filesystem migration

### Changed
- `api/services/workspace.py`: Added `UserMemory` class scoped to `/memory/`. Three files: `MEMORY.md` (profile), `preferences.md` (per-platform tone/verbosity), `notes.md` (facts/instructions/preferences). Read-merge-write pattern for all mutations. Both async and sync read methods for thread pool compatibility.
- `api/services/working_memory.py`: Replaced `_get_user_memory_sync()` (user_memory table) with `_get_user_memory_files_sync()` (workspace_files /memory/). `_extract_profile`, `_extract_preferences`, `_extract_known` replaced with `_extract_profile_from_file`, `_extract_preferences_from_file`, `_extract_known_from_file` that parse markdown instead of key-value rows.
- `api/services/memory.py`: `process_conversation()` now read-merge-writes to `/memory/notes.md` with deduplication instead of row-level upserts to user_memory. `get_for_prompt()` concatenates /memory/ files.
- `api/routes/memory.py`: All endpoints rewritten to use `UserMemory` class. Profile → MEMORY.md, Styles → preferences.md, Entries → notes.md. Delete endpoint uses content hash IDs instead of UUID row IDs.
- `api/services/agent_execution.py`: Headless user context reads from `/memory/` files instead of user_memory table.
- `api/services/execution_strategies.py`: `_get_user_memories()` reads `/memory/notes.md` instead of user_memory table.
- `api/services/primitives/search.py`: `_search_user_memories()` reads `/memory/notes.md` instead of user_memory table.
- `api/routes/system.py`, `api/routes/integrations.py`, `api/jobs/platform_sync_scheduler.py`: Timezone reads from `/memory/MEMORY.md` instead of user_memory table.
- Expected behavior: All memory reads/writes use `/memory/` files in workspace_files. user_memory table preserved but no longer read by application code. Extraction cron deduplicates on content. Memory page shows notes from notes.md with stable content-hash IDs.

---

## [2026.03.11.5] - ADR-107 Phase 1: Knowledge filesystem — singular cutover

### Changed
- `api/services/workspace.py`: `KnowledgeBase` class extended with `write()`, `get_knowledge_path()`, `CONTENT_CLASS_MAP`, `count()`, `list_files()`, `list_classes()`. Search parameter renamed from `platform` to `content_class`.
- `api/services/agent_execution.py`: Replaced `store_platform_content(platform="yarnnn")` with `KnowledgeBase.write()`. Agent outputs now write to `/knowledge/{class}/{slug}-{date}.md`.
- `api/services/primitives/workspace.py`: `QueryKnowledge` tool definition updated — removed `platform` enum (was `["slack", "gmail", "notion", "calendar", "yarnnn"]`), replaced with `content_class` enum (`["digests", "analyses", "briefs", "research", "insights"]`). Handler updated to pass `content_class` instead of `platform`. Fallback search excludes `platform='yarnnn'` rows.
- `api/services/primitives/search.py`: Removed `"yarnnn"` from Search tool platform enum.
- `api/services/platform_content.py`: Removed `"yarnnn"` from `PlatformType`, `"yarnnn_output"` from `RetainedReason`, and yarnnn TTL entry.
- Expected behavior: Agent outputs accumulate in `/knowledge/` filesystem (workspace_files) instead of `platform_content`. QueryKnowledge searches `/knowledge/` first, falls back to `platform_content` for external data. TP Search no longer offers `"yarnnn"` platform filter.

---

## [2026.03.11.4] - ADR-106 Phase 2: Workspace as singular source of truth

### Changed
- `api/services/workspace.py`: Added `ensure_seeded()` (lazy migration from DB columns), structured read methods (`get_observations()`, `get_review_log()`, `get_created_agents()`, `get_goal()`, `get_state()`), write helpers (`append_observation()`, `clear_observations()`, `append_review_log()`, `append_created_agent()`, `set_state()`, `record_observation()`).
- `api/services/agent_execution.py`: `generate_draft_inline()` reads instructions and memory from workspace via `AgentWorkspace`, not from `agent["agent_instructions"]` / `agent["agent_memory"]`.
- `api/services/proactive_review.py`: `_build_review_system_prompt()` and `apply_review_decision()` changed to async. All reads/writes use workspace files. `agent_memory` JSONB no longer read or written.
- `api/jobs/unified_scheduler.py`: Updated to `await apply_review_decision()`.
- `api/services/trigger_dispatch.py`: `_dispatch_medium()` and `_dispatch_medium_reactive()` use `ws.append_observation()` instead of JSONB manipulation.
- `api/services/primitives/edit.py`: `_handle_agent_memory_write()` writes to workspace files (observations.md, goal.md), not `agent_memory` JSONB.
- `api/services/primitives/execute.py`: `_handle_agent_acknowledge()` uses workspace observation.
- `api/services/primitives/coordinator.py`: Coordinator dedup log uses `ws.append_created_agent()`.
- `api/services/primitives/write.py`: Agent creation seeds workspace `AGENT.md`.
- `api/routes/agents.py`: Create/update endpoints seed/sync workspace `AGENT.md`.
- `api/services/working_memory.py`: `_extract_agent_scope()` reads from workspace.
- Expected behavior: All agent intelligence flows through workspace files. DB columns (`agent_instructions`, `agent_memory`) are write-through for backwards compat but never read for prompt injection or decision-making. Lazy migration seeds workspace from DB on first access.

---

## [2026.03.11.3] - ADR-106: Workspace convention alignment — AGENT.md + topic-scoped memory

### Changed
- `api/services/primitives/workspace.py`: Tool descriptions updated to reflect new conventions.
  - `ReadWorkspace`: `directives.md` → `AGENT.md`, `memory.md` → `memory/observations.md` + `memory/{topic}.md`
  - `WriteWorkspace`: References `memory/observations.md` and `memory/{topic}.md`
- `api/services/workspace.py`: `load_context()` reads `AGENT.md` (was `directives.md`), loads all files from `memory/` directory (was single `memory.md`). AGENT.md loaded first as identity context.
- `api/services/workspace.py`: `record_observation()` writes to `memory/observations.md` (was `memory.md`).
- `api/services/proactive_review.py`: Workspace observation writes target `memory/observations.md`.
- `api/services/execution_strategies.py`: Analyst directive references `memory/observations.md`.
- Expected behavior: Agents see AGENT.md as their identity file (like CLAUDE.md). Memory is topic-scoped — agents can create memory files on any topic. Convention alignment with Claude Code's filesystem patterns for future agent-to-agent interop.

---

## [2026.03.11.2] - ADR-103: Terminology guardrail — ban "deliverable" from TP output

### Changed
- `api/agents/tp_prompts/base.py`: Added terminology directive to Tone and Style section. TP must use "agent" or "work-agent" for recurring work entities, "runs" for outputs. Never say "deliverable" or "version".
- Expected behavior: TP chat responses will stop echoing "deliverable" language from training data. New conversations will use consistent agent/run terminology.

---

## [2026.03.11.1] - ADR-106: Agent Workspace Architecture — workspace primitives and analyst strategy

### Added
- `api/services/workspace.py`: New module — `AgentWorkspace` and `KnowledgeBase` abstraction classes. Virtual filesystem over Postgres (`workspace_files` table). Path-based operations (read, write, append, list, search, delete). Storage-agnostic design.
- `api/services/primitives/workspace.py`: Five new headless-only primitives:
  - `ReadWorkspace` — read from agent's workspace (thesis, memory, working notes)
  - `WriteWorkspace` — write/append to workspace (persist insights across runs)
  - `SearchWorkspace` — full-text search within agent's workspace
  - `QueryKnowledge` — search shared knowledge base (platform content). Falls back to `platform_content` table if workspace `/knowledge/` not yet populated.
  - `ListWorkspace` — list files in agent's workspace
- `api/services/execution_strategies.py`: `AnalystStrategy` — workspace-driven context gathering for reasoning agents. Loads thesis + memory + feedback from workspace instead of platform content dump.

### Changed
- `api/services/execution_strategies.py`: `get_execution_strategy()` now routes reasoning agents (deep_research, watch, coordinator, custom; proactive/coordinator modes) to `AnalystStrategy` instead of `HybridStrategy`. Reporter agents (digest, status, brief) unchanged.
- `api/services/agent_execution.py`: `HEADLESS_TOOL_ROUNDS` adds `analyst: 8` (reasoning agents need more tool rounds for workspace + knowledge base queries). `generate_draft_inline()` passes full agent dict to headless executor.
- `api/services/primitives/registry.py`: Workspace primitives registered in PRIMITIVES, HANDLERS, and PRIMITIVE_MODES (all headless-only). `create_headless_executor()` accepts optional `agent` param for workspace primitive context.
- `api/services/proactive_review.py`: `apply_review_decision()` writes observations to workspace `memory.md` alongside existing `agent_memory` JSONB.
- Expected behavior: Reasoning agents (Proactive Insights, Watch, Coordinator, Custom) will load their workspace context instead of receiving a chronological platform dump. They drive their own investigation via QueryKnowledge and WebSearch. Reporter agents (Digest, Status, Brief) are completely unchanged. First-run agents with empty workspaces will produce broad output, then focus as workspace accumulates.

---

## [2026.03.10.4] - ADR-105: Instructions to chat surface migration (prompt guidance)

### Changed
- `api/agents/tp_prompts/behaviors.py`: Added "Update audience" guidance to Agent Workspace Management section. TP now has an explicit example for persisting recipient_context via the Edit primitive when users describe who an agent is for.
- `api/agents/tp_prompts/tools.py`: Added "Audience" field documentation to Agent Workspace section between "Instructions" and "Observations", with Edit primitive example for setting recipient_context.
- Expected behavior: When a user says "this report is for my CTO Sarah, she cares about velocity", TP will use `Edit(ref="agent:{id}", changes={recipient_context: {...}})` to persist the audience context. Previously TP had examples for instructions and observations but not audience — it would append an observation instead of setting the structured recipient_context field.

---

## [2026.03.10.3] - ADR-104: Agent instructions as unified targeting layer

### Changed
- `api/services/agent_pipeline.py`: Added `{user_instructions}` slot to all 7 TYPE_PROMPTS templates. `build_type_prompt()` now injects `agent_instructions` into the user message as "USER INSTRUCTIONS (priority lens for this agent)". This is **dual injection** — instructions appear in both the headless system prompt (behavioral constraints, step 3 of ADR-101 composition) and the user message (priority lens for interpreting gathered context). Deleted dead code: `SECTION_TEMPLATES`, `normalize_sections()`, `build_sections_list()`, unused `LENGTH_GUIDANCE` entries (`scan`, `analysis`, `deep_dive`).
- `web/types/index.ts`: Removed dead `type_config` fields never consumed by `build_type_prompt()`: `DigestConfig.max_items`, all `BriefConfig` fields, `WatchConfig.threshold_notes`, all `DeepResearchConfig` fields, `CustomConfig.example_content`. Removed `TypeClassification.platform_grounding` and `freshness_requirement_hours` (stored, never consumed by any strategy).
- Expected behavior: Agent outputs should be more targeted. Previously, `agent_instructions` only influenced the system prompt — the agent saw instructions and gathered content in separate contexts. Now the agent sees instructions *alongside* the content it needs to interpret, providing a priority lens. Users who customize instructions should see noticeably more focused output.

---

## [2026.03.10.2] - Sync freshness consolidation: sync_registry as single source of truth

### Changed
- `api/services/freshness.py`: Added shared `calculate_freshness()` and `get_platform_freshness_from_registry()` — single source of truth for freshness calculations, eliminating duplicate implementations across working_memory.py and system_state.py.
- `api/services/working_memory.py`: Both platform freshness injection points (chat context + headless system state) now derive freshness from `sync_registry` instead of `platform_connections.last_synced_at`. Deleted local `_calculate_freshness()`.
- `api/services/primitives/system_state.py`: Platform-level freshness derived from `sync_registry` (max per-resource `last_synced_at`). Deleted local `_calculate_freshness()`, imports shared one from freshness.py.
- Expected behavior: TP and system status now reflect per-resource sync truth. A platform with some stale resources no longer appears "fresh" just because the sync process ran. Scheduler decisions use resource-level freshness, so partially-failed syncs get retried sooner.

---

## [2026.03.10.1] - Context provenance for agent runs (ADR-049 evolution)

### Changed
- `api/services/working_memory.py`: Agent-scoped TP sessions now receive source provenance in working memory injection. The `latest_version` scope includes `sources` (per-source platform/name/items_used), `total_items_fetched`, and `strategy`. TP can answer "what context was used?" from working memory without needing tool calls.
- `api/services/primitives/refs.py`: Read primitive now includes `source_snapshots` and `metadata` columns when reading version refs. TP can inspect full provenance details including `platform_content_ids`.
- Expected behavior: When a user opens agent-scoped chat and asks "what context was used for the latest version?", TP immediately sees the source list, per-source item counts, strategy used, and total items fetched. For deeper inspection, TP can read the version to get individual `platform_content_ids`.

---

## [2026.03.09.6] - Agent feedback loop: chat auto-persist + version feedback strip + email CTA

### Changed
- `api/agents/tp_prompts/behaviors.py`: Strengthened "Agent Workspace Management" section with explicit guidance for TP to auto-persist user feedback from chat as observations. Added "IMPORTANT" block explaining that headless generation does NOT see chat history — feedback must be written to agent_memory or agent_instructions to influence autonomous runs. Added patterns for direct feedback, implicit feedback, and corrections. Changed "don't update for one-off requests" to "still append observation even for one-offs".
- `web/components/agents/AgentRunDisplay.tsx`: Added `VersionFeedbackStrip` component — compact inline feedback UI on delivered version cards. Calls existing `updateVersion` API with `feedback_notes`. Shows on delivered/approved versions with content. Includes helper text explaining feedback shapes future runs.
- `api/services/platform_output.py`: Email footer CTA changed from "View agent in yarnnn" to "Reply with feedback" with subtext "Tell the agent what to change — it learns from your feedback." Encourages users to visit the agent page and engage with scoped chat or feedback strip.
- Expected behavior: Three complementary feedback paths now active. (1) Chat path: TP recognizes feedback in agent-scoped chat and proactively persists it via `Edit(append_observation)`, flowing into headless generation via `agent_memory.observations`. (2) Direct path: Users can leave `feedback_notes` on versions via the UI strip, flowing into headless generation via `get_past_versions_context()` → "Learned Preferences" in system prompt. (3) Email nudge: Delivered emails encourage users to provide feedback, driving them to the agent page.

---

## [2026.03.09.5] - yarnnn as internal content platform (ADR-102)

### Changed
- `api/services/platform_content.py`: Added `"yarnnn"` to `PlatformType` literal and `"yarnnn_output"` to `RetainedReason`. Added TTL entry (unused — yarnnn content is always retained).
- `api/services/agent_execution.py`: After successful delivery, writes the version draft as a `platform_content` row with `platform="yarnnn"`, `retained=True`, `retained_reason="yarnnn_output"`. Closes the accumulation loop — agent outputs become searchable context for TP and other agents.
- `api/services/primitives/search.py`: Search tool enum now includes `"yarnnn"` — agents can search agent outputs alongside platform content.
- `api/routes/system.py`: `content_platforms` includes `"yarnnn"` for system status content counts.
- `api/routes/admin.py`: Admin dashboard includes `"yarnnn"` in platform content counts and `"yarnnn_output"` in retention reason breakdown.
- Expected behavior: Each successful agent delivery now writes the generated content to `platform_content`. TP and headless agents can search across agent outputs via `platform="yarnnn"`. Cross-agent context sharing is now possible — a coordinator can reference outputs from agents it orchestrates.

---

## [2026.03.09.4] - JSONB type alignment + per-agent token tracking (ADR-101)

### Changed
- `api/services/anthropic.py`: `ChatResponse` dataclass now includes `usage: Optional[dict]`. `_parse_response()` extracts `response.usage.input_tokens` and `output_tokens` from Anthropic API responses. This was already done for the streaming path — now the non-streaming path (`chat_completion_with_tools`) also captures usage.
- `api/services/agent_execution.py`: `generate_draft_inline()` accumulates token usage across all tool rounds in the agentic loop and returns `(draft, usage)` tuple. `update_version_for_delivery()` accepts optional `metadata` dict stored on the version row. `execute_agent_generation()` passes token metadata to both `agent_runs.metadata` and `activity_log.metadata`.
- `supabase/migrations/096_version_metadata.sql`: Adds `metadata JSONB` column to `agent_runs`.
- `web/types/index.ts`: `AgentMemory` type completed with `review_log`, `created_agents`, `last_generated_at`. `AgentRun` extended with `metadata` field.
- `web/components/agents/AgentDrawerPanels.tsx`: MemoryPanel displays `review_log` entries with color-coded action pills. Prompt preview includes review history section.
- `web/components/agents/AgentRunDisplay.tsx`: Token count displayed on version cards (hover for input/output breakdown).
- Expected behavior: Each agent generation now records token usage. Version cards show total tokens used. MemoryPanel displays proactive review history. AgentMemory TypeScript type matches backend JSONB structure.

---

## [2026.03.09.3] - Fix empty draft on proactive agents hitting tool round limit

### Changed
- `api/services/agent_execution.py`: Reworded proactive review trigger prompt — no longer tells agent to "investigate themes further with your tools" (which caused tool-looping). Now says "focus on synthesizing insights from the gathered context."
- `api/services/agent_execution.py`: Added fallback synthesis call when agent hits max tool rounds with no text. Instead of failing with empty draft, makes one final API call with no tools available, forcing the agent to synthesize all gathered information into a response.
- Expected behavior: Proactive agents that previously failed with "Agent produced empty draft" when the agent exhausted tool rounds without producing text will now produce a draft via the forced synthesis fallback.

---

## [2026.03.09.2] - Agent intelligence model: close feedback loop (ADR-101)

### Changed
- `api/services/agent_execution.py`: `_build_headless_system_prompt()` now accepts `learned_preferences` parameter. Feedback from past version edits is injected as a "## Learned Preferences" section in the system prompt (after Memory, before Tool Usage). Previously this data was only in the type prompt (user message). `generate_draft_inline()` passes learned preferences to system prompt and empty string to type prompt to avoid duplication.
- `api/services/agent_pipeline.py`: `get_past_versions_context()` status filter changed from `eq("status", "approved")` to `in_("status", ["approved", "delivered"])`. This unbreaks the feedback loop for delivery-first (ADR-066) versions that skip the approval gate.
- `api/services/feedback_engine.py`: Deleted dead `create_feedback_memory()` function (never called). Updated module docstring to reference ADR-101.
- Expected behavior: Headless agent now sees learned preferences from user edits in its system prompt. For delivery-first agents, edit history from delivered versions is now included (previously only approved versions were queried, which excluded most versions under ADR-066).

---

## [2026.03.09.1] - Structured Instructions panel with prompt preview (frontend only)

### Changed
- `web/components/agents/AgentDrawerPanels.tsx`: Replaced single textarea InstructionsPanel with structured editor — Behavior Directives (agent_instructions), Audience (recipient_context, moved from Settings), Output Format (template_structure.format_notes, custom type only), and a live Prompt Preview showing composed agent context. Client-side `composePromptPreview()` mirrors `_build_headless_system_prompt()` logic.
- `web/components/agents/AgentSettingsPanel.tsx`: Removed Recipient Context section (moved to Instructions panel).
- No backend prompt changes — this is purely UI visibility. The agent receives exactly the same composed prompt as before.
- Expected behavior: Users can now see exactly what the agent receives from their instruction inputs, improving inspectability and confidence in agent configuration.

---

## [2026.03.07.1] - Proactive Insights review pass hardening (from Pass 4 testing)

### Changed
- `api/services/proactive_review.py`: Bumped REVIEW_MAX_TOOL_ROUNDS 3→5 for broader platform scanning. Added forced final turn (tools=[]) when all rounds exhausted — ensures agent always produces JSON decision. Improved deep_research search guidance: short single-topic queries ("decision", "blocked", "investor") instead of long multi-keyword strings that match nothing. Added text-based action extraction fallback when JSON not found.
- Expected behavior: Haiku review pass no longer exhausts tool rounds without producing a decision. Search queries now match actual platform_content. Graceful degradation: even if JSON parsing fails, action keyword is extracted from text.

---

## [2026.03.06.6] - Deep Research → Proactive Insights: signal-driven autonomous intelligence

### Changed
- `api/services/agent_pipeline.py`: Deleted entire old deep_research prompt (static `{focus_area}`, `{subjects_list}`, `{purpose}` fields). Replaced with v2 Proactive Insights prompt: autonomous signal detection from platform data, WebSearch for external context, BAD/GOOD examples showing generic news vs platform-grounded intelligence. New output format: "This Week's Signals" (internal signal + external context + why it matters) + "What I'm Watching" (progressive tracking). Updated section templates, default instructions, build_type_prompt (now just `{today_date}`). Simplified output validation (flat 200-word minimum, no depth tiers).
- `api/services/proactive_review.py`: Added `deep_research` type-specific review prompt. Haiku agent scans platform_content for emerging themes (HOT threads, DECISIONS, new contacts, stalled work). Uses WebSearch to check for external relevance. Signal vs noise distinction (strategic vs operational). Generates only when themes have internal momentum AND external context.
- `api/services/agent_execution.py`: Added proactive review trigger context forwarding — review decision note surfaced to generation agent as "Review Context" section.
- `api/services/skills.py`: Deleted old deep-research skill (form-based focus area dropdown). Replaced with Proactive Insights skill: no topic selection (autonomous), one per user, asks frequency (daily/weekly), all connected platforms as sources, mode=proactive.
- `api/routes/agents.py`: Replaced `DeepResearchConfig` (was `focus_area` enum, `subjects` list, `purpose`, `depth`) with `pulse_frequency` only. Changed type classification from `binding: research, temporal: on_demand` to `binding: hybrid, temporal: proactive`.
- Frontend: Updated type label, starter card, and landing page across `agents.ts`, `ChatFirstDesk.tsx`, `page.tsx`.
- Expected behavior: Deep research is now a persistent proactive agent that autonomously identifies interesting themes from the user's work platforms, researches them externally, and delivers intelligence the user didn't ask for. Two-phase execution: cheap Haiku review (most days sleep/observe) → full Sonnet generation only when warranted. Progressive learning via agent_memory observations and user refinement via scoped TP sessions.

---

## [2026.03.06.5] - Auto Meeting Prep prompt v3: deeper research, anti-flat output

### Changed
- `api/services/agent_pipeline.py`: Rewrote brief prompt from v2 → v3. Added explicit "you are a research assistant, not a calendar formatter" framing. Per-classification BAD/GOOD examples. WebSearch instruction for external contacts. "Search for each attendee" directive. Honest gap acknowledgment ("no results found" instead of padding). Recurring meetings: focus on what the OTHER person needs.
- `api/services/agent_execution.py`: Bumped brief type tool rounds from 3 → 5. Meeting prep benefits from per-attendee search + WebSearch more than other cross_platform types.
- Expected behavior: v3 output is significantly richer — agent uses WebSearch for external contacts, acknowledges information gaps honestly, connects dots between meetings (e.g., mentioning investor meeting during 1:1 prep). Output reads as intelligence, not reformatted calendar.

---

## [2026.03.06.4] - Brief → Auto Meeting Prep: daily calendar-driven prep with meeting classification

### Changed
- `api/services/agent_pipeline.py`: Deleted entire old brief prompt (static `{event_context}`, `{attendees}`, `{focus_areas}` fields). Replaced with v2 auto meeting prep prompt: scans calendar events for today + tomorrow morning, classifies each meeting (recurring internal / external / large group / low-stakes), adapts prep depth per classification. Updated section templates, default instructions, and build_type_prompt to compute `{today_date}` and `{date_range}` dynamically.
- `api/services/skills.py`: Deleted old brief skill (event-specific flow). Replaced with auto meeting prep skill: one per user guard, Google Calendar connection check, delivery time preference, auto-populated sources (calendar + all connected platforms).
- `api/routes/agents.py`: Replaced `BriefConfig` (was `event_title`, `attendees`, `focus_areas`, `depth`) with `delivery_time` only. Changed type classification from `reactive` to `scheduled` with 24hr freshness.
- Expected behavior: Brief type is now a daily-batch auto meeting prep. Runs every morning, preps all meetings for today + tomorrow morning with classification-adapted depth. Cross-platform context (Slack/Gmail/Notion) surfaced for attendee research.

---

## [2026.03.06.3] - Digest → Recap: platform-wide synthesis + rename

### Changed
- `api/services/agent_pipeline.py`: Rewrote `digest` TYPE_PROMPT from single-source summary to platform-wide recap. New two-part structure: Highlights (top 3-5 across entire platform) + By Source (subsections per channel/label/page). Updated default instructions to match.
- `api/services/skills.py`: Renamed skill to "Recap". Flow now asks which platform + frequency. Duplicate guard: 1 recap per platform per user. Sources auto-populated with all synced sources for selected platform.
- Expected behavior: Recap covers entire platform (all Slack channels, all Gmail labels, etc.) instead of a single source. Output is richer and more useful as a catchup tool.

---

## [2026.03.06.2] - Status prompt: stronger cross-platform connection language

### Changed
- `api/services/agent_pipeline.py`: Expanded the cross-platform connection bullet in the status prompt from a single line to a detailed section with concrete examples (e.g., "The Render deployment issues in #dev-ops align with billing alerts in Gmail"). Instructs the agent to look for same-topic threads, cause-and-effect chains, and people mentioned across platforms.
- Expected behavior: Part 1 synthesis now explicitly connects dots between platforms — the key differentiator that no single-platform tool can provide.

---

## [2026.03.06.1] - Status agent: two-part format (synthesis + platform breakdown)

### Changed
- `api/services/agent_pipeline.py`: Rewrote `status` TYPE_PROMPT to produce a two-part document: Part 1 is cross-platform synthesis (TL;DR, accomplishments, blockers, next steps with cross-platform connections); Part 2 is per-platform activity breakdown (Slack by channel, Gmail highlights, Notion updates, Calendar). Updated SECTION_TEMPLATES to include platform sections. Bumped LENGTH_GUIDANCE for standard/detailed to accommodate richer output.
- Expected behavior: Status agents now produce a more comprehensive document — intelligence at the top, evidence per platform below. Users get both "what matters" and "what happened where."

---

## [2026.03.05.7] - Agent creation: TP chat handoff + coordinator skill

### Changed
- `api/services/skills.py`: Added coordinator skill (was missing — only 6 of 7 types had skills). Added `create a {type}` trigger patterns to all type skills so TP chat pre-fill messages match correctly.
- `api/agents/tp_prompts/behaviors.py`: Added "Type-Specific Creation Guidance" table after agent creation section. TP now knows which 1-2 key questions to ask per type, default mode, and schedule.

### Expected behavior
- **Coordinator skill available**: `/coordinator` or "create a coordinator" triggers coordinator creation flow.
- **Type-specific creation**: TP asks focused questions per type instead of generic form-like questions. If user provides enough context, skips clarification entirely.
- **Frontend**: All "New Agent" buttons redirect to `/dashboard?create` which pre-fills TP chat with "I want to create a new agent". No separate create page.

---

## [2026.03.05.6] - Fix: working memory parallelization thread safety + skill detection resilience

### Changed
- `api/services/working_memory.py`: Each parallel thread now gets its own Supabase client instance instead of sharing one. Fixes `[Errno 35] Resource temporarily unavailable` from httpx connection pool thread-safety issue. Removed dead async wrapper functions (`_get_user_memory`, `_get_active_agents`, etc.) per singular implementation discipline.
- `api/services/skills.py`: `detect_skill_hybrid()` now catches general exceptions from semantic skill detection (not just `ImportError`). Missing `OPENAI_API_KEY` no longer crashes the chat flow — falls back to pattern matching gracefully.

### Expected behavior
- **Working memory parallelization works correctly**: 5 concurrent DB queries each with isolated httpx connection pool.
- **Chat flow resilient to missing OPENAI_API_KEY**: Semantic skill detection is best-effort; pattern matching alone is sufficient for core functionality.

---

## [2026.03.05.5] - TP qualitative experience: structural optimizations

### Changed
- `api/agents/thinking_partner.py`: `tool_choice` changed from `{"type": "any"}` to `{"type": "auto"}`. TP no longer forced to call a tool on every response — can answer directly from working memory for simple questions.
- `api/agents/tp_prompts/base.py`: "How You Work" section expanded with explicit "When to use tools" vs "When to answer directly from working memory" guidance. Examples updated to show direct answers for profile/agent/platform questions.
- `api/routes/chat.py`: History format switched from simplified text (`[Called ToolName]`) to structured `tool_use`/`tool_result` blocks. TP now sees proper tool call history across turns, reducing redundant tool calls.
- `api/routes/chat.py`: Inline session summary generation on session close — when a new session is created, the previous session's summary is generated as a background task instead of waiting for nightly cron.
- `api/services/working_memory.py`: Working memory queries parallelized via `asyncio.gather()` + `asyncio.to_thread()` (sync Supabase client). 5 independent DB queries now run concurrently instead of sequentially. Each thread gets its own client to avoid httpx pool thread-safety issues.
- `api/services/anthropic.py`: Tool result truncation now adds `_truncated` and `_truncation_note` metadata when results are clipped, so TP can report "showing 5 of 12 results" instead of silently presenting partial data.

### Expected behavior
- **Faster responses**: Simple questions answered directly without tool roundtrip. Working memory loads ~4x faster (parallel vs sequential queries).
- **Better multi-turn coherence**: Structured tool history lets TP reason about what it already called, reducing redundant Search/List calls.
- **No intraday context gaps**: Session summaries generated at close time, available immediately when user starts a new session.
- **Transparent truncation**: TP knows when results were clipped and can suggest narrowing the query.

---

## [2026.03.05.4] - Fix: agent ref visible in scoped working memory

### Changed
- `api/services/working_memory.py`: `format_for_prompt()` now renders `**Ref:** agent:{id}` in the scoped agent section. Previously the UUID was in the data dict but never shown in the prompt, forcing TP to List-resolve the ID before every Edit call.
- `api/agents/tp_prompts/behaviors.py`: Added explicit instruction to use the Ref from working memory for Edit calls — "do NOT guess or fabricate the agent ID."

### Expected behavior
- TP can now Edit agent instructions/observations/goals on the first attempt without a List roundtrip.
- Eliminates the `Edit→fail→List→Edit→success` pattern observed in qualitative testing.

---

## [2026.03.05.3] - Active agent workspace management: behavioral triggers for TP

### Changed
- `api/agents/tp_prompts/behaviors.py`: Replaced stale "Work Boundary (ADR-061)" section with two new sections:
  1. "Conversation vs Generation Boundary" — clarifies DO/DON'T without referencing obsolete ADR-061 Path A/B split. Adds "actively manage agent workspaces during scoped sessions" to the DO list.
  2. "Agent Workspace Management (ADR-087 / ADR-091)" — defines the dual posture: passive for user memory (nightly cron), active for agent workspace (real-time TP-managed). Includes concrete behavioral triggers: when to update instructions, append observations, update goals. Distinguishes scoped sessions (proactive steward) from general sessions (hands-off).
- `api/agents/tp_prompts/tools.py`: Fixed incorrect Edit syntax in Agent Workspace section — was using `action="append_observation", content="..."` (wrong), now uses `changes={append_observation: {note: "..."}}` and `changes={set_goal: {...}}` (matches actual Edit primitive). Added cross-reference to Behaviors for when-to-act guidance.

### Expected behavior
- **In agent-scoped sessions**: TP proactively updates instructions when user states output preferences ("make it shorter", "use bullet points"), appends observations when user shares relevant context or gives version feedback, and updates goals on milestone changes. This is analogous to Claude Code updating CLAUDE.md/memory for a project.
- **In general sessions**: TP only touches agent workspaces when explicitly asked. No unsolicited browsing or updating.
- **User memory unchanged**: Still handled by nightly cron extraction. TP acknowledges preferences naturally but does not call Write/Edit on user_memory.
- **Stale reference removed**: "Work Boundary (ADR-061)" replaced — ADR-061 was superseded by ADR-080.

---

## [2026.03.05.2] - Remove Conversation Analyst (ADR-060 superseded)

### Removed
- `api/services/conversation_analysis.py`: Entire file deleted. Background conversation pattern detection and suggested agent creation.
- `api/jobs/unified_scheduler.py`: Removed 6 AM UTC analysis phase (~90 lines) — no more daily behavioral pattern scanning.
- `api/routes/agents.py`: Removed `GET /suggested`, `POST /{id}/versions/{vid}/enable`, `DELETE /{id}/versions/{vid}/dismiss` endpoints. Removed `AnalystMetadata` model, `SuggestedRunResponse`, `_parse_analyst_metadata()`.
- `api/routes/admin.py`: Removed `POST /trigger-analysis/{user_id}` and `POST /trigger-analysis-all` admin endpoints.
- `api/services/notifications.py`: Removed `notify_suggestion_created()` and `notify_analyst_cold_start()`.
- `api/scripts/test_conversation_analyst.py`: Deleted test script.
- Frontend: Removed "Suggested for you" section, suggestion API calls, `SuggestedRun`/`AnalystMetadata` types.

### Expected behavior
- No more background LLM calls to analyze chat sessions for patterns.
- No more `status=suggested` versions or `status=paused` analyst-created agents.
- Coordinator agents (ADR-092) are the sole system-initiated creation path.
- Zero LLM cost from the daily analysis phase.

---

## [2026.03.05.1] - TP structural overhaul: agent context visibility & active management

### Added
- `api/services/primitives/refs.py`: Added `version` entity type to `ENTITY_TYPES` and `TABLE_MAP` (`"version": "agent_runs"`). Added `_resolve_version_ref()` for version-specific resolution including `version:latest?agent_id=X` pattern. TP can now read generated agent content.
- `api/services/primitives/search.py`: Added `version` search scope and `_search_versions()` handler. Supports `agent_id` filter parameter. Versions scoped through user's agents for security.
- `api/services/working_memory.py`: `_extract_agent_scope()` now queries `agent_runs` for latest version and includes `latest_version` dict (version_number, status, created_at, delivery_status, content_preview at 400 chars). `format_for_prompt()` renders this in the "Current agent" section.
- `api/agents/tp_prompts/tools.py`: Added "Agent Workspace" section documenting instructions editing, observation appending, goal setting, and version reading patterns. Added `version` to Reference Syntax types.
- `api/services/agent_pipeline.py`: Added `DEFAULT_INSTRUCTIONS` dict with per-type seed instructions for 7 agent types.
- `api/services/primitives/write.py`: Agent creation now seeds `agent_instructions` from `DEFAULT_INSTRUCTIONS` when not explicitly provided.

### Changed
- `api/services/agent_execution.py`: `_build_headless_system_prompt()` now accepts and renders `user_context` (profile + preferences from `user_memory`). Full `agent_memory` injection: goal, review_log (last 3), observations. `generate_draft_inline()` fetches lightweight user context before building prompt.
- `api/agents/tp_prompts/tools.py`: Replaced stale `"work"` references with `"agent"` in Reference Syntax types and Domain Terms. Removed "work = one-time agent task" domain term.
- `api/services/primitives/search.py`: Cleaned stale `"work"` scope reference from scope list and docstring.
- `api/services/primitives/write.py`: Removed stale `work:new` example from tool description.

### Expected behavior
- **Version visibility**: TP can now see generated content via `Read(ref="version:latest?agent_id=X")` or `Search(scope="version")`. In agent-scoped chat, latest version preview is auto-injected into working memory — no tool call needed.
- **Active workspace management**: TP has prompt guidance for updating instructions (`Edit`), appending observations, setting goals, and reading versions. New agents start with type-appropriate seed instructions.
- **Headless quality**: Draft generation now reflects user preferences (tone, verbosity) and full agent memory (goals, review history, observations). Adds ~300-500 tokens to headless prompt.
- **Stale cleanup**: No more "work" entity references in tool docs or search scopes.

---

## [2026.03.04.1] - ADR-091: Agent workspace primitives

### Changed
- `api/services/primitives/edit.py`: Added scoped `agent_memory` write paths — `append_observation` and `set_goal` keys on agent Edit calls. Raw `agent_memory` JSONB replacement blocked to prevent clobbering system-accumulated memory. Added `agent_instructions` as an editable field (was previously accepted by the generic update path but not documented or validated).
- `api/services/primitives/execute.py`: Added `agent.acknowledge` action — lightweight observation append to `agent_memory` from conversation context. Haiku-level cost, no generation triggered. Observations capped at 20 most recent. Removed dead `work.run` from tool description (deleted in ADR-090).

### Expected behavior
- TP can now update agent instructions from chat: `Edit(ref="agent:uuid", changes={agent_instructions: "Always use bullet points."})`
- TP can record user-shared context without triggering full generation: `Execute(action="agent.acknowledge", target="agent:uuid", params={note: "Q4 data is finalized"})`
- Memory writes are scoped (append-only for observations) — system-accumulated observations are preserved
- Enables ADR-091 agent workspace: chat on agent page can act on agent state directly

---

## [2026.03.03.2] - ADR-087 Phase 2: Simplified memory architecture

### Changed
- `api/services/memory.py`: Renamed `MemoryService` → `UserMemoryService`. Explicitly scoped as user_memory service. Deleted `process_feedback()`, `_analyze_edit_patterns()`, `process_patterns()`, `_detect_activity_patterns()`, `generate_session_summary()`. Only `process_conversation()` and `get_for_prompt()` remain.
- `api/services/working_memory.py`: `_extract_agent_scope()` now async — queries `chat_sessions` by `agent_id` FK at read time instead of reading `session_summaries` from JSONB. Removed `feedback_patterns` rendering from `format_for_prompt()`.
- `api/services/agent_execution.py`: `_build_headless_system_prompt()` no longer renders `feedback_patterns` — only `observations` from `agent_memory` JSONB.
- Expected behavior: Agent learning now happens through conversational iteration (TP chat + `agent_instructions`), not approval-gate edit-diff analysis. Session summaries are queried live via FK, not duplicated in JSONB.

### Added
- `api/services/session_continuity.py`: `generate_session_summary()` moved here from memory.py. Chat-layer feature for cross-session conversational continuity (YARNNN's equivalent of Claude Code auto-memory).

### Removed
- `process_feedback()` caller in `api/routes/agents.py` — approval-gate feedback loop deleted
- `process_patterns()` caller in `api/jobs/unified_scheduler.py` — activity pattern detection deleted
- `feedback_patterns` and `session_summaries` reads from `agent_memory` JSONB

---

## [2026.03.03.1] - ADR-087 Phase 1: Agent-scoped context injection

### Changed
- `api/services/working_memory.py`: `build_working_memory()` accepts optional `agent` dict. When scoped, injects agent instructions, observations, and goal into the working memory prompt under "### Current agent".
- `api/services/agent_execution.py`: `_build_headless_system_prompt()` accepts optional `agent` dict. Injects `agent_instructions` as "## Agent Instructions" and `agent_memory` observations as "## Agent Memory" into headless generation prompts.
- `api/agents/thinking_partner.py`: Passes `scoped_agent` parameter from chat route through to `build_working_memory()`.
- Expected behavior: When a user chats on a agent page, TP now sees that agent's instructions and accumulated memory. When headless generation runs, the agent sees the same context. Both modes share a common understanding of the agent.

---

## [2026.02.28.2] - Add RefreshPlatformContent primitive (ADR-085)

### Added
- `api/services/primitives/refresh.py`: New `RefreshPlatformContent` primitive — synchronous write-through cache refresh. Calls `_sync_platform_async()` (same pipeline as scheduler), awaits completion, returns summary. 30-minute staleness threshold prevents redundant syncs.
- `api/services/primitives/registry.py`: Registered as chat-only primitive (headless uses `freshness.sync_stale_sources()`).

### Changed
- `api/services/primitives/search.py`: Replaced ADR-065 "live-first" guidance with ADR-085 pattern (Search → RefreshPlatformContent → Search). Added "calendar" to platform enum.
- `api/services/primitives/execute.py`: Removed `platform.sync` action (singular implementation — replaced by RefreshPlatformContent). Added helpful error message redirecting TP to new primitive.
- `api/agents/tp_prompts/platforms.py`: Updated "Reading platform content" section from fire-and-forget to synchronous refresh flow.
- `api/agents/tp_prompts/behaviors.py`: Replaced Step 3 (fire-and-forget + STOP) with synchronous refresh-and-requery pattern.
- `api/agents/tp_prompts/tools.py`: Added RefreshPlatformContent to tool docs. Updated Search description. Removed platform.sync from Execute examples.

### Behavior
- TP can now answer real-time platform questions within a single chat turn (Search → Refresh → Search → answer)
- No more "come back in 30-60 seconds" dead end when cache is stale/empty
- `Execute(action="platform.sync")` returns a helpful redirect message instead of running

---

## [2026.02.28.1] - Fix Google/Gmail/Calendar domain separation in TP context

### Changed
- `api/services/working_memory.py`: Fixed `format_for_prompt()` platform status check from `== "connected"` to `== "active"` (matching DB enum). Added calendar as separate connected platform synthesized from the "gmail" DB row. TP now sees both "gmail" and "calendar" in working memory and system summary.
- `api/services/project_tools.py`: `handle_list_integrations()` now synthesizes a "calendar" item from the "gmail" DB row. TP's `list_integrations` tool returns both gmail and calendar as connected platforms.
- `api/services/platform_tools.py`: Calendar tools (mapped to "google" in registry) now load when "gmail" is connected. TP has access to calendar tools when Google OAuth is active.

### Behavior
- TP no longer reports "Gmail is disconnected" when platform_connections has status="active"
- TP sees calendar as a connected platform and can use calendar tools
- Working memory shows freshness for both gmail and calendar separately

---

## [2026.02.27.2] - Dead code deletion: remove all deprecated type code (ADR-082)

### Deleted
- `api/services/agent_pipeline.py`: Deleted 19 deprecated TYPE_PROMPTS entries, 19 SECTION_TEMPLATES entries, 16 deprecated validation functions (`validate_stakeholder_update`, `validate_meeting_summary`, `validate_client_proposal`, `validate_performance_self_assessment`, `validate_newsletter_section`, `validate_changelog`, `validate_one_on_one_prep`, `validate_board_update`, `validate_inbox_summary`, `validate_reply_draft`, `validate_follow_up_tracker`, `validate_thread_summary`, `validate_slack_standup`, `validate_deep_research`, `validate_daily_strategy_reflection`, `validate_intelligence_brief`). Deleted deprecated VARIANT_PROMPTS (email_summary, email_draft_reply, email_follow_up, email_weekly_digest, email_triage, notion_page, weekly_status, project_brief, cross_platform_digest, activity_summary) and their handler branches in `_build_variant_prompt()`. `validate_output()` reduced to 6 active validators.
- `api/routes/agents.py`: Deleted 6 deprecated Pydantic config models (DeepResearch*, DailyStrategyReflection*, IntelligenceBrief*). TypeConfig union reduced to 6 active types. `get_default_config()` reduced to 6 entries. Removed unused `Annotated` import.
- `web/types/index.ts`: Deleted 24 deprecated TypeScript interfaces (Section + Config pairs for all deprecated types). Deleted `SynthesizerType`. TypeConfig union reduced to 6 active types + `Record` fallback.
- `web/components/modals/AgentSettingsModal.tsx`: AGENT_TYPE_LABELS reduced to 8 active types.
- `web/components/surfaces/IdleSurface.tsx`: AGENT_TYPE_LABELS reduced to 8 active types.

### Behavior
- Deprecated types still work via aliasing in `get_type_classification()` and `_TYPE_PROMPT_ALIASES` in `build_type_prompt()` — they route to the parent type's prompt, strategy, and validation.
- No backwards-compatibility shims for the deleted code per CLAUDE.md Section 2.

---

## [2026.02.27.1] - Type consolidation: 27→8 active types (ADR-082)

### Changed
- `api/services/signal_processing.py`: Updated `_REASONING_SYSTEM_PROMPT` to reference only active types (`status_report`, `research_brief`, `custom`) instead of deprecated types (`daily_strategy_reflection`, `intelligence_brief`, `deep_research`). Updated JSON examples accordingly. Removed hardcoded `MEETING_PREP_TYPE_CLASSIFICATION` — now uses `get_type_classification()` from routes.
- `api/services/agent_pipeline.py`: `build_type_prompt()` now resolves deprecated types to parent type's prompt template and field mapping via `_TYPE_PROMPT_ALIASES`. e.g., `stakeholder_update` → `status_report` template.
- `api/services/conversation_analysis.py`: Removed `weekly_status` from `SUGGESTABLE_TYPES` (deprecated, absorbed by `status_report`).

### Behavior
- Signal processing now instructs the LLM to create only active types. Deprecated types returned by LLM still work via aliasing in `get_type_classification()`.
- Deprecated types in existing agents use parent type's prompt template on next execution, not their original dedicated prompt.
- Conversation analysis no longer suggests `weekly_status` as an agent type.

---

## [2026.02.26.4] - Execution path consolidation: absorb web research into headless mode (ADR-081)

### Changed
- `api/services/agent_execution.py`: `_build_headless_system_prompt()` now accepts `research_directive` parameter. When provided (research/hybrid bindings), the system prompt includes a `## Research Directive` section instructing the agent to actively use WebSearch, replacing the default conservative "use tools only if needed" guidance. `generate_draft_inline()` accepts `research_directive` and uses binding-aware tool round limits (`HEADLESS_TOOL_ROUNDS` dict) instead of flat `HEADLESS_MAX_TOOL_ROUNDS=3`.
- `api/services/execution_strategies.py`: `ResearchStrategy` and `HybridStrategy` no longer call `web_research.research_topic()`. Instead they gather platform context only and pass a `research_directive` string via `GatheredContext.summary`. New `_build_research_directive()` helper builds the directive from agent title/description.
- `api/services/web_research.py`: Marked as DEPRECATED. No longer imported by any pipeline code.

### Behavior
- Research-type agents (`research_brief`, `deep_research`) now use the headless agent's WebSearch primitive for web research during generation, instead of a separate pre-generation web research loop. The agent can do targeted research informed by the agent template.
- Binding-aware tool rounds: platform_bound=2, cross_platform=3, research=6, hybrid=6 (was flat 3 for all).
- Eliminates one of three independent agentic loops in the agent pipeline, achieving true "one agent, two modes" as ADR-080 intended.
- Cost profile: research types may use more tool rounds (up to 6) but eliminate a separate Sonnet call from `web_research.py`. Net cost should be comparable.

---

## [2026.02.26.3] - Headless mode: agentic generation with read-only tools (ADR-080 Phase 1+2)

### Changed
- `api/services/agent_execution.py`: `generate_draft_inline()` now uses `chat_completion_with_tools()` instead of `chat_completion()`. Agent runs in headless mode with read-only tools (Search, Read, List, WebSearch, GetSystemState) and max 3 tool rounds. New `_build_headless_system_prompt()` extracts and enhances the system prompt with tool usage instructions.
- `api/services/primitives/registry.py`: Added `PRIMITIVE_MODES` dict, `get_tools_for_mode()`, and `create_headless_executor()` for mode-gated primitive access.

### Behavior
- Agent generation is now agentic — the agent CAN use read-only tools to investigate when gathered context is insufficient, but is instructed to prefer generating from provided context directly.
- Most agents will generate in a single turn (no tool use), same as before. The tools are a safety net for when context gathering misses something.
- System prompt restructured into sections (Output Rules, Tool Usage) for clearer instruction following.
- Cost impact: ~0-3 additional API calls per generation in the rare case tools are used. Typical case unchanged (single call).

---

## [2026.02.26.2] - Signal context forwarding to agent generation (ADR-080 Phase 0)

### Changed
- `api/services/agent_execution.py`: System prompt now includes signal reasoning and signal context (entity, platforms) when an agent is triggered by signal processing. Added `trigger_context` parameter to `generate_draft_inline()`.
- `api/services/signal_processing.py`: `_queue_signal_emergent_execution()` now forwards `reasoning_summary` and per-action `signal_context` from the SignalAction into `trigger_context`.

### Behavior
- Signal-emergent agents now receive the LLM reasoning that caused their creation, enabling the generation step to understand WHY the agent exists and focus on the relevant entity/pattern.
- Previously, `trigger_context={"type": "signal_emergent"}` passed zero intelligence. Now includes `signal_reasoning` (up to 1000 chars) and `signal_context` (entity, platforms).
- Non-signal-triggered agents are unaffected (trigger_context is None or lacks signal fields).

---

## [2026.02.26.1] - Agent quality: no-emoji, conciseness, calendar preview rewrite

### Changed
- `api/services/agent_execution.py`: System prompt now instructs no-emoji output, enforces conciseness preference, uses plain markdown headers.
- `api/services/agent_pipeline.py`: Rewrote `weekly_calendar_preview` prompt to analyze raw event data instead of expecting pre-computed stats ({meeting_count}, {total_hours} etc. were never filled). Prompt now instructs LLM to compute counts from context.
- `api/services/agent_pipeline.py`: Updated `gmail_inbox_brief` prompt to explicitly request plain markdown headers and no-emoji output.

### Behavior
- All agent types now produce plain markdown output without emoji headers
- Calendar preview no longer shows "N/A" placeholders — derives stats from raw event data
- Gmail inbox brief uses consistent `## Urgent`, `## Action Required` headers instead of emoji variants
- User conciseness preferences (from working memory) are now prioritized by system prompt

---

## [2026.02.25.1] - Eliminate MCP Gateway, all platforms use Direct API (ADR-076)

### Changed
- `api/services/platform_tools.py`: Replaced `_handle_mcp_tool()` with `_handle_slack_tool()` using `SlackAPIClient`. Deleted `map_to_mcp_format()`, normalization helpers. All platform routing now uses Direct API.
- `api/integrations/exporters/slack.py`: Replaced `call_platform_tool()` gateway calls with `slack_client.post_message()` / `get_channel_info()`.
- `api/workers/platform_worker.py`: Replaced `MCPClientManager` subprocess manager with `get_slack_client()` direct API calls.
- `api/jobs/import_jobs.py`: Replaced `get_mcp_manager()` with platform-specific clients (`get_slack_client()`, `get_notion_client()`).
- `api/integrations/validation.py`: Fixed broken Gmail validation test (was calling nonexistent method). All 3 platform tests now use Direct API clients.

### Behavior
- **No user-facing behavior change** — all Slack operations (list channels, get history, post messages, join channels) work identically via Direct API.
- **Removed**: `mcp-gateway/` Node.js service, `MCPClientManager`, `mcp_gateway.py` HTTP client.
- **Performance**: Eliminates network hop (Python → Node.js → Slack becomes Python → Slack).

---

## [2026.02.24.6] - Consolidate notification architecture (single path)

### Changed
- `api/jobs/unified_scheduler.py`: Removed all agent notification email logic. Scheduler no longer sends `send_agent_ready_email()` or `send_agent_failed_email()`. Exception handler now calls `notify_agent_failed()` from notifications.py instead.
- `api/jobs/email.py`: Deleted `send_agent_ready_email()` and `send_agent_failed_email()` — legacy functions only used by the scheduler.
- `api/services/delivery.py`: Always calls `_notify_delivered()` (removed email-platform skip). Passes `delivery_platform` to notification service for skip decision.
- `api/services/notifications.py`: `notify_agent_delivered()` now accepts `delivery_platform` param. When platform is "email"/"gmail", logs as in_app notification instead of sending a separate email (content email IS the notification). Removed unused `notify_agent_ready()`.

### Behavior
- **Single notification path**: All agent notifications flow through `delivery.py` → `notifications.py`. The scheduler only handles generation + scheduling.
- **Email-platform skip logic** lives in one place (`notifications.py`) instead of three (was in scheduler, delivery.py, and notifications.py).
- No change to user-facing behavior — email deliveries still produce exactly 1 email (the content), non-email deliveries still get a notification email.

---

## [2026.02.24.5] - Agent detail page rewrite (content-first layout)

### Changed
- `web/app/(authenticated)/agents/[id]/page.tsx`: Full rewrite — content-first layout with rendered markdown (ReactMarkdown), version selection via delivery history rows, clean status model (delivered/failed/generating only), execution details bar with source snapshot pills.
- Added `react-markdown` and `@tailwindcss/typography` dependencies for markdown rendering.

### Behavior
- Agent content is now the hero element, rendered as formatted markdown instead of hidden behind a collapsible `<details>` element
- Delivery history rows switch the content area on click (replaces accordion pattern)
- Source snapshots, word count, and delivery timestamps shown inline
- Failed versions show error banner with delivery_error message and Retry button
- Legacy status mappings (staged, reviewing, approved, rejected) removed

---

## [2026.02.24.4] - ResendExporter: default email delivery without OAuth

### Changed
- `api/integrations/exporters/resend.py`: New `ResendExporter` — delivers content via Resend API (server-side, no user OAuth). Registered as `platform="email"` handler.
- `api/integrations/exporters/registry.py`: Register `ResendExporter` as default "email" handler. `GmailExporter` remains for explicit Gmail drafts/sends via OAuth.
- `api/services/delivery.py`: Added "email" to no-auth platforms in `_get_exporter_context()`.
- `api/jobs/unified_scheduler.py`: Skip notification email when content was delivered via email (content email IS the notification). Failure emails still send.
- `api/routes/agents.py`: Added `delivery_error` to `VersionResponse` model; populated `source_snapshots`, `analyst_metadata`, `source_fetch_summary`, `delivery_error` in detail endpoint.

### Behavior
- All users receive agent outputs via email regardless of Google OAuth status (Resend = server-side API key)
- `GmailExporter` (`platform="gmail"`) remains for creating Gmail drafts or sending as user's own address
- No duplicate notification email when content already lands in user's inbox
- `/agents/{id}` API now returns full version metadata (delivery_error, source_snapshots, etc.)

---

## [2026.02.24.3] - Fix signal processing: agent ID missing from prompt

### Changed
- `api/services/signal_processing.py`: Include agent UUID in brackets in EXISTING AGENTS list (`[uuid] Title (type, next run: ...)`). Previously only showed title, causing LLM to return title as `trigger_agent_id` instead of UUID — which crashed with "invalid input syntax for type uuid".
- Added UUID validation guard in `_parse_reasoning_response()` to reject non-UUID `trigger_agent_id` values gracefully instead of crashing.

### Behavior
- `trigger_existing` actions now work correctly — LLM can see and return the actual UUID
- Invalid IDs logged as warnings instead of crashing the entire signal processing run

---

## [2026.02.24.2] - Fix email delivery: Gmail/Google platform connection lookup

### Changed
- `api/services/delivery.py`: `_get_exporter_context()` now falls back from `gmail` to `google` when looking up platform connections. Google OAuth stores both Gmail and Calendar under the `google` platform name, but the email exporter looked for `gmail` only, causing "No email integration connected" errors.

### Behavior
- Email delivery (`platform: "email"`) now works for users with Google OAuth connections stored as `platform = "google"`
- Fixes agent delivery failures where content was generated successfully but couldn't be emailed

---

## [2026.02.24.1] - Fix ADR-035 Wave 1 prompt template field mappings

### Changed
- `api/services/agent_pipeline.py`: Added `elif` blocks for `slack_channel_digest`, `slack_standup`, `gmail_inbox_brief`, and `notion_page_summary` in `build_type_prompt()`. These types had prompt templates defined in `TYPE_PROMPTS` but no field mapping in the main function, causing KeyError fallback to the generic custom template.

### Behavior
- `slack_channel_digest` now renders with proper `{focus}`, `{reply_threshold}`, `{reaction_threshold}`, `{sections_list}` fields
- `slack_standup` renders with `{source_mode}`, `{format}`, `{sections_list}`
- `gmail_inbox_brief` renders with `{focus}`, `{sections_list}`
- `notion_page_summary` renders with `{summary_type}`, `{max_depth}`, `{sections_list}`
- All Wave 1 types now produce type-specific output instead of degrading to generic custom format

---

## [2026.02.23.9] - Add signal.process Execute action for TP orchestration

### Changed
- `api/services/primitives/execute.py`: Added `signal.process` action to Execute primitive. TP can now trigger signal extraction + LLM triage + action execution via `Execute(action="signal.process", target="system:signals")`. Same pipeline as manual trigger endpoint and scheduler.
- `api/services/primitives/refs.py`: Added `system` entity type for system-level targets (e.g., `system:signals`).

### Behavior
- TP can now proactively process signals when asked ("check for updates", "process my signals", etc.)
- Respects tier gate (Starter+ only) and returns structured results with reasoning
- Execute tool description updated with new action and example

---

## [2026.02.23.8] - Fix Gmail content extraction (full body, title, author)

### Changed
- `api/workers/platform_worker.py`: Added `_extract_gmail_body()` that decodes base64 Gmail payloads (simple, multipart, nested multipart) to extract full plain text. Falls back to HTML→text stripping, then to snippet. Previously only stored `snippet` (~200 chars). Also populates `title` (subject), `author` (sender), and adds `subject`/`thread_id` to metadata.
- `api/workers/platform_worker.py`: `_store_platform_content()` now accepts and writes `title` and `author` params to `platform_content` table.

### Behavior
- Gmail emails now store full body text (up to 10k chars) instead of 200-char snippets
- Signal processing gets richer email content for triage
- No prompt/tool changes

---

## [2026.02.23.7] - Fix Google provider dispatch + admin test endpoints

### Changed
- `api/workers/platform_worker.py`: Added `"google"` provider handling. When scheduler passes `provider="google"`, worker now splits `selected_sources` by resource type (gmail labels vs calendar calendars) using `landscape.resources[].metadata.platform`, then runs both `_sync_gmail()` and `_sync_calendar()` sub-syncs. Previously hit "Unknown provider" branch silently.
- `api/routes/admin.py`: Added `trigger-sync` and `trigger-signal-processing` admin endpoints (service-key auth) for per-platform testing without user JWT.

### Behavior
- Google OAuth sync now works end-to-end: Gmail emails and Calendar events fetched in a single sync call
- No prompt/tool changes

---

## [2026.02.23.6] - Fix Gmail/Calendar signal extraction platform alias

### Changed
- `api/services/signal_extraction.py`: Google OAuth stores `"google"` in `platform_connections.platform`, but worker writes `platform_content` with `platform="gmail"` and `platform="calendar"`. Signal extraction dispatch now checks for any of `"google"`, `"gmail"`, `"calendar"` in `active_platforms` to handle both naming conventions.

### Behavior
- Gmail and Calendar content now included in signal extraction regardless of whether the platform connection is stored as `"google"`, `"gmail"`, or `"calendar"`
- No prompt/tool changes

---

## [2026.02.23.5] - Tier model hardening: token budget, signal gating, sync frequency

### Changed
- `api/services/platform_limits.py`: Complete tier model overhaul (ADR-053):
  - Replaced `tp_conversations_per_month` with `daily_token_budget` (50k/250k/1M)
  - Updated source limits: free=2, starter=5, pro=unlimited (-1)
  - Added `1x_daily` sync frequency for free tier
  - Calendar sources set to -1 (no source selection)
  - All platforms open (total_platforms=4 for all tiers)
  - Removed dead `check_platform_limit()`, `check_tp_conversation_limit()`, `get_tp_conversation_count()`
  - Added `check_daily_token_budget()` and `get_daily_token_usage()` via SQL RPC
- `api/routes/chat.py`: Token budget enforcement replaces conversation count limit. Token usage persisted to `session_messages.metadata` (`input_tokens`, `output_tokens`).
- `api/routes/signal_processing.py`: Free-tier users blocked from manual signal processing trigger (403).
- `api/jobs/unified_scheduler.py`: Signal processing phase skips free-tier users.
- `api/services/signal_processing.py`: `execute_signal_actions()` checks agent limit before creating signal-emergent agents.
- `supabase/migrations/079_daily_token_usage.sql`: SQL function `get_daily_token_usage()` for efficient daily token aggregation.

### Frontend
- All sync frequency labels updated for `1x_daily` (SyncStatusBanner, ConnectionDetailsModal, system page, ResourceList)
- Context pages (slack, gmail, notion, calendar) handle `?status=connected` OAuth redirect param
- TypeScript types updated: `daily_token_budget`/`daily_tokens_used` replaces conversation fields
- `useChatGate` → `useTokenBudgetGate`, limits.ts updated for new tier model

### Behavior
- Free tier: 50k tokens/day, 2 sources/platform, 1x/day sync, 2 agents, no signal processing
- Starter: 250k tokens/day, 5 sources, 4x/day sync, 5 agents, signal processing on
- Pro: unlimited tokens, unlimited sources, hourly sync, unlimited agents

---

## [2026.02.23.4] - Fix signal processing crash + scheduler health query

### Changed
- `api/routes/signal_processing.py`: Removed `.order("agent_runs(created_at)")` — PostgREST PGRST118 error on one-to-many related table ordering. Sort versions client-side instead.
- `api/jobs/unified_scheduler.py`: Same PGRST118 fix for scheduler signal processing path.
- `api/services/primitives/system_state.py`: `_get_scheduler_health()` now queries per-user heartbeats instead of non-existent sentinel UUID `00000000-...`.
- `web/app/(authenticated)/system/page.tsx`: Removed dead Conversation Analyst icon map entry + unused MessageSquare import.

### Behavior
- Signal processing no longer crashes with 500 when agents exist
- TP GetSystemState primitive now correctly retrieves scheduler heartbeat data
- No prompt/tool definition changes

---

## [2026.02.23.3] - Sync pipeline reliability + status surfacing fixes

### Changed
- `api/workers/platform_worker.py`: Worker now checks for `error` key + 0 items before reporting success. Only updates `last_synced_at` on actual success. Activity log includes `(error)` or `(success)` label.
- `api/routes/signal_processing.py`: Signal trigger writes `signal_processed` to `activity_log` even on early return (no signals found), so system page shows last run time instead of "Never Run".
- `api/routes/system.py`: Platform Sync status aggregates all `platform_synced` events in 30-min window instead of `limit(1)`.
- `api/jobs/unified_scheduler.py`: Heartbeat writes per real `user_id` from `platform_connections` instead of dummy UUID (FK violation fix).

### Behavior
- No prompt/tool changes — these are backend reliability fixes
- Worker no longer reports false success when OAuth token decryption fails
- System page shows consistent, accurate status across all processing phases

---

## [2026.02.23.2] - ADR-073: Implement unified fetch architecture in code

### Changed
- `api/services/execution_strategies.py`: Migrated PlatformBound + CrossPlatform strategies from live API calls (`fetch_integration_source_data`) to `platform_content` reads via `get_content_summary_for_generation()`. Added `platform_content_ids` field to `GatheredContext` for retention tracking. Research and Hybrid strategies propagate content IDs from delegated CrossPlatform calls.
- `api/services/signal_extraction.py`: Complete rewrite — replaced `_fetch_calendar_content`, `_fetch_gmail_content`, `_fetch_slack_content`, `_fetch_notion_content` (live API calls) with `_read_*` variants that query `platform_content` table. Same output shape (`SignalSummary`) so `signal_processing.py` unchanged.
- `api/services/agent_execution.py`: Wired `mark_content_retained()` after draft generation to mark consumed content as retained. Fixed source snapshot logic (sources_used became strings after migration). Deleted legacy `gather_context_inline()` and `_get_relevant_memories()`.
- `api/services/agent_pipeline.py`: Deleted ~1440 lines — `fetch_integration_source_data`, all `_fetch_*_data` helpers, `execute_agent_pipeline`, pipeline step functions, cache infrastructure. Retained: `TYPE_PROMPTS`, validation functions, `build_type_prompt`, `get_past_versions_context`.
- `api/workers/platform_worker.py`: Fixed Slack method name bug — `get_slack_messages()` → `get_slack_channel_history()` (actual MCP client method).
- `api/services/platform_content.py`: Deleted deprecated backward-compat stubs (`FilesystemItem`, `store_filesystem_item`, `get_filesystem_items`, etc.).

### Removed
- `fetch_integration_source_data()` and all per-platform live fetch helpers from `agent_pipeline.py`
- `gather_context_inline()` from `agent_execution.py` (superseded by `execution_strategies.py`)
- All live API calls from `signal_extraction.py` (now reads from `platform_content`)
- Deprecated `FilesystemItem` alias and stub functions from `platform_content.py`

### Behavior
- **Single fetch path enforced**: Only `platform_sync_scheduler` → `platform_worker` calls external APIs. All consumers (execution strategies, signal extraction, agents) read from `platform_content` table.
- **Content retention wired**: Platform content consumed during agent generation is marked retained (excluded from TTL cleanup).
- **Slack sync fixed**: Method name mismatch that would have caused runtime errors corrected.
- **No behavioral change to signal_processing.py**: LLM triage still runs; transformation to scheduling heuristics is deferred per ADR-073 migration path.

---

## [2026.02.23.1] - ADR-073: Unified Fetch Architecture + Platform Integrations rewrite

### Added
- `docs/adr/ADR-073-unified-fetch-architecture.md`: Establishes single fetch path (platform_sync only), eliminates triple-fetch pattern (sync + signal extraction + agent execution all calling live APIs independently). Defines per-platform fetch specs (time windows, source filtering, sync token strategy, items per source, TTLs). Documents retention lifecycle wiring, scheduling heuristics replacing LLM signal triage, and deferred webhook strategy.

### Changed
- `docs/integrations/PLATFORM-INTEGRATIONS.md`: Full rewrite reflecting ADR-073 architecture. Documents singular fetch → platform_content → consumers data flow. Per-platform specification tables (Slack, Gmail, Calendar, Notion) with credential handling, sync token approach, content types, TTLs. Replaces prior documentation that showed three independent data paths.

### Architectural decisions
- Signal processing LLM triage (Haiku call per user per hour) to be replaced by scheduling heuristics (rules + freshness checks, no LLM). LLM reasoning happens at consumption time only (TP chat or agent execution).
- Monetization enforcement scoped to ADR-074 (separate).
- Observability scoped to separate feature documentation.
- `mark_content_retained()` and `cleanup_expired_content()` to be wired into existing pipeline.

---

## [2026.02.19.15] - Calendar full CRUD: update_event + delete_event

### Added
- `api/integrations/core/google_client.py`: `update_calendar_event()` — PATCH semantics, only provided fields changed
- `api/integrations/core/google_client.py`: `delete_calendar_event()` — DELETE, treats 204 and 410 (already deleted) as success
- `api/services/platform_tools.py`: `platform_calendar_update_event` tool — enforces list→get→confirm→update workflow in description; all fields optional except `event_id`
- `api/services/platform_tools.py`: `platform_calendar_delete_event` tool — enforces list→get→explicit confirm→delete; emphasizes permanence
- `api/services/platform_tools.py`: Handlers for both new tools in `_execute_calendar_tool()`
- `api/agents/tp_prompts/platforms.py`: "Calendar CRUD — full workflow" section with step-by-step Read/Create/Update/Delete instructions; explicit note that scheduling intelligence (conflict detection, free-slot reasoning, timezone awareness) is TP's responsibility, not a separate Python service

### Expected behavior
- TP can now modify and delete existing calendar events, completing the full CRUD surface
- TP will always list→get before modifying (enforced by tool description workflow)
- TP will confirm with user before update, and get explicit confirmation before delete
- Scheduling intelligence (finding free slots, checking conflicts) happens in TP's reasoning context using list_events data — no separate Python logic needed

---

## [2026.02.19.14] - Activity tracking gaps fixed

### Added
- `supabase/migrations/063_activity_log_event_types.sql`: Extends CHECK constraint with 4 new event types:
  `integration_connected`, `integration_disconnected`, `agent_approved`, `agent_rejected`
- `api/services/activity_log.py`: Added all 4 new types to `VALID_EVENT_TYPES`
- `api/routes/integrations.py`: Logs `integration_connected` after OAuth callback success;
  logs `integration_disconnected` after disconnect
- `api/routes/agents.py`: Logs `agent_approved` / `agent_rejected` after version status change;
  also fetches `title` from agents for human-readable summary
- `web/app/(authenticated)/activity/page.tsx`: Added display config for all 4 new event types
  (ThumbsUp/ThumbsDown icons for approvals, Link/Unlink for integrations); click navigation to
  agent page or integration context page; `FILTER_TYPES` constant for curated filter chips

---

## [2026.02.19.13] - ADR-066: Delivery-first, remove governance

### Changed
- `api/services/agent_execution.py`: Remove governance gate, always deliver immediately
  - No more `staged` status — versions go directly to `delivered` or `failed`
  - Removed governance check before delivery (manual/semi_auto/full_auto → always deliver)
  - Added `update_version_for_delivery()` to replace `update_version_staged()`
  - Error status changed from `rejected` to `failed`
  - Activity log records delivery result, not governance state

- `web/app/(authenticated)/agents/[id]/page.tsx`: Delivery-first detail page
  - Removed Approve/Reject buttons (no governance workflow)
  - "Latest Output" → "Latest Delivery" with delivery status
  - "Previous Versions" → "Delivery History"
  - Added platform badge in header
  - Added external link to delivered content
  - Added Retry button for failed deliveries

- `web/app/(authenticated)/agents/page.tsx`: Enhanced list view per ADR-067
  - Platform badges on every card (not just group headers)
  - Delivery status (delivered/failed) instead of governance
  - Schedule status (Active/Paused) independent from delivery
  - Destination visibility with arrow indicator

### Behavior
- Agents now deliver immediately when generated — no approval step
- Users control automation via Pause/Resume, not Approve/Reject
- Single-user workflow: scheduling + pause is sufficient governance
- Multi-user governance can be re-added as feature flag in future

---

## [2026.02.19.12] - Agent creation flow: delivery options + instant run

### Changed
- `web/components/surfaces/AgentCreateSurface.tsx`: Platform-agnostic delivery options + instant run
  - Added delivery mode selector: Email (default), Slack DM, or Platform Channel
  - Email sends to user's registered email address (fetched from Supabase auth)
  - Slack DM sends as direct message to user (if Slack is connected)
  - Platform Channel shows channel selector (original behavior)
  - Instant run: Creates agent AND immediately triggers run for instant gratification
  - Button changed from "Create" to "Create & Run" with Play icon
  - Notice updated to explain instant run behavior

### Behavior
- Users get immediate feedback when creating an agent (runs on creation)
- Default delivery is email, no longer requires selecting a platform channel
- Builds trust by showing sample output immediately after setup

---

## [2026.02.19.12] - Rewrite GmailExporter to use GoogleAPIClient (Direct API)

### Changed
- `api/integrations/exporters/gmail.py`: Replace `get_mcp_manager()` with `get_google_client()`
  - Old code called `get_mcp_manager()` then called `create_gmail_draft`, `send_gmail_message`,
    `list_gmail_messages` — methods that don't exist on MCPClientManager, only on GoogleAPIClient. Was silently broken.
  - Now imports `from integrations.core.google_client import get_google_client`
  - Reads `context.refresh_token` (set by delivery.py) instead of wrong `context.metadata.get("refresh_token")`
  - Removed `MCP_AVAILABLE` guard (no MCP used)
  - `verify_destination_access()` also uses `google_client.list_gmail_messages()` instead of MCP

### Behavior
- Gmail agent delivery (draft, send, reply, html formats) now correctly routes through Google Direct API
- All three exporters now use production-compatible backends: Slack → MCP Gateway, Notion → Direct API, Gmail → Direct API

---

## [2026.02.19.11] - Rewrite Slack/Notion exporters to use production-compatible backends

### Changed
- `api/integrations/exporters/slack.py`: Route through MCP Gateway instead of spawning npx
  - Removed `MCPClientManager` dependency (can't spawn npx on Render's Python service)
  - Now calls `services.mcp_gateway.call_platform_tool()` (HTTP to Node.js MCP Gateway)
  - `verify_destination_access()` also routes through Gateway
  - DM draft (`dm_draft` format): uses Slack REST API directly (users.lookupByEmail, conversations.open, chat.postMessage) — no MCP needed for these simple calls
  - Removed MCP_AVAILABLE guard (Gateway availability check replaces it)

- `api/integrations/exporters/notion.py`: Route through Direct API instead of MCP npx
  - Removed `MCPClientManager` dependency (Notion MCP server requires ntn_... internal tokens, incompatible with OAuth)
  - Added `_create_notion_page()` helper using Notion REST API POST /v1/pages
  - Added `_markdown_to_notion_blocks()` to convert agent markdown to Notion blocks
  - Supported formats: page (child under parent_id), database_item (in database), draft (YARNNN Drafts DB)
  - `verify_destination_access()` uses `NotionAPIClient.get_page()` instead of MCP notion-fetch
  - Removed MCP_AVAILABLE guard

### Behavior
- Agent delivery (scheduled + semi_auto) now works on Render (no Node.js required in Python service)
- Slack delivery uses MCP Gateway (same path as TP tools), Notion delivery uses Direct API
- All existing destination schemas are preserved — no DB migration required

---

## [2026.02.19.10] - Add platform_notion_get_page tool

### Added
- `api/services/platform_tools.py`: New `platform_notion_get_page` tool
  - Calls `NotionAPIClient.get_page()` for title/metadata + `get_page_content()` for block children
  - Returns `{title, url, blocks: [{type, text}], block_count}`
  - Block normalizer `_normalize_notion_blocks()` strips Notion API noise to plain text per block type
  - Helper `_extract_rich_text()` for Notion rich_text arrays
  - Handler in `_execute_notion_tool()` for `tool == "get_page"`
  - Tool description instructs TP: search → get_page, never use Read or create_comment as read probes

### Behavior
- TP can now read Notion page content after `platform_notion_search` returns a page ID
- Blocks normalized: paragraphs, headings, bullets, to-dos, code, dividers, images → `{type, text}`
- Fixes TP fallback to `Read(ref: document:...)` and `create_comment` used as probes (both wrong)

---

## [2026.02.19.9] - Improve channel_names_unavailable hint (brevity)

### Changed
- `api/services/platform_tools.py`: Updated `_detect_channel_names_unavailable()` hint
  - Old: Verbose hint telling TP to "use Clarify to ask the user for channel name or ID"
  - New: Brief hint saying "ask for channel link (one question, no tutorial)"
  - Also includes `available_channel_ids` in result for context
- `platform_slack_list_channels` description: Shortened fallback guidance to match

### Behavior
- When channel names are unavailable, TP now asks briefly for the channel link
- No more verbose 4-step tutorial about how to find channel IDs in Slack
- TP can extract channel ID from the link URL the user pastes

### Root cause
TP was giving users a lengthy technical explanation of how to find channel IDs instead of simply asking "Can you share the channel link?" — a cleaner UX.

---

## [2026.02.19.8] - Remove legacy load_memories (ADR-059/064 alignment)

### Removed
- `api/routes/chat.py`: Deleted `load_memories()` function and all its RPC calls
  - `search_memories` RPC: referenced `memories` table which no longer exists (ADR-059 collapsed to `user_memory`)
  - `get_memories_by_importance` RPC: same legacy table reference
  - These RPC functions never existed in the database after ADR-059 migration, causing 404 errors
- `api/routes/chat.py`: Removed `get_embedding` import (was only used by `load_memories`)
- `api/routes/chat.py`: Removed `Memory` import from `agents.base` (no longer needed)

### Changed
- `api/routes/chat.py`: Replaced `load_memories()` call with empty `ContextBundle()`
  - Memory is now loaded internally by `execute_stream_with_tools()` via `build_working_memory()`
  - The `context` parameter is passed for backwards compatibility but is ignored when `injected_context` builds successfully
  - This was the "preferred path" all along (line 148 of thinking_partner.py)

### Behavior
- No change to TP behavior — memory was already loaded via `build_working_memory()` in the agent
- 404 errors for `search_memories` and `get_memories_by_importance` RPC calls eliminated
- Chat endpoint no longer makes unnecessary RPC calls that fail silently

### Root cause
ADR-059 collapsed `memories`, `knowledge_profile`, `knowledge_styles`, `knowledge_domains`, `knowledge_entries` into `user_memory`. The `load_memories()` function and its RPC calls were dead code referencing the old schema. The code silently caught the 404 errors and continued with empty memories, while `build_working_memory()` correctly loaded context from `user_memory` table.

---

## [2026.02.19.9] - Normalize get_channel_history result (closes raw MCP pass-through gap)

### Changed
- `_normalize_get_channel_history_result()` strips raw `conversations.history` response to `{user, text, ts, reactions}` per message before TP sees it
- Empty/bot messages with no text are filtered out
- Reactions normalized to `{name, count}` pairs only (was full user-list array)
- All other Slack API fields (`ok`, `has_more`, `pin_count`, `response_metadata`, `subtype`, `team`, etc.) removed

### Context
With `list_channels` now normalized (`[2026.02.19.8]`), `get_channel_history` was the last Slack MCP tool passing raw API responses to TP. Notion, Gmail, and Calendar all normalize at the handler level — this closes the same gap for Slack MCP. All platform tools now return clean, minimal response dicts.

## [2026.02.19.8] - Normalize list_channels result to eliminate model hallucination

### Fixed
- `_normalize_list_channels_result()` strips raw Slack `conversations.list` response to only `id`, `name`, `is_private`, `is_archived` per channel before TP sees the result
- Root cause confirmed via debug log: names were present (`all-episode0`, `daily-work`, etc.) but Slack MCP returns 20+ fields per channel (internal metadata, timestamps, team IDs, etc.) — the model misread noise as "redacted" data and hallucinated "privacy" as the cause

### Behavior before
`result["result"]` = full `conversations.list` dict with 20+ fields per channel → model hallucinates "redacted for privacy"

### Behavior after
`result["result"]` = `{"channels": [{"id": "C...", "name": "daily-work", "is_private": false, "is_archived": false}], "count": 18}` → model reads `daily-work`, calls `get_channel_history` directly

### Note
`[2026.02.19.7]` warning detection is preserved inside the normalizer — if names are empty after normalization, `warning="channel_names_unavailable"` is still added.

## [2026.02.19.7] - Result-level failure detection for list_channels

### Changed
- `api/services/platform_tools.py`: Added `_detect_channel_names_unavailable()` post-processor
  - After a successful `list_channels` call, inspects whether all channels have empty/missing `name` fields
  - If so, annotates the result with `warning="channel_names_unavailable"` and a `hint` before TP sees it
  - This is a runtime signal in the data — TP no longer needs to infer the failure from description text
- `platform_slack_list_channels` description: shortened — removed compensating "if names missing" guidance
  - Replaced with: "If result includes `warning=channel_names_unavailable`: use Clarify to ask the user"
  - Description-level guidance was compensating for a silent failure; the result now carries the signal
- `platform_slack_get_channel_history` description: removed now-redundant "if list_channels doesn't show readable names" line

### Why this matters
Description-level guidance is a compensating control — it tells the model what to do when something goes wrong, but the model has to correctly interpret a success response as a failure. Result-level annotation is structural: the data itself says what happened. Same class of bug as Render MCP's `list_logs` schema/runtime mismatch, but solved at the source rather than compensated in the prompt layer.

### Behavior before
TP: list_channels → success:true, channels with empty names → description says "if names missing ask user" → model may or may not follow

### Behavior after
TP: list_channels → success:true, warning="channel_names_unavailable" → result carries explicit signal → Clarify("Can you tell me the channel name or ID?")

## [2026.02.19.6] - Fix TP fallback when Slack channel names are unreadable

### Fixed
- `platform_slack_list_channels` description: added guidance for when channel names appear redacted/missing
  - Instructs TP to use Clarify to ask user for channel name/ID — NOT to fall back to Search
  - Root cause: Slack user OAuth token may lack `channels:read`/`groups:read` scope; API returns IDs without names
- `platform_slack_get_channel_history` description: added explicit "do NOT fall back to Search" instruction
  - Search only queries old cached `filesystem_items`; live channel history requires the live tool
  - Added `oldest` timestamp example for date-range queries

### Behavior before
TP: list_channels → names unreadable → Search(cache) → empty → "sync is running, check back later"

### Behavior after
TP: list_channels → names unreadable → Clarify("Can you tell me the channel name or ID?") → get_channel_history(confirmed_id)

## [2026.02.19.5] - Tool system: wire list_integrations into PRIMITIVES; slim platforms.py

### Changed
- `api/services/primitives/registry.py`: Added `LIST_INTEGRATIONS_TOOL` and wired `handle_list_integrations` handler
  - `list_integrations` was documented in `platforms.py` as a tool TP should call but was never in PRIMITIVES — a ghost tool
  - TP now has the tool in its schema and can actually call it; handler routes to `services.project_tools.handle_list_integrations`
  - `LIST_INTEGRATIONS_TOOL` description carries full behavioral docs (which platforms, what fields, agentic pattern)
- `api/agents/tp_prompts/platforms.py`: Slimmed `PLATFORMS_SECTION` from ~130 lines to ~30 lines
  - Removed all per-tool documentation (call sequences, arg names, etc.) — this now lives in each tool's `description` field
  - Kept: agentic pattern (call list_integrations first), landing zones table, ADR-065 live→cache→sync reading pattern, notifications
  - Tool descriptions are now the single source of truth; the prompt section provides behavioral framing only

### Why
Claude Code's pattern: tool `description` fields carry all model-facing workflow docs. No separate "here are your tools" prompt layer.
The `get_channel_history` bug was a direct consequence of maintaining docs in a separate prompt layer that could diverge from execution.
By keeping tool docs in schema definitions (co-located with the handler mapping), prompt and execution stay in sync automatically.

## [2026.02.19.4] - Fix Slack get_channel_history MCP tool name + platform result truncation

### Fixed
- `api/services/platform_tools.py`: `map_to_mcp_format()` — added missing `get_channel_history` → `slack_get_channel_history` mapping
  - `platform_slack_get_channel_history` was passing `get_channel_history` to the MCP gateway, which the Slack MCP server (`@modelcontextprotocol/server-slack`) does not recognise
  - MCP server returned an empty/error result (200 OK with no messages), causing TP to cascade into the sync fallback loop
  - Now correctly routes to `slack_get_channel_history` with `channel_id`, `limit`, `oldest` args passed through
- `api/services/anthropic.py`: `_truncate_tool_result()` — platform tools now use `max_items=100, max_content_len=1000`
  - Default was `max_items=5`: a workspace with 20 channels would show only 5 to TP, forcing it to guess channel IDs
  - Platform tool results (channel lists, message history) now pass up to 100 items with 1000-char content per item

### Behavior
- TP can now correctly read Slack channel history in one live call:
  `platform_slack_list_channels()` → find channel_id → `platform_slack_get_channel_history(channel_id, ...)` → summarise
- Sync fallback (`Execute platform.sync`) only triggers when live tools genuinely return empty (no content), not on tool name mismatch
- Channel list result is no longer truncated before TP can find the right channel by name

### Root cause
`handle_platform_tool()` parses `platform_slack_get_channel_history` as `provider=slack, tool=get_channel_history`.
`map_to_mcp_format()` had no case for `get_channel_history`, falling through to the default pass-through.
The MCP gateway hit `/api/mcp/tools/slack/get_channel_history`; the Slack MCP server has no such tool (its name is `slack_get_channel_history`).

---

## [2026.02.19.3] - ADR-067: Session compaction and conversational continuity

### Added
- `api/routes/chat.py`: `maybe_compact_history()` — ADR-067 Phase 3 in-session compaction
  - Triggers when session history exceeds `COMPACTION_THRESHOLD` (40k tokens = 80% of 50k budget)
  - Makes a single LLM call (haiku) to generate a compaction summary of all session messages
  - Persists summary to `chat_sessions.compaction_summary`
  - Returns an assistant `<summary>` block in the same format as Claude Code auto-compaction
  - On subsequent turns, reuses the stored compaction without re-generating
- `api/routes/chat.py`: `COMPACTION_THRESHOLD = 40000` and `COMPACTION_PROMPT` constants
- `api/services/memory.py`: `generate_session_summary()` — ADR-067 Phase 1
  - Single haiku LLM call to produce 2-5 sentence prose summary of a completed session
  - Called by nightly cron after `process_conversation()` for sessions with ≥ 5 user messages
  - Output written to `chat_sessions.summary`
- `supabase/migrations/061_session_compaction.sql`: Schema changes for all three phases
  - `chat_sessions.summary TEXT` — cross-session memory (Phase 1)
  - `chat_sessions.compaction_summary TEXT` — in-session compaction block (Phase 3)
  - `get_or_create_chat_session()` — 5-arg version with inactivity boundary (Phase 2)

### Changed
- `api/routes/chat.py`: `build_history_for_claude()` — added `compaction_block` parameter
  - If provided, the compaction block is prepended to the truncated history
  - Messages prior to compaction are excluded from the API call (retained in `session_messages` for audit)
- `api/routes/chat.py`: `global_chat` endpoint — loads `compaction_summary` from session, calls `maybe_compact_history()` before history build
- `api/routes/chat.py`: `get_or_create_session()` fallback — updated to use `updated_at`-based inactivity check (4h window) instead of `DATE(started_at) = CURRENT_DATE`
- `api/jobs/unified_scheduler.py`: Nightly cron wires `generate_session_summary()` after `process_conversation()`, writes result to `chat_sessions.summary`

### Session philosophy update
- **Before (ADR-049)**: "Sessions are for API coherence only; simple truncation; no compression needed"
- **After (ADR-067)**: In-session compaction at 80% (no silent truncation); cross-session summaries via nightly cron; inactivity-based boundary (4h) decoupled from cron cadence

### Behavior
- Silent truncation eliminated: when history fills, model receives a `<summary>` of what was dropped
- "Recent conversations" block in working memory will populate from next nightly cron run
- Session boundary now reflects user inactivity (4h gap = new session) rather than UTC midnight
- Nightly cron and session boundary are fully decoupled domains

---

## [2026.02.19.2] - Slack channel history tool + sync hand-off fix

### Added
- `api/services/platform_tools.py`: Added `platform_slack_get_channel_history` to SLACK_TOOLS
  - Parameters: `channel_id` (required), `limit` (default 50), `oldest` (unix timestamp, optional)
  - Routes via MCP Gateway as `slack/get_channel_history`
  - This is the primary tool for reading Slack message content in conversation

### Changed
- `api/agents/tp_prompts/behaviors.py`: Fixed "Platform Content Access" Step 1 example
  - Replaced hallucinated `platform_slack_search` with correct `platform_slack_list_channels → platform_slack_get_channel_history` workflow
- `api/agents/tp_prompts/behaviors.py`: Fixed Step 3 sync wait-loop
  - Removed `get_sync_status()` poll (tool not in TP's tool list — it's in project_tools.py, not loaded by TP)
  - Replaced with hand-off pattern: trigger sync, tell user ~30–60s, stop; user re-engages after sync completes
- `api/agents/tp_prompts/platforms.py`: Updated Slack section with full tool inventory
  - Added `platform_slack_get_channel_history` as primary read tool with workflow example
  - Clarified `platform_slack_list_channels` purpose (find channel_id) vs `platform_slack_send_message` (output to self)

### Behavior
- TP can now read Slack channel messages directly (live) without needing a sync
- Sync hand-off is explicit: trigger + inform user + stop (not spin-wait)
- No more hallucinated `platform_slack_search` calls

### Root cause documented
- TP hallucinated `platform_slack_search` because behaviors.py referenced it as an example
- TP tried `Execute(action="platform.sync.status")` because it had no real status-check tool
- Both fixed by this entry

---

## [2026.02.19.1] - Live-First Platform Context (ADR-065)

### Changed
- `api/agents/tp_prompts/behaviors.py`: Added "Platform Content Access (ADR-065)" section
  - Defines three-step access order: live tools → cache fallback → sync+wait+re-query
  - Explicit rule: TP must disclose `synced_at` age when responding from `filesystem_items` cache
  - Explicit rule: never re-query immediately after `Execute(action="platform.sync")` — sync is async
  - Wait-loop pattern: poll `get_sync_status()` before re-querying (like Claude Code waiting for a deploy)
- `api/agents/tp_prompts/behaviors.py`: Fixed Work Boundary DO list — removed "Write to memory" (ADR-064 removed explicit memory tools)
- `api/services/primitives/search.py`: Removed `scope="memory"` from valid enum values
- `api/services/primitives/search.py`: Removed silent `scope="memory"` → `scope="platform_content"` redirect; now returns a clear error directing TP to working memory context
- `api/services/primitives/search.py`: Added `synced_at` field to `platform_content` results so TP can form correct disclosure statements
- `api/services/primitives/search.py`: `scope="all"` no longer includes `memory` (ADR-065)
- `api/services/primitives/search.py`: Updated tool description to make live-first model explicit

### Behavior
- TP's first move for platform content is now a live tool call, not a cache search
- `Search(scope="platform_content")` is a fallback, not the primary path
- When fallback is used, TP discloses cache age from `synced_at` field
- Empty cache → sync → wait → re-query (not immediate re-query)
- `Search(scope="memory")` now returns a clear error explaining Memory is already in working memory

### Impact
- Eliminates the empty-query bug: TP no longer falls into cache-miss → sync → immediate re-query → empty loop
- User always knows when they're seeing cached vs live data
- Memory search scope removed from TP's available tools — cleaner layer separation

### Token budget impact
- New behaviors section: ~300 tokens added to system prompt
- Tool description updated (net neutral — replaced old text)

---

## [2026.02.18.2] - Implicit Memory (ADR-064)

### Removed
- `api/services/project_tools.py`: Removed `create_memory`, `update_memory`, `delete_memory`, `suggest_project_for_memory` tools
- `api/services/extraction.py`: Deleted file (replaced by `memory.py`)

### Added
- `api/services/memory.py`: New unified Memory Service with `process_conversation()`, `process_feedback()`, `process_patterns()`, `get_for_prompt()`

### Changed
- `api/agents/tp_prompts/tools.py`: Updated tool documentation to reflect memory is now implicit
  - Removed `Write(ref="memory:new")` examples
  - Added "Memory (ADR-064)" section explaining implicit handling
  - Marked `List(pattern="memory:*")` as read-only
- `api/routes/context.py`: Updated import from `extraction` to `memory`

### Expected behavior
- TP no longer has explicit memory tools
- When users state preferences, TP acknowledges naturally without tool calls
- Memory extraction runs via nightly cron (midnight UTC, processes prior day's sessions in batch)
- User edits via Context page continue to work (no change)

### Token budget impact
- None — memory format in working memory unchanged

---

## [2026.02.18.1] - Activity Log Injection into Working Memory (ADR-063)

### Added
- `api/services/activity_log.py`: New module — `write_activity()` and `get_recent_activity()`
- `supabase/migrations/060_activity_log.sql`: `activity_log` table (append-only, RLS)

### Changed
- `api/services/working_memory.py`: Added `_get_recent_activity()` helper and `recent_activity` key
- `api/services/working_memory.py`: Added "Recent activity" section to `format_for_prompt()`
- `api/services/agent_execution.py`: Writes `agent_run` event after generation completes
- `api/workers/platform_worker.py`: Writes `platform_synced` event after each sync batch

### Expected behavior
- TP system prompt now includes a "### Recent activity" block (up to 10 events, 7-day window)
- Format: `- 2026-02-18 09:00 · Weekly Digest v3 generated (staged)`
- TP can now answer "when did you last run my digest?" without a live DB query
- Cold-start sessions: block renders empty until first agent run or sync
- All writes are non-fatal — failures log a warning and never block the primary operation

### Token budget impact
- New block: ~300 tokens of the 2,000 token budget
- "Recent conversations" block retained but currently renders empty (chat session summaries not yet written)

---

## [2026.02.16.8] - Suggestion Notification Layer (ADR-060 Phase 3)

### Added
- `api/services/notifications.py`: Added `notify_suggestion_created()` function
- `supabase/migrations/052_suggestion_notification_preference.sql`: New preference column
- `api/routes/account.py`: Added `email_suggestion_created` preference

### Changed
- `api/jobs/unified_scheduler.py`: Analysis phase now sends notifications for created suggestions
- `api/services/notifications.py`: Added "suggestion" source type with proper preference mapping
- **Behavior**: Users receive email when Conversation Analyst creates suggestions
- **Impact**:
  - Users notified about new suggestions (respects preferences)
  - Suggestion notifications can be toggled in account settings
  - Chat session shows notification message for continuity

---

## [2026.02.16.7] - Admin Analysis Endpoints + Suggested Agents UI (ADR-060/061)

### Added
- `api/routes/admin.py`: Added `/trigger-analysis/{user_id}` and `/trigger-analysis-all` endpoints
- `web/app/(authenticated)/agents/page.tsx`: Added Suggested Agents section

### Changed
- **Behavior**: Admin can manually trigger conversation analysis for testing
- **Impact**:
  - Manual testing of ADR-060 Background Conversation Analyst without waiting for daily cron
  - Users see suggested agents at top of /agents page
  - Enable/dismiss actions for analyst-detected patterns

### UI Changes
- Purple-themed suggestion cards with confidence scores
- One-click enable or dismiss buttons
- Detection reason shown for transparency

---

## [2026.02.16.6] - Work Boundary (ADR-061)

### Changed
- `api/agents/tp_prompts/behaviors.py`: Added "Work Boundary (ADR-061)" section
- **Behavior**: TP now has explicit guidance on Path A vs Path B responsibilities
  - DO: Answer questions, execute one-time actions, create agents when asked
  - DON'T: Generate agent content inline, suggest automations mid-conversation
- **Impact**:
  - TP stays conversational and responsive (Path A)
  - Agent content generation happens in orchestrator (Path B)
  - Pattern detection runs in background, not in conversation

### Architectural Note
- Part of ADR-061 Two-Path Architecture implementation
- TP creates agent configurations; orchestrator generates content on schedule

---

## [2026.02.16.5] - WebSearch primitive for TP (ADR-045)

### Added
- `api/services/primitives/web_search.py`: New WebSearch primitive using Anthropic's native `web_search_20250305` tool
- `api/services/primitives/registry.py`: Added WebSearch to primitives list and handlers
- `api/agents/tp_prompts/tools.py`: Added Web Operations section with WebSearch documentation

### Changed
- **Behavior**: TP can now search the web for external information (news, docs, research, competitors)
- **Impact**:
  - TP has access to current information beyond user's synced data
  - Clear distinction: WebSearch for external info, Search for user's data
  - Aligns TP capabilities with Claude Code's WebSearch tool

---

## [2026.02.16.4] - Modular prompt architecture (ADR-059)

### Changed
- `api/agents/thinking_partner.py`: Removed ~450 lines of embedded prompts, now imports from `tp_prompts/`
- Created `api/agents/tp_prompts/` directory with modular prompt files:
  - `base.py`: Core identity and style
  - `behaviors.py`: Search→Read→Act, verification, resilience patterns
  - `tools.py`: Tool documentation (Read, Write, Search, etc.)
  - `platforms.py`: Platform-specific tools (Slack, Notion, Gmail, Calendar)
  - `onboarding.py`: New user onboarding context
  - `__init__.py`: `build_system_prompt()` function to compose prompts
- **Behavior**: No behavioral change - same prompts, just modularized
- **Impact**:
  - Easier to maintain and update individual prompt sections
  - Clear separation of concerns (base identity vs tools vs platforms)
  - Simpler diffs when changing specific prompt sections

### Added
- `api/agents/tp_prompts/behaviors.py`: Now includes "Verify After Acting" section for Gap #5

---

## [2026.02.16.3] - Claude Code architectural alignment

### Changed
- `api/services/anthropic.py`: Increased `max_tool_rounds` from 5 to 15 (safety net only; model should decide when done)
- `api/services/primitives/read.py`: Added `retry_hint` to error responses to guide model recovery
- `api/agents/thinking_partner.py`: Added "Core Behavior: Search → Read → Act" section early in prompt
- **Behavior**:
  - Model has more room to complete complex tasks before hitting safety cap
  - When Read fails, error includes specific guidance on how to fix (e.g., "Use Search first")
  - System prompt now explicitly teaches "Search to get UUID → Read with UUID" workflow
- **Impact**:
  - Fewer premature tool exhaustion cases
  - Model learns from errors via retry_hint
  - Correct ref usage pattern emphasized early

### Architectural alignment with Claude Code
- Tool loops: Model-driven termination (high cap as safety net)
- Error handling: Structured errors with actionable retry hints
- Exploration pattern: Emphasized Search→Read workflow

---

## [2026.02.16.2] - Document reading and tool exhaustion fixes

### Changed
- `api/services/primitives/refs.py`: Added `_enrich_document_with_content()` to fetch chunks when reading documents
- `api/services/primitives/read.py`: Updated tool description to emphasize UUID refs from Search results
- `api/services/primitives/search.py`: Updated tool description to clarify ref workflow
- `api/services/anthropic.py`: Added final text response when max_tool_rounds exhausted
- **Behavior**:
  - Read(ref="document:UUID") now returns full document content, not just metadata
  - Tool descriptions explicitly guide TP to use refs from Search results
  - When tool rounds exhaust, TP now generates a summary instead of silent failure
- **Impact**:
  - TP can now read and summarize uploaded documents
  - No more silent failures when TP uses many tools
  - Clearer workflow: Search → get ref → Read with ref

---

## [2026.02.16.1] - Document content search fix

### Changed
- `api/services/primitives/search.py`: Added `_search_document_content()` function
- **Behavior**: Document search now queries `filesystem_chunks.content` instead of only `filesystem_documents.filename`
- **Impact**: TP can now find content within uploaded PDFs, DOCX, TXT, MD files

---

## [2026.02.15.1] - ADR-058 schema alignment

### Changed
- `api/services/primitives/search.py`: Updated `_search_user_memories()` to query `knowledge_entries` table
- `api/services/primitives/read.py`: Updated memory refs to resolve from `knowledge_entries`
- **Behavior**: Memory/knowledge search uses new ADR-058 schema
- **Impact**: TP working memory injection now pulls from `knowledge_entries`

---

## [2026.02.13.1] - Initial prompt tracking

### Established
- TP system prompt in `api/agents/thinking_partner.py`
- Tool definitions in `api/services/primitives/*.py`:
  - `Search` - Find entities by content
  - `Read` - Retrieve entity by reference
  - `Write` - Create/update entities
  - `Remember` - Store user facts
  - `CreateWork` - Create work tickets
  - `Schedule` - Schedule tasks
- Extraction prompt in `api/services/extraction.py`
- Inference prompt in `api/services/profile_inference.py`

---

## Template

```markdown
## [YYYY.MM.DD.N] - Short description

### Changed
- file.py: What changed
- **Behavior**: How this affects LLM behavior
- **Impact**: User-visible effects

### Added
- New prompt or tool

### Removed
- Deprecated prompt or tool
```
