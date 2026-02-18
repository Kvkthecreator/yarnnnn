# Database Access Guide

## Supabase Project Details

**Project Reference**: `noxgqcwynkzqabljjyon`
**Region**: `ap-southeast-1` (Singapore)
**Dashboard**: https://supabase.com/dashboard/project/noxgqcwynkzqabljjyon

## Quick Access (Copy-Paste Ready)

### psql Command Line (Recommended)

```bash
# Working connection string with URL-encoded password
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
```

**Important**: The password must be URL-encoded in the connection string. Don't use PGPASSWORD env var with special characters.

### Password Reference

- **Raw password**: `yarNNN!!@@##$$`
- **URL-encoded**: `yarNNN%21%21%40%40%23%23%24%24`

## Connection String Formats

### Transaction Pooler (Port 6543) - For Serverless/API
```
postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?pgbouncer=true
```

### Session Pooler (Port 5432) - For Long-Lived Connections
```
postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres
```

## Environment Variables

For Render API deployment:
```bash
DATABASE_URL=postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?pgbouncer=true
SUPABASE_URL=https://noxgqcwynkzqabljjyon.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5veGdxY3d5bmt6cWFibGpqeW9uIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk1NzgyMzAsImV4cCI6MjA4NTE1NDIzMH0.XnE9rO-7ipQH_9F5Xx0wdSlQK1MM-00y0c3ny6cP6Ic
SUPABASE_SERVICE_KEY=sb_secret_-8NWVKf09Cf56mO3JrjPqw_5FqL423G
```

## Running Migrations via psql

### Run SQL File
```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/001_initial_schema.sql
```

### Run Inline SQL
```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -c "SELECT * FROM projects LIMIT 5;"
```

### Verify Tables
```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"
```

## Password Encoding Reference

| Character | Encoded |
|-----------|---------|
| `!` | `%21` |
| `@` | `%40` |
| `#` | `%23` |
| `$` | `%24` |
| `%` | `%25` |
| `&` | `%26` |

Example: `yarNNN!!@@##$$` → `yarNNN%21%21%40%40%23%23%24%24`

## GUI Tools (TablePlus, DBeaver, pgAdmin)

- **Host**: `aws-1-ap-southeast-1.pooler.supabase.com`
- **Port**: `6543` (transaction pooler) or `5432` (session pooler)
- **Database**: `postgres`
- **User**: `postgres.noxgqcwynkzqabljjyon`
- **Password**: `yarNNN!!@@##$$`
- **SSL**: Required

## Troubleshooting

### "password authentication failed"
- PGPASSWORD env var doesn't work well with special characters
- Use the URL-encoded password directly in the connection string instead

### "Tenant or user not found"
- Verify the region is correct (`aws-0-ap-southeast-1`)
- Double-check all special characters are encoded

### Connection Timeout
- Add `?sslmode=require` to connection string
- Try session pooler (port 5432) instead of transaction pooler (6543)

---

## Completed Migrations

### Migration 059: Drop dead columns from session_messages (2026-02-18) ✅

**Status**: Applied

```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/059_drop_dead_columns.sql
```

**Changes**:
- Drops `knowledge_extracted` and `knowledge_extracted_at` from `session_messages`
- These were placeholder columns for background conversation extraction (ADR-059 removed that pipeline)
- Zero reads/writes in application code — confirmed before dropping

---

### Migration 058: Fix SECURITY DEFINER View (2026-02-18) ✅

**Status**: Applied

```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/058_fix_security_definer_view.sql
```

**Changes**:
- Recreates `deliverable_type_metrics` view with `security_invoker = true`
- Fixes Supabase Advisor security warning about RLS bypass via SECURITY DEFINER views

---

### Migrations 055-057: ADR-059 Simplified Context Model (2026-02-18) ✅

**Status**: Applied

```bash
# Run in sequence:
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/055_user_context_table.sql
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/056_user_context_data_migration.sql
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/057_drop_knowledge_tables.sql
```

**Changes**:
- **Creates** `user_context(user_id, key, value, source, confidence)` — single flat Memory store
  - Keys: `name`, `role`, `company`, `timezone`, `summary`, `tone_{platform}`, `verbosity_{platform}`, `fact:...`, `instruction:...`, `preference:...`
  - Sources: `user_stated`, `tp_extracted`, `document`
- **Migrates** stated fields from `knowledge_profile` → `user_context` (inferred fields discarded)
- **Migrates** `user_stated` entries from `knowledge_entries` → `user_context`
- **Migrates** stated style preferences from `knowledge_styles` → `user_context`
- **Drops**: `knowledge_profile`, `knowledge_styles`, `knowledge_domains`, `knowledge_entries`

---

### Migrations 051-054: ADR-060 Background Conversation Analyst (2026-02-16/17) ✅

**Status**: Applied

```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/051_suggested_deliverable_status.sql
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/052_suggestion_notification_preference.sql
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/053_get_active_users_for_analysis.sql
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/054_analyst_cold_start_tracking.sql
```

**Changes**:
- Adds `suggested` status to `deliverable_versions` (auto-detected pattern proposals)
- Adds notification preference for suggested deliverables to `user_notification_preferences`
- Adds `get_active_users_for_analysis()` RPC for conversation analyst
- Adds cold-start tracking column to `user_notification_preferences`

---

### Migrations 049-050: Fix RPCs for ADR-058 schema (2026-02-13) ✅

**Status**: Applied

```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/049_fix_document_rpcs.sql
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/050_fix_coverage_summary.sql
```

**Changes**:
- 049: Updates `get_document_with_stats()` to use `filesystem_documents`/`filesystem_chunks`
- 050: Recreates `get_coverage_summary()` using `sync_registry` (replaces dropped `integration_coverage`)

---

### Migrations 043-048: ADR-058 Knowledge Base Architecture (2026-02-13) ✅

**Status**: Applied — **knowledge_* tables superseded by ADR-059** (migrations 055-057)

**Changes**:
- **Terminology alignment** (still current — these table names are correct):
  - `user_integrations` → `platform_connections`
  - `ephemeral_context` → `filesystem_items`
  - `documents` → `filesystem_documents`
  - `chunks` → `filesystem_chunks`
- **knowledge_* tables** (created in 043, dropped in 057 — do not reference in new code):
  - `knowledge_profile`, `knowledge_styles`, `knowledge_domains`, `knowledge_entries`
- 046: Restores `integration_import_jobs` (accidentally dropped in 045)
- 047-048: Fix RPCs to use knowledge_entries/knowledge_domains (also superseded by ADR-059)

---

### Migrations 001-050: Prior migrations ✅

**Status**: Applied — see individual files in `supabase/migrations/` for details.

Notable milestones:
- 041: `notifications` + `event_trigger_log` tables (ADR-040)
- 039: Calendar type classification (`meeting_prep`, `weekly_calendar_preview`)
- 037: Deliverable type classification + `deliverable_proposals` + `user_interaction_patterns`