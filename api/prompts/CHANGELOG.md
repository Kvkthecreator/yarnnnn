# Prompt Changelog

Track changes to system prompts, tool definitions, and LLM-facing content.

Format: `[YYYY.MM.DD.N]` where N is the revision number for that day.

---

## [2026.02.27.1] - Type consolidation: 27→8 active types (ADR-082)

### Changed
- `api/services/signal_processing.py`: Updated `_REASONING_SYSTEM_PROMPT` to reference only active types (`status_report`, `research_brief`, `custom`) instead of deprecated types (`daily_strategy_reflection`, `intelligence_brief`, `deep_research`). Updated JSON examples accordingly. Removed hardcoded `MEETING_PREP_TYPE_CLASSIFICATION` — now uses `get_type_classification()` from routes.
- `api/services/deliverable_pipeline.py`: `build_type_prompt()` now resolves deprecated types to parent type's prompt template and field mapping via `_TYPE_PROMPT_ALIASES`. e.g., `stakeholder_update` → `status_report` template.
- `api/services/conversation_analysis.py`: Removed `weekly_status` from `SUGGESTABLE_TYPES` (deprecated, absorbed by `status_report`).

### Behavior
- Signal processing now instructs the LLM to create only active types. Deprecated types returned by LLM still work via aliasing in `get_type_classification()`.
- Deprecated types in existing deliverables use parent type's prompt template on next execution, not their original dedicated prompt.
- Conversation analysis no longer suggests `weekly_status` as a deliverable type.

---

## [2026.02.26.4] - Execution path consolidation: absorb web research into headless mode (ADR-081)

### Changed
- `api/services/deliverable_execution.py`: `_build_headless_system_prompt()` now accepts `research_directive` parameter. When provided (research/hybrid bindings), the system prompt includes a `## Research Directive` section instructing the agent to actively use WebSearch, replacing the default conservative "use tools only if needed" guidance. `generate_draft_inline()` accepts `research_directive` and uses binding-aware tool round limits (`HEADLESS_TOOL_ROUNDS` dict) instead of flat `HEADLESS_MAX_TOOL_ROUNDS=3`.
- `api/services/execution_strategies.py`: `ResearchStrategy` and `HybridStrategy` no longer call `web_research.research_topic()`. Instead they gather platform context only and pass a `research_directive` string via `GatheredContext.summary`. New `_build_research_directive()` helper builds the directive from deliverable title/description.
- `api/services/web_research.py`: Marked as DEPRECATED. No longer imported by any pipeline code.

### Behavior
- Research-type deliverables (`research_brief`, `deep_research`) now use the headless agent's WebSearch primitive for web research during generation, instead of a separate pre-generation web research loop. The agent can do targeted research informed by the deliverable template.
- Binding-aware tool rounds: platform_bound=2, cross_platform=3, research=6, hybrid=6 (was flat 3 for all).
- Eliminates one of three independent agentic loops in the deliverable pipeline, achieving true "one agent, two modes" as ADR-080 intended.
- Cost profile: research types may use more tool rounds (up to 6) but eliminate a separate Sonnet call from `web_research.py`. Net cost should be comparable.

---

## [2026.02.26.3] - Headless mode: agentic generation with read-only tools (ADR-080 Phase 1+2)

### Changed
- `api/services/deliverable_execution.py`: `generate_draft_inline()` now uses `chat_completion_with_tools()` instead of `chat_completion()`. Agent runs in headless mode with read-only tools (Search, Read, List, WebSearch, GetSystemState) and max 3 tool rounds. New `_build_headless_system_prompt()` extracts and enhances the system prompt with tool usage instructions.
- `api/services/primitives/registry.py`: Added `PRIMITIVE_MODES` dict, `get_tools_for_mode()`, and `create_headless_executor()` for mode-gated primitive access.

### Behavior
- Deliverable generation is now agentic — the agent CAN use read-only tools to investigate when gathered context is insufficient, but is instructed to prefer generating from provided context directly.
- Most deliverables will generate in a single turn (no tool use), same as before. The tools are a safety net for when context gathering misses something.
- System prompt restructured into sections (Output Rules, Tool Usage) for clearer instruction following.
- Cost impact: ~0-3 additional API calls per generation in the rare case tools are used. Typical case unchanged (single call).

