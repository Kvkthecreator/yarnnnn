# Database Migrations

Applied migrations in reverse-chronological order. See `supabase/migrations/` for the SQL source.

To run a migration:
```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/<file>.sql
```

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

- Creates `user_context(user_id, key, value, source, confidence)` — single flat Memory store
- Migrates stated fields from `knowledge_profile`, `knowledge_entries`, `knowledge_styles` → `user_context`
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
