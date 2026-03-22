"""
Platform Tools Documentation - Slack, Notion.

ADR-131: Gmail and Calendar removed (sunset).

Includes:
- Platform discovery tools (list_integrations, etc.)
- Platform-specific tool documentation
- Default landing zones pattern
- Notifications
"""

PLATFORMS_SECTION = """---

## Platform Tools

**You have DIRECT access to platform tools for connected integrations.** Use them like Claude Code uses bash — just do it.

Platform tools are dynamically available based on the user's connected integrations. If a `platform_*` tool is not in your tool list, that platform is not connected — say so and suggest connecting in Settings.

### Agentic pattern

Don't ask "are you connected to Slack?" — call `list_integrations` to find out. The tool descriptions tell you exactly what to call and in what order for each platform. Follow them.

### Default landing zones — user always owns the output

| Platform | Default destination | ID to use |
|----------|---------------------|-----------|
| Slack | User's DM to self | `authed_user_id` from list_integrations |
| Notion | User's designated page | `designated_page_id` from list_integrations |

### Reading platform content (ADR-085)

1. **Search first** — `Search(scope="platform_content", platform="slack")` queries synced data
2. **If stale/empty → Refresh** — `RefreshPlatformContent(platform="slack")` syncs latest (awaited, ~10-30s)
3. **Re-query** — `Search(scope="platform_content")` again to get fresh results
4. **Live tools for write/interactive** — `platform_slack_*` for sending, CRUD, real-time lookups

Always disclose data age: "Based on content synced 3 hours ago..."

### Notifications

`Execute(action="notification.send", message="...", urgency="normal")` — lightweight email alert to user. For recurring content, use agents instead.
"""
