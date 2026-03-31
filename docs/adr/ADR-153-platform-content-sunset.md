# ADR-153: Platform Content Sunset — Task-First External Data Flow

**Status:** Implemented  
**Date:** 2026-03-31 (proposed), 2026-04-01 (implemented)  
**Supersedes:** ADR-072 (unified content layer), ADR-077 (platform sync overhaul), ADR-085 (RefreshPlatformContent primitive)  
**Extends:** ADR-151 (shared context domains), ADR-152 (unified directory registry)

---

## Context

`platform_content` is a DB table + sync pipeline + search primitives that stage raw platform data (Slack, Notion, GitHub) for agent consumption. It was built pre-ADR-151 when there was no task-first context accumulation model.

**The problem:** `platform_content` creates a parallel context path that undermines the task-first architecture:

1. **Dual accumulation:** Platform sync writes raw data to `platform_content` (automatic, TTL). Tasks write structured context to `/workspace/context/` (agent-processed, accumulated). Two competing paths for the same external signals.
2. **Framework dilution:** TP prompts teach `Search(scope="platform_content")` as a primary tool, bypassing context domains entirely. Users get value without creating tracking tasks, killing the task-first model.
3. **Dead weight:** `/platforms/` filesystem directory is written to by sync but read by nothing. Orphaned infrastructure.
4. **Architectural ambiguity:** When an agent needs platform data, should it search `platform_content` (raw) or `/workspace/context/` (structured)? Both exist, no clear precedent.

**The correct model (ADR-151/152):** Platform connections provide auth + API access. Tasks are the bridge — agents call platform APIs during execution, process signals, write structured findings to context domains. Context domains are the sole source for all subsequent reads.

## Decision

**Full sunset of `platform_content` as a context source.** Platform data flows exclusively through tasks into context domains.

### What STAYS

| Component | Why |
|---|---|
| `platform_connections` table | OAuth tokens, connection status, source selection — auth infrastructure |
| Platform API clients (`slack_client.py`, `notion_client.py`, `github_client.py`) | Agents call these during task execution via headless tools |
| OAuth flow (`oauth.py`) | User connects platforms — auth is independent of data model |
| `landscape.py` | Source discovery (channels, pages, repos) — feeds task setup, not context |
| Integration routes (connect/disconnect/sources) | User manages connections — independent of data model |

### What GOES

| Component | Replacement |
|---|---|
| `platform_content` DB table | Context domains (`/workspace/context/`) |
| `platform_worker.py` (sync pipeline) | Task execution calls platform APIs directly |
| `platform_sync_scheduler.py` (sync cron) | Task scheduler triggers tracking tasks |
| `/platforms/` filesystem directory | Dissolved — no filesystem staging |
| `Search(scope="platform_content")` primitive scope | Agents use `ReadPlatformContent` tool for live API reads during task execution |
| `RefreshPlatformContent` primitive | Unnecessary — tasks call APIs directly, no cache to refresh |
| `mark_content_retained()` RPC | Unnecessary — context domain files have workspace lifecycle |
| `_search_platform_content()` function | Replaced by context domain search |
| `QueryKnowledge` platform_content fallback | Removed — context domains are sole source |
| TP prompt references to `Search(scope="platform_content")` | Replaced with task-first guidance |

### Data Flow (Post-Sunset)

```
User connects Slack → platform_connections stores OAuth token
    ↓
User creates "Monitor Slack" task → task scheduled daily
    ↓
Task executes:
    Agent calls Slack API via slack_client.py (live, using OAuth token)
    Agent processes signals (decisions, action items, key discussions)
    Agent writes structured findings to /workspace/context/signals/
    Agent produces daily digest → /workspace/outputs/briefs/
    ↓
Other tasks read from /workspace/context/ (accumulated, structured)
    ↓
TP reads context domain health in working memory
TP guides users to create tracking tasks if domains are thin
```

### TP Prompt Changes

**Remove:**
- `Search(scope="platform_content")` examples and instructions
- `RefreshPlatformContent` tool documentation
- "Search synced content" pattern

**Add:**
- "Platform data flows through tasks. If a context domain is thin, suggest creating a tracking task."
- "Use platform tools (ReadSlack, ReadNotion) within task execution for live API access."
- "Context domains are the sole source for accumulated intelligence."

### Platform Sync → Task Execution Migration

| Current (platform sync) | Post-sunset (task execution) |
|---|---|
| Cron runs every 1-6h per tier | Task scheduler runs per task schedule (daily/weekly) |
| Syncs ALL selected sources | Agent decides what to read based on task objective |
| Writes raw content to DB table | Agent writes structured context to domains |
| TTL-based expiration (14d/90d) | Permanent accumulation (context grows) |
| No judgment — mechanical extraction | Agent judgment — what matters, what's noise |

---

## Impact Radius

### Code — REMOVE (8 files, ~3,500 LOC)

| File | LOC | What |
|---|---|---|
| `api/services/platform_content.py` | ~920 | Content store/retrieve/search API |
| `api/workers/platform_worker.py` | ~1,210 | Sync implementation (Slack, Notion, GitHub) |
| `api/jobs/platform_sync_scheduler.py` | ~307 | Sync scheduling cron |
| `api/services/primitives/refresh.py` | ~246 | RefreshPlatformContent primitive |
| `api/services/primitives/search.py` | ~449 (partial) | Search scope="platform_content" path |

