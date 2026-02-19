# Prompt Changelog

Track changes to system prompts, tool definitions, and LLM-facing content.

Format: `[YYYY.MM.DD.N]` where N is the revision number for that day.

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