---

## [2026.02.26.2] - Signal context forwarding to deliverable generation (ADR-080 Phase 0)

### Changed
- `api/services/deliverable_execution.py`: System prompt now includes signal reasoning and signal context (entity, platforms) when a deliverable is triggered by signal processing. Added `trigger_context` parameter to `generate_draft_inline()`.
- `api/services/signal_processing.py`: `_queue_signal_emergent_execution()` now forwards `reasoning_summary` and per-action `signal_context` from the SignalAction into `trigger_context`.

### Behavior
- Signal-emergent deliverables now receive the LLM reasoning that caused their creation, enabling the generation step to understand WHY the deliverable exists and focus on the relevant entity/pattern.
- Previously, `trigger_context={"type": "signal_emergent"}` passed zero intelligence. Now includes `signal_reasoning` (up to 1000 chars) and `signal_context` (entity, platforms).
- Non-signal-triggered deliverables are unaffected (trigger_context is None or lacks signal fields).

---

## [2026.02.26.1] - Deliverable quality: no-emoji, conciseness, calendar preview rewrite

### Changed
- `api/services/deliverable_execution.py`: System prompt now instructs no-emoji output, enforces conciseness preference, uses plain markdown headers.
- `api/services/deliverable_pipeline.py`: Rewrote `weekly_calendar_preview` prompt to analyze raw event data instead of expecting pre-computed stats ({meeting_count}, {total_hours} etc. were never filled). Prompt now instructs LLM to compute counts from context.
- `api/services/deliverable_pipeline.py`: Updated `gmail_inbox_brief` prompt to explicitly request plain markdown headers and no-emoji output.

### Behavior
- All deliverable types now produce plain markdown output without emoji headers
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
- `api/jobs/unified_scheduler.py`: Removed all deliverable notification email logic. Scheduler no longer sends `send_deliverable_ready_email()` or `send_deliverable_failed_email()`. Exception handler now calls `notify_deliverable_failed()` from notifications.py instead.
- `api/jobs/email.py`: Deleted `send_deliverable_ready_email()` and `send_deliverable_failed_email()` — legacy functions only used by the scheduler.
- `api/services/delivery.py`: Always calls `_notify_delivered()` (removed email-platform skip). Passes `delivery_platform` to notification service for skip decision.
- `api/services/notifications.py`: `notify_deliverable_delivered()` now accepts `delivery_platform` param. When platform is "email"/"gmail", logs as in_app notification instead of sending a separate email (content email IS the notification). Removed unused `notify_deliverable_ready()`.

### Behavior
- **Single notification path**: All deliverable notifications flow through `delivery.py` → `notifications.py`. The scheduler only handles generation + scheduling.
- **Email-platform skip logic** lives in one place (`notifications.py`) instead of three (was in scheduler, delivery.py, and notifications.py).
- No change to user-facing behavior — email deliveries still produce exactly 1 email (the content), non-email deliveries still get a notification email.

---

## [2026.02.24.5] - Deliverable detail page rewrite (content-first layout)

### Changed
- `web/app/(authenticated)/deliverables/[id]/page.tsx`: Full rewrite — content-first layout with rendered markdown (ReactMarkdown), version selection via delivery history rows, clean status model (delivered/failed/generating only), execution details bar with source snapshot pills.
- Added `react-markdown` and `@tailwindcss/typography` dependencies for markdown rendering.

### Behavior
- Deliverable content is now the hero element, rendered as formatted markdown instead of hidden behind a collapsible `<details>` element
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
- `api/routes/deliverables.py`: Added `delivery_error` to `VersionResponse` model; populated `source_snapshots`, `analyst_metadata`, `source_fetch_summary`, `delivery_error` in detail endpoint.

