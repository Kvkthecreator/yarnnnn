# Database Migrations

Applied migrations in reverse-chronological order. See `supabase/migrations/` for the SQL source.

To run a migration:
```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/<file>.sql
```

---

### 084 — Rename user_context → user_memory (2026-03-03)

- Renames `user_context` table to `user_memory`
- Renames indexes: `user_context_user_id_idx` → `user_memory_user_id_idx`, `idx_user_context_source_ref` → `idx_user_memory_source_ref`
- Renames RLS policy and unique constraint
- ADR-087: Naming debt resolution (naming-conventions.md)

---

### 083 — Sync registry error columns (2026-02-27) ✅

- Adds error tracking columns to `sync_registry`
- ADR-077: Platform sync reliability

---

### 082 — MCP OAuth tables (2026-02-27) ✅

- Creates `mcp_oauth_clients`, `mcp_oauth_codes`, `mcp_oauth_access_tokens`, `mcp_oauth_refresh_tokens`
- ADR-075: MCP server OAuth 2.1 storage

---

### 081 — Signal history RLS (2026-02-27) ✅

- Adds RLS policies to `signal_history` table
- ADR-068: Signal processing access control

---

### 080 — Activity log granular events (2026-02-27) ✅

- Extends `activity_log_event_type_check` with granular event types
- ADR-063: Activity layer expansion

---

### 079 — Daily token usage (2026-02-25) ✅

- Creates `get_daily_token_usage()` SQL function
- Aggregates `input_tokens + output_tokens` from `session_messages.metadata`
- ADR-053: Token budget enforcement

---

### 078 — User context source ref (2026-02-25) ✅

- Adds `source_ref UUID` and `source_type TEXT` to `user_context` (now `user_memory`)
- Partial index on `source_ref WHERE source_ref IS NOT NULL`
- ADR-072: Provenance tracking for extracted memories

---

### 074–077 — ADR-072 + ADR-077 Platform Content (2026-02-25) ✅

- 074: Creates `platform_content` table (replaces `filesystem_items`)
- 075: Migrates `filesystem_items` data → `platform_content`
- 076: Drops `filesystem_items` table
- 077: Platform sync overhaul indexes and constraints
- TTLs: Slack 14d, Gmail 30d, Notion 90d, Calendar 2d

---

### 073 — Drop governance columns (2026-02-19) ✅

- Removes `governance` and `governance_ceiling` columns from `deliverables`
- ADR-066 removed governance gates (delivery-first for all deliverables)
- Columns were marked deprecated on 2026-02-19, now fully removed
- CLAUDE.md discipline: "Delete legacy code when replacing with new implementation"

---

### 072 — Signal preferences (2026-02-19) ✅

- Extends `user_notification_preferences` with signal type toggles
- Columns: `signal_meeting_prep`, `signal_silence_alert`, `signal_contact_drift` (all BOOLEAN DEFAULT true)
- Users can opt-in/opt-out of specific proactive signal types
- ADR-068 Phase 3

---

### 071 — Signal history table (2026-02-19) ✅

- Creates `signal_history` table for per-signal deduplication tracking
- Schema: `(user_id, signal_type, signal_ref, last_triggered_at, deliverable_id, metadata)`
- UNIQUE constraint on `(user_id, signal_type, signal_ref)`
- Prevents re-creating signal-emergent deliverables for same signal within deduplication windows
- Deduplication windows: meeting_prep (24h), silence_alert (7d), contact_drift (14d)
- ADR-068 Phase 4

---

### 070 — ADR-068 deliverables.origin column (2026-02-19) ✅

- Adds `origin TEXT NOT NULL DEFAULT 'user_configured'` with CHECK constraint `('user_configured', 'analyst_suggested', 'signal_emergent')`
- All existing rows default to `user_configured`
- Adds sparse index on `(user_id, origin)` WHERE origin != 'user_configured' for signal-emergent queries

---

### 069 — Fix filesystem_items item_id deduplication (2026-02-19) ✅

