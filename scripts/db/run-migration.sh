#!/usr/bin/env bash
# run-migration.sh — apply a SQL migration through psql, securely.
#
# Security model (2026-08-03): the DB connection string is NEVER in the tracked
# tree (Phase 1 invariant). It lives in a gitignored `.secrets.local` at repo
# root as `export SUPABASE_DB_URL=...`. This script sources that file, runs the
# migration in a single transaction, and never echoes the secret. If the secret
# is absent it fails closed with instructions — it does not prompt for or print
# the value.
#
# Usage:
#   scripts/db/run-migration.sh supabase/migrations/229_security_enable_rls_on_tasks.sql
#   scripts/db/run-migration.sh --dry-run supabase/migrations/231_adr465_share_as_view.sql
#
# --dry-run wraps the file in BEGIN; ... ROLLBACK; so you can see it apply
# cleanly without committing (use for a safety check before the real run).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SECRETS_FILE="$REPO_ROOT/.secrets.local"

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi

MIGRATION="${1:-}"
if [[ -z "$MIGRATION" ]]; then
  echo "usage: $0 [--dry-run] <path-to-migration.sql>" >&2
  exit 2
fi
if [[ ! -f "$MIGRATION" ]]; then
  echo "error: migration file not found: $MIGRATION" >&2
  exit 2
fi

# Load the secret ONLY from the gitignored local file (or an already-exported env).
if [[ -z "${SUPABASE_DB_URL:-}" ]]; then
  if [[ -f "$SECRETS_FILE" ]]; then
    # shellcheck disable=SC1090
    set +u; source "$SECRETS_FILE"; set -u
  fi
fi

if [[ -z "${SUPABASE_DB_URL:-}" ]]; then
  cat >&2 <<EOF
error: SUPABASE_DB_URL is not set and $SECRETS_FILE does not define it.

One-time setup (the connection string never enters the tracked tree):
  1. Copy the string from the Supabase dashboard → Project Settings → Database.
  2. Create $REPO_ROOT/.secrets.local (already gitignored) containing:
       export SUPABASE_DB_URL="postgresql://postgres.<ref>:<url-encoded-pw>@<host>:6543/postgres?sslmode=require"
  3. Re-run this script. Nothing prints the value.
EOF
  exit 3
fi

# Guardrail: never let the secret leak into the shell trace / logs.
set +x

echo "→ applying $(basename "$MIGRATION")$([[ $DRY_RUN == 1 ]] && echo ' (DRY RUN — will ROLLBACK)')"

if [[ $DRY_RUN == 1 ]]; then
  # Preview: run inside one transaction and ROLLBACK. We append ROLLBACK and let
  # --single-transaction supply the opening BEGIN (no manual BEGIN — that would
  # double-open and warn). ON_ERROR_STOP aborts loudly on the first error.
  { cat "$MIGRATION"; echo ""; echo "ROLLBACK;"; } \
    | psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 --single-transaction
else
  # Real apply: single transaction, stop on first error.
  psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 --single-transaction -f "$MIGRATION"
fi

echo "✓ done: $(basename "$MIGRATION")"