### Behavior
- All users receive deliverables via email regardless of Google OAuth status (Resend = server-side API key)
- `GmailExporter` (`platform="gmail"`) remains for creating Gmail drafts or sending as user's own address
- No duplicate notification email when content already lands in user's inbox
- `/deliverables/{id}` API now returns full version metadata (delivery_error, source_snapshots, etc.)

---

## [2026.02.24.3] - Fix signal processing: deliverable ID missing from prompt

### Changed
- `api/services/signal_processing.py`: Include deliverable UUID in brackets in EXISTING DELIVERABLES list (`[uuid] Title (type, next run: ...)`). Previously only showed title, causing LLM to return title as `trigger_deliverable_id` instead of UUID — which crashed with "invalid input syntax for type uuid".
- Added UUID validation guard in `_parse_reasoning_response()` to reject non-UUID `trigger_deliverable_id` values gracefully instead of crashing.

### Behavior
- `trigger_existing` actions now work correctly — LLM can see and return the actual UUID
- Invalid IDs logged as warnings instead of crashing the entire signal processing run

---

## [2026.02.24.2] - Fix email delivery: Gmail/Google platform connection lookup

### Changed
- `api/services/delivery.py`: `_get_exporter_context()` now falls back from `gmail` to `google` when looking up platform connections. Google OAuth stores both Gmail and Calendar under the `google` platform name, but the email exporter looked for `gmail` only, causing "No email integration connected" errors.

### Behavior
- Email delivery (`platform: "email"`) now works for users with Google OAuth connections stored as `platform = "google"`
- Fixes deliverable delivery failures where content was generated successfully but couldn't be emailed

---

## [2026.02.24.1] - Fix ADR-035 Wave 1 prompt template field mappings

### Changed
- `api/services/deliverable_pipeline.py`: Added `elif` blocks for `slack_channel_digest`, `slack_standup`, `gmail_inbox_brief`, and `notion_page_summary` in `build_type_prompt()`. These types had prompt templates defined in `TYPE_PROMPTS` but no field mapping in the main function, causing KeyError fallback to the generic custom template.

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
- `api/services/signal_processing.py`: `execute_signal_actions()` checks deliverable limit before creating signal-emergent deliverables.
- `supabase/migrations/079_daily_token_usage.sql`: SQL function `get_daily_token_usage()` for efficient daily token aggregation.

### Frontend
- All sync frequency labels updated for `1x_daily` (SyncStatusBanner, ConnectionDetailsModal, system page, ResourceList)
- Context pages (slack, gmail, notion, calendar) handle `?status=connected` OAuth redirect param
- TypeScript types updated: `daily_token_budget`/`daily_tokens_used` replaces conversation fields
- `useChatGate` → `useTokenBudgetGate`, limits.ts updated for new tier model

### Behavior
- Free tier: 50k tokens/day, 2 sources/platform, 1x/day sync, 2 deliverables, no signal processing
- Starter: 250k tokens/day, 5 sources, 4x/day sync, 5 deliverables, signal processing on
- Pro: unlimited tokens, unlimited sources, hourly sync, unlimited deliverables

---

## [2026.02.23.4] - Fix signal processing crash + scheduler health query

### Changed
- `api/routes/signal_processing.py`: Removed `.order("deliverable_versions(created_at)")` — PostgREST PGRST118 error on one-to-many related table ordering. Sort versions client-side instead.
- `api/jobs/unified_scheduler.py`: Same PGRST118 fix for scheduler signal processing path.
- `api/services/primitives/system_state.py`: `_get_scheduler_health()` now queries per-user heartbeats instead of non-existent sentinel UUID `00000000-...`.
- `web/app/(authenticated)/system/page.tsx`: Removed dead Conversation Analyst icon map entry + unused MessageSquare import.

