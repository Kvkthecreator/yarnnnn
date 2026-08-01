# Credential Rotation Runbook

> Written 2026-08-01 during the Phase 1–3 security audit. This repo is **public**
> and git history is permanent — any credential ever committed must be treated as
> compromised and rotated. Purging it from the working tree (already done) stops
> *new* leaks; it does **not** un-leak history.

## When to rotate

- A secret appears in a `git grep` / gitleaks scan of the tracked tree or history.
- The Supabase "secret key revoked / GitHub secret scanning" email (the trigger for this audit).
- A contractor/session with access rotates off.
- Routine: at least every 90 days for the service key and DB password.

## What is exposed (as of this audit)

Committed to public history (rotate all — history purge is separate, see below):

| Secret | Where it lived | Rotate via |
|--------|----------------|------------|
| Postgres password (`postgres.noxgq…`) | ACCESS.md + ~12 files, now purged from tree | Supabase → Project Settings → Database → **Reset database password** |
| Service key (`sb_secret_…`) | ACCESS.md, TESTING-ENVIRONMENT.md, now purged | Supabase → Project Settings → API → **Rotate service_role key** |
| Anon key (JWT) | ACCESS.md, now purged | Rotates with the JWT secret; low urgency (anon is public by design) but roll it when you roll the JWT secret |

## Rotation procedure (DB password + service key)

The **danger** during rotation is service outage from the CLAUDE.md §5 env-var parity trap:
the same secret lives on 3 Render services. Change all of them together.

1. **Rotate in Supabase** (dashboard) — get the new value.
2. **Update all 3 Render services atomically** — use the Render MCP `update_environment_variables`:
   - `yarnnn-api` (`srv-d5sqotcr85hc73dpkqdg`)
   - `yarnnn-unified-scheduler` (`crn-d604uqili9vc73ankvag`)
   - `yarnnn-mcp-server` (`srv-d6f4vg1drdic739nli4g`)

   | Secret | API | Scheduler | MCP |
   |--------|-----|-----------|-----|
   | `DATABASE_URL` (new password) | ✅ | ✅ | ✅ |
   | `SUPABASE_SERVICE_KEY` | ✅ | ✅ | ✅ |
   | `SUPABASE_ANON_KEY` | ✅ | ✅ | ✅ |

   Missing the Scheduler is the classic mistake — it silently fails to decrypt OAuth
   tokens and reports `success=True` with 0 items (CLAUDE.md Common Pitfalls #4).
3. **Redeploy** all three; confirm health checks green.
4. **Update your local `~/.zshrc` / `docs/database/ACCESS.local.md`** (gitignored) with the new
   `SUPABASE_DB_URL` etc.
5. **Verify the old credential is dead** — an old psql connection string should now fail auth.
6. **Review Supabase access logs** for the exposure window (the email cited ~7 days of the
   revoked key still authenticating) — look for bulk reads on `platform_connections`
   (encrypted OAuth tokens), `workspace_files`, and `memories`.

## Least-privilege roles (stop using `postgres` superuser)

Apply `supabase/migrations/230_security_least_privilege_roles.sql` once (fill in passwords
from a secret manager first). Then, for **human** ad-hoc access, prefer:

```bash
export SUPABASE_DB_URL_RO="postgresql://yarnnn_readonly:<pw>@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
export SUPABASE_DB_URL_MIGRATE="postgresql://yarnnn_migrate:<pw>@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
```

The app runtime keeps `service_role` (`SUPABASE_SERVICE_KEY`) — those roles are operator-only.

## Purging secrets from git history (separate, disruptive)

Purging the working tree does not remove secrets from past commits. To scrub history:

```bash
# Preferred: git-filter-repo (install via brew/pip)
git filter-repo --replace-text <(cat <<'EOF'
yarNNN!!@@##$$==>REDACTED
sb_secret_-8NWVKf09Cf56mO3JrjPqw_5FqL423G==>REDACTED
EOF
)
# then force-push (coordinate — rewrites all hashes) and have collaborators re-clone.
```

This is **not a substitute for rotation** — assume the values were already harvested from the
public repo. Rotate first; scrub history second (or accept history and rely on rotation).

## Guardrails now in place (Phase 1)

- `.gitleaks.toml` + `.github/workflows/secret-scan.yml` — CI blocks pushed secrets.
- `.pre-commit-config.yaml` — local gitleaks hook (`pip install pre-commit && pre-commit install`).
- `docs/database/ACCESS.local.md` and `.secrets.local` are gitignored.
- All tracked docs/scripts reference `$SUPABASE_DB_URL` / env vars, never literals.
