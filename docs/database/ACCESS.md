# Database Access Guide

> **Security (2026-08-01):** Credentials MUST NOT live in this file or anywhere in the tracked
> tree — this repo is public and git history is permanent. All connection strings below reference
> environment variables. Put the real values in a **gitignored** `docs/database/ACCESS.local.md`
> (or your shell profile / a `.env` you never commit). If you ever see a raw password or key in a
> tracked file, treat it as a leak: rotate it and purge it.

## Supabase Project Details

**Project Reference**: `noxgqcwynkzqabljjyon`
**Region**: `ap-southeast-1` (Singapore)
**Dashboard**: https://supabase.com/dashboard/project/noxgqcwynkzqabljjyon

## One-Time Setup (local, uncommitted)

Two ways to hold the connection string, both keeping it out of the tracked tree:

**(A) Shell profile** — export it in `~/.zshrc` (real value never committed):

```bash
export SUPABASE_DB_URL="postgresql://postgres.noxgqcwynkzqabljjyon:<URL_ENCODED_PASSWORD>@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
```

**(B) Repo-local `.secrets.local`** (gitignored) — preferred when a tool/agent should run
migrations from the repo without inheriting your interactive shell. Copy `.secrets.local.example`
to `.secrets.local` and fill in the one line. Then apply migrations through the secure runner,
which sources `.secrets.local`, runs in a single transaction, and never echoes the secret:

```bash
cp .secrets.local.example .secrets.local     # then paste the real string into it
scripts/db/run-migration.sh --dry-run supabase/migrations/229_security_enable_rls_on_tasks.sql  # BEGIN…ROLLBACK preview
scripts/db/run-migration.sh supabase/migrations/229_security_enable_rls_on_tasks.sql             # real apply
```

`.secrets.local` is the ONLY place a live credential may sit locally; it is gitignored and must
never be committed or pasted into chat.

Prefer the **least-privilege** roles for day-to-day work rather than the `postgres` superuser.
Create them once with `supabase/migrations/230_security_least_privilege_roles.sql` (fill in the
passwords first), then use `yarnnn_readonly` for ad-hoc queries and `yarnnn_migrate` for DDL:

```bash
export SUPABASE_DB_URL_RO="postgresql://yarnnn_readonly:<PW>@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"   # SELECT-only, for ad-hoc queries
export SUPABASE_DB_URL_MIGRATE="postgresql://yarnnn_migrate:<PW>@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" # DDL, for migrations
```

## Quick Access

### psql Command Line

```bash
# Ad-hoc read-only queries — uses the readonly role
psql "$SUPABASE_DB_URL_RO"

# Full access (migrations, DDL) — superuser or migrate role
psql "$SUPABASE_DB_URL"
```

**Note**: The password contains special characters and must be **URL-encoded** inside the
connection string (`!`→`%21`, `@`→`%40`, `#`→`%23`, `$`→`%24`, `%`→`%25`, `&`→`%26`).
Don't use `PGPASSWORD` with special characters.

## Connection String Shapes (ports)

| Purpose | Port | Notes |
|---------|------|-------|
| Transaction pooler (serverless/API) | `6543` | append `?pgbouncer=true` |
| Session pooler (long-lived) | `5432` | for GUI tools / long connections |

Both use host `aws-1-ap-southeast-1.pooler.supabase.com`, database `postgres`,
user `postgres.noxgqcwynkzqabljjyon` (or a least-privilege role).

## Environment Variables (Render)

Set these in the Render dashboard for **all 3 services** (see CLAUDE.md §5 for the parity matrix) —
never in a tracked file. Names only:

```bash
DATABASE_URL          # transaction-pooler connection string, ?pgbouncer=true
SUPABASE_URL          # https://noxgqcwynkzqabljjyon.supabase.co
SUPABASE_ANON_KEY     # public anon JWT (safe client-side, but keep out of git)
SUPABASE_SERVICE_KEY  # sb_secret_… — RLS bypass; SECRET; API + Scheduler + MCP only
```

## Running Migrations via psql

```bash
# Run a SQL file
psql "$SUPABASE_DB_URL_MIGRATE" -f supabase/migrations/001_initial_schema.sql

# Run inline SQL
psql "$SUPABASE_DB_URL_RO" -c "SELECT * FROM agents LIMIT 5;"

# Verify tables
psql "$SUPABASE_DB_URL_RO" -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"
```

## GUI Tools (TablePlus, DBeaver, pgAdmin)

- **Host**: `aws-1-ap-southeast-1.pooler.supabase.com`
- **Port**: `6543` (transaction pooler) or `5432` (session pooler)
- **Database**: `postgres`
- **User**: `postgres.noxgqcwynkzqabljjyon` (or a least-privilege role)
- **Password**: from the dashboard — never recorded here
- **SSL**: Required

## Troubleshooting

### "password authentication failed"
- `PGPASSWORD` doesn't work well with special characters — put the URL-encoded password
  directly in the connection string instead.

### "Tenant or user not found"
- Verify the region (`ap-southeast-1`) and that every special character is URL-encoded.

### Connection Timeout
- Add `?sslmode=require`; try the session pooler (5432) instead of the transaction pooler (6543).

## API Testing with User JWT

For production API endpoints requiring user auth (`/api/chat`, `/api/agents/{id}/run`), you need a
valid **user JWT** — service keys don't work on `UserClient`-protected routes.

### Generate a JWT via Magic Link OTP

```python
import os
from supabase import create_client

SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]   # never hardcode
ANON_KEY    = os.environ["SUPABASE_ANON_KEY"]
URL         = os.environ["SUPABASE_URL"]

# Step 1: Generate magic link (requires service key — admin endpoint)
admin_client = create_client(URL, SERVICE_KEY)
link_resp = admin_client.auth.admin.generate_link({
    "type": "magiclink",
    "email": "kvkthecreator@gmail.com",
})
otp = link_resp.properties.email_otp

# Step 2: Verify OTP to get access token (uses anon key)
anon_client = create_client(URL, ANON_KEY)
auth_resp = anon_client.auth.verify_otp({
    "email": "kvkthecreator@gmail.com",
    "token": otp,
    "type": "magiclink",
})
jwt = auth_resp.session.access_token  # Valid ~1 hour
```

### Use the JWT

```bash
curl -N "https://yarnnn-api.onrender.com/api/chat" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello", "include_context": true}'

curl -X POST "https://yarnnn-api.onrender.com/api/agents/{agent_id}/run" \
  -H "Authorization: Bearer $JWT"
```

### List All Users (Admin)

```python
admin_client = create_client(URL, SERVICE_KEY)
for u in admin_client.auth.admin.list_users():
    print(f"{u.id} {u.email}")
```

---

See [MIGRATIONS.md](MIGRATIONS.md) for applied migration history.