- `TRUNCATE TABLE filesystem_items` — clears all rows where `item_id` was stored as `uuid4()` (same as `id` PK) instead of the platform-native identifier
- Root cause: `_store_filesystem_items` in `platform_worker.py` passed `"id": uuid4()` to upsert; PostgREST stored it in both `id` and `item_id`. The UNIQUE constraint `(user_id, platform, resource_id, item_id)` was meaningless — every sync run inserted rather than upserted
- Fix: `platform_worker.py` now passes `item_id` explicitly (message_ts for Slack, message_id for Gmail, page_id for Notion, event_id for Calendar) with `on_conflict="user_id,platform,resource_id,item_id"`
- filesystem_items is a TTL cache; truncating and repopulating on next sync is correct

---

### 064 — Extend deliverable_type CHECK constraint (2026-02-19) ✅

- Drops and recreates `deliverables_deliverable_type_check` with all 25 types from `TYPE_TIERS`
- Previously missing: `slack_channel_digest`, `slack_standup`, `gmail_inbox_brief`, `notion_page_summary`, `meeting_prep`, `weekly_calendar_preview`, `weekly_status`, `project_brief`, `cross_platform_digest`, `activity_summary`, `inbox_summary`, `reply_draft`, `follow_up_tracker`, `thread_summary`
- These were accepted by backend/frontend but rejected by DB, causing 500 on deliverable create

---

### 063 — Extend activity_log event_type CHECK constraint (2026-02-19) ✅

- Adds `integration_connected`, `integration_disconnected`, `deliverable_approved`, `deliverable_rejected` to `activity_log_event_type_check`
- ADR-063: Activity log lifecycle events for OAuth and deliverable review

---

### 062 — Delivery-first status (2026-02-19) ✅

- Adds `delivered` and `failed` statuses to `deliverable_versions_status_check`
- ADR-066: Delivery-First, No Governance

---

### 061 — Session compaction (2026-02-19) ✅

- Adds `summary TEXT` and `compaction_summary TEXT` to `chat_sessions`
- Replaces 4-arg `get_or_create_chat_session` with 5-arg version using inactivity-based boundary (4h)
- Drops `idx_chat_sessions_daily`; creates `idx_chat_sessions_inactivity`
- ADR-067: Session compaction and conversational continuity

---

### 060 — Create activity_log table (2026-02-18) ✅

- Creates `activity_log(user_id, event_type, event_ref, summary, metadata, created_at)`
- event_types: `deliverable_run`, `memory_written`, `platform_synced`, `chat_session`
- RLS: users SELECT own rows; INSERT/UPDATE/DELETE service-role only (append-only)
- ADR-063: Activity layer in four-layer model

---

### 059 — Drop dead columns from session_messages (2026-02-18) ✅

- Drops `knowledge_extracted` and `knowledge_extracted_at` from `session_messages`

---

### 058 — Fix SECURITY DEFINER view (2026-02-18) ✅

- Recreates `deliverable_type_metrics` view with `security_invoker = true`

---

### 055–057 — ADR-059 Simplified Context Model (2026-02-18) ✅

- Creates `user_memory(user_id, key, value, source, confidence)` — single flat Memory store
- Migrates stated fields from `knowledge_profile`, `knowledge_entries`, `knowledge_styles` → `user_memory`
- Drops `knowledge_profile`, `knowledge_styles`, `knowledge_domains`, `knowledge_entries`

---

### 051–054 — ADR-060 Background Conversation Analyst (2026-02-16/17) ✅

- Adds `suggested` status to `deliverable_versions`
- Adds notification preference for suggested deliverables
- Adds `get_active_users_for_analysis()` RPC
- Adds cold-start tracking to `user_notification_preferences`

---

### 049–050 — Fix RPCs for ADR-058 schema (2026-02-13) ✅

- 049: Updates `get_document_with_stats()` to use `filesystem_documents`/`filesystem_chunks`
- 050: Recreates `get_coverage_summary()` using `sync_registry`

---

### 043–048 — ADR-058 Knowledge Base Architecture (2026-02-13) ✅

Terminology renames (still current):
- `user_integrations` → `platform_connections`
- `ephemeral_context` → `filesystem_items`
- `documents` → `filesystem_documents`
- `chunks` → `filesystem_chunks`

Note: knowledge_* tables created here were dropped in 055–057.

---

### 001–042 — Prior migrations ✅

Notable milestones:
- 041: `notifications` + `event_trigger_log` tables (ADR-040)
- 039: Calendar type classification (`meeting_prep`, `weekly_calendar_preview`)
- 037: Deliverable type classification + `deliverable_proposals` + `user_interaction_patterns`
