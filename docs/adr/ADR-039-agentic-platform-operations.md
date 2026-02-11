# ADR-039: Agentic Platform Operations

> **Status**: Accepted
> **Date**: 2026-02-11
> **Deciders**: Kevin (solo founder)
> **Related**: ADR-038 (Filesystem-as-Context), ADR-025 (Claude Code Alignment)

---

## Context

In the Thinking Partner (TP) experience, users frequently mention platform resources:
- "Create a digest from my daily work channel"
- "Summarize emails from Sarah this week"
- "What did we discuss in #product-updates?"

Prior to this ADR, TP would often respond with friction:
> "I can see Slack is connected, but there's no content from your 'daily work channel' synced yet. I'd need to sync your Slack data first..."

This passive, permission-seeking behavior breaks the user experience. Users expect TP to be proactive — like Claude Code, which doesn't ask "should I run grep?" but simply runs it.

## Decision

**TP should be agentic with platform operations.** When a user mentions a platform resource, TP should:

1. **Check** if the platform is connected (via `list_integrations`)
2. **Find** the specific resource (via `list_platform_resources`)
3. **Sync** the resource if needed (via `sync_platform_resource`)
4. **Report** progress and results to the user

### The Claude Code Parallel

```
Claude Code                    YARNNN TP
──────────                    ─────────
bash "npm test"              sync_platform_resource("slack", "C123")
grep "TODO"                  list_platform_resources("slack")
git status                   list_integrations()
                             get_sync_status("slack")
```

Claude Code doesn't ask "should I run npm test?" — it just runs it. TP should operate the same way with platform operations.

## New Tools Added

### 1. `list_integrations`
Show connected platforms and their status.

**Use case**: Check what's connected before attempting platform operations.

```json
{
  "success": true,
  "integrations": [
    {"provider": "slack", "status": "active", "workspace_name": "Acme Corp"},
    {"provider": "gmail", "status": "active", "email": "kevin@acme.com"}
  ],
  "not_connected": ["notion", "calendar"]
}
```

### 2. `list_platform_resources`
List available resources from a connected platform.

**Use case**: Find the specific channel/label/page the user mentioned.

```json
{
  "platform": "slack",
  "resources": [
    {"id": "C123ABC", "name": "general", "type": "public"},
    {"id": "C456DEF", "name": "daily-work", "type": "private"},
    {"id": "C789GHI", "name": "product-updates", "type": "public"}
  ]
}
```

### 3. `sync_platform_resource`
Trigger a sync/import for a specific resource.

**Use case**: Fetch latest content from a channel/label before creating a deliverable.

```json
{
  "platform": "slack",
  "resource_id": "C456DEF",
  "resource_name": "#daily-work",
  "max_items": 100,
  "recency_days": 7
}
```

Returns immediately with job_id; sync runs in background.

### 4. `get_sync_status`
Check what data has been synced and when.

**Use case**: Decide whether to re-sync stale data.

```json
{
  "platform": "slack",
  "synced_resources": [
    {"resource_name": "#general", "last_synced": "2h ago", "items_synced": 150},
    {"resource_name": "#daily-work", "last_synced": "1d ago", "items_synced": 89}
  ]
}
```

## Agentic Behavior Guidelines

### DO (Be Proactive)

```
User: "Create a digest from my daily work channel"

TP thinks:
1. Check if Slack connected → list_integrations
2. Find "daily work" channel → list_platform_resources(slack)
3. Check if recently synced → get_sync_status(slack, C456)
4. If stale, sync it → sync_platform_resource(slack, C456)
5. Create the deliverable → create_deliverable(...)

TP says:
"I found your #daily-work channel and I'm syncing the last 7 days of messages.
Once that's ready, I'll create a weekly digest for you. This typically takes
about a minute."
```

### DON'T (Ask Permission)

```
User: "Create a digest from my daily work channel"

TP says:
"I see Slack is connected but the daily work channel isn't synced yet.
Would you like me to sync it first?"

❌ This adds friction. Just do it.
```

### Edge Cases

1. **Platform not connected**: Don't ask "should I connect?" — inform user and suggest connecting in Settings.
2. **Resource not found**: After listing resources, inform user if no match found and show available options.
3. **Sync in progress**: If sync already running, inform user and provide expected completion time.

## Implementation Notes

- Tools added to `THINKING_PARTNER_TOOLS` list
- Handlers use existing `MCPClientManager` and `import_jobs` infrastructure
- No new tables — uses existing `user_integrations`, `integration_coverage`, `integration_import_jobs`
- Sync jobs run asynchronously via existing `unified_scheduler`

## Consequences

### Positive
- **Better UX**: Users don't face friction when mentioning platforms
- **Trust building**: TP demonstrates capability by taking action
- **Consistency**: Aligns with Claude Code's agentic model

### Negative
- **Potential over-syncing**: TP might sync data user doesn't need
- **Background job awareness**: TP needs to handle async sync completion

### Mitigations
- Rate limit sync jobs per user
- Add `get_sync_status` so TP can check before re-syncing
- Sync jobs respect existing scope limits (max_items, recency_days)
