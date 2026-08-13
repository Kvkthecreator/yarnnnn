# Post-Rename E2E Testing Playbook

**Context:** ADR-103 terminology migration (deliverable → agent) merged and deployed.
**Date:** 2026-03-11
**Deployment:** `21971f7` — live on Render API (`yarnnn-api.onrender.com`)
**DB Migration:** `098_agentic_terminology_rename.sql` — already applied to production Supabase

---

## Pre-Flight Checks

- [ ] **API health**: `GET /health` returns `{"status":"ok"}`
- [ ] **Supabase PostgREST schema cache**: Refresh from Supabase Dashboard → Settings → API → "Reload" if any PGRST errors appear
- [ ] **All 4 Render services running**: API (live), Unified Scheduler (cron), Platform Sync (cron), MCP Server (live)

---

## 1. Agent CRUD (Core Data Layer)

Tests that the `agents` table, RPC functions, and API routes work end-to-end.

### 1.1 Create Agent
- [ ] Open YARNNN → navigate to Agent chat
- [ ] Ask TP to create a new agent (e.g., "Create a weekly Slack digest for #general")
- [ ] Verify agent appears in `/agents` list page
- [ ] Verify agent card shows: title, mode badge (recurring), schedule, destination
- [ ] **DB check**: `agents` table has row with correct `agent_type`, `mode`, `schedule`, `agent_instructions`

### 1.2 List Agents
- [ ] `/agents` page loads without errors
- [ ] All existing agents display with correct mode badges
- [ ] Filter toggle (All / Active / Paused) works
- [ ] `AGENT_TYPE_LABELS` renders correctly (Recap, Auto Meeting Prep, etc.)

### 1.3 Agent Detail
- [ ] Click into an agent → `/agents/{id}` loads
- [ ] Left panel: agent-scoped chat area renders
- [ ] Right panel tabs all load:
  - [ ] **Versions** — shows run history (or empty state)
  - [ ] **Instructions** — shows `agent_instructions` content
  - [ ] **Memory** — shows `agent_memory` (observations, goal, etc.)
  - [ ] **Sessions** — shows scoped chat sessions
  - [ ] **Settings** — shows schedule, sources, destination config

### 1.4 Update Agent
- [ ] Edit agent title via Settings tab → verify save persists
- [ ] Edit agent instructions → verify persists
- [ ] Toggle agent status (active ↔ paused) → verify mode badge updates
- [ ] Change schedule → verify `next_run_at` recalculated

### 1.5 Archive Agent
- [ ] Archive an agent → verify it disappears from active list
- [ ] Verify it's not returned by `GET /api/agents` (default filter excludes archived)

---

## 2. Agent Execution Pipeline

Tests the full generation pipeline: trigger → strategy → generation → delivery.

### 2.1 Ad-Hoc Run (Manual Trigger)
- [ ] From agent detail page, click "Run Now"
- [ ] Verify `POST /api/agents/{id}/run` returns success
- [ ] Verify new run appears in Versions tab with status `delivered` or `generating`
- [ ] Verify `agent_runs` table has new row with correct `agent_id`, `version_number`
- [ ] Verify `last_run_at` updated on the agent

### 2.2 Scheduled Run (Cron Trigger)
- [ ] Create/update a recurring agent with `next_run_at` in the past
- [ ] Wait for scheduler cron tick (≤5 min) OR check scheduler logs
- [ ] Verify run was triggered and completed
- [ ] Verify `next_run_at` advanced to next occurrence
- [ ] Verify `activity_log` has `agent_run` event

### 2.3 Proactive Review
- [ ] Create a proactive-mode agent
- [ ] Set `proactive_next_review_at` to past
- [ ] Wait for scheduler → verify Haiku review pass runs
- [ ] Verify `agent_memory` updated with review decision (observe/generate/sleep)
- [ ] Verify `proactive_next_review_at` advanced

### 2.4 Source Freshness
- [ ] `GET /api/agents/{id}/sources/freshness` returns valid response
- [ ] Verify stale sources flagged correctly (based on last sync vs last run)

### 2.5 Delivery
- [ ] Agent with email destination → verify email sent via Resend
- [ ] Agent with no destination → verify status is `delivered` (content-only)
- [ ] Check `agent_runs.delivered_at` populated on success
- [ ] Check `agent_runs.delivery_error` populated on failure

### 2.6 ADR-102: Output as Platform Content
- [ ] After successful run, verify `platform_content` row exists with `platform='yarnnn'`
- [ ] Verify `resource_id` = agent_id, `retained=true`, `retained_reason='yarnnn_output'`

---

## 3. Agent-Scoped Chat (ADR-087 Phase 3)

### 3.1 Scoped Session Creation
- [ ] Navigate to `/agents/{id}` → send a message in the chat panel
- [ ] Verify `chat_sessions` row created with `agent_id` = this agent's ID
- [ ] Verify agent instructions + memory injected into TP working memory

