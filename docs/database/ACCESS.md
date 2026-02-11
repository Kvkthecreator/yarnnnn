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

### Migration 041: ADR-040 Notifications (2026-02-11) ✅

**Status**: Applied

```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/041_notifications.sql
```

**Changes**:
- Creates `notifications` table for audit logging of sent notifications
- Creates `event_trigger_log` table for database-backed cooldown tracking
- Adds `cleanup_old_trigger_logs()` function for retention management
- RLS policies for user access and service role

---

### Migration 039: Calendar Type Classification (2026-02-11) ✅

**Status**: Applied

```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/039_calendar_type_classification.sql
```

**Changes**:
- Adds type_classification for `meeting_prep` and `weekly_calendar_preview` types
- Both are `platform_bound` with `primary_platform: "calendar"`
- `meeting_prep` is `reactive` (triggers before meetings)
- `weekly_calendar_preview` is `scheduled`

---

### Migration 038: Agent Type Rename (2026-02-11) ✅

**Status**: Applied

```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/038_agent_type_rename.sql
```

**Changes**:
- Renames `agent_type` values: research → synthesizer, content → deliverable, reporting → report
- Updates `work_tickets` and `agent_sessions` tables
- Adds documentation comments to columns

---

### Migration 037: ADR-044 Deliverable Type Classification (2026-02-11) ✅

**Status**: Applied

```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/037_deliverable_type_classification.sql
```

**Changes**:
- Adds `type_classification` JSONB column to `deliverables` table
- Creates `deliverable_proposals` table for emergent discovery
- Creates `user_interaction_patterns` table for pattern detection
- Backfills existing deliverables with inferred classification
- Helper functions: `increment_interaction_pattern`, `should_propose_deliverable`