### Code — MODIFY (12+ files)

| File | Changes |
|---|---|
| `api/services/primitives/search.py` | Remove platform_content scope, keep document/agent scopes |
| `api/services/primitives/workspace.py` | Remove platform_content fallback from QueryKnowledge |
| `api/services/primitives/registry.py` | Remove RefreshPlatformContent registration |
| `api/services/agent_execution.py` | Remove mark_content_retained, platform_content_ids |
| `api/services/task_pipeline.py` | Remove platform_content_ids from metadata |
| `api/services/working_memory.py` | Remove platform sync freshness from system summary |
| `api/agents/tp_prompts/behaviors.py` | Remove Search(scope=platform_content) examples |
| `api/agents/tp_prompts/tools.py` | Remove platform_content tool descriptions |
| `api/agents/tp_prompts/platforms.py` | Rewrite: platform tools = live API access, not cached search |
| `api/routes/integrations.py` | Remove /platform/{provider}/content endpoint |
| `api/mcp_server/server.py` | Remove search_knowledge platform_content fallback |
| `web/lib/api/client.ts` | Remove PlatformContentResponse type |

### Render Services

| Service | Impact |
|---|---|
| yarnnn-platform-sync (cron) | **DELETE ENTIRE SERVICE** — no more sync cron |
| yarnnn-api | Remove platform_content endpoints |
| yarnnn-unified-scheduler | Remove platform sync scheduling |
| yarnnn-mcp-server | Remove platform_content search |

### Documentation — UPDATE

| Document | Changes |
|---|---|
| `workspace-conventions.md` | Remove `/platforms/` root. Four roots → three roots. |
| `SERVICE-MODEL.md` | Remove platform sync layer. Update perception model. |
| `FOUNDATIONS.md` | Update Axiom 2 perception layers — remove external platform layer |
| `registry-matrix.md` | Update — Monitor Slack/Notion tasks call live APIs |
| `CLAUDE.md` | ADR-153 entry. Remove platform sync service references. |
| `features/context.md` | Remove platform content as context source |
| `docs/database/ACCESS.md` | Note platform_content table deprecated |

### Database

| Artifact | Action |
|---|---|
| `platform_content` table | DROP (migration) |
| `mark_content_retained` RPC | DROP |
| `platform_content` retention functions | DROP |
| `platform_connections` table | KEEP (auth infrastructure) |
| `integration_import_jobs` table | Evaluate — may be unused post-sunset |

---

## Phases

### Phase 1: TP Prompt + Primitive Cleanup
- Remove Search(scope="platform_content") from primitives and TP prompts
- Remove RefreshPlatformContent primitive
- Remove QueryKnowledge platform_content fallback
- Remove platform_content_ids from pipeline metadata
- Update TP prompts: task-first guidance replaces platform search

### Phase 2: Sync Infrastructure Removal
- Delete platform_worker.py
- Delete platform_sync_scheduler.py
- Delete platform_content.py service
- Remove platform-sync Render cron service
- Remove sync scheduling from unified_scheduler.py

### Phase 3: Route + Frontend Cleanup
- Remove /platform/{provider}/content API endpoint
- Remove PlatformContentResponse from frontend types
- Remove platform content display from settings page
- Remove /platforms/ filesystem references from workspace-conventions

### Phase 4: Database Cleanup
- Migration: DROP platform_content table
- Migration: DROP mark_content_retained RPC
- Migration: DROP retention functions
- Evaluate integration_import_jobs table

### Phase 5: Documentation Alignment
- Update all architecture docs (SERVICE-MODEL, FOUNDATIONS, workspace-conventions)
- Update feature docs (context.md, memory.md)
- Update CLAUDE.md with ADR-153 status
- Archive ADR-072, ADR-077, ADR-085 as superseded

---

## Consequences

### Positive
- **Single accumulation path.** Context domains are THE source. No ambiguity.
- **Task-first model enforced.** Platform data ONLY flows through tasks. Creates tracking task adoption.
- **Simplified architecture.** Delete entire sync pipeline (~3,500 LOC), 1 Render service, 1 DB table.
- **Agent judgment over mechanical extraction.** Agents decide what matters, not a blind sync.
- **Permanent accumulation.** No TTL expiration — context compounds indefinitely.

### Negative
- **Cold start gap.** New user connects Slack → no data until first tracking task runs. Mitigate: auto-create Monitor Slack task on platform connect.
- **No raw platform search.** TP can't answer "search Slack for X" without a tracking task having captured relevant signals. Mitigate: agents can call platform APIs live during any task execution.
- **Loss of semantic search on platform data.** platform_content had pgvector embeddings. Post-sunset, semantic search only on workspace_files (context domains). Mitigate: context domain files get embeddings via workspace_files table.

### Risks
- **Platform API rate limits.** Live API calls during task execution may hit rate limits. Mitigate: task schedules are infrequent (daily/weekly); platform clients have rate limiting built in.
- **Sync latency.** Tasks run on schedule, not continuously. "What happened in Slack 5 minutes ago?" requires waiting for next task run. Mitigate: ManageTask trigger for on-demand runs.
