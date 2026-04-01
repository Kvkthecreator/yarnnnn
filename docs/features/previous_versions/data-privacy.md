# Data & Privacy (Settings Purge Workflows)

> **Status**: Active
> **Surface**: `/settings?tab=account`

---

## Overview

YARNNN exposes three levels of destructive actions:

1. **Selective Purge**: remove one data type.
2. **Category Reset**: remove a related group of data.
3. **Full Actions**: reset all product data or fully deactivate account.

All backend purge operations run with service-role filtering by `user_id` (or `owner_id` for workspaces) to ensure consistent deletion behavior across RLS policies.

---

## Retention Rules

### Selective Purge

- **Clear Conversations**: deletes `chat_sessions` (and cascading messages).
- **Clear Memories**: deletes only entry keys in `user_memory` matching:
  - `fact:*`
  - `instruction:*`
  - `preference:*`
- **Clear Documents**: deletes `filesystem_documents` (and cascading chunks).

### Category Reset

- **Clear All Content**: removes agent artifacts and planning/execution traces:
  - `agents` (cascades `agent_runs`, `agent_export_preferences`, delivery logs)
  - `agent_proposals`
  - `user_interaction_patterns`
  - `event_trigger_log` (+ optional legacy `trigger_event_log`)
- **Clear All Context**: removes context and sync-state:
  - `chat_sessions`
  - `user_memory` (all keys)
  - `filesystem_documents`
  - `platform_content`
  - `sync_registry`
  - `integration_sync_config`
  - optional `slack_user_cache`
- **Clear Integrations**: disconnects integrations and removes integration-linked state/history:
  - `platform_connections`
  - `integration_import_jobs`
  - `export_log`
  - `platform_content`
  - `sync_registry`
  - `integration_sync_config`
  - optional `slack_user_cache`
  - `agent_export_preferences` for user-owned agents

### Full Actions

- **Full Data Reset**:
  - Deletes all user-scoped product data (activity, notifications, context, content, integrations, platform styles, proposal/pattern traces, etc.)
  - Deletes all user workspaces
  - Recreates one default workspace (`"My Workspace"`)
  - Keeps auth account active
- **Delete Account (Deactivate)**:
  - Deletes `auth.users` record via admin API
  - Relies on FK cascade for user-linked data removal
  - Performs best-effort cleanup of non-FK MCP OAuth token/code tables

---

## Key Files

| File | Purpose |
|------|---------|
| `api/routes/account.py` | Purge endpoint implementation and retention logic |
| `web/app/(authenticated)/settings/page.tsx` | Data & Privacy UI, confirmation copy, action wiring |
| `web/lib/api/client.ts` | Settings API client methods |

---

## Notes

- Deactivation returns success only when auth-user deletion succeeds.
- Optional/legacy tables are handled defensively (best-effort cleanup) to avoid hard failures on schema drift.
