# FINDING — `get_or_create_chat_session` RPC errors on every call (stale column refs)

**Date**: 2026-06-25
**Hat**: B (external developer — finding; recommends a Hat-A fix, does not make it)
**Surfaced by**: ADR-368 MCP work — the operator-visibility fix tried to reuse this RPC for daily-session resolution and hit the error. ADR-368 routed around it (plain table ops); this finding records the underlying breakage for its own fix.
**Severity**: Low-but-real — a degraded-silently path, not a crash. Worth a small migration.

## The receipt

```
postgrest.exceptions.APIError: {'message': 'column "project_id" does not exist', 'code': '42703'}
```

- The live RPC signature (verified via `pg_proc`): `get_or_create_chat_session(p_user_id uuid, p_project_id uuid, p_session_type text, p_scope text, p_inactivity_hours int, p_agent_id uuid)`.
- The RPC **body** (last defined in `supabase/migrations/097_scoped_sessions.sql`) inserts/selects against `chat_sessions.project_id` and `chat_sessions.deliverable_id`.
- The live `chat_sessions` table (verified via `information_schema.columns`) has **neither** column — both were dropped by a later migration (the project-layer collapse, ADR-138 band) without updating the RPC body.

So **every call to this RPC raises `42703`** the moment its body touches the dropped columns.

## Blast radius (all silently degraded via try/except)

| Caller | Effect when the RPC raises |
|---|---|
| `api/services/notifications.py::_insert_chat_notification` | background notifications never land in chat history (caught, logged as warning, notification still emailed) |
| `api/routes/feed.py` session creation | falls into its except path; session resolution degrades |
| `api/mcp_server/server.py` (pre-ADR-368 draft) | would have failed the operator-visibility narrative — **ADR-368 deliberately uses plain table ops instead**, so the shipped MCP path is unaffected |

None of these crash — they all wrap the call — which is exactly why the breakage went unnoticed: the failure mode is *silent absence of a feature*, not an error surfaced to anyone.

## Recommended fix (Hat A — small migration)

Redefine `get_or_create_chat_session` against the current `chat_sessions` schema: drop the `project_id` / `deliverable_id` references from the body (the params can stay for signature compatibility, ignored, or be dropped if no caller passes them meaningfully — `feed.py` passes `p_project_id=None`). The current columns are `id, user_id, session_type, status, started_at, ended_at, context_metadata, created_at, updated_at, domain_id, summary, agent_id, task_slug, cancellation_requested` — the daily-scope logic should key on `(user_id, session_type, status, updated_at)` + `agent_id`/`task_slug` for the scoped variants.

After the migration, `notifications.py` and `feed.py` can drop their RPC-failure tolerance (or keep it as defense), and ADR-368's `_ensure_daily_session` could optionally route back through the RPC for Singular Implementation — though the plain-table-ops version is fine to keep.

**Not in scope for ADR-368** — flagged here so it doesn't stay invisible.