### Behavior
- Signal processing no longer crashes with 500 when deliverables exist
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
- `api/services/deliverable_execution.py`: Wired `mark_content_retained()` after draft generation to mark consumed content as retained. Fixed source snapshot logic (sources_used became strings after migration). Deleted legacy `gather_context_inline()` and `_get_relevant_memories()`.
- `api/services/deliverable_pipeline.py`: Deleted ~1440 lines — `fetch_integration_source_data`, all `_fetch_*_data` helpers, `execute_deliverable_pipeline`, pipeline step functions, cache infrastructure. Retained: `TYPE_PROMPTS`, validation functions, `build_type_prompt`, `get_past_versions_context`.
- `api/workers/platform_worker.py`: Fixed Slack method name bug — `get_slack_messages()` → `get_slack_channel_history()` (actual MCP client method).
- `api/services/platform_content.py`: Deleted deprecated backward-compat stubs (`FilesystemItem`, `store_filesystem_item`, `get_filesystem_items`, etc.).

### Removed
- `fetch_integration_source_data()` and all per-platform live fetch helpers from `deliverable_pipeline.py`
- `gather_context_inline()` from `deliverable_execution.py` (superseded by `execution_strategies.py`)
- All live API calls from `signal_extraction.py` (now reads from `platform_content`)
- Deprecated `FilesystemItem` alias and stub functions from `platform_content.py`

### Behavior
- **Single fetch path enforced**: Only `platform_sync_scheduler` → `platform_worker` calls external APIs. All consumers (execution strategies, signal extraction, deliverables) read from `platform_content` table.
- **Content retention wired**: Platform content consumed during deliverable generation is marked retained (excluded from TTL cleanup).
- **Slack sync fixed**: Method name mismatch that would have caused runtime errors corrected.
- **No behavioral change to signal_processing.py**: LLM triage still runs; transformation to scheduling heuristics is deferred per ADR-073 migration path.

---

## [2026.02.23.1] - ADR-073: Unified Fetch Architecture + Platform Integrations rewrite

### Added
- `docs/adr/ADR-073-unified-fetch-architecture.md`: Establishes single fetch path (platform_sync only), eliminates triple-fetch pattern (sync + signal extraction + deliverable execution all calling live APIs independently). Defines per-platform fetch specs (time windows, source filtering, sync token strategy, items per source, TTLs). Documents retention lifecycle wiring, scheduling heuristics replacing LLM signal triage, and deferred webhook strategy.

### Changed
- `docs/integrations/PLATFORM-INTEGRATIONS.md`: Full rewrite reflecting ADR-073 architecture. Documents singular fetch → platform_content → consumers data flow. Per-platform specification tables (Slack, Gmail, Calendar, Notion) with credential handling, sync token approach, content types, TTLs. Replaces prior documentation that showed three independent data paths.

### Architectural decisions
- Signal processing LLM triage (Haiku call per user per hour) to be replaced by scheduling heuristics (rules + freshness checks, no LLM). LLM reasoning happens at consumption time only (TP chat or deliverable execution).
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
  `integration_connected`, `integration_disconnected`, `deliverable_approved`, `deliverable_rejected`
- `api/services/activity_log.py`: Added all 4 new types to `VALID_EVENT_TYPES`
- `api/routes/integrations.py`: Logs `integration_connected` after OAuth callback success;
  logs `integration_disconnected` after disconnect
- `api/routes/deliverables.py`: Logs `deliverable_approved` / `deliverable_rejected` after version status change;
  also fetches `title` from deliverables for human-readable summary
- `web/app/(authenticated)/activity/page.tsx`: Added display config for all 4 new event types
  (ThumbsUp/ThumbsDown icons for approvals, Link/Unlink for integrations); click navigation to
  deliverable page or integration context page; `FILTER_TYPES` constant for curated filter chips

---

## [2026.02.19.13] - ADR-066: Delivery-first, remove governance

### Changed
- `api/services/deliverable_execution.py`: Remove governance gate, always deliver immediately
  - No more `staged` status — versions go directly to `delivered` or `failed`
  - Removed governance check before delivery (manual/semi_auto/full_auto → always deliver)
  - Added `update_version_for_delivery()` to replace `update_version_staged()`
  - Error status changed from `rejected` to `failed`
  - Activity log records delivery result, not governance state

- `web/app/(authenticated)/deliverables/[id]/page.tsx`: Delivery-first detail page
  - Removed Approve/Reject buttons (no governance workflow)
  - "Latest Output" → "Latest Delivery" with delivery status
  - "Previous Versions" → "Delivery History"
  - Added platform badge in header
  - Added external link to delivered content
  - Added Retry button for failed deliveries