### 3.2 Session History
- [ ] Sessions tab shows scoped sessions for this agent only
- [ ] Global chat history (`/chat/history`) still works independently

### 3.3 Context Injection
- [ ] In agent-scoped chat, ask "what are your instructions?"
- [ ] TP should reference the agent's `agent_instructions` content
- [ ] Ask "what do you remember?" → TP should reference `agent_memory`

---

## 4. Orchestrator Chat (Global TP)

### 4.1 Basic Chat
- [ ] Send a message in global chat (not agent-scoped)
- [ ] Verify streaming response works
- [ ] Verify tool use works (search, platform queries)

### 4.2 Agent Management via Chat
- [ ] Ask TP to list agents → verify it uses `ListAgents` primitive
- [ ] Ask TP to create an agent → verify `CreateAgent` primitive works
- [ ] Ask TP about a specific agent's output → verify context retrieval

### 4.3 Coordinator Primitives
- [ ] If coordinator agent exists, verify `CreateAgent` tool definition loads
- [ ] Verify `AdvanceAgentSchedule` tool definition loads
- [ ] Test coordinator creating a child agent (if applicable)

---

## 5. Platform Sync & Context

### 5.1 Sync Pipeline
- [ ] Verify platform sync cron is running (check Render cron logs)
- [ ] Verify `platform_content` table receiving new items
- [ ] Verify TTL-based cleanup running (hourly, first 5 min of hour)

### 5.2 Context Page
- [ ] Navigate to `/context` pages → verify platform content displays
- [ ] Verify search across platforms works

### 5.3 Memory Page
- [ ] Navigate to `/memory` → verify `user_memory` entries display
- [ ] Edit a memory → verify persistence

---

## 6. MCP Server

### 6.1 Tool Availability
- [ ] `get_status` — returns connected platforms, active agents count
- [ ] `list_agents` — returns agent list with correct fields
- [ ] `run_agent` — triggers execution, returns result
- [ ] `get_agent_output` — retrieves latest run content
- [ ] `get_context` — returns assembled working memory
- [ ] `search_content` — queries platform_content with results

### 6.2 Auth
- [ ] Bearer token auth works (Claude Desktop/Code)
- [ ] OAuth 2.1 flow works (Claude.ai) — if testable

---

## 7. Scheduler Subsystems

### 7.1 Unified Scheduler
- [ ] Check Render cron logs for `yarnnn-unified-scheduler`
- [ ] Verify `[AGENT]` log prefix (not `[DELIVERABLE]`)
- [ ] Verify scheduler heartbeat in `activity_log`

### 7.2 Memory Extraction (Nightly)
- [ ] Runs at midnight UTC only
- [ ] Processes sessions with ≥3 user messages
- [ ] Generates summaries for sessions with ≥5 messages

### 7.3 Platform Sync Scheduler
- [ ] Check Render cron logs for `yarnnn-platform-sync`
- [ ] Verify tier-gated frequency (pro=hourly, free=daily)

---

## 8. Database Schema Verification

Quick SQL checks against production:

```sql
-- Verify new tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('agents', 'agent_runs', 'agent_source_runs', 'agent_export_preferences', 'agent_validation_results', 'agent_proposals', 'agent_context_log')
ORDER BY table_name;

-- Verify old tables are gone
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name LIKE 'deliverable%';

-- Verify RPC functions renamed
SELECT routine_name FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_name LIKE '%agent%'
ORDER BY routine_name;

-- Verify agent_id FK on chat_sessions
SELECT column_name FROM information_schema.columns
WHERE table_name = 'chat_sessions' AND column_name = 'agent_id';

-- Verify notifications constraint accepts 'agent'
SELECT * FROM notifications WHERE source_type = 'agent' LIMIT 1;

-- Count agents (sanity — should be 0 if test data was dropped)
SELECT count(*) FROM agents;
```

---

## 9. Regression Watchlist

Things that could break silently:

| Risk | What to check | How |
|------|---------------|-----|
| PostgREST cache stale | Any PGRST205/PGRST301 errors | Check API logs on Render |
| RLS policies missing | 403/empty results on agent queries | Create agent, verify it returns |
| RPC function missing | 500 on scheduler or agent run | Check `get_due_agents()`, `get_next_run_number()` |
| FK constraint violation | 500 on chat session creation | Send message in agent-scoped chat |
| Notification constraint | 500 on agent completion notification | Trigger agent run, check notification |
| Activity log writes | Silent failure (service client needed) | Check `activity_log` after agent run |
| Export/delivery | `deliver_version()` param mismatch | Trigger agent with email destination |

---

## Quick Smoke Test (5 min)

If short on time, do these 5 checks:

1. **Load `/agents` page** — agents list renders
2. **Click into an agent** — detail page loads with all tabs
3. **Send a chat message** (global or scoped) — streaming works
4. **Trigger "Run Now"** on an agent — execution completes
5. **Check Render API logs** — no `NameError`, no `PGRST` errors

---

*Generated post ADR-103 merge. Update this playbook as new surfaces are added.*