- `web/app/(authenticated)/deliverables/page.tsx`: Enhanced list view per ADR-067
  - Platform badges on every card (not just group headers)
  - Delivery status (delivered/failed) instead of governance
  - Schedule status (Active/Paused) independent from delivery
  - Destination visibility with arrow indicator

### Behavior
- Deliverables now deliver immediately when generated — no approval step
- Users control automation via Pause/Resume, not Approve/Reject
- Single-user workflow: scheduling + pause is sufficient governance
- Multi-user governance can be re-added as feature flag in future

---

## [2026.02.19.12] - Deliverable creation flow: delivery options + instant run

### Changed
- `web/components/surfaces/DeliverableCreateSurface.tsx`: Platform-agnostic delivery options + instant run
  - Added delivery mode selector: Email (default), Slack DM, or Platform Channel
  - Email sends to user's registered email address (fetched from Supabase auth)
  - Slack DM sends as direct message to user (if Slack is connected)
  - Platform Channel shows channel selector (original behavior)
  - Instant run: Creates deliverable AND immediately triggers run for instant gratification
  - Button changed from "Create" to "Create & Run" with Play icon
  - Notice updated to explain instant run behavior

### Behavior
- Users get immediate feedback when creating a deliverable (runs on creation)
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
- Gmail deliverable delivery (draft, send, reply, html formats) now correctly routes through Google Direct API
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
  - Added `_markdown_to_notion_blocks()` to convert deliverable markdown to Notion blocks
  - Supported formats: page (child under parent_id), database_item (in database), draft (YARNNN Drafts DB)
  - `verify_destination_access()` uses `NotionAPIClient.get_page()` instead of MCP notion-fetch
  - Removed MCP_AVAILABLE guard

### Behavior
- Deliverable delivery (scheduled + semi_auto) now works on Render (no Node.js required in Python service)
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
  - `search_memories` RPC: referenced `memories` table which no longer exists (ADR-059 collapsed to `user_context`)
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
ADR-059 collapsed `memories`, `knowledge_profile`, `knowledge_styles`, `knowledge_domains`, `knowledge_entries` into `user_context`. The `load_memories()` function and its RPC calls were dead code referencing the old schema. The code silently caught the 404 errors and continued with empty memories, while `build_working_memory()` correctly loaded context from `user_context` table.

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
- `api/services/deliverable_execution.py`: Writes `deliverable_run` event after generation completes
- `api/workers/platform_worker.py`: Writes `platform_synced` event after each sync batch

### Expected behavior
- TP system prompt now includes a "### Recent activity" block (up to 10 events, 7-day window)
- Format: `- 2026-02-18 09:00 · Weekly Digest v3 generated (staged)`
- TP can now answer "when did you last run my digest?" without a live DB query
- Cold-start sessions: block renders empty until first deliverable run or sync
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

## [2026.02.16.7] - Admin Analysis Endpoints + Suggested Deliverables UI (ADR-060/061)

### Added
- `api/routes/admin.py`: Added `/trigger-analysis/{user_id}` and `/trigger-analysis-all` endpoints
- `web/app/(authenticated)/deliverables/page.tsx`: Added Suggested Deliverables section

### Changed
- **Behavior**: Admin can manually trigger conversation analysis for testing
- **Impact**:
  - Manual testing of ADR-060 Background Conversation Analyst without waiting for daily cron
  - Users see suggested deliverables at top of /deliverables page
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
  - DO: Answer questions, execute one-time actions, create deliverables when asked
  - DON'T: Generate deliverable content inline, suggest automations mid-conversation
- **Impact**:
  - TP stays conversational and responsive (Path A)
  - Deliverable content generation happens in orchestrator (Path B)
  - Pattern detection runs in background, not in conversation

### Architectural Note
- Part of ADR-061 Two-Path Architecture implementation
- TP creates deliverable configurations; orchestrator generates content on schedule

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
